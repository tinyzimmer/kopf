import kopf

@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def instant_failure_with_only_a_message(**kwargs):
    raise kopf.PermanentError("Fail once and for all.")

@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def eventual_success_with_few_messages(retry, **kwargs):
    if retry < 3:  # 0, 1, 2, 3
        raise kopf.TemporaryError("Expected recoverable error.", delay=1.0)

@kopf.on.create('zalando.org', 'v1', 'kopfexamples', retries=3, cooldown=1.0)
def eventual_failure_with_tracebacks(**kwargs):
    raise Exception("An error that is supposed to be recoverable.")

@kopf.on.create('zalando.org', 'v1', 'kopfexamples', errors=kopf.ErrorsMode.PERMANENT, cooldown=1.0)
def instant_failure_with_traceback(**kwargs):
    raise Exception("An error that is supposed to be recoverable.")
