import json
import logging
import re
from pathlib import Path

from src.core.config import settings
from src.pipelines.base_pipeline import BasePipeline, PipelineContext
from src.pipelines.document_text_extraction import extract_target_company_block
from src.pipelines.hallucination_check import verify_company_against_ocr
from src.pipelines.llm_client import LLMClientProtocol, OllamaLLMClient
from src.pipelines.llm_messages import system_message, user_message
from src.pipelines.ocr_executors import OCRExecutor
from src.pipelines.prompt_enum import PromptEnum

logger = logging.getLogger(__name__)


class ExtractionPipeline(BasePipeline):
    def __init__(
        self,
        prompt: PromptEnum = PromptEnum.GENERAL_ASSEMBLY,
        url: str = settings.OLLAMA_URL,
        model: str = settings.MODEL_NAME,
        temperature: float = settings.MODEL_TEMPERATURE,
        ocr_executor: OCRExecutor | None = None,
        target_company_name: str | None = None,
        target_mersis: str | None = None,
        llm_client: LLMClientProtocol | None = None,
    ):
        super().__init__(ocr_executor=ocr_executor)
        self.prompt = prompt
        self.model = model
        self.temperature = temperature
        self.url = url
        self.llm_client = (
            llm_client if llm_client is not None else OllamaLLMClient(host=url)
        )
        self.target_company_name = target_company_name
        self.target_mersis = target_mersis

    def extract(self, ctx: PipelineContext, language: str = "tr") -> dict:
        input_text = ctx.full_text
        if not input_text.strip():
            logger.warning(
                "Validation: OCR metni boş, extraction atlanıyor. pdf=%s",
                ctx.pdf_path.name,
            )
            return {"error": "OCR metni boş", "raw_preview": ""}
        if self.target_company_name or self.target_mersis:
            block = extract_target_company_block(
                input_text,
                target_company_name=self.target_company_name,
                target_mersis=self.target_mersis,
            )
            if block:
                input_text = block
                logger.info(
                    "Token optimizasyonu: hedef şirket bloğu kullanıldı (len=%d)",
                    len(input_text),
                )

        logger.info(
            "OCR text length=%d, preview=%s",
            len(input_text),
            repr(input_text[:500]) + ("..." if len(input_text) > 500 else ""),
        )
        messages = [
            system_message(self.prompt.value),
            user_message(f"### Kuruluş Sicil TEXT (OCR OUTPUT):\n{input_text}"),
        ]
        payload = [message.to_ollama() for message in messages]

        try:
            response = self.llm_client.chat(
                model=self.model,
                messages=payload,
                options={"temperature": self.temperature},
            )
            logger.info(
                "LLM response content length=%d",
                len(response.get("message", {}).get("content", "")),
            )
        except Exception as e:
            return {"error": str(e), "raw_preview": input_text[:500]}

        content = response.get("message", {}).get("content", "")
        parsed = self._parse_json_from_response(content)
        if parsed is None:
            logger.warning(
                "LLM JSON parse edilemedi, raw_response uzunluk=%d", len(content)
            )
            return {"error": "LLM JSON parse edilemedi", "raw_response": content}
        companies = parsed.get("companies") or []
        logger.info(
            "LLM extraction: companies sayısı=%d pdf=%s",
            len(companies),
            ctx.pdf_path.name,
        )
        full_ocr_text = ctx.full_text
        for company in parsed.get("companies") or []:
            if isinstance(company, dict):
                verify_company_against_ocr(company, full_ocr_text)
        for i, c in enumerate(companies):
            if not isinstance(c, dict):
                continue
            ci = c.get("company_information") or {}
            name_val = (ci.get("company_name") or {}).get("value")
            mersis_val = (ci.get("mersis_number") or {}).get("value")
            if name_val is None or mersis_val is None:
                logger.info(
                    "Validation sonrası company[%s]: company_name=%s mersis=%s (null ise filtre eşleşmez)",
                    i,
                    name_val,
                    mersis_val,
                )
        parsed["_ocr_preview"] = input_text[:1000]
        parsed["_belge_metin"] = input_text
        return parsed

    def _parse_json_from_response(self, content: str) -> dict | None:
        content = content.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            if start != -1:
                try:
                    return json.loads(content[start:])
                except json.JSONDecodeError:
                    pass
        return None

    def run_full(self, pdf_path: Path) -> dict:
        """Tek entry: OCR + extraction."""
        ctx = self.run(pdf_path)
        return self.extract(ctx)
