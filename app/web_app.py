from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import hmac
import json
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from aiogram import Bot
from aiogram.types import BufferedInputFile
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .access import get_effective_admin_ids, is_admin_dynamic
from .cache import ChannelCache, MovieCache
from .config import Settings, load_settings
from .crypto import Crypto
from .db import Database, MovieRecord
from .handlers.channel import sync_channel_history

SESSION_COOKIE = "kino_admin_session"
SEND_CAPTION_SETTING_KEY = "send_caption_to_user"
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
SESSION_SRC_LOCAL = "local"
SESSION_SRC_TG = "tg"
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"


@dataclass
class WebContext:
    settings: Settings
    db: Database
    bot: Bot
    channel_cache: ChannelCache
    movie_cache: MovieCache
    broadcast_tasks: dict[int, asyncio.Task] = field(default_factory=dict)


@dataclass
class WebIdentity:
    role: str
    source: str
    display_name: str
    user_id: Optional[int] = None

    @property
    def is_owner(self) -> bool:
        return self.role == ROLE_OWNER

    @property
    def home_path(self) -> str:
        return "/admin/owner" if self.is_owner else "/admin/admin"


def _hash_session_token(raw_token: str, secret: str) -> str:
    return hashlib.sha256(f"{raw_token}:{secret}".encode("utf-8")).hexdigest()


def _normalize_role(value: Optional[str]) -> str:
    role = (value or "").strip().lower()
    if role == ROLE_OWNER:
        return ROLE_OWNER
    return ROLE_ADMIN


def _pack_tg_session_username(user_id: int, role: str) -> str:
    clean_role = _normalize_role(role)
    return f"{SESSION_SRC_TG}:{int(user_id)}:{clean_role}"


def _pack_local_session_username(username: str, role: str = ROLE_OWNER) -> str:
    clean_name = (username or "admin").strip() or "admin"
    clean_role = _normalize_role(role)
    return f"{SESSION_SRC_LOCAL}:{clean_name}:{clean_role}"


def _parse_session_username(raw: str) -> tuple[str, Optional[int], str, str]:
    text = str(raw or "").strip()
    if text.startswith(f"{SESSION_SRC_TG}:"):
        parts = text.split(":", 2)
        if len(parts) == 3 and parts[1].lstrip("-").isdigit():
            uid = int(parts[1])
            role = _normalize_role(parts[2])
            return SESSION_SRC_TG, uid, role, f"ID {uid}"
    if text.startswith(f"{SESSION_SRC_LOCAL}:"):
        parts = text.split(":", 2)
        if len(parts) >= 2:
            username = parts[1].strip() or "admin"
            role = _normalize_role(parts[2] if len(parts) == 3 else ROLE_OWNER)
            return SESSION_SRC_LOCAL, None, role, username
    # legacy fallback
    return SESSION_SRC_LOCAL, None, ROLE_OWNER, text or "admin"


def _verify_tg_signature(secret: str, user_id: int, role: str, exp: int, sig: str) -> bool:
    payload = f"{user_id}:{role}:{exp}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig.strip().lower())


def _verify_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 900,
) -> tuple[bool, Optional[int], str]:
    raw = (init_data or "").strip()
    if not raw:
        return False, None, "Telegram initData topilmadi"
    try:
        pairs = dict(parse_qsl(raw, keep_blank_values=True))
        received_hash = (pairs.pop("hash", "") or "").strip().lower()
        if not received_hash:
            return False, None, "Telegram hash topilmadi"

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest().lower()
        if not hmac.compare_digest(calculated_hash, received_hash):
            return False, None, "Telegram initData imzosi xato"

        auth_date_raw = str(pairs.get("auth_date", "")).strip()
        if not auth_date_raw.isdigit():
            return False, None, "Telegram auth_date xato"
        auth_date = int(auth_date_raw)
        now_ts = int(time.time())
        if auth_date > now_ts + 60:
            return False, None, "Telegram auth vaqti noto'g'ri"
        if now_ts - auth_date > max_age_seconds:
            return False, None, "Telegram auth eskirgan. Qayta oching."

        user_raw = str(pairs.get("user", "")).strip()
        if not user_raw:
            return False, None, "Telegram user topilmadi"
        user_obj = json.loads(user_raw)
        user_id = int(user_obj.get("id") or 0)
        if user_id <= 0:
            return False, None, "Telegram user id xato"
        return True, user_id, ""
    except Exception:
        return False, None, "Telegram initData parse xatosi"


def _parse_page(value: Optional[str], default: int = 1) -> int:
    try:
        page = int(value or default)
    except ValueError:
        return default
    return max(page, 1)


def _is_true(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


def _append_query(url: str, **updates: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({k: v for k, v in updates.items() if v is not None})
    return urlunparse(parsed._replace(query=urlencode(query)))


def _set_session_cookie(response: RedirectResponse, raw_token: str, session_hours: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        max_age=session_hours * 3600,
        httponly=True,
        secure=False,
        samesite="lax",
    )


async def _create_session_response(
    *,
    ctx: WebContext,
    session_username: str,
    redirect_url: str,
) -> RedirectResponse:
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_session_token(raw_token, ctx.settings.web_session_secret)
    expires_at = dt.datetime.utcnow() + dt.timedelta(hours=ctx.settings.web_session_hours)
    await ctx.db.create_admin_session(token_hash=token_hash, username=session_username, expires_at=expires_at)
    response = _redirect(redirect_url)
    _set_session_cookie(response, raw_token, ctx.settings.web_session_hours)
    return response


def _current_actor_id(request: Request, settings: Settings) -> int:
    uid = getattr(request.state, "session_user_id", None)
    if uid is None:
        return settings.owner_id
    return int(uid)


def _ensure_owner_or_redirect(request: Request) -> Optional[RedirectResponse]:
    if getattr(request.state, "is_owner", False):
        return None
    return _redirect("/admin/admin?err=Bu bo'lim faqat owner uchun")


def _template_data(request: Request, page_title: str, **kwargs):
    identity: WebIdentity | None = getattr(request.state, "identity", None)
    return {
        "request": request,
        "page_title": page_title,
        "admin_username": getattr(request.state, "admin_username", None),
        "session_role": getattr(request.state, "session_role", None),
        "session_user_id": getattr(request.state, "session_user_id", None),
        "is_owner": getattr(request.state, "is_owner", False),
        "home_path": getattr(request.state, "home_path", "/admin"),
        "identity": identity,
        "ok": request.query_params.get("ok"),
        "err": request.query_params.get("err"),
        **kwargs,
    }


async def _format_user_display_name(db: Database, user_id: int) -> str:
    user = await db.get_user(user_id)
    if not user:
        return f"ID {user_id}"
    full_name = " ".join(
        [
            part.strip()
            for part in [str(user.get("first_name") or ""), str(user.get("last_name") or "")]
            if part and part.strip()
        ]
    ).strip()
    username = (user.get("username") or "").strip()
    if full_name and username:
        return f"{full_name} (@{username})"
    if full_name:
        return full_name
    if username:
        return f"@{username}"
    return f"ID {user_id}"


async def _authenticated_identity(request: Request) -> Optional[WebIdentity]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    ctx: WebContext = request.app.state.ctx
    token_hash = _hash_session_token(token, ctx.settings.web_session_secret)
    session_row = await ctx.db.get_admin_session(token_hash)
    if not session_row:
        return None
    source, user_id, role, display_name = _parse_session_username(str(session_row["username"]))

    # Strict mode: web admin faqat Telegram Mini App sessiyasi bilan ishlaydi.
    if source != SESSION_SRC_TG:
        return None

    if role == ROLE_OWNER:
        if user_id is None or user_id != ctx.settings.owner_id:
            return None
    else:
        if user_id is None:
            return None
        if user_id == ctx.settings.owner_id:
            role = ROLE_OWNER
        elif not await is_admin_dynamic(ctx.db, ctx.settings, user_id):
            return None

    if source == SESSION_SRC_TG and user_id is not None:
        display_name = await _format_user_display_name(ctx.db, user_id)

    return WebIdentity(
        role=role,
        source=source,
        display_name=display_name,
        user_id=user_id,
    )


def _normalize_channel_username(username: Optional[str]) -> Optional[str]:
    if not username:
        return None
    clean = username.strip().lstrip("@")
    return clean or None


def _normalize_kind(raw_kind: Optional[str]) -> str:
    if not raw_kind:
        return "movie"
    kind = raw_kind.strip().lower()
    if kind not in {"movie", "serial"}:
        return "movie"
    return kind


def _normalize_kind_filter(raw_kind: Optional[str]) -> Optional[str]:
    if not raw_kind:
        return None
    kind = raw_kind.strip().lower()
    if kind in {"movie", "serial"}:
        return kind
    return None


async def _validate_movie_slot(
    db: Database,
    *,
    code: str,
    content_kind: str,
    part_number: int,
    channel_id: int,
    message_id: int,
) -> tuple[bool, str | None]:
    parts = await db.list_movie_parts(code)
    if not parts:
        return True, None

    if content_kind == "movie":
        for item in parts:
            if item.channel_id != channel_id or item.message_id != message_id:
                return False, "Bu kod oldin ishlatilgan. Avvalgini o'chiring yoki tahrirlang."
        return True, None

    for item in parts:
        if item.content_kind == "movie" and (item.channel_id != channel_id or item.message_id != message_id):
            return False, "Bir kodda movie va serialni aralashtirib bo'lmaydi."
        if item.part_number == part_number and (item.channel_id != channel_id or item.message_id != message_id):
            return False, "Bu serial qismi allaqachon mavjud."
    return True, None


async def _run_broadcast_task(
    ctx: WebContext,
    log_id: int,
    text: str,
    include_staff: bool,
) -> None:
    try:
        await ctx.db.update_broadcast_log(log_id, status="running")

        user_ids = await ctx.db.list_all_user_ids(include_blocked=False)
        if not include_staff:
            admin_ids = await get_effective_admin_ids(ctx.db, ctx.settings)
            staff_ids = set([ctx.settings.owner_id, *admin_ids])
            user_ids = [uid for uid in user_ids if uid not in staff_ids]

        await ctx.db.update_broadcast_log(log_id, total_users=len(user_ids))
        sent = 0
        failed = 0
        for idx, user_id in enumerate(user_ids, start=1):
            try:
                await ctx.bot.send_message(chat_id=user_id, text=text)
            except Exception:
                failed += 1
            else:
                sent += 1

            if idx % 25 == 0:
                await ctx.db.update_broadcast_log(log_id, sent_count=sent, failed_count=failed)
            await asyncio.sleep(0.04)

        await ctx.db.update_broadcast_log(
            log_id,
            status="done",
            sent_count=sent,
            failed_count=failed,
            completed_at=dt.datetime.utcnow(),
        )
    except Exception as exc:
        await ctx.db.update_broadcast_log(
            log_id,
            status="failed",
            error_text=str(exc)[:500],
            completed_at=dt.datetime.utcnow(),
        )
    finally:
        ctx.broadcast_tasks.pop(log_id, None)


async def _build_user_brief(db: Database, user_id: int) -> dict:
    row = await db.get_user(user_id)
    username = None
    full_name = None
    if row:
        username = (row.get("username") or "").strip() or None
        full_name = " ".join(
            [
                part.strip()
                for part in [str(row.get("first_name") or ""), str(row.get("last_name") or "")]
                if part and part.strip()
            ]
        ).strip() or None
    return {
        "user_id": int(user_id),
        "username": username,
        "full_name": full_name,
        "display_name": full_name or (f"@{username}" if username else f"ID {user_id}"),
    }


def create_fastapi_app() -> FastAPI:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.filters["fmt_dt"] = lambda value: value.strftime("%Y-%m-%d %H:%M") if value else "-"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = load_settings()
        crypto = Crypto(settings.db_encryption_key)
        db = Database(settings.database_url, crypto)
        await db.init()
        await db.purge_expired_admin_sessions()

        bot = Bot(token=settings.main_bot_token, parse_mode=None)
        channel_cache = ChannelCache(db)
        movie_cache = MovieCache(db, enabled=settings.movie_cache_enabled)
        await movie_cache.load()

        app.state.ctx = WebContext(
            settings=settings,
            db=db,
            bot=bot,
            channel_cache=channel_cache,
            movie_cache=movie_cache,
        )
        yield

        for task in list(app.state.ctx.broadcast_tasks.values()):
            task.cancel()
        await bot.session.close()
        await db.dispose()

    app = FastAPI(title="Kino Bot Admin Web", lifespan=lifespan)
    app.mount("/admin/static", StaticFiles(directory=str(STATIC_DIR)), name="admin-static")

    @app.middleware("http")
    async def admin_auth_middleware(request: Request, call_next):
        path = request.url.path
        if not path.startswith("/admin"):
            return await call_next(request)
        if path.startswith("/admin/static") or path in {"/admin/login", "/admin/tg-auth", "/admin/tg-auth/complete"}:
            return await call_next(request)

        identity = await _authenticated_identity(request)
        if not identity:
            return RedirectResponse(url="/admin/login", status_code=303)
        request.state.identity = identity
        request.state.admin_username = identity.display_name
        request.state.session_role = identity.role
        request.state.session_user_id = identity.user_id
        request.state.is_owner = identity.is_owner
        request.state.home_path = identity.home_path
        return await call_next(request)

    @app.get("/")
    async def index() -> RedirectResponse:
        return _redirect("/admin")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "service": "kino-admin-web"}

    @app.get("/admin/login")
    async def admin_login_page(request: Request):
        return templates.TemplateResponse("login.html", _template_data(request, "Admin Login"))

    @app.post("/admin/login")
    async def admin_login(request: Request, username: str = Form(""), password: str = Form("")):
        _ = (username, password)  # direct local login disabled
        return _redirect("/admin/login?err=Faqat Telegram Mini App orqali kiring")

    @app.get("/admin/tg-auth")
    async def admin_tg_auth(
        request: Request,
        uid: int,
        role: str,
        exp: int,
        sig: str,
    ):
        ctx: WebContext = request.app.state.ctx
        clean_role = _normalize_role(role)
        now_ts = int(time.time())
        if exp < now_ts:
            return _redirect("/admin/login?err=Telegram sessiyasi muddati tugagan")
        if exp > now_ts + 3600:
            return _redirect("/admin/login?err=Telegram auth vaqti noto'g'ri")
        if not _verify_tg_signature(ctx.settings.web_session_secret, uid, clean_role, exp, sig):
            return _redirect("/admin/login?err=Telegram auth imzosi noto'g'ri")

        return templates.TemplateResponse(
            "tg_auth.html",
            _template_data(
                request,
                "Telegram Auth",
                auth_uid=uid,
                auth_role=clean_role,
                auth_exp=exp,
                auth_sig=sig,
            ),
        )

    @app.post("/admin/tg-auth/complete")
    async def admin_tg_auth_complete(
        request: Request,
        uid: int = Form(...),
        role: str = Form(...),
        exp: int = Form(...),
        sig: str = Form(...),
        init_data: str = Form(""),
    ):
        ctx: WebContext = request.app.state.ctx
        clean_role = _normalize_role(role)
        now_ts = int(time.time())
        if exp < now_ts:
            return _redirect(_append_query("/admin/login", err="Telegram sessiyasi muddati tugagan"))
        if exp > now_ts + 3600:
            return _redirect(_append_query("/admin/login", err="Telegram auth vaqti noto'g'ri"))
        if not _verify_tg_signature(ctx.settings.web_session_secret, int(uid), clean_role, int(exp), sig):
            return _redirect(_append_query("/admin/login", err="Telegram auth imzosi noto'g'ri"))

        ok, init_uid, init_err = _verify_telegram_init_data(init_data, ctx.settings.main_bot_token)
        if not ok or init_uid is None:
            return _redirect(_append_query("/admin/login", err=init_err or "Telegram auth xato"))
        if int(init_uid) != int(uid):
            return _redirect(_append_query("/admin/login", err="Telegram user mos emas"))

        if clean_role == ROLE_OWNER:
            if int(uid) != ctx.settings.owner_id:
                return _redirect(_append_query("/admin/login", err="Faqat owner owner rejimga kira oladi"))
        else:
            if int(uid) == ctx.settings.owner_id:
                clean_role = ROLE_OWNER
            else:
                is_admin = await is_admin_dynamic(ctx.db, ctx.settings, int(uid))
                if not is_admin:
                    return _redirect(_append_query("/admin/login", err="Bu user admin emas"))

        return await _create_session_response(
            ctx=ctx,
            session_username=_pack_tg_session_username(int(uid), clean_role),
            redirect_url="/admin/owner" if clean_role == ROLE_OWNER else "/admin/admin",
        )

    @app.get("/admin/logout")
    async def admin_logout(request: Request):
        ctx: WebContext = request.app.state.ctx
        raw_token = request.cookies.get(SESSION_COOKIE)
        if raw_token:
            token_hash = _hash_session_token(raw_token, ctx.settings.web_session_secret)
            await ctx.db.delete_admin_session(token_hash)
        response = _redirect("/admin/login?ok=Chiqildi")
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/admin")
    async def admin_home(request: Request):
        if getattr(request.state, "is_owner", False):
            return _redirect("/admin/owner")
        return _redirect("/admin/admin")

    async def _build_dashboard_context(ctx: WebContext) -> dict:
        users_count = await ctx.db.count_users()
        movies_count = await ctx.db.count_movies()
        movie_channels_count = await ctx.db.count_channels()
        sub_channels_count = await ctx.db.count_subscription_channels()
        blocked_count = await ctx.db.count_blocked_users()
        open_support_count = await ctx.db.count_support_tickets(status="open")
        broadcast_logs = await ctx.db.list_broadcast_logs(limit=8)
        send_caption_enabled = await ctx.db.get_bool_setting(
            SEND_CAPTION_SETTING_KEY,
            default=ctx.settings.send_caption_default,
        )
        admin_ids = await get_effective_admin_ids(ctx.db, ctx.settings)
        return {
            "users_count": users_count,
            "movies_count": movies_count,
            "movie_channels_count": movie_channels_count,
            "sub_channels_count": sub_channels_count,
            "blocked_count": blocked_count,
            "open_support_count": open_support_count,
            "broadcast_logs": broadcast_logs,
            "send_caption_enabled": send_caption_enabled,
            "admins_count": len(admin_ids),
            "effective_admin_ids": admin_ids,
        }

    @app.get("/admin/owner")
    async def owner_dashboard(request: Request):
        guard = _ensure_owner_or_redirect(request)
        if guard:
            return guard
        ctx: WebContext = request.app.state.ctx
        data = await _build_dashboard_context(ctx)
        return templates.TemplateResponse(
            "dashboard.html",
            _template_data(
                request,
                "Owner Dashboard",
                dashboard_mode=ROLE_OWNER,
                **data,
            ),
        )

    @app.get("/admin/admin")
    async def admin_dashboard(request: Request):
        ctx: WebContext = request.app.state.ctx
        data = await _build_dashboard_context(ctx)
        return templates.TemplateResponse(
            "dashboard.html",
            _template_data(
                request,
                "Admin Dashboard",
                dashboard_mode=ROLE_ADMIN,
                **data,
            ),
        )

    @app.get("/admin/settings")
    async def admin_settings(request: Request):
        ctx: WebContext = request.app.state.ctx
        send_caption_enabled = await ctx.db.get_bool_setting(
            SEND_CAPTION_SETTING_KEY,
            default=ctx.settings.send_caption_default,
        )
        return templates.TemplateResponse(
            "settings.html",
            _template_data(
                request,
                "Settings",
                send_caption_enabled=send_caption_enabled,
            ),
        )

    @app.post("/admin/settings/caption")
    async def admin_settings_caption(request: Request, send_caption: str = Form("0")):
        ctx: WebContext = request.app.state.ctx
        enabled = _is_true(send_caption)
        await ctx.db.set_bool_setting(SEND_CAPTION_SETTING_KEY, enabled)
        return _redirect("/admin/settings?ok=Caption setting saqlandi")

    @app.get("/admin/admins")
    async def admin_staff_management(request: Request):
        ctx: WebContext = request.app.state.ctx
        owner_id = ctx.settings.owner_id
        static_admin_ids = sorted({uid for uid in ctx.settings.admin_ids if uid != owner_id})
        dynamic_admin_ids = sorted({uid for uid in await ctx.db.get_dynamic_admin_ids() if uid != owner_id})
        dynamic_only_ids = [uid for uid in dynamic_admin_ids if uid not in set(static_admin_ids)]

        owner_info = await _build_user_brief(ctx.db, owner_id)
        staff_rows = []
        for uid in static_admin_ids:
            info = await _build_user_brief(ctx.db, uid)
            info["source"] = "env"
            info["removable"] = False
            staff_rows.append(info)
        for uid in dynamic_only_ids:
            info = await _build_user_brief(ctx.db, uid)
            info["source"] = "dynamic"
            info["removable"] = True
            staff_rows.append(info)

        return templates.TemplateResponse(
            "admins.html",
            _template_data(
                request,
                "Adminlar",
                owner_info=owner_info,
                admin_rows=staff_rows,
                can_manage_admins=getattr(request.state, "is_owner", False),
                total_admins=len(staff_rows),
            ),
        )

    @app.post("/admin/admins/add")
    async def admin_staff_add(request: Request, user_id: int = Form(...)):
        guard = _ensure_owner_or_redirect(request)
        if guard:
            return guard
        ctx: WebContext = request.app.state.ctx
        if user_id == ctx.settings.owner_id:
            return _redirect("/admin/admins?err=Owner admin sifatida qo'shilmaydi")
        if user_id in ctx.settings.admin_ids:
            return _redirect("/admin/admins?ok=Bu user allaqachon ENV admin")
        await ctx.db.add_dynamic_admin(user_id)
        return _redirect("/admin/admins?ok=Admin tayinlandi")

    @app.post("/admin/admins/remove")
    async def admin_staff_remove(request: Request, user_id: int = Form(...)):
        guard = _ensure_owner_or_redirect(request)
        if guard:
            return guard
        ctx: WebContext = request.app.state.ctx
        if user_id == ctx.settings.owner_id:
            return _redirect("/admin/admins?err=Owner o'chirilmaydi")
        if user_id in ctx.settings.admin_ids:
            return _redirect("/admin/admins?err=ENV adminni webdan o'chirib bo'lmaydi")
        await ctx.db.remove_dynamic_admin(user_id)
        return _redirect("/admin/admins?ok=Admin o'chirildi")

    @app.get("/admin/users")
    async def admin_users(request: Request):
        ctx: WebContext = request.app.state.ctx
        q = (request.query_params.get("q") or "").strip()
        page = _parse_page(request.query_params.get("page"), default=1)
        limit = 30
        offset = (page - 1) * limit

        total = await ctx.db.count_users_filtered(query=q or None, include_blocked=True)
        users_list = await ctx.db.list_users_paginated(
            limit=limit,
            offset=offset,
            query=q or None,
            include_blocked=True,
        )
        owner_id = ctx.settings.owner_id
        effective_admin_ids = set(await get_effective_admin_ids(ctx.db, ctx.settings))
        dynamic_admin_ids = set(await ctx.db.get_dynamic_admin_ids())
        for row in users_list:
            uid = int(row.get("user_id"))
            row["is_owner"] = uid == owner_id
            row["is_admin"] = uid in effective_admin_ids
            row["is_dynamic_admin"] = uid in dynamic_admin_ids

        return templates.TemplateResponse(
            "users.html",
            _template_data(
                request,
                "Userlar",
                users_list=users_list,
                q=q,
                page=page,
                total=total,
                limit=limit,
                owner_id=owner_id,
                can_manage_admins=getattr(request.state, "is_owner", False),
            ),
        )

    @app.post("/admin/users/block")
    async def admin_user_block(
        request: Request,
        user_id: int = Form(...),
        reason: str = Form(""),
        next_url: str = Form("/admin/users"),
    ):
        ctx: WebContext = request.app.state.ctx
        if user_id == ctx.settings.owner_id:
            return _redirect(_append_query(next_url, err="Owner bloklanmaydi"))
        blocked_by = _current_actor_id(request, ctx.settings)
        await ctx.db.block_user(user_id=user_id, blocked_by=blocked_by, reason=reason)
        return _redirect(_append_query(next_url, ok="User bloklandi"))

    @app.post("/admin/users/unblock")
    async def admin_user_unblock(
        request: Request,
        user_id: int = Form(...),
        next_url: str = Form("/admin/users"),
    ):
        ctx: WebContext = request.app.state.ctx
        await ctx.db.unblock_user(user_id)
        return _redirect(_append_query(next_url, ok="User blokdan chiqarildi"))

    @app.get("/admin/movies")
    async def admin_movies(request: Request):
        ctx: WebContext = request.app.state.ctx
        q = (request.query_params.get("q") or "").strip()
        kind = _normalize_kind_filter(request.query_params.get("kind"))
        page = _parse_page(request.query_params.get("page"), default=1)
        limit = 25
        offset = (page - 1) * limit
        total = await ctx.db.count_movies_filtered(query=q or None, content_kind=kind)
        movies_list = await ctx.db.list_movies_paginated(
            limit=limit,
            offset=offset,
            query=q or None,
            content_kind=kind,
        )
        code_overview = await ctx.db.list_code_overview(limit=15, query=q or None, content_kind=kind)
        movie_channels = await ctx.db.list_movie_channels()

        return templates.TemplateResponse(
            "movies.html",
            _template_data(
                request,
                "Kinolar",
                movies_list=movies_list,
                code_overview=code_overview,
                movie_channels=movie_channels,
                q=q,
                kind=kind or "all",
                page=page,
                total=total,
                limit=limit,
            ),
        )

    @app.get("/admin/movies/parts")
    async def admin_movie_parts(request: Request):
        ctx: WebContext = request.app.state.ctx
        code = (request.query_params.get("code") or "").strip()
        if not code:
            return _redirect("/admin/movies?err=Kod berilmagan")
        parts = await ctx.db.list_movie_parts(code)
        if not parts:
            return _redirect("/admin/movies?err=Kod topilmadi")
        return templates.TemplateResponse(
            "movie_parts.html",
            _template_data(
                request,
                f"Qismlar #{code}",
                code=code,
                parts=parts,
            ),
        )

    @app.post("/admin/movies/delete")
    async def admin_movie_delete(
        request: Request,
        code: str = Form(...),
        content_kind: str = Form("movie"),
        part_number: int = Form(1),
    ):
        ctx: WebContext = request.app.state.ctx
        normalized_code = code.strip()
        normalized_kind = _normalize_kind(content_kind)
        clean_part = int(part_number or 1)
        if clean_part < 1:
            clean_part = 1

        if normalized_kind == "serial":
            deleted = await ctx.db.delete_movie_part(normalized_code, clean_part)
            if deleted:
                ctx.movie_cache.delete_part(normalized_code, clean_part)
            else:
                return _redirect("/admin/movies?err=Serial qismi topilmadi")
        else:
            deleted = await ctx.db.delete_movie_by_code(normalized_code)
            ctx.movie_cache.delete_by_code(normalized_code)

        if deleted:
            return _redirect("/admin/movies?ok=Kino o'chirildi")
        return _redirect("/admin/movies?err=Kino topilmadi")

    @app.post("/admin/movies/upload")
    async def admin_movie_upload(
        request: Request,
        code: str = Form(...),
        content_kind: str = Form("movie"),
        part_number: int = Form(1),
        caption: str = Form(""),
        movie_channel_id: int = Form(...),
        media_file: UploadFile = None,
    ):
        ctx: WebContext = request.app.state.ctx
        normalized_code = code.strip()
        if not normalized_code.isdigit():
            return _redirect("/admin/movies?err=Kod faqat raqam bo'lishi kerak")
        if media_file is None:
            return _redirect("/admin/movies?err=Fayl tanlanmagan")
        normalized_kind = _normalize_kind(content_kind)
        clean_part = int(part_number or 1)
        if clean_part < 1:
            return _redirect("/admin/movies?err=Qism 1 yoki undan katta bo'lishi kerak")
        if normalized_kind == "movie":
            clean_part = 1

        channels = await ctx.db.list_movie_channels()
        target = next((ch for ch in channels if ch.chat_id == int(movie_channel_id)), None)
        if not target:
            return _redirect("/admin/movies?err=Kino kanali topilmadi")

        payload = await media_file.read()
        if not payload:
            return _redirect("/admin/movies?err=Yuklangan fayl bo'sh")

        filename = media_file.filename or f"{normalized_code}.bin"
        input_file = BufferedInputFile(payload, filename=filename)
        cleaned_caption = caption.strip()
        meta_lines = [f"type:{normalized_kind}"]
        if normalized_kind == "serial":
            meta_lines.append(f"qism:{clean_part}")
        meta_lines.append(f"Kod: {normalized_code}")
        send_caption = (
            f"{cleaned_caption}\n\n" + "\n".join(meta_lines)
            if cleaned_caption
            else "\n".join(meta_lines)
        )

        try:
            if (media_file.content_type or "").startswith("video/"):
                sent = await ctx.bot.send_video(target.chat_id, video=input_file, caption=send_caption)
                file_id = sent.video.file_id if sent.video else ""
                file_unique_id = sent.video.file_unique_id if sent.video else None
                file_type = "video"
            else:
                sent = await ctx.bot.send_document(target.chat_id, document=input_file, caption=send_caption)
                file_id = sent.document.file_id if sent.document else ""
                file_unique_id = sent.document.file_unique_id if sent.document else None
                file_type = "document"
        except Exception:
            return _redirect("/admin/movies?err=Telegram kanalga upload qilib bo'lmadi")

        if not file_id:
            return _redirect("/admin/movies?err=Telegram file_id olinmadi")

        ok, err = await _validate_movie_slot(
            ctx.db,
            code=normalized_code,
            content_kind=normalized_kind,
            part_number=clean_part,
            channel_id=target.chat_id,
            message_id=sent.message_id,
        )
        if not ok:
            try:
                await ctx.bot.delete_message(target.chat_id, sent.message_id)
            except Exception:
                pass
            return _redirect(f"/admin/movies?err={err or 'Kod allaqachon mavjud'}")

        await ctx.db.add_movie(
            code=normalized_code,
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_type=file_type,
            channel_id=target.chat_id,
            message_id=sent.message_id,
            caption=cleaned_caption or None,
            content_kind=normalized_kind,
            part_number=clean_part,
        )
        ctx.movie_cache.set(
            MovieRecord(
                code=normalized_code,
                file_id=file_id,
                file_type=file_type,
                channel_id=target.chat_id,
                message_id=sent.message_id,
                caption=cleaned_caption or None,
                content_kind=normalized_kind,
                part_number=clean_part,
            )
        )
        return _redirect("/admin/movies?ok=Kino muvaffaqiyatli yuklandi")

    @app.get("/admin/channels")
    async def admin_channels(request: Request):
        ctx: WebContext = request.app.state.ctx
        movie_channels = await ctx.db.list_movie_channels()
        sub_channels = await ctx.db.list_subscription_channels()
        return templates.TemplateResponse(
            "channels.html",
            _template_data(
                request,
                "Kanallar",
                movie_channels=movie_channels,
                sub_channels=sub_channels,
            ),
        )

    @app.post("/admin/channels/movie/add")
    async def admin_channel_movie_add(
        request: Request,
        chat_id: int = Form(...),
        title: str = Form(""),
        username: str = Form(""),
        auto_sync: str = Form("1"),
    ):
        ctx: WebContext = request.app.state.ctx
        await ctx.db.add_movie_channel(chat_id, title.strip() or None, _normalize_channel_username(username))
        ctx.channel_cache.invalidate_movie_channels()
        if _is_true(auto_sync):
            notify_chat_id = _current_actor_id(request, ctx.settings)
            asyncio.create_task(
                sync_channel_history(
                    bot=ctx.bot,
                    db=ctx.db,
                    movie_cache=ctx.movie_cache,
                    channel_id=chat_id,
                    notify_chat_id=notify_chat_id,
                    max_scan=500,
                )
            )
            return _redirect("/admin/channels?ok=Kino kanali qo'shildi, history sync boshlandi")
        return _redirect("/admin/channels?ok=Kino kanali qo'shildi")

    @app.post("/admin/channels/movie/remove")
    async def admin_channel_movie_remove(request: Request, chat_id: int = Form(...)):
        ctx: WebContext = request.app.state.ctx
        await ctx.db.remove_movie_channel(chat_id)
        ctx.channel_cache.invalidate_movie_channels()
        return _redirect("/admin/channels?ok=Kino kanali o'chirildi")

    @app.post("/admin/channels/movie/sync")
    async def admin_channel_movie_sync(request: Request, chat_id: int = Form(...), scan_limit: int = Form(500)):
        ctx: WebContext = request.app.state.ctx
        limit = max(50, min(int(scan_limit or 500), 2000))
        notify_chat_id = _current_actor_id(request, ctx.settings)
        asyncio.create_task(
            sync_channel_history(
                bot=ctx.bot,
                db=ctx.db,
                movie_cache=ctx.movie_cache,
                channel_id=chat_id,
                notify_chat_id=notify_chat_id,
                max_scan=limit,
            )
        )
        return _redirect("/admin/channels?ok=History sync ishga tushdi")

    @app.post("/admin/channels/sub/add")
    async def admin_channel_sub_add(
        request: Request,
        chat_id: int = Form(...),
        title: str = Form(""),
        username: str = Form(""),
        invite_link: str = Form(""),
    ):
        ctx: WebContext = request.app.state.ctx
        clean_username = _normalize_channel_username(username)
        clean_invite = invite_link.strip() or None
        await ctx.db.add_subscription_channel(
            chat_id=chat_id,
            title=title.strip() or None,
            username=clean_username,
            invite_link=clean_invite,
        )
        ctx.channel_cache.invalidate_subscription_channels()
        return _redirect("/admin/channels?ok=Obuna kanali qo'shildi")

    @app.post("/admin/channels/sub/remove")
    async def admin_channel_sub_remove(request: Request, chat_id: int = Form(...)):
        ctx: WebContext = request.app.state.ctx
        await ctx.db.remove_subscription_channel(chat_id)
        ctx.channel_cache.invalidate_subscription_channels()
        return _redirect("/admin/channels?ok=Obuna kanali o'chirildi")

    @app.get("/admin/support")
    async def admin_support(request: Request):
        ctx: WebContext = request.app.state.ctx
        status = (request.query_params.get("status") or "open").strip()
        if status not in {"open", "answered", "all"}:
            status = "open"

        page = _parse_page(request.query_params.get("page"), default=1)
        limit = 20
        offset = (page - 1) * limit
        db_status = None if status == "all" else status
        total = await ctx.db.count_support_tickets(status=db_status)
        tickets = await ctx.db.list_support_tickets(status=db_status, limit=limit, offset=offset)

        return templates.TemplateResponse(
            "support.html",
            _template_data(
                request,
                "Support",
                support_status=status,
                tickets=tickets,
                page=page,
                total=total,
                limit=limit,
            ),
        )

    @app.post("/admin/support/reply")
    async def admin_support_reply(
        request: Request,
        ticket_id: int = Form(...),
        reply_text: str = Form(...),
    ):
        ctx: WebContext = request.app.state.ctx
        text = reply_text.strip()
        if not text:
            return _redirect("/admin/support?err=Javob matni bo'sh")

        ticket = await ctx.db.get_support_ticket(ticket_id)
        if not ticket:
            return _redirect("/admin/support?err=Ticket topilmadi")

        try:
            await ctx.bot.send_message(chat_id=ticket.user_id, text=f"Support javobi:\n\n{text}")
        except Exception:
            return _redirect("/admin/support?err=Userga yuborib bo'lmadi")

        await ctx.db.mark_support_ticket_answered(
            ticket_id=ticket_id,
            answer_text=text,
            answered_by=_current_actor_id(request, ctx.settings),
        )
        return _redirect("/admin/support?ok=Javob yuborildi")

    @app.get("/admin/broadcast")
    async def admin_broadcast(request: Request):
        ctx: WebContext = request.app.state.ctx
        logs = await ctx.db.list_broadcast_logs(limit=30)
        return templates.TemplateResponse(
            "broadcast.html",
            _template_data(request, "Broadcast", logs=logs),
        )

    @app.post("/admin/broadcast/send")
    async def admin_broadcast_send(
        request: Request,
        message_text: str = Form(...),
        include_staff: str = Form("0"),
    ):
        ctx: WebContext = request.app.state.ctx
        text = message_text.strip()
        if not text:
            return _redirect("/admin/broadcast?err=Xabar matni bo'sh")

        include_staff_flag = _is_true(include_staff)
        log_id = await ctx.db.create_broadcast_log(
            created_by=_current_actor_id(request, ctx.settings),
            message_text=text,
            total_users=0,
            status="queued",
        )
        task = asyncio.create_task(_run_broadcast_task(ctx, log_id, text, include_staff_flag))
        ctx.broadcast_tasks[log_id] = task
        return _redirect("/admin/broadcast?ok=Broadcast navbatga qo'yildi")

    return app
