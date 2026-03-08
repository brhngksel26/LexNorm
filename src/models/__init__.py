"""Tüm ORM modelleri; FK çözümü için worker ve app başlangıcında import edilir."""

from src.models.authentication import Authentication
from src.models.scan_result import ScanResult

__all__ = ["Authentication", "ScanResult"]
