"""Optional FastAPI surface — kept minimal for future extension."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from pdf2md.application.dto.dtos import ConversionRequest
from pdf2md.config.service_factory import build_default_service

app = FastAPI(
    title="pdf2md API",
    version="0.1.0",
    description="Convert PDFs to Markdown over HTTP.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return service liveness."""
    return {"status": "ok"}


@app.post("/convert")
def convert(request: ConversionRequest) -> dict:
    """Convert a PDF synchronously.

    The request must include a PDF path that the server can read.
    """
    if not Path(request.pdf_path).is_file():
        raise HTTPException(status_code=404, detail="pdf not found")
    service = build_default_service(
        output_dir=request.output_dir, config=request.config
    )
    result = service.convert(request)
    if result.status != "success":
        raise HTTPException(
            status_code=500,
            detail={
                "error": result.error,
                "message": result.error_message,
            },
        )
    return {
        "output_path": str(result.output_path),
        "image_count": result.image_count,
        "table_count": result.table_count,
        "page_count": result.page_count,
        "elapsed_seconds": result.elapsed_seconds,
    }


__all__ = ["app"]
