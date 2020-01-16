import pytest

from kopf import ActivityRegistry
from kopf import ResourceWatchingRegistry, ResourceChangingRegistry
from kopf import OperatorRegistry
from kopf import SimpleRegistry, GlobalRegistry  # deprecated, but tested
from kopf.reactor.causation import ResourceChangingCause


@pytest.fixture(params=[
    pytest.param(ActivityRegistry, id='activity-registry'),
    pytest.param(ResourceWatchingRegistry, id='resource-watching-registry'),
    pytest.param(ResourceChangingRegistry, id='resource-changing-registry'),
    pytest.param(SimpleRegistry, id='simple-registry'),  # deprecated
])
def generic_registry_cls(request):
    return request.param


@pytest.fixture(params=[
    pytest.param(ActivityRegistry, id='activity-registry'),
])
def activity_registry_cls(request):
    return request.param


@pytest.fixture(params=[
    pytest.param(ResourceWatchingRegistry, id='resource-watching-registry'),
    pytest.param(ResourceChangingRegistry, id='resource-changing-registry'),
    pytest.param(SimpleRegistry, id='simple-registry'),  # deprecated
])
def resource_registry_cls(request):
    return request.param


@pytest.fixture(params=[
    pytest.param(OperatorRegistry, id='operator-registry'),
    pytest.param(GlobalRegistry, id='global-registry'),  # deprecated
])
def operator_registry_cls(request):
    return request.param


@pytest.fixture(params=[
    # pytest.param(None, id='without-diff'),
    pytest.param([], id='with-empty-diff'),
])
def cause_no_diff(request, resource):
    body = {'metadata': {'labels': {'somelabel': 'somevalue'}, 'annotations': {'someannotation': 'somevalue'}}}
    # TODO: test against other causes, not only ResourceChangingCause
    return ResourceChangingCause(
        resource=resource,
        initial=False,
        logger=None,
        reason='some-reason',
        patch={},
        memo=None,
        body=body,
        diff=request.param,
        old=None,
        new=None,
    )


@pytest.fixture(params=[
    pytest.param([('op', ('some-field',), 'old', 'new')], id='with-field-diff'),
])
def cause_with_diff(resource):
    body = {'metadata': {'labels': {'somelabel': 'somevalue'}, 'annotations': {'someannotation': 'somevalue'}}}
    diff = [('op', ('some-field',), 'old', 'new')]
    return ResourceChangingCause(
        resource=resource,
        initial=False,
        logger=None,
        reason='some-reason',
        patch={},
        memo=None,
        body=body,
        diff=diff,
        old=None,
        new=None,
    )


@pytest.fixture(params=[
    # pytest.param(None, id='without-diff'),
    pytest.param([], id='with-empty-diff'),
    pytest.param([('op', ('some-field',), 'old', 'new')], id='with-field-diff'),
])
def cause_any_diff(resource, request):
    body = {'metadata': {'labels': {'somelabel': 'somevalue'}, 'annotations': {'someannotation': 'somevalue'}}}
    return ResourceChangingCause(
        resource=resource,
        initial=False,
        logger=None,
        reason='some-reason',
        patch={},
        memo=None,
        body=body,
        diff=request.param,
        old=None,
        new=None,
    )
