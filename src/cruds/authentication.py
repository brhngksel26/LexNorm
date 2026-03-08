from src.core.base_crud import BaseCrudService
from src.models.authentication import Authentication


class AuthenticationCrud(BaseCrudService):
    def __init__(self):
        super().__init__(Authentication)
