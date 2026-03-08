"""Celery task for target_scan (long-running multi-PDF extraction + consolidation)."""

import asyncio
import io
import json
import logging
import shutil
from pathlib import Path

from starlette.datastructures import UploadFile

from src.core.celery_app import celery_app
from src.core.database import worker_async_session_maker
from src.cruds.scan_result import ScanResultCrud
from src.services.target_scan_service import (
    TargetScanNoExtractionsError,
    TargetScanService,
    TargetScanValidationError,
)

logger = logging.getLogger(__name__)


async def _run_target_scan_async(task_dir: Path, meta: dict) -> int:
    """Run target scan from saved files; create ScanResult; return scan_result_id."""
    document_names: list[str] = meta["document_names"]
    announcement_types: str = meta["announcement_types"]
    target_name: str | None = meta.get("target_name")
    target_mersis: str | None = meta.get("target_mersis")
    user_id: int = meta["user_id"]

    uploads: list[UploadFile] = []
    for i in range(len(document_names)):
        path = task_dir / f"doc_{i}.pdf"
        if not path.exists():
            raise FileNotFoundError(f"Expected file not found: {path}")
        content = path.read_bytes()
        name = document_names[i] if i < len(document_names) else f"doc_{i}.pdf"
        uploads.append(UploadFile(filename=name, file=io.BytesIO(content)))

    service = TargetScanService(max_concurrent=1)
    result = await service.run(
        documents=uploads,
        announcement_types=announcement_types,
        target_name=target_name,
        target_mersis=target_mersis,
    )

    # document_name column is String(512); store comma-separated names, truncate if needed
    document_name_str = ", ".join(result["document_names"])[:512]

    async with worker_async_session_maker() as session:
        row = await ScanResultCrud().create(
            session,
            data={
                "document_name": document_name_str,
                "user_id": user_id,
                "result": {
                    "guncel_sirket_bilgileri": result["guncel_sirket_bilgileri"],
                    "yonetim_kurulu_uyeleri": result["yonetim_kurulu_uyeleri"],
                    "konsolide_esas_sozlesme": result["konsolide_esas_sozlesme"],
                    "belge_bazli_metinler": result.get("belge_bazli_metinler", []),
                },
            },
        )
        return row.id


@celery_app.task(bind=True, name="lexnorm.run_target_scan")
def run_target_scan_task(self, task_id: str, task_dir: str) -> dict:
    """
    Celery task: run target scan from files in task_dir, save result to DB, return scan_result_id.
    task_dir contains doc_0.pdf, doc_1.pdf, ... and meta.json.
    """
    path = Path(task_dir)
    if not path.is_dir():
        return {"status": "failed", "error": f"Task directory not found: {task_dir}"}

    meta_path = path / "meta.json"
    if not meta_path.exists():
        _cleanup(path)
        return {"status": "failed", "error": "meta.json not found"}

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        _cleanup(path)
        return {"status": "failed", "error": f"Invalid meta.json: {e}"}

    logger.info(
        "run_target_scan_task started: task_id=%s target_name=%r target_mersis=%r documents=%s",
        task_id,
        meta.get("target_name"),
        meta.get("target_mersis"),
        meta.get("document_names", []),
    )

    try:
        scan_result_id = asyncio.run(_run_target_scan_async(path, meta))
        _cleanup(path)
        logger.info(
            "run_target_scan_task completed: task_id=%s scan_result_id=%s",
            task_id,
            scan_result_id,
        )
        return {"status": "completed", "scan_result_id": scan_result_id}
    except (TargetScanValidationError, TargetScanNoExtractionsError) as e:
        detail = getattr(e, "detail", str(e))
        logger.warning(
            "run_target_scan_task business failure: task_id=%s error=%s",
            task_id,
            detail,
        )
        _cleanup(path)
        return {"status": "failed", "error": detail}
    except Exception as e:
        logger.exception("run_target_scan_task failed: %s", e)
        _cleanup(path)
        return {"status": "failed", "error": str(e)}


def _cleanup(task_dir: Path) -> None:
    try:
        shutil.rmtree(task_dir, ignore_errors=True)
    except OSError as e:
        logger.warning("Cleanup task dir %s failed: %s", task_dir, e)
