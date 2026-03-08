import re
from pathlib import Path

from src.pipelines.base_pipeline import BasePipeline, PipelineContext
from src.pipelines.ocr_executors import OCRExecutor


def _normalize_for_match(text: str | None) -> str:
    if text is None or not isinstance(text, str):
        return ""
    u = text.upper().strip()
    u = re.sub(r"\s+", " ", u)
    u = u.replace("\u0130", "I")
    return u


def extract_target_company_block(
    full_text: str,
    target_company_name: str | None = None,
    target_mersis: str | None = None,
) -> str:
    """
    OCR tam metninden hedef şirket ilanı bloğunu çıkarır (paragraflar, maddeler, tablolar dahil eksiksiz).
    Başlangıç: şirket unvanı veya MERSİS geçen satır.
    Bitiş: bir sonraki şirketin unvan/MERSİS satırı veya metin sonu.
    """
    if not full_text or (not target_company_name and not target_mersis):
        return full_text or ""

    lines = full_text.splitlines()
    norm_name = _normalize_for_match(target_company_name) if target_company_name else ""
    norm_mersis = re.sub(r"\s+", "", (target_mersis or "").strip())

    start_i: int | None = None
    for i, line in enumerate(lines):
        ln = _normalize_for_match(line)
        if norm_name and norm_name in ln:
            start_i = i
            break
        if norm_mersis and norm_mersis in re.sub(r"\s+", "", ln):
            start_i = i
            break
    if start_i is None:
        return ""

    end_i = len(lines)
    for j in range(start_i + 1, len(lines)):
        line = lines[j]
        ln = _normalize_for_match(line)
        if "TİCARET UNVANI" in ln or "TİCARET UNVANİ" in ln or "TICARET UNVANI" in ln:
            if norm_name and norm_name not in ln:
                end_i = j
                break
            if norm_mersis:
                rest = " ".join(lines[j : j + 10])
                if norm_mersis not in re.sub(r"\s+", "", rest):
                    end_i = j
                    break
        if "MERSİS" in ln or "MERSIS" in ln:
            if norm_mersis and norm_mersis not in re.sub(r"\s+", "", ln):
                end_i = j
                break

    return "\n".join(lines[start_i:end_i]).strip()


class DocumentTextExtractionPipeline(BasePipeline):
    """Hedef şirket ilanının tam metnini (paragraf yapısı korunarak) çıkarır."""

    def __init__(
        self,
        target_company_name: str | None = None,
        target_mersis: str | None = None,
        ocr_executor: OCRExecutor | None = None,
    ):
        super().__init__(ocr_executor=ocr_executor)
        self.target_company_name = target_company_name
        self.target_mersis = target_mersis

    def extract(self, ctx: PipelineContext) -> dict:
        full_text = ctx.full_text
        if not full_text.strip():
            return {"error": "OCR metni boş", "full_text": ""}
        block = extract_target_company_block(
            full_text,
            target_company_name=self.target_company_name,
            target_mersis=self.target_mersis,
        )
        if not block:
            return {
                "error": "Hedef şirket bloğu bulunamadı",
                "full_text": "",
                "_ocr_preview": full_text[:1000],
            }
        return {"full_text": block, "_ocr_preview": full_text[:1000]}

    def run_full(self, pdf_path: Path) -> dict:
        ctx = self.run(pdf_path)
        return self.extract(ctx)
