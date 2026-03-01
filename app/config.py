from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


def _parse_int_list(value: str | None) -> List[int]:
    if not value:
        return []
    items = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        items.append(int(part))
    return items


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_hours(value: str | None, default_hours: float = 24.0) -> float:
    if not value:
        return default_hours
    raw = value.strip().lower()
    if not raw:
        return default_hours
    if raw.endswith("h"):
        return float(raw[:-1])
    if raw.endswith("m"):
        return float(raw[:-1]) / 60.0
    if raw.endswith("s"):
        return float(raw[:-1]) / 3600.0
    return float(raw)


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    raw = value.strip()
    if not raw:
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    main_bot_token: str
    main_bot_username: str
    main_bot_link: str
    owner_id: int
    admin_ids: List[int]
    support_group_id: Optional[int]
    reset_password: str
    database_url: str
    delete_after_hours: float
    db_encryption_key: Optional[str]
    log_chat_id: Optional[int]
    subscription_cache_ttl: int
    movie_cache_enabled: bool
    web_admin_enabled: bool
    web_admin_username: str
    web_admin_password: str
    web_host: str
    web_port: int
    web_session_hours: int
    web_session_secret: str
    web_app_url: str
    send_caption_default: bool


def load_settings() -> Settings:
    load_dotenv()

    main_bot_token = os.getenv("MAIN_BOT_TOKEN", "").strip()
    if not main_bot_token:
        raise RuntimeError("MAIN_BOT_TOKEN is required")

    main_bot_username = os.getenv("MAIN_BOT_USERNAME", "").strip().lstrip("@")
    if not main_bot_username:
        raise RuntimeError("MAIN_BOT_USERNAME is required")

    main_bot_link = os.getenv("MAIN_BOT_LINK", "").strip()
    if not main_bot_link:
        main_bot_link = f"https://t.me/{main_bot_username}"

    owner_id_raw = os.getenv("OWNER_ID", "").strip()
    owner_id: Optional[int] = int(owner_id_raw) if owner_id_raw else None

    admin_ids = _parse_int_list(os.getenv("ADMIN_IDS"))
    if owner_id is None:
        if admin_ids:
            owner_id = admin_ids[0]
        else:
            raise RuntimeError("OWNER_ID is required (or put owner as first ADMIN_IDS item)")

    support_group_raw = os.getenv("SUPPORT_GROUP_ID", "").strip()
    support_group_id = int(support_group_raw) if support_group_raw else None
    reset_password = os.getenv("RESET_PASSWORD", "Mustafo202214@")

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data.sqlite3").strip()
    delete_after_hours = _parse_hours(os.getenv("DELETE_AFTER_HOURS", "24"))
    db_encryption_key = os.getenv("DB_ENCRYPTION_KEY") or None
    log_chat_id_raw = os.getenv("LOG_CHAT_ID", "").strip()
    log_chat_id = int(log_chat_id_raw) if log_chat_id_raw else None
    subscription_cache_ttl = int(os.getenv("SUBSCRIPTION_CACHE_TTL", "30"))
    movie_cache_enabled = _parse_bool(os.getenv("MOVIE_CACHE_ENABLED", "1"), default=True)
    web_admin_enabled = _parse_bool(os.getenv("WEB_ADMIN_ENABLED", "1"), default=True)
    web_admin_username = os.getenv("WEB_ADMIN_USERNAME", "admin").strip() or "admin"
    web_admin_password = os.getenv("WEB_ADMIN_PASSWORD", "").strip() or reset_password
    web_host = os.getenv("WEB_HOST", "0.0.0.0").strip() or "0.0.0.0"
    web_port = _parse_int(os.getenv("WEB_PORT", "8080"), default=8080)
    web_session_hours = _parse_int(os.getenv("WEB_SESSION_HOURS", "12"), default=12)
    web_app_url = os.getenv("WEB_APP_URL", "").strip()

    web_session_secret = (os.getenv("WEB_SESSION_SECRET", "").strip() or db_encryption_key or "").strip()
    if not web_session_secret:
        web_session_secret = f"{main_bot_token}:{owner_id}"
    send_caption_default = _parse_bool(os.getenv("SEND_CAPTION_DEFAULT", "0"), default=False)

    return Settings(
        main_bot_token=main_bot_token,
        main_bot_username=main_bot_username,
        main_bot_link=main_bot_link,
        owner_id=owner_id,
        admin_ids=admin_ids,
        support_group_id=support_group_id,
        reset_password=reset_password,
        database_url=database_url,
        delete_after_hours=delete_after_hours,
        db_encryption_key=db_encryption_key,
        log_chat_id=log_chat_id,
        subscription_cache_ttl=subscription_cache_ttl,
        movie_cache_enabled=movie_cache_enabled,
        web_admin_enabled=web_admin_enabled,
        web_admin_username=web_admin_username,
        web_admin_password=web_admin_password,
        web_host=web_host,
        web_port=web_port,
        web_session_hours=web_session_hours,
        web_session_secret=web_session_secret,
        web_app_url=web_app_url,
        send_caption_default=send_caption_default,
    )
