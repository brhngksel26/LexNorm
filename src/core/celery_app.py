import logging

from celery import Celery

from src.core.config import settings

_log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_log_datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=settings.LOG_LEVEL, format=_log_fmt, datefmt=_log_datefmt)
_src_logger = logging.getLogger("src")
_src_logger.setLevel(settings.LOG_LEVEL)
if not _src_logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter(_log_fmt, datefmt=_log_datefmt))
    _src_logger.addHandler(_h)
_src_logger.propagate = False

import src.models  # noqa: F401

celery_app = Celery(
    "lexnorm",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
)
celery_app.autodiscover_tasks(["src.tasks"])
