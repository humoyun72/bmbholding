"""
Avtomatik deadline hisoblash xizmati.
Priority asosida due_at sanasini aniqlaydi.
"""
from datetime import datetime, timedelta, timezone

# Priority → soat hisobida deadline
DEADLINE_HOURS: dict[str, int] = {
    "critical": 24,      # 1 kun
    "high":     72,      # 3 kun
    "medium":   168,     # 7 kun
    "low":      720,     # 30 kun
}


def calculate_due_at(priority, created_at: datetime | None = None) -> datetime:
    """
    Priority asosida deadline sanasini hisoblaydi.

    Args:
        priority: CasePriority enum yoki str (masalan "critical")
        created_at: Boshlanish sanasi (default: hozirgi vaqt)

    Returns:
        datetime: due_at sanasi (UTC)
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    # Enum yoki str bo'lishi mumkin
    pri_value = priority.value if hasattr(priority, "value") else str(priority)

    hours = DEADLINE_HOURS.get(pri_value, DEADLINE_HOURS["medium"])
    return created_at + timedelta(hours=hours)

