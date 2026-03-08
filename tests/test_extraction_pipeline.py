from pathlib import Path
from unittest.mock import MagicMock

from src.pipelines.base_pipeline import PipelineContext
from src.pipelines.extraction_pipeline import ExtractionPipeline
from src.pipelines.llm_client import LLMClientProtocol
from src.pipelines.prompt_enum import PromptEnum


class MockLLMClient:
    """Returns fixed JSON for tests."""

    def __init__(self, response_content: str) -> None:
        self.response_content = response_content

    def chat(self, model: str, messages: list[dict], options: dict) -> dict:
        return {
            "message": {"content": self.response_content},
        }


def test_extract_returns_companies_with_mock_llm():
    llm_response = """```json
    {"companies": [{"company_information": {"company_name": {"value": "TEST A.Ş."}, "mersis_number": {"value": "0123456789012345"}}, "registration_information": {}}]}
    ```"""
    mock_llm: LLMClientProtocol = MockLLMClient(llm_response)
    pipeline = ExtractionPipeline(
        prompt=PromptEnum.GENERAL_ASSEMBLY,
        llm_client=mock_llm,
    )
    ctx = PipelineContext(
        pdf_path=Path("dummy.pdf"),
        raw_text_by_page=["Kuruluş ilanı metni"],
    )
    result = pipeline.extract(ctx)
    assert "companies" in result
    assert len(result["companies"]) == 1
    assert (
        result["companies"][0]["company_information"]["company_name"]["value"]
        == "TEST A.Ş."
    )
    assert "_ocr_preview" in result
    assert "_belge_metin" in result


def test_extract_returns_error_dict_when_llm_fails():
    mock_llm = MagicMock(spec=LLMClientProtocol)
    mock_llm.chat.side_effect = RuntimeError("Connection refused")
    pipeline = ExtractionPipeline(
        prompt=PromptEnum.GENERAL_ASSEMBLY, llm_client=mock_llm
    )
    ctx = PipelineContext(pdf_path=Path("dummy.pdf"), raw_text_by_page=["text"])
    result = pipeline.extract(ctx)
    assert "error" in result
    assert "raw_preview" in result
    assert "Connection refused" in result["error"]


def test_extract_empty_ocr_returns_error():
    mock_llm = MagicMock(spec=LLMClientProtocol)
    pipeline = ExtractionPipeline(
        prompt=PromptEnum.GENERAL_ASSEMBLY, llm_client=mock_llm
    )
    ctx = PipelineContext(pdf_path=Path("dummy.pdf"), raw_text_by_page=["   ", ""])
    result = pipeline.extract(ctx)
    assert "error" in result
    assert "OCR metni boş" in result["error"]
    mock_llm.chat.assert_not_called()
