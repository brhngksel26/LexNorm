"""API integration tests for scan_document (target_scan 202)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.utils import get_current_user
from src.main import app
from src.models.authentication import Authentication


@pytest.fixture
def mock_auth_user():
    """Fake user for dependency override."""
    user = MagicMock(spec=Authentication)
    user.id = 1
    user.email = "test@example.com"
    return user


@pytest.fixture
def temp_task_dir(monkeypatch):
    """Use a temp dir for LEXNORM_TASK_BASE_DIR so API and test don't clash."""
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setattr(
            "src.api.v1.scan_document.settings"
        )  # need to patch settings
        # Patch the getter used in the router
        from src.api.v1 import scan_document as scan_module

        base = Path(d)

        def _get():
            return base

        monkeypatch.setattr(scan_module, "_get_task_base_dir", _get)
        yield base


def _make_minimal_pdf_bytes() -> bytes:
    """One-page minimal PDF (PyMuPDF)."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def minimal_pdf_bytes():
    return _make_minimal_pdf_bytes()


@pytest.mark.asyncio
async def test_target_scan_returns_202_and_task_id(
    mock_auth_user,
    minimal_pdf_bytes,
):
    """POST /v1/scan_document/target_scan returns 202 and task_id when validation passes."""

    async def override_get_current_user():
        return mock_auth_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    with tempfile.TemporaryDirectory() as task_base:
        with patch(
            "src.api.v1.scan_document._get_task_base_dir", return_value=Path(task_base)
        ):
            with patch("src.api.v1.scan_document.settings") as mock_settings:
                mock_settings.TARGET_COMPANY_NAME = None
                mock_settings.TARGET_MERSIS = None
                with patch(
                    "src.api.v1.scan_document.run_target_scan_task"
                ) as mock_task:
                    mock_task.delay = MagicMock(
                        return_value=MagicMock(id="fake-task-id")
                    )
                    client = TestClient(app)
                    files = [
                        (
                            "documents",
                            ("test.pdf", minimal_pdf_bytes, "application/pdf"),
                        )
                    ]
                    data = {"announcement_types": json.dumps(["kuruluş"])}
                    response = client.post(
                        "/v1/scan_document/target_scan",
                        data=data,
                        files=files,
                        params={"target_company_name": "Test Şirket"},
                        headers={"Authorization": "Bearer fake-token"},
                    )
                    assert response.status_code == 202
                    body = response.json()
                    assert "task_id" in body
                    assert body.get("status") == "accepted"
                    mock_task.delay.assert_called_once()
    app.dependency_overrides.pop(get_current_user, None)
