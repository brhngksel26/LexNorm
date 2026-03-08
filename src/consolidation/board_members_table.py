from typing import Any

from src.consolidation.utils import (
    announcement_ref,
    build_sorted_extraction_items,
    get_value,
)


def _format_member_name(rep: dict) -> str:
    """Tüzel kişi ise '[Şirket] (adına hareket eden: [Gerçek Kişi])' formatı."""
    person_name = get_value(rep.get("person_name"))
    is_tuzel = get_value(rep.get("is_tüzel_kişi"))
    tuzel_name = get_value(rep.get("tüzel_kişi_name"))
    acting = get_value(rep.get("acting_person_name"))
    if is_tuzel and tuzel_name:
        if acting:
            return f"[{tuzel_name}] (adına hareket edecek gerçek kişi: {acting})"
        return f"[{tuzel_name}]"
    return person_name or ""


def build_board_members_table(
    extractions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Görevde olan YK üyelerini döner. Her öğe: {"document_name", "result"}.
    result["companies"][0] hedef şirket. Önce kuruluş initial_representatives,
    sonra tarih sırasına göre management_changes (atama/görevden ayrılma) uygulanır.
    """
    items = build_sorted_extraction_items(extractions)
    # role -> (display_name, end_date, source_ref, source_doc)
    current: dict[str, tuple[str, str, str, str]] = {}
    seen_initial = False

    for _date, company, doc_name in items:
        if not seen_initial:
            inits = company.get("initial_representatives") or []
            if inits:
                seen_initial = True
                ref = announcement_ref(company)
                for rep in inits:
                    if not isinstance(rep, dict):
                        continue
                    name = _format_member_name(rep)
                    title = get_value(rep.get("title")) or "YK Üyesi"
                    role_key = f"{title}|{name}"
                    term_end = get_value(rep.get("term_duration")) or ""
                    current[role_key] = (name, term_end, ref, doc_name)

        for ch in company.get("management_changes") or []:
            if not isinstance(ch, dict):
                continue
            change_type = (get_value(ch.get("change_type")) or "").upper()
            person_name = get_value(ch.get("person_name")) or _format_member_name(ch)
            new_role = (
                get_value(ch.get("new_role"))
                or get_value(ch.get("previous_role"))
                or "YK Üyesi"
            )
            ref = announcement_ref(company)
            term_end = get_value(ch.get("termination_date")) or ""

            if (
                "ATAMA" in change_type
                or "SEÇİLDİ" in change_type
                or "SEÇILDI" in change_type
            ):
                role_key = f"{new_role}|{person_name}"
                current[role_key] = (person_name, term_end, ref, doc_name)
            elif (
                "İSTİFA" in change_type
                or "GÖREVDEN AYRILMA" in change_type
                or "SONA ERME" in change_type
            ):
                to_remove = [
                    k for k, (nm, _, _, _) in current.items() if nm == person_name
                ]
                for k in to_remove:
                    current.pop(k, None)

    rows = []
    for role_key, (display_name, gorev_bitis, ttsg_ref, kaynak_pdf) in current.items():
        title = role_key.split("|", 1)[0] if "|" in role_key else "YK Üyesi"
        rows.append(
            {
                "ad_soyad_unvan": (
                    f"{display_name}"
                    if title == "YK Üyesi"
                    else f"{display_name} / {title}"
                ),
                "gorev_bitis_tarihi": gorev_bitis,
                "atandigi_ttsg_tarih_sayi": ttsg_ref,
                "kaynak_pdf": kaynak_pdf,
            }
        )
    return rows
