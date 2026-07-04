"""Storage adapters."""

from md2docx.infrastructure.storage.batch_runner import ThreadPoolBatchRunner
from md2docx.infrastructure.storage.file_storage import FileStorage

__all__ = ["FileStorage", "ThreadPoolBatchRunner"]
