"""Consolidation service: single entry point for report outputs."""

from typing import Any

from src.consolidation.articles_consolidation import build_consolidated_articles
from src.consolidation.board_members_table import build_board_members_table
from src.consolidation.company_info_table import build_company_info_table
from src.consolidation.protocols import ConsolidationProtocol


class ConsolidationService(ConsolidationProtocol):
    """Produces consolidated company info, board members, and articles from extraction list."""

    def __init__(self, extractions: list[dict[str, Any]]) -> None:
        self._extractions = extractions

    def company_info_table(self) -> dict[str, Any]:
        """Current company info (latest values by document date)."""
        return build_company_info_table(self._extractions)

    def board_members_table(self) -> list[dict[str, Any]]:
        """Current board members with role and source reference."""
        return build_board_members_table(self._extractions)

    def consolidated_articles(self) -> list[dict[str, Any]]:
        """Consolidated articles of association."""
        return build_consolidated_articles(self._extractions)
