"""
🔒 SIEM / Log Forwarding Servisi
=================================

TZ talabi (bo'lim 10):
  "SIEM/Log management (Splunk/Elastic) — opsional"

Qo'llab-quvvatlanadigan tizimlar:
  1. Splunk HEC (HTTP Event Collector)
  2. Elasticsearch (direct REST API)
  3. Graylog (GELF over HTTP)
  4. Webhook (har qanday HTTP endpoint)

Sozlash (.env):
  SIEM_ENABLED=true
  SIEM_BACKEND=splunk          # splunk | elastic | graylog | webhook
  SIEM_URL=https://splunk.company.uz:8088/services/collector
  SIEM_TOKEN=your-hec-token    # Splunk HEC token
  SIEM_INDEX=integritybot      # Splunk/Elastic index nomi
  SIEM_VERIFY_SSL=true

Ishlatish:
  from app.services.siem import siem_service

  # Audit hodisasini yuborish
  await siem_service.send_audit_event(
      action="CASE_VIEW",
      user_id="admin",
      case_id="CASE-2026-001",
      ip="192.168.1.1",
  )

  # Xavfsizlik hodisasini yuborish (login muvaffaqiyatsizliklari, XSS, brute-force)
  await siem_service.send_security_event(
      event_type="LOGIN_FAILED",
      severity="medium",
      ip="1.2.3.4",
      details={"username": "admin", "attempts": 5},
  )
"""

import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Hodisa Strukturasi ────────────────────────────────────────────────────────

def _build_event(
    event_type: str,
    severity: str = "info",
    **kwargs,
) -> dict:
    """SIEM uchun standart hodisa obyekti."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "integritybot",
        "environment": settings.ENVIRONMENT,
        "event_type": event_type,
        "severity": severity,
        **kwargs,
    }


# ── Splunk HEC Client ─────────────────────────────────────────────────────────

class SplunkClient:
    """Splunk HTTP Event Collector (HEC) ga loglar yuboradi."""

    def __init__(self):
        self.url = (getattr(settings, "SIEM_URL", "") or "").rstrip("/")
        self.token = getattr(settings, "SIEM_TOKEN", "") or ""
        self.index = getattr(settings, "SIEM_INDEX", "integritybot")
        self.verify_ssl = getattr(settings, "SIEM_VERIFY_SSL", True)

    def is_configured(self) -> bool:
        return bool(self.url and self.token)

    async def send(self, event: dict) -> bool:
        if not self.is_configured():
            return False
        try:
            import aiohttp
            payload = {
                "time": datetime.fromisoformat(event["timestamp"]).timestamp(),
                "host": "integritybot",
                "source": "integritybot:backend",
                "sourcetype": "_json",
                "index": self.index,
                "event": event,
            }
            ssl_context = None if self.verify_ssl else False
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=payload,
                    headers={
                        "Authorization": f"Splunk {self.token}",
                        "Content-Type": "application/json",
                    },
                    ssl=ssl_context,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status in (200, 201):
                        return True
                    logger.debug(f"Splunk HEC javob: {resp.status}")
                    return False
        except Exception as e:
            logger.debug(f"Splunk yuborishda xato: {e}")
            return False


# ── Elasticsearch Client ──────────────────────────────────────────────────────

class ElasticsearchClient:
    """Elasticsearch ga to'g'ridan log yuboradi."""

    def __init__(self):
        self.url = (getattr(settings, "SIEM_URL", "") or "").rstrip("/")
        self.token = getattr(settings, "SIEM_TOKEN", "") or ""  # API key yoki Basic
        self.index = getattr(settings, "SIEM_INDEX", "integritybot-logs")
        self.verify_ssl = getattr(settings, "SIEM_VERIFY_SSL", True)

    def is_configured(self) -> bool:
        return bool(self.url)

    async def send(self, event: dict) -> bool:
        if not self.is_configured():
            return False
        try:
            import aiohttp
            headers = {"Content-Type": "application/json"}
            if self.token:
                if ":" in self.token:
                    # Basic auth format: "user:password"
                    import base64
                    creds = base64.b64encode(self.token.encode()).decode()
                    headers["Authorization"] = f"Basic {creds}"
                else:
                    # API key
                    headers["Authorization"] = f"ApiKey {self.token}"

            # Data stream / index endpoint
            endpoint = f"{self.url}/{self.index}/_doc"
            ssl_context = None if self.verify_ssl else False
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=event,
                    headers=headers,
                    ssl=ssl_context,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status in (200, 201):
                        return True
                    logger.debug(f"Elasticsearch javob: {resp.status}")
                    return False
        except Exception as e:
            logger.debug(f"Elasticsearch yuborishda xato: {e}")
            return False


# ── Graylog GELF Client ───────────────────────────────────────────────────────

class GraylogClient:
    """Graylog ga GELF over HTTP yuboradi."""

    def __init__(self):
        self.url = (getattr(settings, "SIEM_URL", "") or "").rstrip("/")
        self.token = getattr(settings, "SIEM_TOKEN", "") or ""
        self.verify_ssl = getattr(settings, "SIEM_VERIFY_SSL", True)

    def is_configured(self) -> bool:
        return bool(self.url)

    async def send(self, event: dict) -> bool:
        if not self.is_configured():
            return False
        try:
            import aiohttp
            # GELF format
            severity_to_level = {
                "critical": 2, "high": 3, "error": 3,
                "medium": 4, "warning": 4, "info": 6, "debug": 7,
            }
            gelf_payload = {
                "version": "1.1",
                "host": "integritybot",
                "short_message": event.get("event_type", "event"),
                "timestamp": datetime.fromisoformat(event["timestamp"]).timestamp(),
                "level": severity_to_level.get(event.get("severity", "info"), 6),
                "_service": event.get("service", "integritybot"),
                "_environment": event.get("environment", "production"),
            }
            # Qo'shimcha maydonlarni _prefix bilan qo'shish
            for k, v in event.items():
                if k not in ("timestamp", "service", "environment") and not k.startswith("_"):
                    gelf_payload[f"_{k}"] = str(v) if not isinstance(v, (int, float, bool)) else v

            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            ssl_context = None if self.verify_ssl else False
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/gelf",
                    json=gelf_payload,
                    headers=headers,
                    ssl=ssl_context,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    return resp.status in (200, 201, 202)
        except Exception as e:
            logger.debug(f"Graylog yuborishda xato: {e}")
            return False


# ── Webhook Client ─────────────────────────────────────────────────────────────

class WebhookClient:
    """Har qanday HTTP endpoint ga JSON yuboradi."""

    def __init__(self):
        self.url = (getattr(settings, "SIEM_URL", "") or "").rstrip("/")
        self.token = getattr(settings, "SIEM_TOKEN", "") or ""
        self.verify_ssl = getattr(settings, "SIEM_VERIFY_SSL", True)

    def is_configured(self) -> bool:
        return bool(self.url)

    async def send(self, event: dict) -> bool:
        if not self.is_configured():
            return False
        try:
            import aiohttp
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            ssl_context = None if self.verify_ssl else False
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=event,
                    headers=headers,
                    ssl=ssl_context,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    return resp.status < 400
        except Exception as e:
            logger.debug(f"Webhook yuborishda xato: {e}")
            return False


# ── SIEM Service (yagona interfeys) ──────────────────────────────────────────

class SIEMService:
    """
    Yagona SIEM/Log Forwarding servisi.
    Backend avtomatik tanlanadi: SIEM_BACKEND env o'zgaruvchisi asosida.
    """

    def __init__(self):
        self._enabled = getattr(settings, "SIEM_ENABLED", False)
        backend_name = (getattr(settings, "SIEM_BACKEND", "splunk") or "splunk").lower()

        self._backend_name = backend_name
        self._client = self._init_client(backend_name)

    def _init_client(self, backend: str):
        if backend == "elastic":
            return ElasticsearchClient()
        elif backend == "graylog":
            return GraylogClient()
        elif backend == "webhook":
            return WebhookClient()
        else:
            # default: splunk
            return SplunkClient()

    def is_enabled(self) -> bool:
        return self._enabled and self._client.is_configured()

    def status(self) -> dict:
        return {
            "enabled": self._enabled,
            "configured": self._client.is_configured() if self._enabled else False,
            "backend": self._backend_name,
        }

    async def _send_safe(self, event: dict) -> None:
        """Background da yuboradi — xato bo'lsa asosiy oqimga ta'sir qilmaydi."""
        if not self.is_enabled():
            return
        try:
            await asyncio.wait_for(self._client.send(event), timeout=5.0)
        except Exception as e:
            logger.debug(f"SIEM yuborishda xato (kritik emas): {e}")

    async def send_audit_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
        severity: str = "info",
    ) -> None:
        """
        Audit hodisasini SIEM ga yuboradi.
        Case VIEW, STATUS_CHANGE, LOGIN, LOGOUT, EXPORT va boshqalar.
        """
        if not self.is_enabled():
            return
        event = _build_event(
            event_type=f"AUDIT_{action.upper()}",
            severity=severity,
            user_id=user_id,
            case_id=case_id,
            ip_address=ip_address,
            **(details or {}),
        )
        asyncio.create_task(self._send_safe(event))

    async def send_security_event(
        self,
        event_type: str,
        severity: str = "medium",
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """
        Xavfsizlik hodisasini SIEM ga yuboradi.
        LOGIN_FAILED, BRUTE_FORCE, INVALID_TOKEN, SUSPICIOUS_FILE va boshqalar.
        """
        if not self.is_enabled():
            return
        event = _build_event(
            event_type=f"SECURITY_{event_type.upper()}",
            severity=severity,
            ip_address=ip_address,
            user_id=user_id,
            **(details or {}),
        )
        asyncio.create_task(self._send_safe(event))

    async def send_case_event(
        self,
        action: str,
        case_id: str,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        is_anonymous: bool = True,
        details: Optional[dict] = None,
    ) -> None:
        """
        Murojaat hodisasini SIEM ga yuboradi.
        CASE_CREATED, CASE_ASSIGNED, CASE_CLOSED va boshqalar.
        """
        if not self.is_enabled():
            return
        # Privacy: SIEM ga shaxsiy ma'lumot yuborilmaydi
        event = _build_event(
            event_type=f"CASE_{action.upper()}",
            severity="info",
            case_id=case_id,
            category=category,
            priority=priority,
            is_anonymous=is_anonymous,
            **(details or {}),
        )
        asyncio.create_task(self._send_safe(event))

    async def health_check(self) -> dict:
        """SIEM ulanishini tekshiradi."""
        if not self._enabled:
            return {"enabled": False, "backend": self._backend_name, "status": "disabled"}
        if not self._client.is_configured():
            return {
                "enabled": True,
                "backend": self._backend_name,
                "status": "not_configured",
                "message": "SIEM_URL va SIEM_TOKEN ni .env da sozlang",
            }
        # Test event yuborish
        test_event = _build_event(
            event_type="HEALTH_CHECK",
            severity="info",
            message="IntegrityBot SIEM health check",
        )
        try:
            success = await asyncio.wait_for(
                self._client.send(test_event), timeout=5.0
            )
            return {
                "enabled": True,
                "backend": self._backend_name,
                "status": "ok" if success else "error",
                "message": "Ulanish muvaffaqiyatli" if success else "Yuborishda muammo",
            }
        except Exception as e:
            return {
                "enabled": True,
                "backend": self._backend_name,
                "status": "error",
                "message": str(e),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
siem_service = SIEMService()

