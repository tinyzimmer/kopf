"""
The routines to manipulate the handler progression over the event cycle.

Used to track which handlers are finished, which are not yet,
and how many retries were there.

There could be more than one low-level k8s watch-events per one actual
high-level kopf-event (a cause). The handlers are called at different times,
and the overall handling routine should persist the handler status somewhere.

The structure is this::

    metainfo: ...
    spec: ...
    status: ...
        kopf:
            digest: 7f7ab91d809223e52d7e1939dfc5f411
            progress:
                handler1:
                    started: 2018-12-31T23:59:59,999999
                    stopped: 2018-01-01T12:34:56,789000
                    success: true
                handler2:
                    started: 2018-12-31T23:59:59,999999
                    stopped: 2018-01-01T12:34:56,789000
                    failure: true
                    message: "Error message."
                handler3:
                    started: 2018-12-31T23:59:59,999999
                    retries: 30
                handler3/sub1:
                    started: 2018-12-31T23:59:59,999999
                    delayed: 2018-01-01T12:34:56,789000
                    retries: 10
                    message: "Not ready yet."
                handler3/sub2:
                    started: 2018-12-31T23:59:59,999999

* `status.kopf.digest` is a hash of the last handled or currently being handled
  state of the object -- to detect if a new change was introduced (read below).
* `status.kopf.success` are the handlers that succeeded (no re-execution).
* `status.kopf.failure` are the handlers that failed completely (no retries).
* `status.kopf.delayed` are the timestamps, until which these handlers sleep.
* `status.kopf.retries` are number of retries for succeeded, failed,
  and for the progressing handlers.

After the full event cycle is executed (possibly including multiple re-runs),
the `status.kopf` section is persisted and can be used in the resource fields
or can be investigated manually. Only the last handling cycle is persisted.

For simplicity, the digest can be considered as an "identifier" (a "version")
of the object's state being handled, whose progress is currently stored
in `status.kopf.progress`: if the object changes during the handling,
a new event cycle begins, and the existing progress must be ignored
(it belongs to the previous state of the object).
"""

import datetime


def is_started(*, body, handler):
    progress = body.get('status', {}).get('kopf', {}).get('progress', {})
    return handler.id in progress


def is_sleeping(*, body, handler):
    ts = get_awake_time(body=body, handler=handler)
    finished = is_finished(body=body, handler=handler)
    return not finished and ts is not None and ts > datetime.datetime.utcnow()


def is_awakened(*, body, handler):
    finished = is_finished(body=body, handler=handler)
    sleeping = is_sleeping(body=body, handler=handler)
    return not finished and not sleeping


def is_finished(*, body, handler):
    progress = body.get('status', {}).get('kopf', {}).get('progress', {})
    success = progress.get(handler.id, {}).get('success', None)
    failure = progress.get(handler.id, {}).get('failure', None)
    return success or failure


def get_start_time(*, body, patch, handler):
    progress = patch.get('status', {}).get('kopf', {}).get('progress', {})
    new_value = progress.get(handler.id, {}).get('started', None)
    progress = body.get('status', {}).get('kopf', {}).get('progress', {})
    old_value = progress.get(handler.id, {}).get('started', None)
    value = new_value or old_value
    return None if value is None else datetime.datetime.fromisoformat(value)


def get_awake_time(*, body, handler):
    progress = body.get('status', {}).get('kopf', {}).get('progress', {})
    value = progress.get(handler.id, {}).get('delayed', None)
    return None if value is None else datetime.datetime.fromisoformat(value)


def get_retry_count(*, body, handler):
    progress = body.get('status', {}).get('kopf', {}).get('progress', {})
    return progress.get(handler.id, {}).get('retries', 0)


def set_start_time(*, body, patch, handler):
    progress = patch.setdefault('status', {}).setdefault('kopf', {}).setdefault('progress', {})
    progress.setdefault(handler.id, {}).update({
        'started': datetime.datetime.utcnow().isoformat(),
    })


def set_awake_time(*, body, patch, handler, delay=None):
    if delay is not None:
        ts = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay)
        ts = ts.isoformat()
    else:
        ts = None
    progress = patch.setdefault('status', {}).setdefault('kopf', {}).setdefault('progress', {})
    progress.setdefault(handler.id, {}).update({
        'delayed': ts,
    })


def set_retry_time(*, body, patch, handler, delay=None):
    retry = get_retry_count(body=body, handler=handler)
    progress = patch.setdefault('status', {}).setdefault('kopf', {}).setdefault('progress', {})
    progress.setdefault(handler.id, {}).update({
        'retries': retry + 1,
    })
    set_awake_time(body=body, patch=patch, handler=handler, delay=delay)


def store_failure(*, body, patch, handler, exc):
    retry = get_retry_count(body=body, handler=handler)
    progress = patch.setdefault('status', {}).setdefault('kopf', {}).setdefault('progress', {})
    progress.setdefault(handler.id, {}).update({
        'stopped': datetime.datetime.utcnow().isoformat(),
        'failure': True,
        'retries': retry + 1,
        'message': f'{exc}',
    })


def store_success(*, body, patch, handler, result=None):
    retry = get_retry_count(body=body, handler=handler)
    progress = patch.setdefault('status', {}).setdefault('kopf', {}).setdefault('progress', {})
    progress.setdefault(handler.id, {}).update({
        'stopped': datetime.datetime.utcnow().isoformat(),
        'success': True,
        'retries': retry + 1,
        'message': None,
    })
    if result is not None:
        # TODO: merge recursively (patch-merge), do not overwrite the keys if they are present.
        patch.setdefault('status', {}).setdefault(handler.id, {}).update(result)


def get_stored_digest(*, body):
    return body.setdefault('status', {}).setdefault('kopf', {}).get('digest', None)


def set_stored_digest(*, body, patch, digest):
    patch.setdefault('status', {}).setdefault('kopf', {})['digest'] = digest


def purge_progress(*, body, patch, digest=None):
    patch.setdefault('status', {}).setdefault('kopf', {})['progress'] = None
    patch.setdefault('status', {}).setdefault('kopf', {})['digest'] = digest

