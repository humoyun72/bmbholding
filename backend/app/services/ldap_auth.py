"""
🔐 LDAP / Active Directory Autentifikatsiya Servisi
====================================================

TZ talabi (bo'lim 9):
  "SSO/LDAP integratsiya (mumkin bo'lsa)"

Qo'llab-quvvatlanadigan serverlar:
  - Microsoft Active Directory (AD)
  - OpenLDAP
  - FreeIPA
  - Azure AD (LDAPS orqali)

Sozlash (.env):
  LDAP_ENABLED=true
  LDAP_URL=ldap://dc.yourcompany.uz         # yoki ldaps:// SSL uchun
  LDAP_DOMAIN=yourcompany.uz                # AD domain (user@domain uchun)
  LDAP_BASE_DN=DC=yourcompany,DC=uz         # Qidiruv uchun base DN
  LDAP_BIND_DN=CN=ldap-reader,OU=Service Accounts,DC=yourcompany,DC=uz
  LDAP_BIND_PASSWORD=service_account_pass   # Read-only service account paroli
  LDAP_USER_FILTER=(sAMAccountName={username})
  LDAP_GROUP_ADMIN=CN=IntegrityBot-Admins,OU=Groups,DC=yourcompany,DC=uz
  LDAP_GROUP_INVESTIGATOR=CN=IntegrityBot-Investigators,OU=Groups,DC=yourcompany,DC=uz
  LDAP_USE_SSL=false                        # ldaps:// uchun true
  LDAP_TLS_VALIDATE=true                    # SSL sertifikat tekshirish

Ishlash tartibi:
  1. Foydalanuvchi login va parolni kiritadi
  2. LDAP serverga ulanadi (bind DN bilan)
  3. Foydalanuvchini qidiradi (sAMAccountName yoki uid)
  4. Foydalanuvchi paroli bilan tekshiradi (re-bind)
  5. Guruhlarini aniqlaydi → IntegrityBot roli belgilanadi
  6. DB da foydalanuvchi avtomatik yaratiladi yoki yangilanadi
"""

import logging
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LDAPUser:
    """LDAP dan olingan foydalanuvchi ma'lumotlari."""
    username: str
    email: str
    full_name: str
    groups: list[str]
    dn: str


def is_ldap_enabled() -> bool:
    """LDAP integratsiya sozlanganmi?"""
    return bool(
        getattr(settings, "LDAP_ENABLED", False)
        and getattr(settings, "LDAP_URL", None)
    )


async def authenticate_ldap(username: str, password: str) -> Optional[LDAPUser]:
    """
    LDAP / Active Directory orqali autentifikatsiya.

    Args:
        username: Foydalanuvchi nomi (parolsiz, masalan: "john.doe")
        password: Parol

    Returns:
        LDAPUser — muvaffaqiyatli autentifikatsiya
        None — xato yoki LDAP sozlanmagan
    """
    if not is_ldap_enabled():
        return None

    try:
        import ldap3
        from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE
        from ldap3.core.exceptions import LDAPBindError, LDAPException
    except ImportError:
        logger.warning("ldap3 kutubxonasi o'rnatilmagan. 'pip install ldap3' ni bajaring.")
        return None

    ldap_url = settings.LDAP_URL
    base_dn = getattr(settings, "LDAP_BASE_DN", "")
    bind_dn = getattr(settings, "LDAP_BIND_DN", "")
    bind_password = getattr(settings, "LDAP_BIND_PASSWORD", "")
    user_filter_template = getattr(
        settings, "LDAP_USER_FILTER", "(sAMAccountName={username})"
    )
    use_ssl = getattr(settings, "LDAP_USE_SSL", False)
    tls_validate = getattr(settings, "LDAP_TLS_VALIDATE", True)
    domain = getattr(settings, "LDAP_DOMAIN", "")

    try:
        # ── 1. Server sozlash ────────────────────────────────────────────
        tls = None
        if use_ssl or ldap_url.startswith("ldaps://"):
            import ssl
            tls = ldap3.Tls(
                validate=ssl.CERT_REQUIRED if tls_validate else ssl.CERT_NONE
            )

        server = Server(ldap_url, use_ssl=use_ssl, tls=tls, get_info=ALL)

        # ── 2. Service account bilan bind (foydalanuvchini qidirish uchun) ─
        if bind_dn and bind_password:
            bind_conn = Connection(
                server,
                user=bind_dn,
                password=bind_password,
                auto_bind=True,
                authentication=SIMPLE,
            )
        elif domain:
            # AD: domain\username format
            bind_conn = Connection(
                server,
                user=f"{domain}\\{username}",
                password=password,
                auto_bind=True,
                authentication=NTLM,
            )
        else:
            # Simple bind — to'g'ridan username bilan
            bind_conn = Connection(
                server,
                user=username,
                password=password,
                auto_bind=True,
            )

        # ── 3. Foydalanuvchini qidirish ───────────────────────────────────
        user_filter = user_filter_template.format(username=_escape_ldap(username))
        bind_conn.search(
            search_base=base_dn,
            search_filter=user_filter,
            search_scope=SUBTREE,
            attributes=[
                "distinguishedName", "sAMAccountName", "uid",
                "displayName", "cn", "mail", "memberOf",
                "userPrincipalName",
            ],
        )

        if not bind_conn.entries:
            logger.warning(f"LDAP: foydalanuvchi topilmadi: {username}")
            bind_conn.unbind()
            return None

        entry = bind_conn.entries[0]
        user_dn = str(entry.distinguishedName) if hasattr(entry, "distinguishedName") else entry.entry_dn

        # ── 4. Foydalanuvchi paroli bilan qayta autentifikatsiya ──────────
        if bind_dn and bind_password:
            # Service account ishlatilgan bo'lsa — foydalanuvchining o'zi bilan bind
            try:
                user_conn = Connection(
                    server,
                    user=user_dn,
                    password=password,
                    auto_bind=True,
                    authentication=SIMPLE,
                )
                user_conn.unbind()
            except LDAPBindError:
                logger.warning(f"LDAP: noto'g'ri parol: {username}")
                bind_conn.unbind()
                return None

        # ── 5. Ma'lumotlarni yig'ish ──────────────────────────────────────
        def _attr(name: str) -> str:
            try:
                val = getattr(entry, name, None)
                if val:
                    return str(val)
            except Exception:
                pass
            return ""

        email = (
            _attr("mail")
            or _attr("userPrincipalName")
            or f"{username}@{domain}"
            if domain else username
        )
        full_name = _attr("displayName") or _attr("cn") or username
        groups_raw = entry.memberOf.values if hasattr(entry, "memberOf") and entry.memberOf else []
        groups = [str(g) for g in groups_raw]

        bind_conn.unbind()

        return LDAPUser(
            username=username,
            email=email,
            full_name=full_name,
            groups=groups,
            dn=user_dn,
        )

    except LDAPBindError:
        logger.warning(f"LDAP: autentifikatsiya muvaffaqiyatsiz: {username}")
        return None
    except Exception as e:
        logger.error(f"LDAP: kutilmagan xato: {e}")
        return None


def get_role_from_ldap_groups(groups: list[str]) -> str:
    """
    LDAP guruhlaridan IntegrityBot rolini aniqlaydi.

    Guruh DN lar .env da sozlanadi:
      LDAP_GROUP_ADMIN=CN=IntegrityBot-Admins,...
      LDAP_GROUP_INVESTIGATOR=CN=IntegrityBot-Investigators,...
    Aks holda — default 'viewer' roli beriladi.
    """
    admin_group = getattr(settings, "LDAP_GROUP_ADMIN", "").lower()
    investigator_group = getattr(settings, "LDAP_GROUP_INVESTIGATOR", "").lower()

    groups_lower = [g.lower() for g in groups]

    if admin_group and any(admin_group in g for g in groups_lower):
        return "admin"
    if investigator_group and any(investigator_group in g for g in groups_lower):
        return "investigator"
    return "viewer"


def _escape_ldap(value: str) -> str:
    """LDAP injection oldini olish uchun maxsus belgilarni escape qiladi."""
    # RFC 4515 bo'yicha escape
    escape_map = {
        "\\": "\\5c",
        "*":  "\\2a",
        "(":  "\\28",
        ")":  "\\29",
        "\0": "\\00",
    }
    for char, escaped in escape_map.items():
        value = value.replace(char, escaped)
    return value

