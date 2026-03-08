import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from src.pipelines.ocr_executors import OCRExecutor, SequentialOCRExecutor

logger = logging.getLogger(__name__)


def build_ocr_input_from_chunks(chunks: list) -> str:
    parts = []
    for chunk in chunks:
        text = chunk if isinstance(chunk, str) else getattr(chunk, "text", chunk)
        if text and str(text).strip():
            parts.append(str(text))
    return "\n\n".join(parts) if parts else ""


@dataclass
class PipelineContext:
    pdf_path: Path
    raw_text_by_page: list[str]

    @property
    def full_text(self) -> str:
        return "\n\n".join(self.raw_text_by_page)

    def full_text_from_chunks(self, chunks: list) -> str:
        """Chunk listesinden veri kaybı olmadan tek metin."""
        return build_ocr_input_from_chunks(chunks)


class BasePipeline(ABC):
    def __init__(
        self,
        ocr_executor: OCRExecutor | None = None,
    ):
        self.ocr_executor = ocr_executor or SequentialOCRExecutor()

    def run_ocr(self, pdf_path: Path, language: str = "tr") -> list[str]:
        import fitz

        doc = fitz.open(pdf_path)
        img_paths: list[str] = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                img_path = f.name
            pix.save(img_path)
            img_paths.append(img_path)
        doc.close()

        try:
            return self.ocr_executor.run_ocr(img_paths, lang=language)
        finally:
            for img_path in img_paths:
                Path(img_path).unlink(missing_ok=True)

    def normalize_ocr_text(self, text: str) -> str:
        lines = text.splitlines()
        merged = []
        buffer = ""

        for line in lines:
            if len(line.strip()) == 1:
                buffer += line.strip()
            else:
                if buffer:
                    merged.append(buffer)
                    buffer = ""
                merged.append(line)

        if buffer:
            merged.append(buffer)

        return "\n".join(merged)

    def run(self, pdf_path: Path) -> PipelineContext:
        raw_by_page = self.run_ocr(pdf_path)
        total_chars = sum(len(t) for t in raw_by_page)
        logger.info(
            "OCR tamamlandı: pdf=%s sayfa_sayisi=%d toplam_karakter=%d",
            pdf_path.name,
            len(raw_by_page),
            total_chars,
        )
        if total_chars == 0:
            logger.warning("OCR çıktısı boş: pdf=%s", pdf_path.name)

        normalized_pages = [self.normalize_ocr_text(text) for text in raw_by_page]

        return PipelineContext(pdf_path=pdf_path, raw_text_by_page=normalized_pages)

    @abstractmethod
    def extract(self, ctx: PipelineContext) -> dict:
        pass
