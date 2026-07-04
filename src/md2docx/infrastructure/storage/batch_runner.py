"""Thread-pool batch runner."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from md2docx.domain.ports.ports import IBatchRunner


class ThreadPoolBatchRunner(IBatchRunner):
    """Run a callable over many items using a thread pool."""

    def run(
        self,
        items: list[object],
        worker: Callable[[object], object],
        *,
        workers: int,
    ) -> list[object]:
        """Apply worker(item) to every element, returning results in order."""
        if workers < 1 or len(items) <= 1:
            return [worker(item) for item in items]

        results: list[object] = [None] * len(items)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_index = {
                pool.submit(worker, item): idx for idx, item in enumerate(items)
            }
            for fut in as_completed(future_to_index):
                idx = future_to_index[fut]
                results[idx] = fut.result()
        return results


__all__ = ["ThreadPoolBatchRunner"]
