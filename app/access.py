from __future__ import annotations

from .config import Settings
from .db import Database


def is_owner(settings: Settings, user_id: int) -> bool:
    return user_id == settings.owner_id


def is_admin(settings: Settings, user_id: int) -> bool:
    return user_id in settings.admin_ids


def is_staff(settings: Settings, user_id: int) -> bool:
    return is_owner(settings, user_id) or is_admin(settings, user_id)


async def get_effective_admin_ids(db: Database, settings: Settings) -> list[int]:
    dynamic = await db.get_dynamic_admin_ids()
    merged = set(settings.admin_ids)
    merged.update(dynamic)
    if settings.owner_id in merged:
        merged.remove(settings.owner_id)
    return sorted(merged)


async def is_admin_dynamic(db: Database, settings: Settings, user_id: int) -> bool:
    if user_id in settings.admin_ids:
        return True
    dynamic = await db.get_dynamic_admin_ids()
    return user_id in dynamic


async def is_staff_dynamic(db: Database, settings: Settings, user_id: int) -> bool:
    return is_owner(settings, user_id) or await is_admin_dynamic(db, settings, user_id)
