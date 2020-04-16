"""
Keeping track of what resources (custom and builtin) are available.
"""
import asyncio
import fnmatch
import functools
import itertools
import logging
from typing import Tuple, Union, Collection, MutableMapping, NamedTuple, TYPE_CHECKING, Optional, Set

from kopf.clients import fetching
from kopf.reactor import queueing
from kopf.reactor import registries
from kopf.structs import bodies
from kopf.structs import configuration
from kopf.structs import primitives
from kopf.structs import resources

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    asyncio_Task = asyncio.Task[None]
else:
    asyncio_Task = asyncio.Task


class Dimensions(NamedTuple):
    namespaces: Set[str]
    resources: Set[resources.Resource]


DimensionKey = Tuple[str, resources.Resource]
Watchers = MutableMapping[DimensionKey, asyncio_Task]


async def discovery(
        namespaces: Collection[Union[None, str]],
        processor: queueing.WatchStreamProcessor,
        registry: registries.OperatorRegistry,
        settings: configuration.OperatorSettings,  # TODO
        freeze_mode: Optional[primitives.Toggle] = None,
) -> None:
    """
    An ever-running root task to monitor the dimensions (resources, namespaces).

    Custom resources can be added and removed while the operator is running.
    With globs in the resource definitions, we need to keep track of which
    actual resources kinds are available, so that proper URLs can be used
    to watch and patch the resources.
    """

    dimensions = Dimensions(
        namespaces=set(),
        resources=set(),
    )
    watchers: Watchers = {}
    dimensions_watchers: Set[asyncio_Task] = set()

    if None in namespaces:
        dimensions.namespaces.add(None)

    # If some dimensions are known in advance, or there is no discovery at all, spawn them now.
    if dimensions.namespaces and dimensions.resources:
        await adjust_watchers(
            dimensions=dimensions,
            watchers=watchers,
            processor=processor,
            settings=settings,
            freeze_mode=freeze_mode,
        )

    # TODO: not None, but a WHOLE_CLUSTER marker.
    # TODO: better: if there are globs (not just strict names).
    if None not in dimensions.namespaces:
        dimensions_watchers.add(asyncio.create_task(queueing.watcher(
            freeze_mode=freeze_mode,
            settings=settings,
            resource=resources.Resource('', 'v1', 'namespaces'),
            namespace=None,
            processor=functools.partial(discover_namespace,
                                        processor=processor,
                                        settings=settings,
                                        namespaces=namespaces,
                                        dimensions=dimensions,
                                        watchers=watchers),
        )))

    # Top-level watchers over the discovery space (one watcher for each dimension).
    # They spawn or stop the actual resource watchers inside of those dimensions.
    # TODO: FIXME: resources must be LISTed differently. Not only CRDs, but via APIversions! (scan_resources()).
    #                       async for resource in fetching.scan_resources():
    dimensions_watchers.add(asyncio.create_task(queueing.watcher(
        freeze_mode=freeze_mode,
        settings=settings,
        resource=fetching.CRD_CRD,
        namespace=None,
        processor=functools.partial(discover_resource,
                                    processor=processor,
                                    registry=registry,
                                    settings=settings,
                                    dimensions=dimensions,
                                    watchers=watchers),
    )))

    try:
        await asyncio.wait(dimensions_watchers)
    except asyncio.CancelledError:
        # TODO: cancel all the meta- & task-watchers, and wait for them.
        all_watchers = frozenset(dimensions_watchers) | frozenset(watchers.values())
        for watcher_task in all_watchers:
            watcher_task.cancel()

        await asyncio.wait(all_watchers, return_when=asyncio.ALL_COMPLETED)
        # TODO: reraise? from inside, just in case. except CancelledError!

        raise


async def discover_namespace(
        *,
        dimensions: Dimensions,
        watchers: Watchers,
        raw_event: bodies.RawEvent,
        replenished: asyncio.Event,
        processor: queueing.WatchStreamProcessor,
        namespaces: Set[str],
        settings: configuration.OperatorSettings,  # TODO
        freeze_mode: Optional[primitives.Toggle] = None,
) -> None:
    namespace: str = raw_event['object']['metadata']['name']

    # Silently ignore all resources not matching our handlers.
    # TODO: cluster-flag should go on its own, not in namespaces. for simpler typing?
    cluster = None in namespaces
    matches = cluster or any(fnmatch.fnmatch(namespace, pattern) for pattern in namespaces)

    if raw_event['type'] == 'DELETED':  # TODO: or marked for deletion?
        if namespace in dimensions.namespaces:
            dimensions.namespaces.remove(namespace)
    else:
        if namespace not in dimensions.namespaces and matches:
            dimensions.namespaces.add(namespace)

    await adjust_watchers(
        dimensions=dimensions,
        watchers=watchers,
        processor=processor,
        settings=settings,
        freeze_mode=freeze_mode,
    )


async def discover_resource(
        *,
        dimensions: Dimensions,
        watchers: Watchers,
        raw_event: bodies.RawEvent,
        replenished: asyncio.Event,
        processor: queueing.WatchStreamProcessor,
        registry: registries.OperatorRegistry,
        settings: configuration.OperatorSettings,  # TODO
        freeze_mode: Optional[primitives.Toggle] = None,
) -> None:
    resource = resources.Resource(
        raw_event['object']['spec']['group'],
        raw_event['object']['spec']['versions'][0]['name'],  # TODO: all of the versions!
        raw_event['object']['spec']['names']['plural'],
    )

    # Silently ignore all resources not matching any single resource glob of registered handlers.
    if not registry.has_handlers(resource=resource):
        return

    if raw_event['type'] == 'DELETED':  # TODO: or marked for deletion?
        if resource in dimensions.resources:
            dimensions.resources.remove(resource)
    else:
        if resource not in dimensions.resources:
            dimensions.resources.add(resource)

    await adjust_watchers(
        dimensions=dimensions,
        watchers=watchers,
        processor=processor,
        settings=settings,
        freeze_mode=freeze_mode,
    )


async def adjust_watchers(
        *,
        dimensions: Dimensions,
        watchers: Watchers,
        processor: queueing.WatchStreamProcessor,
        settings: configuration.OperatorSettings,  # TODO
        freeze_mode: Optional[primitives.Toggle] = None,
) -> None:
    key: DimensionKey

    # Start the watchers for newly appeared dimensions.
    for namespace, resource in itertools.product(dimensions.namespaces, dimensions.resources):
        key = (namespace, resource)
        if key not in watchers:
            watchers[key] = asyncio.create_task(queueing.watcher(
                settings=settings,
                resource=resource,
                namespace=namespace,
                processor=functools.partial(processor, resource=resource),
                freeze_mode=freeze_mode,
            ))

    # Stop the watchers for disappeared dimensions.
    for key in list(watchers.keys()):
        namespace, resource = key
        if namespace not in dimensions.namespaces or resource not in dimensions.resources:
            watchers[key].cancel()
            await asyncio.wait({watchers[key]}, return_when=asyncio.ALL_COMPLETED)
            del watchers[key]
            # TODO: reraise? from inside, just in case. except CancelledError!
