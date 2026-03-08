from src.core.base_crud import BaseCrudService
from src.models.scan_result import ScanResult


class ScanResultCrud(BaseCrudService):
    def __init__(self) -> None:
        super().__init__(ScanResult)
