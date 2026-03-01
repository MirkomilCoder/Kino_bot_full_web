from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from typing import Optional
from urllib.parse import urlencode

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from ..access import is_owner, is_staff_dynamic
from ..cache import ChannelCache, MovieCache
from ..config import Settings
from ..db import Database
from ..subscription import SubscriptionService
from ..texts import (
    ADD_MOVIE_CHANNEL_TEXT,
    ADD_SUB_CHANNEL_TEXT,
    ADMIN_MENU_TEXT,
    ASK_INVITE_LINK_TEXT,
    INVALID_CHANNEL_TEXT,
)
from ..utils import format_channel_line, mask_token
from .channel import sync_channel_history

router = Router()


class AdminStates(StatesGroup):
    waiting_movie_channel = State()
    waiting_sub_channel = State()
    waiting_sub_invite = State()
    waiting_helper_token = State()
    waiting_reset_password = State()


def _build_webapp_url(settings: Settings, user_id: int, owner_mode: bool) -> Optional[str]:
    base_url = (settings.web_app_url or "").strip()
    if not base_url:
        return None
    role = "owner" if owner_mode else "admin"
    exp = int(time.time()) + 900
    payload = f"{user_id}:{role}:{exp}"
    signature = hmac.new(
        settings.web_session_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    query = urlencode({"uid": user_id, "role": role, "exp": exp, "sig": signature})
    return f"{base_url.rstrip('/')}/admin/tg-auth?{query}"


def _admin_menu_kb(owner_mode: bool = False, webapp_url: Optional[str] = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕🎥 Kino kanal qo'shish", callback_data="admin:add_movie")],
        [InlineKeyboardButton(text="➖🎥 Kino kanal o'chirish", callback_data="admin:remove_movie")],
        [InlineKeyboardButton(text="📡 Obuna kanallari", callback_data="admin:subs")],
        [InlineKeyboardButton(text="👥 Userlar ro'yxati", callback_data="admin:users")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats")],
        [InlineKeyboardButton(text="⚙️ Admin settings", callback_data="admin:settings")],
        [InlineKeyboardButton(text="🤖 Helper botlar", callback_data="admin:helpers")],
    ]
    if webapp_url:
        rows.append([InlineKeyboardButton(text="🌐 Web App", web_app=WebAppInfo(url=webapp_url))])
    else:
        rows.append([InlineKeyboardButton(text="🌐 Web App", callback_data="admin:webapp")])
    if owner_mode:
        rows.append([InlineKeyboardButton(text="🧹 Reset (Owner)", callback_data="admin:reset")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _subs_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕📡 Obuna kanal qo'shish", callback_data="admin:add_sub")],
            [InlineKeyboardButton(text="➖📡 Obuna kanal o'chirish", callback_data="admin:remove_sub")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:back")],
        ]
    )


def _helpers_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕🤖 Helper bot qo'shish", callback_data="admin:add_helper")],
            [InlineKeyboardButton(text="➖🤖 Helper bot o'chirish", callback_data="admin:remove_helper")],
            [InlineKeyboardButton(text="📋🤖 Helper botlar ro'yxati", callback_data="admin:list_helper")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:back")],
        ]
    )


def _settings_menu_kb(send_caption_enabled: bool) -> InlineKeyboardMarkup:
    status = "✅ ON" if send_caption_enabled else "❌ OFF"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🎬 Caption yuborish: {status}", callback_data="admin:toggle_caption")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:back")],
        ]
    )


def _reset_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, hammasini o'chirish", callback_data="admin:reset_yes")],
            [InlineKeyboardButton(text="❌ Yo'q", callback_data="admin:reset_no")],
        ]
    )


def _main_menu_for(settings: Settings, user_id: int) -> InlineKeyboardMarkup:
    owner_mode = is_owner(settings, user_id)
    webapp_url = _build_webapp_url(settings, user_id, owner_mode)
    return _admin_menu_kb(owner_mode=owner_mode, webapp_url=webapp_url)


async def _safe_edit_text(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    if not callback.message:
        return
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return
        raise


async def _resolve_channel(message: Message, bot: Bot) -> Optional[tuple[int, Optional[str], Optional[str]]]:
    if message.forward_from_chat:
        chat = message.forward_from_chat
        if chat.type == ChatType.CHANNEL:
            return chat.id, chat.title, chat.username
    if message.text:
        text = message.text.strip()
        if text.startswith("@"):
            try:
                chat = await bot.get_chat(text)
                if chat.type == ChatType.CHANNEL:
                    return chat.id, chat.title, chat.username
            except Exception:
                return None
        if text.lstrip("-").isdigit():
            try:
                chat = await bot.get_chat(int(text))
                if chat.type == ChatType.CHANNEL:
                    return chat.id, chat.title, chat.username
            except Exception:
                return None
    return None


@router.message(Command("admin"))
async def admin_menu(message: Message, settings: Settings, db: Database) -> None:
    if not message.from_user or not await is_staff_dynamic(db, settings, message.from_user.id):
        return
    await message.answer(ADMIN_MENU_TEXT, reply_markup=_main_menu_for(settings, message.from_user.id))


@router.message(Command("webapp"))
async def webapp_menu(message: Message, settings: Settings, db: Database) -> None:
    if not message.from_user or not await is_staff_dynamic(db, settings, message.from_user.id):
        return
    owner_mode = is_owner(settings, message.from_user.id)
    webapp_url = _build_webapp_url(settings, message.from_user.id, owner_mode)
    if not webapp_url:
        await message.answer("WEB_APP_URL sozlanmagan.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🌐 Admin Web App", web_app=WebAppInfo(url=webapp_url))]]
    )
    await message.answer("Web app ochish uchun tugmani bosing.", reply_markup=kb)


@router.callback_query(F.data == "admin:webapp")
async def admin_webapp_button(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    owner_mode = is_owner(settings, callback.from_user.id)
    webapp_url = _build_webapp_url(settings, callback.from_user.id, owner_mode)
    if not webapp_url:
        await callback.answer("WEB_APP_URL sozlanmagan.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🌐 Admin Web App", web_app=WebAppInfo(url=webapp_url))]]
    )
    if callback.message and hasattr(callback.message, "answer"):
        await callback.message.answer("Web app ochish uchun tugmani bosing.", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    await _safe_edit_text(
        callback,
        ADMIN_MENU_TEXT,
        reply_markup=_main_menu_for(settings, callback.from_user.id),
    )


@router.callback_query(F.data == "admin:add_movie")
async def admin_add_movie_channel(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_movie_channel)
    await _safe_edit_text(callback, ADD_MOVIE_CHANNEL_TEXT)


@router.message(AdminStates.waiting_movie_channel)
async def admin_receive_movie_channel(
    message: Message,
    state: FSMContext,
    bot: Bot,
    db: Database,
    movie_cache: MovieCache,
    channel_cache: ChannelCache,
    settings: Settings,
) -> None:
    if not message.from_user or not await is_staff_dynamic(db, settings, message.from_user.id):
        return
    resolved = await _resolve_channel(message, bot)
    if not resolved:
        await message.answer(INVALID_CHANNEL_TEXT)
        return
    chat_id, title, username = resolved
    await db.add_movie_channel(chat_id, title, username)
    channel_cache.invalidate_movie_channels()
    await state.clear()
    await message.answer("✅ Kino kanali qo'shildi. History auto-sync boshlandi...")
    asyncio.create_task(
        sync_channel_history(
            bot=bot,
            db=db,
            movie_cache=movie_cache,
            channel_id=chat_id,
            notify_chat_id=message.chat.id,
            max_scan=500,
        )
    )


@router.callback_query(F.data == "admin:remove_movie")
async def admin_remove_movie_menu(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    channels = await db.list_movie_channels()
    if not channels:
        await _safe_edit_text(
            callback,
            "🔭 Kino kanallari hozircha bo'sh.",
            reply_markup=_main_menu_for(settings, callback.from_user.id),
        )
        return
    rows = []
    for ch in channels:
        label = format_channel_line(ch)
        rows.append([InlineKeyboardButton(text=f"🗑 {label}", callback_data=f"admin:remove_movie:{ch.chat_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:back")])
    await _safe_edit_text(
        callback,
        "🎥 O'chirish uchun kanalni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("admin:remove_movie:"))
async def admin_remove_movie_channel(
    callback: CallbackQuery,
    db: Database,
    channel_cache: ChannelCache,
    settings: Settings,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    chat_id = int(callback.data.split(":")[2])
    await db.remove_movie_channel(chat_id)
    channel_cache.invalidate_movie_channels()
    await _safe_edit_text(
        callback,
        "✅ Kino kanali o'chirildi.",
        reply_markup=_main_menu_for(settings, callback.from_user.id),
    )


@router.callback_query(F.data == "admin:subs")
async def admin_subs_menu(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    await _safe_edit_text(callback, "📢 Obuna kanallari bo'limi:", reply_markup=_subs_menu_kb())


@router.callback_query(F.data == "admin:add_sub")
async def admin_add_sub_channel(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_sub_channel)
    await _safe_edit_text(callback, ADD_SUB_CHANNEL_TEXT)


@router.message(AdminStates.waiting_sub_channel)
async def admin_receive_sub_channel(
    message: Message,
    state: FSMContext,
    bot: Bot,
    db: Database,
    channel_cache: ChannelCache,
    settings: Settings,
) -> None:
    if not message.from_user or not await is_staff_dynamic(db, settings, message.from_user.id):
        return
    resolved = await _resolve_channel(message, bot)
    if not resolved:
        await message.answer(INVALID_CHANNEL_TEXT)
        return
    chat_id, title, username = resolved
    if username:
        await db.add_subscription_channel(chat_id, title, username, invite_link=None)
        channel_cache.invalidate_subscription_channels()
        await state.clear()
        await message.answer("✅ Obuna kanali qo'shildi.")
        return

    await state.update_data(chat_id=chat_id, title=title, username=username)
    await state.set_state(AdminStates.waiting_sub_invite)
    await message.answer(ASK_INVITE_LINK_TEXT)


@router.message(AdminStates.waiting_sub_invite)
async def admin_receive_sub_invite(
    message: Message,
    state: FSMContext,
    db: Database,
    channel_cache: ChannelCache,
    settings: Settings,
) -> None:
    if not message.from_user or not await is_staff_dynamic(db, settings, message.from_user.id):
        return
    invite_link = (message.text or "").strip()
    if not invite_link or "t.me" not in invite_link:
        await message.answer("❌ Invite link noto'g'ri. Qayta yuboring.")
        return
    data = await state.get_data()
    chat_id = data.get("chat_id")
    title = data.get("title")
    username = data.get("username")
    if not chat_id:
        await state.clear()
        await message.answer("❌ Xatolik: kanal topilmadi.")
        return
    await db.add_subscription_channel(chat_id, title, username, invite_link=invite_link)
    channel_cache.invalidate_subscription_channels()
    await state.clear()
    await message.answer("✅ Obuna kanali qo'shildi.")


@router.callback_query(F.data == "admin:remove_sub")
async def admin_remove_sub_menu(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    channels = await db.list_subscription_channels()
    if not channels:
        await _safe_edit_text(
            callback,
            "🔭 Obuna kanallari hozircha bo'sh.",
            reply_markup=_main_menu_for(settings, callback.from_user.id),
        )
        return
    rows = []
    for ch in channels:
        label = format_channel_line(ch)
        rows.append([InlineKeyboardButton(text=f"🗑 {label}", callback_data=f"admin:remove_sub:{ch.chat_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:subs")])
    await _safe_edit_text(
        callback,
        "📢 O'chirish uchun obuna kanalini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("admin:remove_sub:"))
async def admin_remove_sub_channel(
    callback: CallbackQuery,
    db: Database,
    channel_cache: ChannelCache,
    settings: Settings,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    chat_id = int(callback.data.split(":")[2])
    await db.remove_subscription_channel(chat_id)
    channel_cache.invalidate_subscription_channels()
    await _safe_edit_text(callback, "✅ Obuna kanali o'chirildi.", reply_markup=_subs_menu_kb())


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    items = await db.list_users(limit=20)
    lines = ["👥 So'nggi 20 ta user:"]
    for item in items:
        username = item.get("username") or ""
        display = f"{item.get('user_id')} {username}"
        lines.append(display.strip())
    await _safe_edit_text(callback, "\n".join(lines), reply_markup=_main_menu_for(settings, callback.from_user.id))


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    users_count = await db.count_users()
    movies_count = await db.count_movies()
    movie_channels_count = await db.count_channels()
    sub_channels_count = await db.count_subscription_channels()
    blocked_count = await db.count_blocked_users()
    open_support_count = await db.count_support_tickets(status="open")
    text = (
        f"📊 Statistika\n\n"
        f"👥 Userlar: {users_count}\n"
        f"🎬 Kinolar: {movies_count}\n"
        f"🎥 Kino kanallar: {movie_channels_count}\n"
        f"📢 Obuna kanallar: {sub_channels_count}\n"
        f"⛔ Bloklangan userlar: {blocked_count}\n"
        f"🎫 Ochiq support: {open_support_count}"
    )
    await _safe_edit_text(callback, text, reply_markup=_main_menu_for(settings, callback.from_user.id))


@router.callback_query(F.data == "admin:settings")
async def admin_settings_menu(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    enabled = await db.get_bool_setting("send_caption_to_user", default=settings.send_caption_default)
    await _safe_edit_text(
        callback,
        "⚙️ Bot settings",
        reply_markup=_settings_menu_kb(enabled),
    )


@router.callback_query(F.data == "admin:toggle_caption")
async def admin_toggle_caption(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    current = await db.get_bool_setting("send_caption_to_user", default=settings.send_caption_default)
    new_value = not current
    await db.set_bool_setting("send_caption_to_user", new_value)
    await _safe_edit_text(
        callback,
        "⚙️ Bot settings yangilandi.",
        reply_markup=_settings_menu_kb(new_value),
    )


@router.callback_query(F.data == "admin:helpers")
async def admin_helpers_menu(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    await _safe_edit_text(callback, "🤖 Helper botlar bo'limi:", reply_markup=_helpers_menu_kb())


@router.callback_query(F.data == "admin:add_helper")
async def admin_add_helper(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_helper_token)
    await _safe_edit_text(callback, "🔐 Helper bot token yuboring.")


@router.message(AdminStates.waiting_helper_token)
async def admin_receive_helper_token(
    message: Message,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if not message.from_user or not await is_staff_dynamic(db, settings, message.from_user.id):
        return
    token = (message.text or "").strip()
    if ":" not in token:
        await message.answer("❌ Token noto'g'ri. Qayta yuboring.")
        return

    temp_bot = Bot(token=token)
    try:
        me = await temp_bot.get_me()
    except Exception:
        await message.answer("❌ Token ishlamadi. Qayta tekshiring.")
        return
    finally:
        await temp_bot.session.close()

    await db.add_helper(me.id, token, me.username, me.first_name)
    await state.clear()
    await message.answer(f"✅ Helper bot qo'shildi: @{me.username or me.first_name}")


@router.callback_query(F.data == "admin:list_helper")
async def admin_list_helpers(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    helpers = await db.list_helpers()
    if not helpers:
        await _safe_edit_text(callback, "📭 Helper botlar yo'q.", reply_markup=_helpers_menu_kb())
        return
    lines = ["🤖 Helper botlar ro'yxati:"]
    for helper in helpers:
        token_mask = mask_token(helper.token)
        name = helper.username or helper.first_name or "bot"
        lines.append(f"{helper.bot_id} @{name} {token_mask}")
    await _safe_edit_text(callback, "\n".join(lines), reply_markup=_helpers_menu_kb())


@router.callback_query(F.data == "admin:remove_helper")
async def admin_remove_helper_menu(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    helpers = await db.list_helpers()
    if not helpers:
        await _safe_edit_text(callback, "📭 Helper botlar yo'q.", reply_markup=_helpers_menu_kb())
        return
    rows = []
    for helper in helpers:
        name = helper.username or helper.first_name or "bot"
        rows.append(
            [InlineKeyboardButton(text=f"🗑 {name} ({helper.bot_id})", callback_data=f"admin:remove_helper:{helper.bot_id}")]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:helpers")])
    await _safe_edit_text(
        callback,
        "🤖 O'chirish uchun helper botni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("admin:remove_helper:"))
async def admin_remove_helper(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    bot_id = int(callback.data.split(":")[2])
    await db.remove_helper(bot_id)
    await _safe_edit_text(callback, "✅ Helper bot o'chirildi.", reply_markup=_helpers_menu_kb())


@router.callback_query(F.data == "admin:reset")
async def admin_reset_start(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not callback.from_user or not is_owner(settings, callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_reset_password)
    await _safe_edit_text(
        callback,
        "🧹 Reset uchun parolni yuboring:\n\nTasdiqlash uchun reset parolini kiriting.",
    )


@router.message(AdminStates.waiting_reset_password)
async def admin_reset_password(
    message: Message,
    state: FSMContext,
    settings: Settings,
) -> None:
    if not message.from_user or not is_owner(settings, message.from_user.id):
        return
    password = (message.text or "").strip()
    if password != settings.reset_password:
        await message.answer("❌ Parol noto'g'ri. Qayta kiriting.")
        return
    await state.update_data(reset_confirm_pending=True)
    await message.answer("⚠️ Hamma ma'lumot o'chirilsinmi?", reply_markup=_reset_confirm_kb())


@router.callback_query(F.data == "admin:reset_no")
async def admin_reset_cancel(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not callback.from_user or not is_owner(settings, callback.from_user.id):
        return
    await state.clear()
    await _safe_edit_text(
        callback,
        "✅ Reset bekor qilindi.",
        reply_markup=_main_menu_for(settings, callback.from_user.id),
    )


@router.callback_query(F.data == "admin:reset_yes")
async def admin_reset_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    movie_cache: MovieCache,
    channel_cache: ChannelCache,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> None:
    if not callback.from_user or not is_owner(settings, callback.from_user.id):
        return
    state_data = await state.get_data()
    if not state_data.get("reset_confirm_pending"):
        await callback.answer("Avval parol tasdiqlansin.", show_alert=True)
        return

    await db.reset_all_data()
    movie_cache.clear()
    channel_cache.clear()
    subscription_service.clear_cache()
    await state.clear()

    await _safe_edit_text(
        callback,
        "✅ Barcha bot ma'lumotlari o'chirildi.",
        reply_markup=_main_menu_for(settings, callback.from_user.id),
    )
    
