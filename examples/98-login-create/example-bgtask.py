import asyncio
import random

import kopf
import pykube


@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
@kopf.on.resume('zalando.org', 'v1', 'kopfexamples')
async def created(body, logger, memo, name, namespace, **kwargs):
    task = asyncio.create_task(bg(name, namespace, logger))
    memo.task = task

@kopf.on.delete('zalando.org', 'v1', 'kopfexamples')
async def deleted(memo, **kwargs):
    if hasattr(memo, 'task'):
        memo.task.cancel()
        try:
            await memo.task
        except Exception:
            pass

async def bg(name, namespace, logger):
    while True:
        try:
            logger.info("Still alive. Checking...")
            some_remote_progress = random.randint(0, 100)

            api = pykube.HTTPClient(pykube.KubeConfig.from_env())
            obj = KopfExample.objects(api, namespace=namespace).get_by_name(name)
            obj.patch({'status': {'message': f'{some_remote_progress}% done'}})

        except Exception as e:
            logger.error("Dead: %r", e)
        else:
            await asyncio.sleep(10)


class KopfExample(pykube.objects.NamespacedAPIObject):
    version = "zalando.org/v1"
    endpoint = "kopfexamples"
    kind = "KopfExample"
