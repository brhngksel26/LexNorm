"""OCR execution strategies. PaddleOCR thread-safe değildir; SequentialOCRExecutor varsayılan güvenli seçenektir."""

import os

# oneDNN/MKLDNN modül yüklenirken kapatılır; Paddle import edilmeden önce set edilmeli.
# Aksi halde ConvertPirAttribute2RuntimeAttribute hatası oluşabilir.
os.environ["FLAGS_use_mkldnn"] = "0"

from typing import Protocol

_ocr_instance = None


def _get_ocr(lang: str = "en"):
    """Singleton PaddleOCR instance."""
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR

        _ocr_instance = PaddleOCR(use_angle_cls=True, lang=lang)
    return _ocr_instance


def _parse_paddle_ocr_result(result: list) -> str:
    """PaddleOCR 3.x ve 2.x çıktı formatlarını metne dönüştürür."""
    if not result or not result[0]:
        return ""

    page = result[0]

    if isinstance(page, dict):
        rec_texts = page.get("rec_texts")
        if rec_texts is None:
            return ""
        lines = []
        for item in rec_texts:
            if isinstance(item, str):
                lines.append(item)
            elif isinstance(item, (list, tuple)):
                for x in item:
                    if isinstance(x, str):
                        lines.append(x)
                    else:
                        lines.append(str(x))
            else:
                lines.append(str(item))
        return "\n".join(lines)

    texts = []
    for item in page:
        text = None
        y = 0
        if isinstance(item, str):
            text = item
        elif isinstance(item, (list, tuple)):
            if len(item) >= 2:
                first, second = item[0], item[1]
                if isinstance(first, (list, tuple)) and len(first) > 0:
                    bbox = first
                    y = bbox[0][1] if len(bbox[0]) > 1 else 0
                    text = second[0] if isinstance(second, (list, tuple)) else second
                else:
                    text = first if isinstance(first, str) else second
            elif item and isinstance(item[0], str):
                text = item[0]
            else:
                for x in item:
                    if isinstance(x, str):
                        text = x
                        break
        if text is not None:
            texts.append((y, str(text)))

    texts.sort(key=lambda x: x[0])
    return "\n".join(t for _, t in texts)


class OCRExecutor(Protocol):
    """OCR çalıştırma stratejisi. PaddleOCR thread-safe değildir."""

    def run_ocr(self, img_paths: list[str], lang: str) -> list[str]:
        """Görsel dosya yollarından metin çıkarır. Sıra korunmalı."""
        ...


class SequentialOCRExecutor:
    """Sıralı OCR. PaddleOCR thread-safe olmadığı için varsayılan güvenli seçenek."""

    def run_ocr(self, img_paths: list[str], lang: str = "tr") -> list[str]:
        ocr = _get_ocr(lang=lang)
        return [_parse_paddle_ocr_result(ocr.ocr(path)) for path in img_paths]
