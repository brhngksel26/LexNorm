"""Hedef şirket filtresi: extraction sonucundaki companies array'ini isim veya MERSİS ile filtreler."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_for_match(text: str | None) -> str:
    if text is None or not isinstance(text, str):
        return ""
    t = text.upper().strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("A.Ş.", "ANONİM ŞİRKETİ").replace("LTD. ŞTİ.", "LİMİTED ŞİRKETİ")
    t = t.replace("LTD. ŞTİ", "LİMİTED ŞİRKETİ")
    t = t.replace("\u0130", "I")  # Turkish capital İ for substring match
    return t


def _get_nested(obj: Any, *keys: str) -> Any:
    for key in keys:
        if obj is None or not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def filter_by_target_company(
    result: dict[str, Any],
    target_company_name: str | None = None,
    target_mersis: str | None = None,
) -> dict[str, Any]:
    """
    result içindeki companies array'ini hedef şirket adı ve/veya MERSİS ile filtreler.

    - En az biri (target_company_name veya target_mersis) dolu olmalı; ikisi de boşsa
      result olduğu gibi döner.
    - İkisi de verilirse her iki koşul da sağlanmalı (AND).
    - Eşleşen tek şirket varsa { "companies": [ o_şirket ] } döner.
    - Hiç eşleşme yoksa { "companies": [], "filter_warning": "Hedef şirket bulunamadı" }.
    """
    if not target_company_name and not target_mersis:
        return result

    norm_name = (
        _normalize_for_match(target_company_name) if target_company_name else None
    )
    norm_mersis = (
        re.sub(r"\s+", "", (target_mersis or "").strip()) if target_mersis else None
    )

    companies = result.get("companies")
    if not isinstance(companies, list):
        return {**result, "companies": []}

    matched = []
    for company in companies:
        if not isinstance(company, dict):
            continue
        ci = company.get("company_information") or {}
        name_val = _get_nested(ci, "company_name", "value")
        mersis_val = _get_nested(ci, "mersis_number", "value")

        name_ok = True
        if norm_name:
            name_ok = norm_name in _normalize_for_match(name_val)
        mersis_ok = True
        if norm_mersis:
            mersis_ok = (
                mersis_val is not None
                and re.sub(r"\s+", "", str(mersis_val).strip()) == norm_mersis
            )
        if name_ok or mersis_ok:
            matched.append(company)

    out = {**result, "companies": matched}
    if not matched and (norm_name or norm_mersis):
        out["filter_warning"] = "Hedef şirket bulunamadı"
        if logger.isEnabledFor(logging.DEBUG) and companies:
            for i, company in enumerate(companies[:5]):
                if not isinstance(company, dict):
                    continue
                ci = company.get("company_information") or {}
                name_val = _get_nested(ci, "company_name", "value")
                mersis_val = _get_nested(ci, "mersis_number", "value")
                logger.debug(
                    "filter_by_target_company no match: target_name=%r target_mersis=%r "
                    "company[%s] name=%r mersis=%r",
                    norm_name,
                    norm_mersis,
                    i,
                    name_val,
                    mersis_val,
                )
    return out
