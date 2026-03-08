from src.api.v1.authentication import router as authentication_router
from src.api.v1.scan_document import router as scan_document_router

routers = [
    authentication_router,
    scan_document_router,
]
