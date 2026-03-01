from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaDocument,
    InputMediaVideo,
    Message,
)

from ..access import is_staff_dynamic
from ..cache import MovieCache
from ..config import Settings
from ..db import Database, MovieRecord
from ..subscription import SubscriptionService
from ..tasks import compute_delete_at
from ..texts import (
    BLOCKED_TEXT,
    NEED_SUBSCRIPTION_TEXT,
    NOT_FOUND_TEXT,
    ONLY_CODE_TEXT,
    SEARCHING_TEXT,
    SEND_ERROR_TEXT,
    START_TEXT,
    SUBSCRIPTION_CHECK_BUTTON_TEXT,
    SUBSCRIPTION_OK_TEXT,
    SUBSCRIPTION_STILL_MISSING_TEXT,
)
from ..utils import channel_button_text, channel_join_link, extract_code_from_text, format_channel_line

router = Router()

SEND_CAPTION_SETTING_KEY = "send_caption_to_user"


async def _send_subscription_needed(message: Message, missing_channels) -> None:
    lines = [NEED_SUBSCRIPTION_TEXT, ""]
    rows = []
    for channel in missing_channels:
        link = channel_join_link(channel)
        title = channel_button_text(channel)
        if link:
            rows.append([InlineKeyboardButton(text=f"📌 {title}", url=link)])
        else:
            lines.append(format_channel_line(channel))

    rows.append([InlineKeyboardButton(text=SUBSCRIPTION_CHECK_BUTTON_TEXT, callback_data="sub:check")])
    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


async def _safe_delete(msg: Message) -> None:
    try:
        await msg.delete()
    except Exception:
        pass


async def _should_send_caption(db: Database, settings: Settings) -> bool:
    return await db.get_bool_setting(SEND_CAPTION_SETTING_KEY, default=settings.send_caption_default)


def _parts_keyboard(code: str, parts: list[MovieRecord], active_part: int) -> InlineKeyboardMarkup | None:
    if len(parts) <= 1:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for idx, item in enumerate(parts, start=1):
        label = f"🎬 {item.part_number}-qism"
        if item.part_number == active_part:
            label = f"✅ {item.part_number}-qism"
        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"serial:{code}:{item.part_number}",
            )
        )
        if len(row) >= 6 or idx == len(parts):
            rows.append(row)
            row = []
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _load_parts(code: str, db: Database, movie_cache: MovieCache) -> list[MovieRecord]:
    parts = movie_cache.get_parts(code)
    if parts:
        return parts
    parts = await db.list_movie_parts(code)
    for item in parts:
        movie_cache.set(item)
    return parts


async def _send_movie_record(
    bot: Bot,
    db: Database,
    settings: Settings,
    *,
    chat_id: int,
    record: MovieRecord,
    parts: list[MovieRecord],
) -> None:
    include_caption = await _should_send_caption(db, settings)
    caption = record.caption if include_caption else None
    reply_markup = _parts_keyboard(record.code, parts, record.part_number)

    if record.file_type == "video":
        await bot.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
        sent = await bot.send_video(
            chat_id=chat_id,
            video=record.file_id,
            caption=caption,
            protect_content=True,
            reply_markup=reply_markup,
        )
    else:
        await bot.send_chat_action(chat_id, ChatAction.UPLOAD_DOCUMENT)
        sent = await bot.send_document(
            chat_id=chat_id,
            document=record.file_id,
            caption=caption,
            protect_content=True,
            reply_markup=reply_markup,
        )

    await db.schedule_delete(
        chat_id=sent.chat.id,
        message_id=sent.message_id,
        delete_at=compute_delete_at(settings.delete_after_hours),
    )


async def _replace_movie_record_in_message(
    bot: Bot,
    db: Database,
    settings: Settings,
    *,
    message: Message,
    record: MovieRecord,
    parts: list[MovieRecord],
) -> bool:
    include_caption = await _should_send_caption(db, settings)
    caption = record.caption if include_caption else None
    reply_markup = _parts_keyboard(record.code, parts, record.part_number)

    try:
        if record.file_type == "video":
            media = InputMediaVideo(media=record.file_id, caption=caption)
        else:
            media = InputMediaDocument(media=record.file_id, caption=caption)
        await bot.edit_message_media(
            chat_id=message.chat.id,
            message_id=message.message_id,
            media=media,
            reply_markup=reply_markup,
        )
        return True
    except Exception as exc:
        if "message is not modified" in str(exc).lower():
            return True
        logging.exception("Failed to replace serial message in place")
        return False


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start(
    message: Message,
    bot: Bot,
    db: Database,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> None:
    if message.from_user:
        await db.upsert_user(
            user_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
        )
        if not await is_staff_dynamic(db, settings, message.from_user.id) and await db.is_user_blocked(
            message.from_user.id
        ):
            await message.answer(BLOCKED_TEXT)
            return
    if message.from_user and await is_staff_dynamic(db, settings, message.from_user.id):
        await message.answer(START_TEXT)
        return

    ok, missing = await subscription_service.check(bot, message.from_user.id, force_refresh=True)
    if not ok:
        await _send_subscription_needed(message, missing)
        return
    await message.answer(START_TEXT)


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def handle_code(
    message: Message,
    bot: Bot,
    db: Database,
    movie_cache: MovieCache,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> None:
    if not message.from_user:
        return
    if not await is_staff_dynamic(db, settings, message.from_user.id) and await db.is_user_blocked(
        message.from_user.id
    ):
        await message.answer(BLOCKED_TEXT)
        return
    if message.text and message.text.startswith("/"):
        return

    code = extract_code_from_text(message.text)
    if not code:
        await message.answer(ONLY_CODE_TEXT)
        return

    loading = await message.answer(SEARCHING_TEXT)

    if not await is_staff_dynamic(db, settings, message.from_user.id):
        ok, missing = await subscription_service.check(bot, message.from_user.id)
        if not ok:
            await _safe_delete(loading)
            await _send_subscription_needed(message, missing)
            return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    record = movie_cache.get(code)
    if not record:
        record = await db.get_movie(code)
        if record:
            movie_cache.set(record)
    if not record:
        await _safe_delete(loading)
        await message.answer(NOT_FOUND_TEXT)
        return

    parts = await _load_parts(code, db, movie_cache)
    if not parts:
        parts = [record]

    try:
        await _send_movie_record(
            bot=bot,
            db=db,
            settings=settings,
            chat_id=message.chat.id,
            record=record,
            parts=parts,
        )
        await _safe_delete(loading)
    except Exception:
        logging.exception("Failed to send movie")
        await _safe_delete(loading)
        await message.answer(SEND_ERROR_TEXT)


@router.callback_query(F.data == "sub:check")
async def recheck_subscription(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> None:
    if not callback.from_user:
        return
    if not await is_staff_dynamic(db, settings, callback.from_user.id) and await db.is_user_blocked(
        callback.from_user.id
    ):
        await callback.answer(BLOCKED_TEXT, show_alert=True)
        return

    if await is_staff_dynamic(db, settings, callback.from_user.id):
        if callback.message and hasattr(callback.message, "answer"):
            await callback.message.answer(START_TEXT)
        await callback.answer()
        return

    ok, missing = await subscription_service.check(bot, callback.from_user.id, force_refresh=True)
    if not callback.message or not hasattr(callback.message, "answer"):
        await callback.answer()
        return

    if not ok:
        await callback.answer(SUBSCRIPTION_STILL_MISSING_TEXT, show_alert=True)
        await _send_subscription_needed(callback.message, missing)
        return

    await callback.answer(SUBSCRIPTION_OK_TEXT, show_alert=False)
    await callback.message.answer(START_TEXT)


@router.callback_query(F.data.startswith("serial:"))
async def serial_part_open(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    movie_cache: MovieCache,
    subscription_service: SubscriptionService,
    settings: Settings,
) -> None:
    if not callback.from_user:
        return
    if not callback.message:
        await callback.answer()
        return
    if not await is_staff_dynamic(db, settings, callback.from_user.id) and await db.is_user_blocked(
        callback.from_user.id
    ):
        await callback.answer(BLOCKED_TEXT, show_alert=True)
        return
    if not await is_staff_dynamic(db, settings, callback.from_user.id):
        ok, missing = await subscription_service.check(bot, callback.from_user.id)
        if not ok:
            await callback.answer(SUBSCRIPTION_STILL_MISSING_TEXT, show_alert=True)
            await _send_subscription_needed(callback.message, missing)
            return

    try:
        _, code, part_raw = callback.data.split(":", 2)
        part_number = int(part_raw)
    except Exception:
        await callback.answer("❌ Qism ma'lumoti xato.", show_alert=True)
        return

    record = movie_cache.get(code, part_number)
    if not record:
        record = await db.get_movie_part(code, part_number)
        if record:
            movie_cache.set(record)

    if not record:
        await callback.answer("❌ Qism topilmadi.", show_alert=True)
        return

    parts = await _load_parts(code, db, movie_cache)
    if not parts:
        parts = [record]

    try:
        replaced = await _replace_movie_record_in_message(
            bot=bot,
            db=db,
            settings=settings,
            message=callback.message,
            record=record,
            parts=parts,
        )
        if not replaced:
            await _send_movie_record(
                bot=bot,
                db=db,
                settings=settings,
                chat_id=callback.message.chat.id,
                record=record,
                parts=parts,
            )
            try:
                await callback.message.delete()
            except Exception:
                pass
    except Exception:
        logging.exception("Failed to send serial part")
        await callback.answer(SEND_ERROR_TEXT, show_alert=True)
        return

    await callback.answer(f"✅ {part_number}-qism ochildi.")
