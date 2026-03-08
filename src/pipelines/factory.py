from src.pipelines.config import ANNOUNCEMENT_TYPE_TO_PROMPT, DEFAULT_PROMPT
from src.pipelines.extraction_pipeline import ExtractionPipeline
from src.pipelines.llm_client import LLMClientProtocol
from src.pipelines.protocols import ExtractionPipelineProtocol


def create_extraction_pipeline(
    announcement_type: str | None = None,
    target_company_name: str | None = None,
    target_mersis: str | None = None,
    llm_client: LLMClientProtocol | None = None,
) -> ExtractionPipelineProtocol:
    prompt = ANNOUNCEMENT_TYPE_TO_PROMPT.get(
        announcement_type or "unknown",
        DEFAULT_PROMPT,
    )
    return ExtractionPipeline(
        prompt=prompt,
        target_company_name=target_company_name,
        target_mersis=target_mersis,
        llm_client=llm_client,
    )
