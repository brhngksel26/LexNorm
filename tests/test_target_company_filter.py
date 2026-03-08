"""Hedef şirket filtresi birim testleri."""

from src.pipelines.target_company_filter import filter_by_target_company


def test_filter_empty_result():
    out = filter_by_target_company({}, target_company_name="Parla")
    assert out.get("companies", []) == []


def test_filter_no_criteria_returns_unchanged():
    data = {"companies": [{"company_information": {"company_name": {"value": "X"}}}]}
    out = filter_by_target_company(data, target_company_name=None, target_mersis=None)
    assert out == data


def test_filter_by_name_match():
    data = {
        "companies": [
            {
                "company_information": {
                    "company_name": {
                        "value": "PARLA ENERJİ YATIRIMLARI ANONİM ŞİRKETİ"
                    },
                    "mersis_number": {"value": "0721091699100001"},
                }
            },
            {
                "company_information": {
                    "company_name": {"value": "CASA MASSAL LİMİTED ŞİRKETİ"},
                    "mersis_number": {"value": "0203079628200001"},
                }
            },
        ]
    }
    out = filter_by_target_company(data, target_company_name="Parla Enerji")
    assert len(out["companies"]) == 1
    assert (
        out["companies"][0]["company_information"]["company_name"]["value"]
        == "PARLA ENERJİ YATIRIMLARI ANONİM ŞİRKETİ"
    )


def test_filter_by_mersis():
    data = {
        "companies": [
            {
                "company_information": {
                    "company_name": {"value": "OTHER"},
                    "mersis_number": {"value": "0721091699100001"},
                }
            },
        ]
    }
    out = filter_by_target_company(data, target_mersis="0721091699100001")
    assert len(out["companies"]) == 1
    assert (
        out["companies"][0]["company_information"]["mersis_number"]["value"]
        == "0721091699100001"
    )


def test_filter_no_match():
    data = {
        "companies": [
            {
                "company_information": {
                    "company_name": {"value": "OTHER ŞİRKET"},
                    "mersis_number": {"value": "1111111111111111"},
                }
            },
        ]
    }
    out = filter_by_target_company(data, target_company_name="Parla Enerji")
    assert len(out["companies"]) == 0
    assert out.get("filter_warning") == "Hedef şirket bulunamadı"
