import asyncio
import json
import tempfile
import uuid
from pathlib import Path
from tempfile import gettempdir

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.celery_app import celery_app
from src.core.config import settings
from src.core.database import get_async_session
from src.core.utils import get_current_user
from src.cruds.scan_result import ScanResultCrud
from src.models.authentication import Authentication
from src.pipelines.factory import create_extraction_pipeline
from src.pipelines.protocols import ExtractionPipelineProtocol
from src.schemas.scan_result import ScanDocumentResponseSchema
from src.services.target_scan_service import (
    TargetScanProtocol,
    TargetScanService,
    TargetScanValidationError,
)
from src.tasks.target_scan import run_target_scan_task

router = APIRouter(prefix="/v1/scan_document", tags=["Scan Document"])


def get_target_scan_service() -> TargetScanProtocol:
    return TargetScanService(max_concurrent=4)


def _get_task_base_dir() -> Path:
    base = settings.LEXNORM_TASK_BASE_DIR or (gettempdir() + "/lexnorm_tasks")
    return Path(base)


@router.post("/scan", response_model=ScanDocumentResponseSchema)
async def scan_document(
    document: UploadFile = File(...),
    announcement_type: str | None = Query(
        None,
        description="Belge türü: kuruluş, sermaye_artırımı, yönetim_kurulu_değişikliği, denetçi_değişikliği, esas_sözleşme_değişikliği, iç_yönerge_yk_ataması",
    ),
    current_user: Authentication = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session),
) -> ScanDocumentResponseSchema:
    """Tek PDF + ilan tipi ile extraction; sonuç DB'ye kaydedilir. Hedef şirket filtresi yok."""
    if not document.filename or not document.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF dosyası gerekli")

    suffix = Path(document.filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await document.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        pipeline: ExtractionPipelineProtocol = create_extraction_pipeline(
            announcement_type
        )
        result = await asyncio.to_thread(pipeline.run_full, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if "error" in result and len(result) == 2:
        raise HTTPException(
            status_code=422, detail=result.get("error", "İşlem başarısız")
        )

    row = await ScanResultCrud().create(
        db_session,
        data={
            "document_name": document.filename or "unknown.pdf",
            "user_id": current_user.id,
            "result": result,
        },
    )

    return ScanDocumentResponseSchema.model_validate(row.to_dict())


@router.post(
    "/target_scan",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["documents", "announcement_types"],
                        "properties": {
                            "documents": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"},
                                "description": "PDF dosyaları (sıra announcement_types ile aynı). Birden fazla dosya seçin.",
                            },
                            "announcement_types": {
                                "type": "string",
                                "description": 'JSON array, örn. ["kuruluş", "denetçi_değişikliği"]',
                            },
                        },
                    },
                    "encoding": {
                        "documents": {
                            "contentType": "application/pdf",
                        },
                    },
                }
            }
        }
    },
    status_code=202,
)
async def target_scan(
    documents: list[UploadFile] = File(
        ..., description="PDF dosyaları (sıra announcement_types ile aynı)"
    ),
    announcement_types: str = Form(
        ...,
        description='JSON array veya virgülle ayrılmış. Örn. ["kuruluş", "denetçi_değişikliği"]',
    ),
    target_company_name: str | None = Query(None),
    target_mersis: str | None = Query(None),
    current_user: Authentication = Depends(get_current_user),
    target_scan_service: TargetScanProtocol = Depends(get_target_scan_service),
):
    """
    Çoklu PDF + ilan tipleri + hedef şirket. İş Celery'de arka planda çalışır.
    Hemen 202 + task_id döner; sonucu GET /target_scan/task/{task_id} ile sorgulayın.
    """
    target_name = target_company_name or settings.TARGET_COMPANY_NAME
    target_mersis_val = target_mersis or settings.TARGET_MERSIS

    try:
        target_scan_service.validate(
            documents, announcement_types, target_name, target_mersis_val
        )
    except TargetScanValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail)

    task_id = uuid.uuid4().hex
    base_dir = _get_task_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    task_dir = base_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    try:
        document_names: list[str] = []
        for i, upload in enumerate(documents):
            content = await upload.read()
            name = upload.filename or f"doc_{i}.pdf"
            document_names.append(name)
            (task_dir / f"doc_{i}.pdf").write_bytes(content)

        meta = {
            "document_names": document_names,
            "announcement_types": announcement_types,
            "target_name": target_name,
            "target_mersis": target_mersis_val,
            "user_id": current_user.id,
        }
        (task_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8"
        )

        run_target_scan_task.delay(task_id, str(task_dir))
    except Exception as e:
        import shutil

        shutil.rmtree(task_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Görev oluşturulamadı: {e}")

    return {
        "task_id": task_id,
        "status": "accepted",
        "message": "İşlem kuyruğa alındı. Sonuç için GET /v1/scan_document/target_scan/task/{task_id} kullanın.",
    }


@router.get("/target_scan/task/{task_id}")
async def get_target_scan_task_status(
    task_id: str,
    current_user: Authentication = Depends(get_current_user),
):
    """
    Celery task durumu ve sonucu. status: pending | running | completed | failed.
    completed ise scan_result_id döner; GET /scan_results/{scan_result_id} ile kaydı alın.
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)
    state = result.state

    if state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    if state == "STARTED":
        return {"task_id": task_id, "status": "running"}

    if state == "SUCCESS":
        data = result.result or {}
        if isinstance(data, dict) and data.get("status") == "failed":
            raise HTTPException(
                status_code=422,
                detail=data.get("error", "İşlem başarısız"),
            )
        scan_result_id = data.get("scan_result_id")
        if scan_result_id is None:
            raise HTTPException(status_code=500, detail="Sonuç beklenmiyordu")
        return {
            "task_id": task_id,
            "status": "completed",
            "scan_result_id": scan_result_id,
        }

    if state == "FAILURE":
        exc = str(result.result) if result.result else "Bilinmeyen hata"
        raise HTTPException(status_code=500, detail=exc)

    return {"task_id": task_id, "status": state.lower()}


@router.get("/scan_results_list")
async def get_scan_results_list(
    current_user: Authentication = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    return await ScanResultCrud().get_many(db_session, user_id=current_user.id)


@router.get("/scan_results/{scan_result_id}")
async def get_scan_results(
    scan_result_id: int,
    current_user: Authentication = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session),
):
    return await ScanResultCrud().get_by_id(db_session, scan_result_id)
