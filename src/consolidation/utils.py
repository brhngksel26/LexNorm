import re
from datetime import datetime
from typing import Any


def get_value(obj: Any) -> Any:
    """
    Extract the value from an extraction field.

    Accepts either a dict with a "value" key (ValueWithSource shape from LLM extraction)
    or a raw value. Returns the inner value or the object itself when not in that shape.
    """
    if obj is None:
        return None
    if isinstance(obj, dict) and "value" in obj:
        return obj["value"]
    return obj


def get_source_text(obj: Any) -> Any:
    """ValueWithSource shape (dict with "value" and optional "source_text") from which source_text is returned."""
    if obj is None or not isinstance(obj, dict):
        return None
    return obj.get("source_text")


def nested_get(d: dict | None, *keys: str) -> Any:
    """İç içe dict'te key zinciri ile değer döner."""
    for key in keys:
        if d is None or not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def parse_date_for_sort(val: Any) -> datetime | None:
    """Tarih string'ini sıralama için datetime'a çevirir. DD.MM.YYYY veya '22 ARALIK 2025' vb."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # DD.MM.YYYY
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    # DD MM YYYY veya "22 ARALIK 2025"
    months = {
        "ocak": 1,
        "şubat": 2,
        "mart": 3,
        "nisan": 4,
        "mayıs": 5,
        "haziran": 6,
        "temmuz": 7,
        "ağustos": 8,
        "eylül": 9,
        "ekim": 10,
        "kasım": 11,
        "aralık": 12,
    }
    parts = s.replace(",", " ").split()
    if len(parts) >= 3:
        try:
            day = int(parts[0])
            month = months.get(parts[1].lower()[:3]) or months.get(parts[1].lower())
            year = int(parts[2])
            if month and 1 <= day <= 31 and 1900 <= year <= 2100:
                return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
    return None


def extract_document_date(company: dict) -> datetime | None:
    """Tek company extraction'dan belge/ilan tarihini çıkarır (sıralama için)."""
    reg = company.get("registration_information") or {}
    d = get_value(nested_get(reg, "registration_date")) or get_value(
        nested_get(reg, "announcement_date")
    )
    if d is None:
        doc_meta = company.get("document_metadata") or {}
        d = get_value(nested_get(doc_meta, "announcement_date"))
    return parse_date_for_sort(d)


def announcement_ref(company: dict) -> str:
    reg = company.get("registration_information") or {}
    date_val = (
        get_value(reg.get("registration_date"))
        or get_value(reg.get("announcement_date"))
        or get_value(reg.get("gazette_date"))
    )
    gazette_num = get_value(reg.get("gazette_number"))
    parts = []
    if date_val:
        parts.append(str(date_val).strip())
    if gazette_num is not None and str(gazette_num).strip():
        parts.append(f"Sayı: {str(gazette_num).strip()}")
    if parts:
        return " - ".join(parts)
    doc_meta = company.get("document_metadata") or {}
    date_val = get_value(doc_meta.get("announcement_date")) or get_value(
        doc_meta.get("registration_date")
    )
    gazette_num = get_value(doc_meta.get("gazette_number"))
    if date_val:
        parts.append(str(date_val).strip())
    if gazette_num is not None and str(gazette_num).strip():
        parts.append(f"Sayı: {str(gazette_num).strip()}")
    return " - ".join(parts) if parts else ""


def build_sorted_extraction_items(
    extractions: list[dict],
) -> list[tuple[datetime | None, dict, str]]:
    """
    Her öğe: {"document_name": str, "result": dict}; result["companies"][0] hedef şirket.
    Tarih sırasına göre sıralanmış (date, company, document_name) listesi döner.
    """
    items: list[tuple[datetime | None, dict, str]] = []
    for item in extractions:
        result = item.get("result") or {}
        companies = result.get("companies") or []
        if not companies:
            continue
        company = companies[0] if isinstance(companies[0], dict) else {}
        doc_name = item.get("document_name") or "unknown"
        date = extract_document_date(company)
        items.append((date, company, doc_name))
    items.sort(key=lambda x: (x[0] or datetime.min,))
    return items
