"""Thread-pool batch runner — the default :class:`IBatchRunner` implementation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from pdf2md.domain.ports.ports import IBatchRunner


class ThreadPoolBatchRunner(IBatchRunner):
    """Run a callable over many items using a thread pool."""

    def run(
        self,
        items: list,
        worker: Callable[[object], object],
        *,
        workers: int,
    ) -> list:
        """Apply ``worker(item)`` to every element, returning results in order.

        Uses a thread pool to overlap file I/O. For CPU-bound workloads
        a process-pool implementation can be substituted without
        changing the use case.
        """
        if workers < 1 or len(items) <= 1:
            return [worker(item) for item in items]

        results: list = [None] * len(items)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_index = {
                pool.submit(worker, item): idx for idx, item in enumerate(items)
            }
            for fut in as_completed(future_to_index):
                idx = future_to_index[fut]
                results[idx] = fut.result()
        return results


__all__ = ["ThreadPoolBatchRunner"]
