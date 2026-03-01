"""
📋 Strukturli JSON Logging Konfiguratsiyasi
==========================================

Bu modul Python standart logging ni structlog bilan boyitadi:
- JSON formatida chiqish (Docker → Filebeat → Elastic/Splunk uchun)
- Har bir log yozuviga avtomatik context qo'shiladi:
  * timestamp (ISO-8601)
  * log_level
  * logger_name
  * environment
  * service_name

Ishlatish:
    from app.core.logging_config import setup_logging, get_logger

    # Ilovani ishga tushirishda bir marta chaqiring:
    setup_logging()

    # Keyin odatdagi logging yoki structlog ishlatish:
    logger = get_logger(__name__)
    logger.info("Case yaratildi", case_id="CASE-2026-001", priority="critical")
    # → {"timestamp":"2026-03-02T10:00:00Z","level":"info","logger":"app.bot.handlers",
    #    "event":"Case yaratildi","case_id":"CASE-2026-001","priority":"critical"}

SIEM_ENABLED=true bo'lsa — loglar SIEM ga ham yuboriladi.
"""

import logging
import logging.config
import sys
import os
from typing import Any

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

from app.core.config import settings


def _get_log_level() -> str:
    if settings.DEBUG:
        return "DEBUG"
    return os.environ.get("LOG_LEVEL", "INFO").upper()


def setup_logging() -> None:
    """
    Logging ni sozlaydi.
    SIEM_LOG_FORMAT=json  → JSON structured logging (default production)
    SIEM_LOG_FORMAT=text  → Oddiy matn (development uchun qulay)
    """
    log_format = getattr(settings, "SIEM_LOG_FORMAT", "json")
    level = _get_log_level()

    if HAS_STRUCTLOG and log_format == "json":
        _setup_structlog_json(level)
    else:
        _setup_plain_logging(level)


def _setup_structlog_json(level: str) -> None:
    """structlog bilan JSON formatda logging."""
    import structlog

    # Timestamper
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Shared processors (stdlib + structlog uchun)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
        # Service meta-data
        _add_service_info,
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Final renderer — JSON
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Shovqinli kutubxonalarni sokinlashtirish
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def _setup_plain_logging(level: str) -> None:
    """Oddiy matn formatida logging (development uchun)."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def _add_service_info(logger: Any, method: str, event_dict: dict) -> dict:
    """Har bir log yozuviga service meta-data qo'shadi."""
    event_dict.setdefault("service", "integritybot")
    event_dict.setdefault("environment", settings.ENVIRONMENT)
    return event_dict


def get_logger(name: str | None = None):
    """
    Logger olish — structlog mavjud bo'lsa structlog, aks holda standart logging.

    Misol:
        logger = get_logger(__name__)
        logger.info("Amal bajarildi", user_id="...", case_id="...")
    """
    if HAS_STRUCTLOG:
        import structlog
        return structlog.get_logger(name)
    return logging.getLogger(name)

