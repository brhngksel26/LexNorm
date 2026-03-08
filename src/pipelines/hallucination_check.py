"""Halüsinasyon kontrolü: extracted value'ların source_text'inin OCR metninde geçtiğini doğrular."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_for_contains(text: str | None) -> str:
    if text is None or not isinstance(text, str):
        return ""
    t = " ".join(str(text).split()).strip()
    return t[:2000]


def _source_text_contained_in_ocr(source_text: Any, ocr_full: str) -> bool:
    if source_text is None:
        return True
    if not isinstance(source_text, str) or not source_text.strip():
        return True
    ocr_n = _normalize_for_contains(ocr_full)
    snippet = _normalize_for_contains(source_text)
    if len(snippet) < 3:
        return True
    return snippet in ocr_n


def _walk_and_verify(obj: Any, ocr_full: str, path: str = "") -> None:
    """obj içindeki {value, source_text} yapılarında source_text OCR'da yoksa value'yu null yapar."""
    if obj is None:
        return
    if isinstance(obj, dict):
        if "value" in obj and "source_text" in obj:
            st = obj.get("source_text")
            if st is not None and isinstance(st, str) and st.strip():
                if not _source_text_contained_in_ocr(st, ocr_full):
                    if "company_name" in path or "mersis_number" in path:
                        logger.info(
                            "Validation (halüsinasyon): OCR'da bulunamadı ama filtre için korunuyor path=%s source_text_preview=%s",
                            path,
                            (st[:80] + "..." if len(st) > 80 else st),
                        )
                    else:
                        logger.info(
                            "Validation (halüsinasyon): OCR'da bulunamadı, value null yapıldı path=%s source_text_preview=%s",
                            path,
                            (st[:80] + "..." if len(st) > 80 else st),
                        )
                        obj["value"] = None
            return
        for k, v in obj.items():
            _walk_and_verify(v, ocr_full, f"{path}.{k}")
        return
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_and_verify(item, ocr_full, f"{path}[{i}]")


def verify_company_against_ocr(company: dict[str, Any], ocr_full: str) -> None:
    """
    company dict'ini yerinde (in-place) günceller: her source_text OCR metninde
    geçmiyorsa ilgili value null yapılır.
    """
    if not ocr_full or not isinstance(company, dict):
        return
    _walk_and_verify(company, ocr_full, "company")
