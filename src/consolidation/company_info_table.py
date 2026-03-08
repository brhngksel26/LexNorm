from typing import Any

from src.consolidation.utils import (
    build_sorted_extraction_items,
    get_value,
    nested_get,
)


def _current_capital(company: dict) -> tuple[Any, Any]:
    cap_changes = company.get("capital_changes") or {}
    new_cap = get_value(nested_get(cap_changes, "new_capital"))
    if new_cap is not None:
        return new_cap, get_value(nested_get(cap_changes, "currency"))
    cap_details = company.get("capital_change_details") or {}
    new_cap = get_value(nested_get(cap_details, "new_capital"))
    if new_cap is not None:
        return new_cap, get_value(nested_get(cap_details, "currency"))
    cap_struct = company.get("capital_structure") or {}
    initial = get_value(nested_get(cap_struct, "initial_capital"))
    return initial, get_value(nested_get(cap_struct, "currency"))


def _auditor_display(company: dict) -> Any:
    """Denetçi: auditor_information'dan tek satır metin."""
    aud = company.get("auditor_information") or {}
    name = get_value(nested_get(aud, "auditor_name"))
    if name is None:
        return None
    parts = [name]
    term_end = get_value(nested_get(aud, "term_end_date"))
    if term_end:
        parts.append(f" (Bitiş: {term_end})")
    return "".join(parts) if parts else None


def build_company_info_table(
    extractions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Her öğe: {"document_name": str, "result": dict}.
    result["companies"] içinde hedef şirket (tek eleman) olmalı.
    Tarih sırasına göre en güncel değerler tek satırda döner.
    """
    items = build_sorted_extraction_items(extractions)
    # En güncel değerler (son eleman en güncel)
    ticaret_unvani = None
    sirket_turu = None
    mersis = None
    ticaret_sicil_mudurlugu = None
    ticaret_sicil_numarasi = None
    adres = None
    mevcut_sermaye = None
    kurulus_tarihi = None
    denetci = None
    source_doc = None

    for _date, company, doc_name in items:
        company = {**company, "_document_name": doc_name}
        ci = company.get("company_information") or {}
        ticaret_unvani = get_value(ci.get("company_name")) or ticaret_unvani
        sirket_turu = get_value(ci.get("company_type")) or sirket_turu
        mersis = get_value(ci.get("mersis_number")) or mersis
        ticaret_sicil_mudurlugu = (
            get_value(ci.get("trade_registry_office")) or ticaret_sicil_mudurlugu
        )
        ticaret_sicil_numarasi = (
            get_value(ci.get("trade_registry_number")) or ticaret_sicil_numarasi
        )
        adres = get_value(ci.get("address")) or adres
        cap, _cur = _current_capital(company)
        if cap is not None:
            mevcut_sermaye = f"{cap}" if not _cur else f"{cap} ({_cur})"
        foundation = get_value(ci.get("foundation_date"))
        if foundation is None:
            reg = company.get("registration_information") or {}
            foundation = get_value(reg.get("registration_date"))
        if foundation is not None and kurulus_tarihi is None:
            kurulus_tarihi = foundation
        aud = _auditor_display(company)
        if aud is not None:
            denetci = aud
        source_doc = company.get("_document_name") or source_doc

    return {
        "ticaret_unvani": ticaret_unvani,
        "sirket_turu": sirket_turu,
        "mersis_numarasi": mersis,
        "ticaret_sicil_mudurlugu": ticaret_sicil_mudurlugu,
        "ticaret_sicil_numarasi": ticaret_sicil_numarasi,
        "adres": adres,
        "mevcut_sermaye": mevcut_sermaye,
        "kurulus_tarihi": kurulus_tarihi,
        "denetci": denetci,
        "kaynak_son_belge": source_doc,
    }
