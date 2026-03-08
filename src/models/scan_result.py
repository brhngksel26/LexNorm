from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import BaseModel


class ScanResult(BaseModel):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_name: Mapped[str] = mapped_column(String(512), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("authentications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # relationship optional, for ORM joins
    # user: Mapped["Authentication"] = relationship("Authentication", back_populates="scan_results")
