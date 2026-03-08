"""Protocols for consolidation domain."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConsolidationProtocol(Protocol):
    """Interface for producing consolidated report outputs from extraction data."""

    def company_info_table(self) -> dict[str, Any]:
        """Returns a single row of current company info (latest values by date)."""
        ...

    def board_members_table(self) -> list[dict[str, Any]]:
        """Returns list of current board members with role and source ref."""
        ...

    def consolidated_articles(self) -> list[dict[str, Any]]:
        """Returns consolidated articles of association (article_number, title, text, source)."""
        ...
