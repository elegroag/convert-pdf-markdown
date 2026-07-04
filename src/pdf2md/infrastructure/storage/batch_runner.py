"""Thread- and process-pool batch runners."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
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
        """Apply ``worker(item)`` to every element, returning results in order."""
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


class ProcessPoolBatchRunner(IBatchRunner):
    """Run a callable over many items using a process pool."""

    def run(
        self,
        items: list,
        worker: Callable[[object], object],
        *,
        workers: int,
    ) -> list:
        """Apply ``worker(item)`` with processes for CPU-bound PDF work."""
        if workers < 1 or len(items) <= 1:
            return [worker(item) for item in items]

        results: list = [None] * len(items)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            future_to_index = {
                pool.submit(worker, item): idx for idx, item in enumerate(items)
            }
            for fut in as_completed(future_to_index):
                idx = future_to_index[fut]
                results[idx] = fut.result()
        return results


__all__ = ["ProcessPoolBatchRunner", "ThreadPoolBatchRunner"]
