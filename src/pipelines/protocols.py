"""Protocols for extraction pipelines."""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExtractionPipelineProtocol(Protocol):
    """Interface for pipelines that run OCR + extraction on a PDF and return a result dict."""

    def run_full(self, pdf_path: Path) -> dict:
        """Run full pipeline (OCR + extraction) on the given PDF path. Returns result dict."""
        ...
