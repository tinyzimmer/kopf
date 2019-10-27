import ast
import collections
import re
import subprocess
import time
from typing import Optional, Dict, Any, Sequence

import pytest

from kopf.testing import KopfRunner


def test_all_examples_are_runnable(mocker, settings, with_crd, exampledir, caplog):

    # If the example has its own opinion on the timing, try to respect it.
    # See e.g. /examples/99-all-at-once/example.py.
    example_py = exampledir / 'example.py'
    e2e = E2EModes(str(example_py))

    # Skip the e2e test if the framework-optional but test-required library is missing.
    if e2e.imports_kubernetes:
        pytest.importorskip('kubernetes')

    # To prevent lengthy sleeps on the simulated retries.
    mocker.patch('kopf.reactor.handling.DEFAULT_RETRY_DELAY', 1)

    # To prevent lengthy threads in the loop executor when the process exits.
    settings.watching.server_timeout = 10

    # Run an operator and simulate some activity with the operated resource.
    with KopfRunner(['run', '--standalone', '--verbose', str(example_py)], timeout=60) as runner:

        # Give it some time to start.
        _sleep_till_stopword(caplog=caplog,
                             delay=e2e.startup_time_limit,
                             patterns=e2e.startup_stop_words or ['Client is configured'])

        # Trigger the reaction. Give it some time to react and to sleep and to retry.
        subprocess.run("kubectl apply -f examples/obj.yaml",
                       shell=True, check=True, timeout=10, capture_output=True)
        _sleep_till_stopword(caplog=caplog,
                             delay=e2e.creation_time_limit,
                             patterns=e2e.creation_stop_words)

        # Trigger the reaction. Give it some time to react.
        subprocess.run("kubectl delete -f examples/obj.yaml",
                       shell=True, check=True, timeout=10, capture_output=True)
        _sleep_till_stopword(caplog=caplog,
                             delay=e2e.deletion_time_limit,
                             patterns=e2e.deletion_stop_words)

    # Give it some time to finish.
    _sleep_till_stopword(caplog=caplog,
                         delay=e2e.cleanup_time_limit,
                         patterns=e2e.cleanup_stop_words or ['Hung tasks', 'Root tasks'])

    # Verify that the operator did not die on start, or during the operation.
    assert runner.exception is None
    assert runner.exit_code == 0

    # There are usually more than these messages, but we only check for the certain ones.
    # This just shows us that the operator is doing something, it is alive.
    if e2e.has_mandatory_on_delete:
        assert '[default/kopf-example-1] Adding the finalizer' in runner.stdout
    if e2e.has_on_create:
        assert '[default/kopf-example-1] Creation event:' in runner.stdout
    if e2e.has_mandatory_on_delete:
        assert '[default/kopf-example-1] Deletion event:' in runner.stdout
    if e2e.has_resource_changing_handlers:
        assert '[default/kopf-example-1] Deleted, really deleted' in runner.stdout
    if not e2e.tracebacks:
        assert 'Traceback (most recent call last):' not in runner.stdout

    # Verify that once a handler succeeds, it is never re-executed again.
    handler_names = re.findall(r"'(.+?)' succeeded", runner.stdout)
    if e2e.success_counts is not None:
        checked_names = [name for name in handler_names if name in e2e.success_counts]
        name_counts = collections.Counter(checked_names)
        assert name_counts == e2e.success_counts
    else:
        name_counts = collections.Counter(handler_names)
        assert set(name_counts.values()) == {1}

    # Verify that once a handler fails, it is never re-executed again.
    handler_names = re.findall(r"'(.+?)' failed (?:permanently|with an exception. Will stop.)", runner.stdout)
    if e2e.failure_counts is not None:
        checked_names = [name for name in handler_names if name in e2e.failure_counts]
        name_counts = collections.Counter(checked_names)
        assert name_counts == e2e.failure_counts
    else:
        name_counts = collections.Counter(handler_names)
        assert not name_counts


def _sleep_till_stopword(
        caplog,
        delay: Optional[float] = None,
        patterns: Optional[Sequence[str]] = None,
        *,
        interval: Optional[float] = None,
) -> bool:
    patterns = list(patterns or [])
    delay = delay or (10.0 if patterns else 1.0)
    interval = interval or min(1.0, max(0.1, delay / 10.))
    started = time.perf_counter()
    found = False
    while not found and time.perf_counter() - started < delay:
        for message in list(caplog.messages):
            if any(re.search(pattern, message) for pattern in patterns or []):
                found = True
                break
        else:
            time.sleep(interval)
    return found


class E2EModes:
    modes: Dict[str, Any]

    def __init__(self, path: str) -> None:
        super().__init__()
        self.modes = {}

        with open(path, 'rt', encoding='utf-8') as f:
            self.path = path
            self.text = f.read()
            self.tree = ast.parse(self.text, path)

        for n in self.tree.body:
            if isinstance(n, ast.Assign):  # module-level assignment
                for target in n.targets:
                    if isinstance(target, ast.Name):  # variable, not a slice
                        if target.id.startswith('E2E_'):
                            key = target.id[len('E2E_'):].lower()
                            val = ast.literal_eval(n.value)
                            self.modes[key] = val

    @property
    def startup_time_limit(self) -> Optional[float]:
        return self.modes.get('E2E_STARTUP_TIME_LIMIT')

    @property
    def startup_stop_words(self) -> Optional[Sequence[str]]:
        return self.modes.get('E2E_STARTUP_STOP_WORDS')

    @property
    def cleanup_time_limit(self) -> Optional[float]:
        return self.modes.get('E2E_CLEANUP_TIME_LIMIT')

    @property
    def cleanup_stop_words(self) -> Optional[Sequence[str]]:
        return self.modes.get('E2E_CLEANUP_STOP_WORDS')

    @property
    def creation_time_limit(self) -> Optional[float]:
        return self.modes.get('E2E_CREATION_TIME_LIMIT')

    @property
    def creation_stop_words(self) -> Optional[Sequence[str]]:
        return self.modes.get('E2E_CREATION_STOP_WORDS')

    @property
    def deletion_time_limit(self) -> Optional[float]:
        return self.modes.get('E2E_DELETION_TIME_LIMIT')

    @property
    def deletion_stop_words(self) -> Optional[Sequence[str]]:
        return self.modes.get('E2E_DELETION_STOP_WORDS')

    @property
    def tracebacks(self) -> Optional[bool]:
        return self.modes.get('E2E_TRACEBACKS')

    @property
    def success_counts(self) -> Optional[Dict[str, int]]:
        return self.modes.get('E2E_SUCCESS_COUNTS')

    @property
    def failure_counts(self) -> Optional[Dict[str, int]]:
        return self.modes.get('E2E_FAILURE_COUNTS')

    @property
    def imports_kubernetes(self) -> bool:
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for name in node.names:
                    name = name.name if isinstance(name, ast.alias) else name
                    if name == 'kubernetes' or name.startswith('kubernetes.'):
                        return True
        return False

    def has_handler(self, name):
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and
                        isinstance(decorator.func, ast.Attribute) and
                        isinstance(decorator.func.value, ast.Attribute) and
                        isinstance(decorator.func.value.value, ast.Name) and
                        decorator.func.value.value.id == 'kopf' and
                        decorator.func.value.attr == 'on' and
                        decorator.func.attr == name
                    ):
                        return True
        return False

    @property
    def has_on_create(self) -> bool:
        return self.has_handler('create')

    @property
    def has_on_update(self) -> bool:
        return self.has_handler('update')

    @property
    def has_on_delete(self) -> bool:
        return self.has_handler('delete')

    @property
    def has_resource_changing_handlers(self) -> bool:
        return self.has_on_create or self.has_on_update or self.has_on_delete

    @property
    def has_mandatory_on_delete(self) -> bool:
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and
                        isinstance(decorator.func, ast.Attribute) and
                        isinstance(decorator.func.value, ast.Attribute) and
                        isinstance(decorator.func.value.value, ast.Name) and
                        decorator.func.value.value.id == 'kopf' and
                        decorator.func.value.attr == 'on' and
                        decorator.func.attr == 'delete' and
                        all([
                            not ast.literal_eval(keyword.value)
                            for keyword in decorator.keywords
                            if keyword == 'optional'
                        ])
                    ):
                        return True
        return False
