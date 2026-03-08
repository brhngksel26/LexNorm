"""Konsolidasyon modülleri birim testleri."""

from src.consolidation import (
    ConsolidationProtocol,
    ConsolidationService,
    build_board_members_table,
    build_company_info_table,
    build_consolidated_articles,
)
from src.consolidation.utils import get_value, parse_date_for_sort


def test_get_value():
    assert get_value(None) is None
    assert get_value({"value": "x"}) == "x"
    assert get_value({"value": None}) is None


def test_parse_date_for_sort():
    assert parse_date_for_sort("22.12.2025") is not None
    assert parse_date_for_sort(None) is None
    assert parse_date_for_sort("") is None


def test_build_company_info_table_single():
    extractions = [
        {
            "document_name": "kurulus.pdf",
            "result": {
                "companies": [
                    {
                        "company_information": {
                            "company_name": {"value": "TEST A.Ş."},
                            "company_type": {"value": "Anonim Şirketi"},
                            "mersis_number": {"value": "0123456789012345"},
                            "trade_registry_office": {"value": "İstanbul"},
                            "trade_registry_number": {"value": "123"},
                            "address": {"value": "Adres 1"},
                            "foundation_date": {"value": "01.01.2020"},
                        },
                        "capital_structure": {
                            "initial_capital": {"value": "100.000 TL"},
                            "currency": {"value": "TL"},
                        },
                        "registration_information": {
                            "registration_date": {"value": "01.01.2020"}
                        },
                    }
                ]
            },
        }
    ]
    out = build_company_info_table(extractions)
    assert out["ticaret_unvani"] == "TEST A.Ş."
    assert out["mevcut_sermaye"] is not None
    assert out["kurulus_tarihi"] == "01.01.2020"


def test_build_board_members_table_empty():
    extractions = [
        {
            "document_name": "x.pdf",
            "result": {
                "companies": [
                    {
                        "company_information": {},
                        "registration_information": {},
                    }
                ]
            },
        }
    ]
    out = build_board_members_table(extractions)
    assert out == []


def test_build_consolidated_articles_empty():
    extractions = [
        {
            "document_name": "x.pdf",
            "result": {"companies": [{"registration_information": {}}]},
        }
    ]
    out = build_consolidated_articles(extractions)
    assert out == []


def test_consolidation_service_implements_protocol():
    """ConsolidationService satisfies ConsolidationProtocol (runtime checkable)."""
    service = ConsolidationService([])
    assert isinstance(service, ConsolidationProtocol)


def test_consolidation_service_same_output_as_build_functions():
    """ConsolidationService produces same results as build_* functions."""
    extractions = [
        {
            "document_name": "kurulus.pdf",
            "result": {
                "companies": [
                    {
                        "company_information": {
                            "company_name": {"value": "TEST A.Ş."},
                            "company_type": {"value": "Anonim Şirketi"},
                            "mersis_number": {"value": "0123456789012345"},
                            "trade_registry_office": {"value": "İstanbul"},
                            "trade_registry_number": {"value": "123"},
                            "address": {"value": "Adres 1"},
                            "foundation_date": {"value": "01.01.2020"},
                        },
                        "capital_structure": {
                            "initial_capital": {"value": "100.000 TL"},
                            "currency": {"value": "TL"},
                        },
                        "registration_information": {
                            "registration_date": {"value": "01.01.2020"}
                        },
                    }
                ]
            },
        }
    ]
    service = ConsolidationService(extractions)
    assert service.company_info_table() == build_company_info_table(extractions)
    assert service.board_members_table() == build_board_members_table(extractions)
    assert service.consolidated_articles() == build_consolidated_articles(extractions)
