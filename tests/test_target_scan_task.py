import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.core.celery_app import celery_app
from src.tasks.target_scan import run_target_scan_task


def _make_minimal_pdf_bytes() -> bytes:
    import fitz

    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def task_dir_fixture():
    """Create a task directory with meta.json and doc_0.pdf."""
    pdf_bytes = _make_minimal_pdf_bytes()
    with tempfile.TemporaryDirectory() as base:
        task_id = "test-task-123"
        task_dir = Path(base) / task_id
        task_dir.mkdir(parents=True)
        (task_dir / "doc_0.pdf").write_bytes(pdf_bytes)
        meta = {
            "document_names": ["fixture.pdf"],
            "announcement_types": '["kuruluş"]',
            "target_name": "Test A.Ş.",
            "target_mersis": None,
            "user_id": 1,
        }
        (task_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False),
            encoding="utf-8",
        )
        yield str(task_dir), task_dir


def test_run_target_scan_task_task_dir_not_found():
    """When task_dir does not exist, task returns failed."""
    with celery_app.connection_or_acquire():
        result = run_target_scan_task.apply(
            args=["tid", "/nonexistent/path/xyz"],
        ).get()
    assert result["status"] == "failed"
    assert "Task directory not found" in result["error"]


def test_run_target_scan_task_meta_not_found(tmp_path):
    """When meta.json is missing, task returns failed."""
    (tmp_path / "doc_0.pdf").write_bytes(b"x")
    with celery_app.connection_or_acquire():
        result = run_target_scan_task.apply(
            args=["tid", str(tmp_path)],
        ).get()
    assert result["status"] == "failed"
    assert "meta.json" in result["error"]


@patch("src.tasks.target_scan._run_target_scan_async", new_callable=AsyncMock)
def test_run_target_scan_task_returns_completed_when_async_succeeds(
    mock_async_run,
    task_dir_fixture,
):
    """With valid task_dir and mocked async run, task returns status completed and scan_result_id."""
    task_dir_str, _ = task_dir_fixture
    mock_async_run.return_value = 42
    with celery_app.connection_or_acquire():
        result = run_target_scan_task.apply(
            args=["test-task-123", task_dir_str],
        ).get()
    assert result["status"] == "completed"
    assert result["scan_result_id"] == 42
    mock_async_run.assert_called_once()
