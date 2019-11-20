import random

import kopf
import pykube


@kopf.on.timer('zalando.org', 'v1', 'kopfexamples', interval=10)
async def check_it(logger, patch, **kwargs):
    logger.info("Checking...")
    some_remote_progress = random.randint(0, 100)
    patch.setdefault('status', {})['message'] = f'{some_remote_progress}%'


class KopfExample(pykube.objects.NamespacedAPIObject):
    version = "zalando.org/v1"
    endpoint = "kopfexamples"
    kind = "KopfExample"
