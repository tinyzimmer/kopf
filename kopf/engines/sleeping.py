"""
Advanced modes of sleeping.
"""
import asyncio
import collections
import contextlib
import logging
import time
from typing import Optional, Collection, Iterable, Union, Type, AsyncGenerator, Tuple

from kopf.structs import containers
from kopf.structs import primitives


async def sleep_or_wait(
        delays: Union[None, float, Collection[Union[None, float]]],
        wakeup: Optional[Union[asyncio.Event, primitives.DaemonStopper]] = None,
) -> Optional[float]:
    """
    Measure the sleep time: either until the timeout, or until the event is set.

    Returns the number of seconds left to sleep, or ``None`` if the sleep was
    not interrupted and reached its specified delay (an equivalent of ``0``).
    In theory, the result can be ``0`` if the sleep was interrupted precisely
    the last moment before timing out; this is unlikely to happen though.
    """
    passed_delays = delays if isinstance(delays, collections.abc.Collection) else [delays]
    actual_delays = [delay for delay in passed_delays if delay is not None]
    minimal_delay = min(actual_delays) if actual_delays else 0

    # Do not go for the real low-level system sleep if there is no need to sleep.
    if minimal_delay <= 0:
        return None

    awakening_event = (
        wakeup.async_event if isinstance(wakeup, primitives.DaemonStopper) else
        wakeup if wakeup is not None else
        asyncio.Event())

    loop = asyncio.get_running_loop()
    try:
        start_time = loop.time()
        await asyncio.wait_for(awakening_event.wait(), timeout=minimal_delay)
    except asyncio.TimeoutError:
        return None  # interruptable sleep is over: uninterrupted.
    else:
        end_time = loop.time()
        duration = end_time - start_time
        return max(0, minimal_delay - duration)


@contextlib.asynccontextmanager
async def throttled(
        *,
        throttler: containers.Throttler,
        delays: Iterable[float],
        wakeup: Optional[Union[asyncio.Event, primitives.DaemonStopper]] = None,
        logger: Union[logging.Logger, logging.LoggerAdapter],
        errors: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = Exception,
) -> AsyncGenerator[bool, None]:
    """
    A helper to throttle any arbitrary operation.
    """

    # The 1st sleep: if throttling is already active, but was interrupted by a queue replenishment.
    # It is needed to properly process the latest known event after the successful sleep.
    if throttler.active_until is not None:
        remaining_time = throttler.active_until - time.monotonic()
        unslept_time = await sleep_or_wait(remaining_time, wakeup=wakeup)
        if unslept_time is None:
            logger.info("Throttling is over. Switching back to normal operations.")
            throttler.active_until = None

    # Run only if throttling either is not active initially, or has just finished sleeping.
    should_run = throttler.active_until is None
    try:
        yield should_run

    except Exception as e:

        # If it is not an error-of-interest, escalate normally. BaseExceptions are escalated always.
        if not isinstance(e, errors):
            raise

        # If the code does not follow the recommendation to not run, escalate.
        if not should_run:
            raise

        # Activate throttling if not yet active, or reuse the active sequence of delays.
        if throttler.source_of_delays is None:
            throttler.source_of_delays = iter(delays)

        # Choose a delay. If there are none, avoid throttling at all.
        throttle_delay = next(throttler.source_of_delays, throttler.last_used_delay)
        if throttle_delay is not None:
            throttler.last_used_delay = throttle_delay
            throttler.active_until = time.monotonic() + throttle_delay
            logger.exception(f"Throttling for {throttle_delay} seconds due to an unexpected error:")

    else:
        # Reset the throttling. Release the iterator to keep the memory free during normal run.
        if should_run:
            throttler.source_of_delays = throttler.last_used_delay = None

    # The 2nd sleep: if throttling has been just activated (i.e. there was a fresh error).
    # It is needed to have better logging/sleeping without workers exiting for "no events".
    if throttler.active_until is not None and should_run:
        remaining_time = throttler.active_until - time.monotonic()
        unslept_time = await sleep_or_wait(remaining_time, wakeup=wakeup)
        if unslept_time is None:
            throttler.active_until = None
            logger.info("Throttling is over. Switching back to normal operations.")
