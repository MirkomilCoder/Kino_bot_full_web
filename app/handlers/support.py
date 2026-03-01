from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..access import is_staff_dynamic
from ..config import Settings
from ..db import Database
from ..texts import (
    BLOCKED_TEXT,
    HELP_NOT_CONFIGURED_TEXT,
    HELP_SENT_TEXT,
    HELP_START_TEXT,
    SEND_ERROR_TEXT,
    SUPPORT_REPLY_ASK_TEXT,
    SUPPORT_REPLY_DELIVERED_TEXT,
    SUPPORT_REPLY_FAILED_TEXT,
    SUPPORT_REPLY_SENT_TEXT,
)

router = Router()


class SupportStates(StatesGroup):
    waiting_help_text = State()
    waiting_admin_reply = State()


def _full_name(message: Message) -> str:
    if not message.from_user:
        return "Unknown"
    parts = [message.from_user.first_name or "", message.from_user.last_name or ""]
    return " ".join([part for part in parts if part]).strip() or "Unknown"


@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def help_start(message: Message, state: FSMContext, settings: Settings, db: Database) -> None:
    if not settings.support_group_id:
        await message.answer(HELP_NOT_CONFIGURED_TEXT)
        return
    if message.from_user and not await is_staff_dynamic(db, settings, message.from_user.id):
        if await db.is_user_blocked(message.from_user.id):
            await message.answer(BLOCKED_TEXT)
            return
    await state.set_state(SupportStates.waiting_help_text)
    await message.answer(HELP_START_TEXT)


@router.message(SupportStates.waiting_help_text, F.chat.type == ChatType.PRIVATE)
async def help_collect_and_send(
    message: Message,
    bot: Bot,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if not settings.support_group_id:
        await state.clear()
        await message.answer(HELP_NOT_CONFIGURED_TEXT)
        return
    if not message.from_user:
        return
    if not await is_staff_dynamic(db, settings, message.from_user.id) and await db.is_user_blocked(
        message.from_user.id
    ):
        await state.clear()
        await message.answer(BLOCKED_TEXT)
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Iltimos, matn yuboring.")
        return

    await db.upsert_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
    )
    ticket_id = await db.create_support_ticket(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        message_text=text,
    )

    username = f"@{message.from_user.username}" if message.from_user.username else "-"
    profile_link = f"tg://user?id={message.from_user.id}"
    support_text = (
        "🆘 Yangi help murojaat\n\n"
        f"🎫 Ticket: #{ticket_id}\n"
        f"👤 Ism: {_full_name(message)}\n"
        f"🆔 User ID: {message.from_user.id}\n"
        f"📱 Username: {username}\n"
        f"🔗 Profil: {profile_link}\n\n"
        f"💬 Xabar:\n{text}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Ko'rish", url=profile_link)],
            [
                InlineKeyboardButton(
                    text="✍️ Javob",
                    callback_data=f"support:reply:{ticket_id}:{message.from_user.id}",
                )
            ],
        ]
    )
    try:
        await bot.send_message(settings.support_group_id, support_text, reply_markup=kb)
    except Exception:
        await message.answer(SEND_ERROR_TEXT)
        return

    await state.clear()
    await message.answer(HELP_SENT_TEXT)


@router.callback_query(F.data.startswith("support:reply:"))
async def support_reply_start(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not callback.from_user or not await is_staff_dynamic(db, settings, callback.from_user.id):
        return
    if not callback.message or not settings.support_group_id:
        return
    if callback.message.chat.id != settings.support_group_id:
        return

    parts = callback.data.split(":")
    ticket_id: int | None = None
    target_user_id: int | None = None

    try:
        if len(parts) >= 4:
            ticket_id = int(parts[2])
            target_user_id = int(parts[3])
        elif len(parts) == 3:
            target_user_id = int(parts[2])
    except ValueError:
        await callback.answer("User ID xato.", show_alert=True)
        return

    if not target_user_id:
        await callback.answer("User topilmadi.", show_alert=True)
        return

    await state.set_state(SupportStates.waiting_admin_reply)
    await state.update_data(target_user_id=target_user_id, ticket_id=ticket_id)
    await callback.answer()
    await callback.message.answer(SUPPORT_REPLY_ASK_TEXT)


@router.message(SupportStates.waiting_admin_reply)
async def support_send_reply(
    message: Message,
    bot: Bot,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not message.from_user or not await is_staff_dynamic(db, settings, message.from_user.id):
        return
    if not settings.support_group_id or message.chat.id != settings.support_group_id:
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Iltimos, javob matnini yozing.")
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    ticket_id = data.get("ticket_id")
    if not target_user_id:
        await state.clear()
        await message.answer("Session topilmadi. Qayta 'Javob' tugmasini bosing.")
        return

    try:
        await bot.send_message(int(target_user_id), SUPPORT_REPLY_DELIVERED_TEXT.format(text=text))
    except Exception:
        await message.answer(SUPPORT_REPLY_FAILED_TEXT)
    else:
        if ticket_id:
            await db.mark_support_ticket_answered(int(ticket_id), text, message.from_user.id)
        await message.answer(SUPPORT_REPLY_SENT_TEXT)
    finally:
        await state.clear()
