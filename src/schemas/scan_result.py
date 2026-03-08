from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScanDocumentResponseSchema(BaseModel):
    scan_result_id: int = Field(
        ..., alias="id", description="ID of the saved scan result"
    )
    document_name: str = Field(..., description="Original document/file name")
    user_id: int = Field(..., description="ID of the user who ran the scan")
    result: dict[str, Any] = Field(
        ..., description="Extraction result (company_information, etc.)"
    )
    created_date: datetime = Field(..., description="When the scan result was saved")

    model_config = ConfigDict(from_attributes=False)
