"""
🎫 Jira / Redmine Integratsiya Servisi
======================================

TZ talabi (bo'lim 10):
  "Jira/Redmine integratsiya — opsional: kritik yangi xabarlarda tiket yaratadi"

Qo'llab-quvvatlanadigan tizimlar:
  - Jira Cloud (Atlassian)   — JIRA_URL + JIRA_TOKEN + JIRA_USER_EMAIL
  - Jira Server/DC (on-prem) — JIRA_URL + JIRA_TOKEN (Bearer)
  - Redmine                  — REDMINE_URL + REDMINE_API_KEY

Sozlash (.env):
  JIRA_URL=https://yourcompany.atlassian.net
  JIRA_TOKEN=your_api_token
  JIRA_USER_EMAIL=admin@yourcompany.com   # Cloud uchun
  JIRA_PROJECT_KEY=COMP
  JIRA_ISSUE_TYPE=Task
  JIRA_MIN_PRIORITY=critical   # critical | high | all

  # Yoki Redmine:
  REDMINE_URL=http://redmine.yourcompany.uz
  REDMINE_API_KEY=your_api_key
  REDMINE_PROJECT_ID=integritybot

Ishlatish:
  from app.services.jira_integration import ticket_service

  result = await ticket_service.create_ticket_for_case(case)
  if result.created:
      print(f"Tiket yaratildi: {result.ticket_id} — {result.url}")
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Prioritylarni Jira formatiga mapping ─────────────────────────────────────
JIRA_PRIORITY_MAP = {
    "critical": "Critical",
    "high":     "High",
    "medium":   "Medium",
    "low":      "Low",
}

REDMINE_PRIORITY_MAP = {
    "critical": "Immediate",
    "high":     "Urgent",
    "medium":   "Normal",
    "low":      "Low",
}

# Qaysi prioritylardan tiket ochilishi kerak
PRIORITY_ORDER = ["critical", "high", "medium", "low"]


# ── Natija data class ─────────────────────────────────────────────────────────

@dataclass
class TicketResult:
    """Tiket yaratish natijasi."""
    created: bool = False
    ticket_id: Optional[str] = None     # Masalan: "COMP-123" yoki "#456"
    url: Optional[str] = None           # Tiketga to'g'ridan havola
    system: Optional[str] = None        # "jira" | "redmine"
    error: Optional[str] = None         # Xato xabari (agar bo'lsa)
    skipped: bool = False               # Priority yetarli emas — o'tkazib yuborildi
    skip_reason: Optional[str] = None


# ── Jira Client ──────────────────────────────────────────────────────────────

class JiraClient:
    """Jira Cloud va Server/DC bilan ishlash."""

    def __init__(self):
        self.base_url = (settings.JIRA_URL or "").rstrip("/")
        self.token = settings.JIRA_TOKEN
        self.email = settings.JIRA_USER_EMAIL
        self.project_key = settings.JIRA_PROJECT_KEY
        self.issue_type = settings.JIRA_ISSUE_TYPE

    def is_configured(self) -> bool:
        return bool(self.base_url and self.token and self.project_key)

    def _get_headers(self) -> dict:
        """Auth headers — Cloud (Basic) yoki Server (Bearer)."""
        if self.email:
            # Atlassian Cloud: Basic auth (email:token)
            import base64
            creds = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
            return {
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        else:
            # Jira Server/DC: Bearer token (PAT)
            return {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

    async def create_issue(
        self,
        case_id: str,
        category: str,
        priority: str,
        description: str,
        is_anonymous: bool,
    ) -> TicketResult:
        """Jira da yangi issue yaratadi."""
        if not self.is_configured():
            return TicketResult(
                created=False,
                error="Jira sozlanmagan (JIRA_URL, JIRA_TOKEN, JIRA_PROJECT_KEY kerak)"
            )

        try:
            import aiohttp
        except ImportError:
            return TicketResult(
                created=False,
                error="aiohttp o'rnatilmagan: pip install aiohttp"
            )

        jira_priority = JIRA_PRIORITY_MAP.get(priority.lower(), "Medium")
        anon_note = "🔒 Anonim murojaat" if is_anonymous else "👤 Anonim emas"

        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"[IntegrityBot] {case_id} — {category.replace('_', ' ').title()}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": line}]
                        }
                        for line in [
                            f"📋 Murojaat ID: {case_id}",
                            f"📁 Kategoriya: {category}",
                            f"⚡ Ustuvorlik: {priority}",
                            f"{anon_note}",
                            "",
                            "📝 Tavsif:",
                            description[:2000] + ("..." if len(description) > 2000 else ""),
                            "",
                            f"🔗 Admin panel: {settings.ALLOWED_ORIGINS.split(',')[0]}/cases/{case_id}",
                        ]
                    ],
                },
                "issuetype": {"name": self.issue_type},
                "priority": {"name": jira_priority},
                "labels": ["IntegrityBot", category, priority],
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/rest/api/3/issue",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        ticket_key = data.get("key", "")
                        ticket_url = f"{self.base_url}/browse/{ticket_key}"
                        logger.info(f"Jira tiket yaratildi: {ticket_key} — {case_id}")
                        return TicketResult(
                            created=True,
                            ticket_id=ticket_key,
                            url=ticket_url,
                            system="jira",
                        )
                    else:
                        body = await resp.text()
                        error_msg = f"Jira HTTP {resp.status}: {body[:200]}"
                        logger.error(f"Jira tiket yaratishda xato: {error_msg}")
                        return TicketResult(created=False, error=error_msg, system="jira")

        except Exception as e:
            logger.error(f"Jira ulanish xatosi ({case_id}): {e}")
            return TicketResult(created=False, error=str(e), system="jira")

    async def add_comment(self, ticket_id: str, comment: str) -> bool:
        """Mavjud Jira tiketga izoh qo'shadi."""
        if not self.is_configured():
            return False
        try:
            import aiohttp
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}],
                }
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/rest/api/3/issue/{ticket_id}/comment",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status in (200, 201)
        except Exception as e:
            logger.error(f"Jira comment xatosi: {e}")
            return False

    async def transition_issue(self, ticket_id: str, status_name: str) -> bool:
        """Tiket statusini o'zgartiradi (masalan: 'Done', 'In Progress')."""
        if not self.is_configured():
            return False
        try:
            import aiohttp
            # Avval mavjud transitionlarni olamiz
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/rest/api/3/issue/{ticket_id}/transitions",
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()

                transitions = data.get("transitions", [])
                target = next(
                    (t for t in transitions if t["name"].lower() == status_name.lower()),
                    None
                )
                if not target:
                    logger.warning(f"Jira transition '{status_name}' topilmadi")
                    return False

                async with session.post(
                    f"{self.base_url}/rest/api/3/issue/{ticket_id}/transitions",
                    json={"transition": {"id": target["id"]}},
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 204
        except Exception as e:
            logger.error(f"Jira transition xatosi: {e}")
            return False


# ── Redmine Client ────────────────────────────────────────────────────────────

class RedmineClient:
    """Redmine REST API bilan ishlash."""

    def __init__(self):
        self.base_url = (settings.REDMINE_URL or "").rstrip("/")
        self.api_key = settings.REDMINE_API_KEY
        self.project_id = settings.REDMINE_PROJECT_ID

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.project_id)

    def _get_headers(self) -> dict:
        return {
            "X-Redmine-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_issue(
        self,
        case_id: str,
        category: str,
        priority: str,
        description: str,
        is_anonymous: bool,
    ) -> TicketResult:
        """Redmine da yangi issue yaratadi."""
        if not self.is_configured():
            return TicketResult(
                created=False,
                error="Redmine sozlanmagan (REDMINE_URL, REDMINE_API_KEY, REDMINE_PROJECT_ID kerak)"
            )

        try:
            import aiohttp
        except ImportError:
            return TicketResult(created=False, error="aiohttp o'rnatilmagan")

        redmine_priority = REDMINE_PRIORITY_MAP.get(priority.lower(), "Normal")
        anon_note = "🔒 Anonim murojaat" if is_anonymous else "👤 Anonim emas"

        full_description = (
            f"*Murojaat ID:* {case_id}\n"
            f"*Kategoriya:* {category}\n"
            f"*Ustuvorlik:* {priority}\n"
            f"*{anon_note}*\n\n"
            f"*Tavsif:*\n{description[:3000]}\n\n"
            f"*Admin panel:* {settings.ALLOWED_ORIGINS.split(',')[0]}/cases/{case_id}"
        )

        payload = {
            "issue": {
                "project_id": self.project_id,
                "subject": f"[IntegrityBot] {case_id} — {category.replace('_', ' ').title()}",
                "description": full_description,
                "priority_id": None,  # Nom bilan belgilanadi
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                # Avval priority ID ni topamiz
                async with session.get(
                    f"{self.base_url}/enumerations/issue_priorities.json",
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        priorities = data.get("issue_priorities", [])
                        priority_obj = next(
                            (p for p in priorities if p["name"].lower() == redmine_priority.lower()),
                            None
                        )
                        if priority_obj:
                            payload["issue"]["priority_id"] = priority_obj["id"]

                # Tiket yaratish
                async with session.post(
                    f"{self.base_url}/issues.json",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        issue_id = data.get("issue", {}).get("id", "")
                        ticket_url = f"{self.base_url}/issues/{issue_id}"
                        logger.info(f"Redmine tiket yaratildi: #{issue_id} — {case_id}")
                        return TicketResult(
                            created=True,
                            ticket_id=f"#{issue_id}",
                            url=ticket_url,
                            system="redmine",
                        )
                    else:
                        body = await resp.text()
                        error_msg = f"Redmine HTTP {resp.status}: {body[:200]}"
                        logger.error(f"Redmine tiket xatosi: {error_msg}")
                        return TicketResult(created=False, error=error_msg, system="redmine")

        except Exception as e:
            logger.error(f"Redmine ulanish xatosi ({case_id}): {e}")
            return TicketResult(created=False, error=str(e), system="redmine")

    async def add_comment(self, ticket_id: str, comment: str) -> bool:
        """Redmine tiketga izoh qo'shadi. ticket_id: '#123' yoki '123'."""
        if not self.is_configured():
            return False
        issue_id = ticket_id.lstrip("#")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.base_url}/issues/{issue_id}.json",
                    json={"issue": {"notes": comment}},
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Redmine comment xatosi: {e}")
            return False


# ── Unified Ticket Service ────────────────────────────────────────────────────

class TicketService:
    """
    Yagona tiket servisi — Jira yoki Redmine ni avtomatik tanlaydi.
    Ikkalasi ham sozlangan bo'lsa — Jira ustunlik qiladi.
    """

    def __init__(self):
        self._jira = JiraClient()
        self._redmine = RedmineClient()

    def is_configured(self) -> bool:
        return self._jira.is_configured() or self._redmine.is_configured()

    def active_system(self) -> Optional[str]:
        if self._jira.is_configured():
            return "jira"
        if self._redmine.is_configured():
            return "redmine"
        return None

    def _should_create_ticket(self, priority: str) -> tuple[bool, str]:
        """
        Berilgan priority uchun tiket yaratish kerakmi?
        JIRA_MIN_PRIORITY ga qarab qaror qabul qilinadi.
        """
        min_p = settings.JIRA_MIN_PRIORITY.lower()
        if min_p == "all":
            return True, ""

        priority_lower = priority.lower()
        if priority_lower not in PRIORITY_ORDER:
            return True, ""  # Noma'lum priority — yaratib qo'yamiz

        min_index = PRIORITY_ORDER.index(min_p) if min_p in PRIORITY_ORDER else 0
        current_index = PRIORITY_ORDER.index(priority_lower)

        if current_index <= min_index:
            return True, ""
        return False, f"Priority '{priority}' min threshold '{min_p}' dan past"

    async def create_ticket_for_case(
        self,
        case_id: str,
        category: str,
        priority: str,
        description: str,
        is_anonymous: bool = True,
    ) -> TicketResult:
        """
        Murojaat uchun tiket yaratadi.
        Priority yetarli bo'lmasa — o'tkazib yuboradi (skipped=True).
        """
        if not self.is_configured():
            logger.debug("Tiket servisi sozlanmagan — o'tkazib yuborildi")
            return TicketResult(
                skipped=True,
                skip_reason="Jira ham Redmine ham sozlanmagan",
            )

        # Priority tekshiruvi
        should_create, skip_reason = self._should_create_ticket(priority)
        if not should_create:
            logger.info(f"Tiket yaratilmadi ({case_id}): {skip_reason}")
            return TicketResult(skipped=True, skip_reason=skip_reason)

        # Tiket yaratish
        if self._jira.is_configured():
            result = await self._jira.create_issue(
                case_id=case_id,
                category=category,
                priority=priority,
                description=description,
                is_anonymous=is_anonymous,
            )
        else:
            result = await self._redmine.create_issue(
                case_id=case_id,
                category=category,
                priority=priority,
                description=description,
                is_anonymous=is_anonymous,
            )

        return result

    async def update_ticket_on_case_status_change(
        self,
        ticket_id: str,
        new_status: str,
        case_id: str,
        comment: Optional[str] = None,
    ) -> bool:
        """
        Murojaat statusini o'zgartirganda tiketni ham yangilaydi.
        """
        if not self.is_configured() or not ticket_id:
            return False

        # Status mapping: case status → Jira/Redmine status
        STATUS_COMMENT_MAP = {
            "in_progress": f"✅ {case_id} murojaati ko'rib chiqilmoqda.",
            "completed":   f"✅ {case_id} murojaati yakunlandi.",
            "rejected":    f"❌ {case_id} murojaati rad etildi.",
            "needs_info":  f"❓ {case_id} murojaati bo'yicha qo'shimcha ma'lumot kerak.",
        }
        note = comment or STATUS_COMMENT_MAP.get(new_status, f"Status yangilandi: {new_status}")

        if self._jira.is_configured():
            # Jira da izoh qo'shib, transition qilamiz
            await self._jira.add_comment(ticket_id, note)
            jira_status_map = {
                "in_progress": "In Progress",
                "completed":   "Done",
                "rejected":    "Won't Do",
                "needs_info":  "In Progress",
            }
            jira_status = jira_status_map.get(new_status)
            if jira_status:
                return await self._jira.transition_issue(ticket_id, jira_status)
            return True
        else:
            return await self._redmine.add_comment(ticket_id, note)

    async def health_check(self) -> dict:
        """Tiket tizimi ulanishini tekshiradi."""
        system = self.active_system()
        if not system:
            return {
                "enabled": False,
                "system": None,
                "status": "disabled",
                "message": "Jira ham Redmine ham sozlanmagan",
            }

        try:
            import aiohttp
            if system == "jira":
                url = f"{self._jira.base_url}/rest/api/3/myself"
                headers = self._jira._get_headers()
            else:
                url = f"{self._redmine.base_url}/users/current.json"
                headers = self._redmine._get_headers()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        return {"enabled": True, "system": system, "status": "ok"}
                    return {
                        "enabled": True,
                        "system": system,
                        "status": "error",
                        "message": f"HTTP {resp.status}",
                    }
        except Exception as e:
            return {
                "enabled": True,
                "system": system,
                "status": "error",
                "message": str(e),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
ticket_service = TicketService()

