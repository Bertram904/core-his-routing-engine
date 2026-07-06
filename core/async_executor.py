"""Async utilities for offloading blocking I/O from the event loop."""

import asyncio
from collections.abc import Callable
from typing import TypeVar

ReturnT = TypeVar("ReturnT")


async def run_blocking_io(operation: Callable[[], ReturnT]) -> ReturnT:
    """Execute a blocking callable in the default thread-pool executor.

    Args:
        operation: Synchronous function performing blocking I/O or CPU work.

    Returns:
        Result returned by ``operation``.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, operation)
