"""Konsolide esas sözleşme: kuruluş maddeleri + değişiklik ilanları ile güncellenmiş madde metinleri."""

from typing import Any

from src.consolidation.utils import (
    announcement_ref,
    build_sorted_extraction_items,
    get_value,
)

_SPECIFIC_ARTICLE_MAP: list[tuple[str, str, str]] = [
    ("article_4_address", "4", "Şirketin Merkezi"),
    ("article_5_duration", "5", "Süre"),
    ("article_6_capital", "6", "Sermaye"),
    ("article_7_business_purpose", "7", "Amaç ve Konu"),
    ("article_8_management", "8", "Yönetim"),
    ("article_9_representation", "9", "Temsil"),
    ("article_10_general_assembly", "10", "Genel Kurul"),
]


def _articles_from_specific(
    company: dict, ref: str, doc_name: str
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    specific = company.get("specific_articles") or {}
    for field_name, num_key, default_title in _SPECIFIC_ARTICLE_MAP:
        val = get_value(specific.get(field_name)) or get_value(company.get(field_name))
        if val is None or not str(val).strip():
            continue
        out[num_key] = {
            "article_number": num_key,
            "article_title": default_title,
            "article_text": str(val).strip(),
            "source_ttsg": ref or doc_name,
        }
    return out


def build_consolidated_articles(
    extractions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Kuruluş ilanındaki esas sözleşme maddelerini alır; esas_sözleşme_değişikliği
    ilanlarındaki maddeleri tarih sırasına göre uygulayarak güncel madde metinlerini döner.
    Her madde: {article_number, article_title, article_text, source_ttsg}.
    articles_of_association boşsa specific_articles (article_4_address vb.) ile fallback yapar.
    """
    items = build_sorted_extraction_items(extractions)
    articles: dict[str, dict[str, Any]] = {}

    for _date, company, doc_name in items:
        ref = announcement_ref(company)

        inits = (
            company.get("articles_of_association")
            or (company.get("establishment_details") or {}).get(
                "articles_of_association"
            )
            or []
        )
        if inits:
            for art in inits:
                if not isinstance(art, dict):
                    continue
                num = get_value(art.get("article_number"))
                if num is None:
                    continue
                key = str(num).strip()
                text = get_value(art.get("article_text"))
                title = get_value(art.get("article_title"))
                if key and text is not None:
                    articles[key] = {
                        "article_number": key,
                        "article_title": title,
                        "article_text": text,
                        "source_ttsg": ref or doc_name,
                    }
        else:
            from_specific = _articles_from_specific(company, ref, doc_name)
            for k, v in from_specific.items():
                if k not in articles:
                    articles[k] = v

        amendments = (
            company.get("articles_of_association_amendments")
            or company.get("articles_of_association_changes")
            or (company.get("establishment_details") or {}).get(
                "articles_of_association_amendments"
            )
            or []
        )
        for am in amendments:
            if not isinstance(am, dict):
                continue
            num = get_value(am.get("article_number"))
            if num is None:
                continue
            key = str(num).strip()
            new_text = get_value(am.get("new_article_text"))
            if new_text is not None and key:
                title = get_value(am.get("article_title"))
                articles[key] = {
                    "article_number": key,
                    "article_title": title,
                    "article_text": new_text,
                    "source_ttsg": ref or doc_name,
                }

    ordered = sorted(articles.items(), key=lambda x: _article_sort_key(x[0]))
    return [v for _k, v in ordered]


def _article_sort_key(num_str: str) -> tuple[int | float, str]:
    """Madde numarası sıralama (6, 7, 10 vb.)."""
    try:
        return (int(num_str), num_str)
    except ValueError:
        return (9999, num_str)
