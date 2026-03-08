"""Target scan use case: multi-PDF parallel extraction, filter, consolidation."""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from fastapi import UploadFile

logger = logging.getLogger(__name__)

from src.consolidation import ConsolidationService
from src.pipelines.factory import create_extraction_pipeline
from src.pipelines.protocols import ExtractionPipelineProtocol
from src.pipelines.target_company_filter import filter_by_target_company


@runtime_checkable
class TargetScanProtocol(Protocol):
    def validate(
        self,
        documents: list[UploadFile],
        announcement_types: str,
        target_name: str | None,
        target_mersis: str | None,
    ) -> list[str]: ...

    async def run(
        self,
        documents: list[UploadFile],
        announcement_types: str,
        target_name: str | None,
        target_mersis: str | None,
    ) -> dict[str, Any]:
        """Run target scan; returns document_names and consolidated tables. Raises *Error on failure."""
        ...


class TargetScanValidationError(Exception):
    """Validation hatası (announcement_types, PDF, target)."""

    def __init__(self, detail: str) -> None:
        self.detail = detail


class TargetScanNoExtractionsError(Exception):
    """Hiç extraction üretilemedi veya hedef şirket eşleşmedi."""

    def __init__(self, detail: str) -> None:
        self.detail = detail


class TargetScanService(TargetScanProtocol):
    """Orchestrates: validate → temp files → parallel pipeline → filter → consolidation."""

    def __init__(self, max_concurrent: int = 4) -> None:
        self._max_concurrent = max_concurrent

    def validate(
        self,
        documents: list[UploadFile],
        announcement_types: str,
        target_name: str | None,
        target_mersis: str | None,
    ) -> list[str]:
        """Parse announcement_types and validate; raise TargetScanValidationError on error. Returns types list."""
        if not target_name and not target_mersis:
            raise TargetScanValidationError(
                "target_company_name veya target_mersis gerekli"
            )
        if not documents:
            raise TargetScanValidationError("En az bir PDF gerekli")

        types_list: list[str]
        try:
            parsed = json.loads(announcement_types)
            if isinstance(parsed, list):
                types_list = [str(x).strip() for x in parsed]
            else:
                raise TargetScanValidationError(
                    "announcement_types geçerli bir JSON array olmalı"
                )
        except (json.JSONDecodeError, TypeError):
            raw = (announcement_types or "").strip()
            if not raw:
                raise TargetScanValidationError(
                    "announcement_types geçerli bir JSON array olmalı"
                )
            types_list = [s.strip() for s in raw.split(",") if s.strip()]

        if len(types_list) != len(documents):
            raise TargetScanValidationError(
                "announcement_types, documents ile aynı uzunlukta bir liste olmalı"
            )

        for f in documents:
            if not f.filename or not f.filename.lower().endswith(".pdf"):
                raise TargetScanValidationError("Tüm dosyalar PDF olmalı")

        return types_list

    async def run(
        self,
        documents: list[UploadFile],
        announcement_types: str,
        target_name: str | None,
        target_mersis: str | None,
    ) -> dict[str, Any]:
        types_list = self.validate(
            documents, announcement_types, target_name, target_mersis
        )

        logger.info(
            "target_scan run started: target_name=%r target_mersis=%r ndocs=%s types=%s",
            target_name,
            target_mersis,
            len(documents),
            types_list,
        )

        temp_paths: list[Path] = []
        try:
            for i, upload in enumerate(documents):
                content = await upload.read()
                suffix = Path(upload.filename or "doc.pdf").suffix or ".pdf"
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix, prefix=f"target_scan_{i}_"
                )
                tmp.write(content)
                tmp.close()
                temp_paths.append(Path(tmp.name))

            semaphore = asyncio.Semaphore(self._max_concurrent)

            async def run_one(path: Path, ann_type: str, doc_name: str):
                async with semaphore:
                    pipeline: ExtractionPipelineProtocol = create_extraction_pipeline(
                        ann_type,
                        target_company_name=target_name,
                        target_mersis=target_mersis,
                    )
                    return await asyncio.to_thread(pipeline.run_full, path), doc_name

            tasks = [
                run_one(
                    temp_paths[i],
                    types_list[i],
                    documents[i].filename or f"doc_{i}.pdf",
                )
                for i in range(len(documents))
            ]
            results_with_names = await asyncio.gather(*tasks, return_exceptions=True)

            extractions: list[dict[str, Any]] = []
            n_exceptions = 0
            n_pipeline_errors = 0
            n_filtered_out = 0

            for idx, item in enumerate(results_with_names):
                doc_name = (
                    documents[idx].filename
                    if idx < len(documents)
                    else f"doc_{idx}.pdf"
                )
                if isinstance(item, BaseException):
                    n_exceptions += 1
                    logger.warning(
                        "target_scan document failed with exception: doc=%s error=%s",
                        doc_name,
                        item,
                        exc_info=False,
                    )
                    continue
                result, doc_name = item
                if "error" in result and len(result) == 2:
                    n_pipeline_errors += 1
                    logger.warning(
                        "target_scan pipeline returned error: doc=%s error=%s",
                        doc_name,
                        result.get("error", "?"),
                    )
                    continue
                filtered = filter_by_target_company(
                    result,
                    target_company_name=target_name,
                    target_mersis=target_mersis,
                )
                companies = filtered.get("companies") or []
                raw_companies = result.get("companies") or []
                if not companies:
                    n_filtered_out += 1
                    logger.info(
                        "target_scan no match for target: doc=%s raw_companies_count=%s filter_warning=%s",
                        doc_name,
                        len(raw_companies),
                        filtered.get("filter_warning", "-"),
                    )
                    if raw_companies and logger.isEnabledFor(logging.DEBUG):
                        for c in raw_companies[:3]:
                            ci = (c or {}).get("company_information") or {}
                            name = (ci.get("company_name") or {}).get("value")
                            mersis = (ci.get("mersis_number") or {}).get("value")
                            logger.debug("  company: name=%r mersis=%r", name, mersis)
                    continue
                belge_metin = (
                    result.get("_belge_metin") or result.get("_ocr_preview") or ""
                )
                extractions.append(
                    {
                        "document_name": doc_name,
                        "result": {"companies": companies, "_belge_metin": belge_metin},
                    }
                )

            if not extractions:
                if n_exceptions == len(documents):
                    detail = "Tüm dökümanlarda extraction hatası (exception)."
                elif n_pipeline_errors == len(documents):
                    detail = "Tüm dökümanlarda pipeline hatası (OCR/LLM)."
                elif n_filtered_out == len(documents):
                    detail = "Tüm extraction'lar tamamlandı ancak hedef şirket hiçbirinde eşleşmedi."
                else:
                    detail = (
                        f"n_exceptions={n_exceptions} n_pipeline_errors={n_pipeline_errors} "
                        f"n_filtered_out={n_filtered_out} ndocs={len(documents)}."
                    )
                logger.warning(
                    "target_scan no extractions: target_name=%r target_mersis=%r n_exceptions=%s "
                    "n_pipeline_errors=%s n_filtered_out=%s ndocs=%s reason=%s",
                    target_name,
                    target_mersis,
                    n_exceptions,
                    n_pipeline_errors,
                    n_filtered_out,
                    len(documents),
                    detail,
                )
                raise TargetScanNoExtractionsError(
                    f"Hedef şirkete ait extraction bulunamadı: {detail}"
                )

            consolidation = ConsolidationService(extractions)
            document_names = [
                f.filename or f"doc_{i}.pdf" for i, f in enumerate(documents)
            ]
            belge_bazli_metinler = [
                {
                    "document_name": e["document_name"],
                    "metin": (e.get("result") or {}).get("_belge_metin") or "",
                }
                for e in extractions
            ]
            return {
                "document_names": document_names,
                "guncel_sirket_bilgileri": consolidation.company_info_table(),
                "yonetim_kurulu_uyeleri": consolidation.board_members_table(),
                "konsolide_esas_sozlesme": consolidation.consolidated_articles(),
                "belge_bazli_metinler": belge_bazli_metinler,
            }
        finally:
            for p in temp_paths:
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
