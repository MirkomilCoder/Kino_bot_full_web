from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from ..cache import ChannelCache, MovieCache
from ..config import Settings
from ..db import Database, MovieRecord
from ..texts import MOVIE_ADDED_LOG, MOVIE_DELETED_LOG
from ..utils import parse_movie_caption_meta

router = Router()

DUPLICATE_CODE_TEXT = (
    "❌ Bu kod oldin ishlatilgan. Avvalgini o'chiring yoki tahrirlang."
)
DUPLICATE_SERIAL_PART_TEXT = (
    "❌ Bu serial kodi va qismi allaqachon mavjud. Avvalgini tahrirlang yoki o'chiring."
)
MIXED_TYPE_TEXT = (
    "❌ Bir kodda movie va serialni aralashtirib bo'lmaydi."
)
ADDED_REPLY_TEXT = "✅ Kino bazaga qo'shildi: #{code}"
ADDED_SERIAL_REPLY_TEXT = "✅ Serial qismi qo'shildi: #{code} · {part}-qism"
UPDATED_REPLY_TEXT = "✏️ Kino kodi yangilandi: {old_code} → {new_code}"
UPDATED_SERIAL_REPLY_TEXT = "✏️ Serial yangilandi: #{code} · {part}-qism"
REMOVED_REPLY_TEXT = "🗑 Kino o'chirildi: #{code}"
REMOVED_SERIAL_REPLY_TEXT = "🗑 Serial qismi o'chirildi: #{code} · {part}-qism"


async def _is_movie_channel(channel_cache: ChannelCache, chat_id: int) -> bool:
    channels = await channel_cache.get_movie_channels()
    return any(c.chat_id == chat_id for c in channels)


async def _log_event(bot: Bot, settings: Settings, text: str) -> None:
    logging.info(text)
    if settings.log_chat_id:
        try:
            await bot.send_message(settings.log_chat_id, text)
        except Exception:
            logging.exception("Failed to send log message")


async def _reply_status(bot: Bot, message: Message, text: str) -> None:
    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_to_message_id=message.message_id,
        )
    except Exception:
        try:
            await bot.send_message(chat_id=message.chat.id, text=text)
        except Exception:
            logging.exception("Failed to send channel status message")


def _extract_media(message: Message) -> Optional[tuple[str, Optional[str], str]]:
    if message.video:
        return message.video.file_id, message.video.file_unique_id, "video"
    if message.document:
        return message.document.file_id, message.document.file_unique_id, "document"
    return None


def _same_message(record: MovieRecord, channel_id: int, message_id: int) -> bool:
    return record.channel_id == channel_id and record.message_id == message_id


async def _get_by_message(
    db: Database,
    movie_cache: MovieCache,
    channel_id: int,
    message_id: int,
) -> Optional[MovieRecord]:
    cached = movie_cache.get_by_message(channel_id, message_id)
    if cached:
        return cached
    record = await db.get_movie_by_message(channel_id, message_id)
    if record:
        movie_cache.set(record)
    return record


async def _save_movie(
    db: Database,
    movie_cache: MovieCache,
    *,
    code: str,
    file_id: str,
    file_unique_id: Optional[str],
    file_type: str,
    channel_id: int,
    message_id: int,
    caption: Optional[str],
    content_kind: str,
    part_number: int,
) -> MovieRecord:
    await db.add_movie(
        code=code,
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_type=file_type,
        channel_id=channel_id,
        message_id=message_id,
        caption=caption,
        content_kind=content_kind,
        part_number=part_number,
    )
    record = MovieRecord(
        code=code,
        file_id=file_id,
        file_type=file_type,
        channel_id=channel_id,
        message_id=message_id,
        caption=caption,
        content_kind=content_kind,
        part_number=part_number,
    )
    movie_cache.set(record)
    return record


def _part_from_caption_or_old(parsed_part: int, old_record: Optional[MovieRecord], is_edited: bool) -> int:
    if parsed_part >= 1:
        return parsed_part
    if is_edited and old_record:
        return old_record.part_number
    return 1


async def _validate_slot(
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
            if not _same_message(item, channel_id, message_id):
                return False, DUPLICATE_CODE_TEXT
        return True, None

    # serial
    for item in parts:
        if item.content_kind == "movie" and not _same_message(item, channel_id, message_id):
            return False, MIXED_TYPE_TEXT
        if item.part_number == part_number and not _same_message(item, channel_id, message_id):
            return False, DUPLICATE_SERIAL_PART_TEXT
    return True, None


async def _handle_movie_message(
    message: Message,
    bot: Bot,
    db: Database,
    movie_cache: MovieCache,
    channel_cache: ChannelCache,
    settings: Settings,
    *,
    is_edited: bool = False,
) -> None:
    if message.chat.type != ChatType.CHANNEL:
        return
    if not await _is_movie_channel(channel_cache, message.chat.id):
        return

    old_record = await _get_by_message(db, movie_cache, message.chat.id, message.message_id)
    media = _extract_media(message)
    code, content_kind, parsed_part = parse_movie_caption_meta(message.caption)

    if old_record and is_edited:
        if not code and (media is not None or message.caption is not None):
            code = old_record.code
            content_kind = old_record.content_kind
            parsed_part = old_record.part_number

        # Media olib tashlanib textga aylansa bazadan ham o'chiramiz.
        if media is None and message.text:
            await db.delete_movie_part(old_record.code, old_record.part_number)
            movie_cache.delete_part(old_record.code, old_record.part_number)
            if old_record.content_kind == "serial":
                await _reply_status(
                    bot,
                    message,
                    REMOVED_SERIAL_REPLY_TEXT.format(code=old_record.code, part=old_record.part_number),
                )
            else:
                await _reply_status(bot, message, REMOVED_REPLY_TEXT.format(code=old_record.code))
            await _log_event(bot, settings, MOVIE_DELETED_LOG.format(code=old_record.code))
            return

    if not code:
        return

    part_number = _part_from_caption_or_old(parsed_part, old_record, is_edited)
    if content_kind != "serial":
        content_kind = "movie"
        part_number = 1

    if media:
        file_id, file_unique_id, file_type = media
    elif old_record:
        file_id = old_record.file_id
        file_unique_id = None
        file_type = old_record.file_type
    else:
        return

    ok, err = await _validate_slot(
        db,
        code=code,
        content_kind=content_kind,
        part_number=part_number,
        channel_id=message.chat.id,
        message_id=message.message_id,
    )
    if not ok and err:
        await _reply_status(bot, message, err)
        return

    final_caption = message.caption if message.caption is not None else (old_record.caption if old_record else None)

    if old_record and (
        old_record.code != code
        or old_record.part_number != part_number
        or old_record.content_kind != content_kind
    ):
        await db.delete_movie_part(old_record.code, old_record.part_number)
        movie_cache.delete_part(old_record.code, old_record.part_number)

    saved = await _save_movie(
        db=db,
        movie_cache=movie_cache,
        code=code,
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_type=file_type,
        channel_id=message.chat.id,
        message_id=message.message_id,
        caption=final_caption,
        content_kind=content_kind,
        part_number=part_number,
    )

    if old_record is None:
        if saved.content_kind == "serial":
            await _reply_status(
                bot,
                message,
                ADDED_SERIAL_REPLY_TEXT.format(code=saved.code, part=saved.part_number),
            )
        else:
            await _reply_status(bot, message, ADDED_REPLY_TEXT.format(code=saved.code))
        await _log_event(bot, settings, MOVIE_ADDED_LOG.format(code=saved.code))
        return

    if is_edited:
        if saved.content_kind == "serial":
            await _reply_status(
                bot,
                message,
                UPDATED_SERIAL_REPLY_TEXT.format(code=saved.code, part=saved.part_number),
            )
        elif old_record.code != saved.code:
            await _reply_status(
                bot,
                message,
                UPDATED_REPLY_TEXT.format(old_code=old_record.code, new_code=saved.code),
            )
        else:
            await _reply_status(bot, message, f"♻️ Kino yangilandi: {saved.code}")


@router.channel_post(F.video | F.document)
async def channel_post(
    message: Message,
    bot: Bot,
    db: Database,
    movie_cache: MovieCache,
    channel_cache: ChannelCache,
    settings: Settings,
) -> None:
    await _handle_movie_message(
        message=message,
        bot=bot,
        db=db,
        movie_cache=movie_cache,
        channel_cache=channel_cache,
        settings=settings,
        is_edited=False,
    )


@router.edited_channel_post()
async def edited_channel_post(
    message: Message,
    bot: Bot,
    db: Database,
    movie_cache: MovieCache,
    channel_cache: ChannelCache,
    settings: Settings,
) -> None:
    await _handle_movie_message(
        message=message,
        bot=bot,
        db=db,
        movie_cache=movie_cache,
        channel_cache=channel_cache,
        settings=settings,
        is_edited=True,
    )


async def sync_channel_history(
    *,
    bot: Bot,
    db: Database,
    movie_cache: MovieCache,
    channel_id: int,
    notify_chat_id: int,
    max_scan: int = 300,
) -> tuple[int, int]:
    imported = 0
    scanned = 0

    try:
        probe = await bot.send_message(channel_id, "🔄 Kino tarixini sinxronlash boshlandi...")
        probe_id = probe.message_id
        await bot.delete_message(channel_id, probe_id)
    except Exception:
        try:
            await bot.send_message(
                notify_chat_id,
                "⚠️ Kanal history auto-sync ishlamadi. Botga kanalga xabar yuborish huquqi kerak.",
            )
        except Exception:
            pass
        return scanned, imported

    start = max(1, probe_id - max_scan)
    for message_id in range(probe_id - 1, start - 1, -1):
        scanned += 1
        try:
            forwarded = await bot.forward_message(
                chat_id=notify_chat_id,
                from_chat_id=channel_id,
                message_id=message_id,
                disable_notification=True,
            )
        except TelegramBadRequest:
            await asyncio.sleep(0.02)
            continue
        except Exception:
            await asyncio.sleep(0.02)
            continue

        try:
            media = _extract_media(forwarded)
            if not media:
                continue
            code, content_kind, part_number = parse_movie_caption_meta(forwarded.caption)
            if not code:
                continue
            if content_kind != "serial":
                content_kind = "movie"
                part_number = 1

            ok, _ = await _validate_slot(
                db,
                code=code,
                content_kind=content_kind,
                part_number=part_number,
                channel_id=channel_id,
                message_id=message_id,
            )
            if not ok:
                continue

            file_id, file_unique_id, file_type = media
            await _save_movie(
                db=db,
                movie_cache=movie_cache,
                code=code,
                file_id=file_id,
                file_unique_id=file_unique_id,
                file_type=file_type,
                channel_id=channel_id,
                message_id=message_id,
                caption=forwarded.caption,
                content_kind=content_kind,
                part_number=part_number,
            )
            imported += 1
        finally:
            try:
                await bot.delete_message(notify_chat_id, forwarded.message_id)
            except Exception:
                pass
        await asyncio.sleep(0.03)

    try:
        await bot.send_message(
            notify_chat_id,
            f"✅ History sync tugadi.\nSkan: {scanned}\nImport: {imported}",
        )
    except Exception:
        pass
    return scanned, imported
