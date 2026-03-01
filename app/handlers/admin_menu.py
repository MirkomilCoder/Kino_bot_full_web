"""
Admin Panel Handler - Telegram Bot
Adminlar va Owner uchun maxsus menyu va funksiyalar
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import F, Router, Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.filters import Command

from ..access import is_staff
from ..config import Settings
from ..db import Database

router = Router()
logger = logging.getLogger(__name__)

# ============= MENU TEXT MESSAGES =============

ADMIN_MENU_TEXT = """
👑 <b>ADMIN PANEL</b>

<b>Tanlang:</b>
📊 Statistika
🎬 Kinolar
👥 Userlar
📡 Kanallar
📢 Broadcast
💬 Support
⚙️ Settings
"""

OWNER_MENU_TEXT = """
🔐 <b>OWNER PANEL</b>

<b>Tanlang:</b>
📊 Statistika - Bot holati
🎬 Kinolar - Kino boshqaruvi
👥 Userlar - User boshqaruvi
📡 Kanallar - Kanal sozlash
📢 Broadcast - Xabar yuborish
💬 Support - Support ticketlar
⚙️ Settings - Sozlamalar
🛡️ Security - Xavfsizlik
⚡ System - Sistem info
"""

# ============= KEYBOARD BUILDERS =============


async def get_admin_menu_keyboard(is_owner: bool = False) -> InlineKeyboardMarkup:
    """Admin menyu tugmalari"""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton(text="🎬 Movies", callback_data="admin_movies"),
        ],
        [
            InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
            InlineKeyboardButton(text="💬 Support", callback_data="admin_support"),
        ],
        [
            InlineKeyboardButton(text="📡 Channels", callback_data="admin_channels"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings"),
        ],
    ]

    if is_owner:
        buttons.extend([
            [InlineKeyboardButton(text="🛡️ Security", callback_data="admin_security")],
            [InlineKeyboardButton(text="⚡ System", callback_data="admin_system")],
        ])

    buttons.append([
        InlineKeyboardButton(text="🏠 Back to Menu", callback_data="back_main_menu"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============= ADMIN COMMAND HANDLERS =============


@router.message(Command("admin"))
async def cmd_admin_menu(message: Message, settings: Settings):
    """Admin menyu ochish"""
    if not message.from_user:
        return

    # Admin yoki Owner bo'lish tekshiruvi
    is_owner = message.from_user.id == settings.owner_id
    is_admin = is_owner or message.from_user.id in settings.admin_ids

    if not is_admin:
        return

    menu_text = OWNER_MENU_TEXT if is_owner else ADMIN_MENU_TEXT

    await message.answer(
        menu_text,
        reply_markup=await get_admin_menu_keyboard(is_owner),
        parse_mode="HTML"
    )


# ============= STATISTICS CALLBACK =============


@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(query: CallbackQuery, db: Database, settings: Settings):
    """Bot statistikasi ko'rish"""
    if not query.from_user:
        return

    is_admin = query.from_user.id == settings.owner_id or query.from_user.id in settings.admin_ids
    if not is_admin:
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    try:
        # Statistikani olish
        users_total = await db.count_users()
        users_blocked = await db.count_blocked_users()
        users_active = users_total - users_blocked
        movies_count = await db.count_movies()
        channels_count = await db.count_channels()
        open_support = await db.count_support_tickets(status='open')

        stats_text = f"""
📊 <b>BOT STATISTIKASI</b>

👥 <b>Foydalanuvchilar:</b>
   ✅ Jami: <code>{users_total}</code>
   🟢 Faol: <code>{users_active}</code>
   🔴 Bloklangan: <code>{users_blocked}</code>

🎬 <b>Kontentlar:</b>
   🎞️ Kinolar: <code>{movies_count}</code>
   📺 Kanallar: <code>{channels_count}</code>

💬 <b>Faoliyat:</b>
   📭 Ochiq Support: <code>{open_support}</code>

📅 <b>Vaqt:</b> <code>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</code>
"""

        buttons = [
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton(text="⬅️ Menu", callback_data="admin_menu_back")],
        ]

        await query.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in admin stats: {e}")
        await query.answer("❌ Xato yuz berdi", show_alert=True)

    await query.answer()


# ============= BROADCAST HANDLER =============


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, settings: Settings, bot: Bot, db: Database):
    """Broadcast yuborish"""
    if not message.from_user:
        return

    is_admin = message.from_user.id == settings.owner_id or message.from_user.id in settings.admin_ids
    if not is_admin:
        return

    # Xabar matnini olish
    text_parts = message.text.split(maxsplit=1)

    if len(text_parts) < 2:
        await message.answer(
            "📢 <b>BROADCAST YUBORISH</b>\n\n"
            "<b>Foydalanish:</b>\n"
            "<code>/broadcast Xabar matni</code>\n\n"
            "<b>Misol:</b>\n"
            "<code>/broadcast Yangi filmlar qo'shildi!</code>\n\n"
            "<i>Barcha aktiv userlarga xabar jo'natiladi.</i>",
            parse_mode="HTML"
        )
        return

    broadcast_text = text_parts[1]

    # Tasdiqlash tugmalari
    buttons = [
        [
            InlineKeyboardButton(text="✅ Jo'natish", callback_data=f"bcast_send:{message.message_id}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="bcast_cancel"),
        ]
    ]

    confirm_text = f"""
📢 <b>BROADCAST TAYYORLASH</b>

<b>Xabar:</b>
<pre>{broadcast_text}</pre>

<b>Qaysi userlarga jo'natiladi?</b>
• Barcha aktiv foydalanuvchilar
• Bloklangan foydalanuvchilar <b>O'TKAZILIB</b> ketadi

<b>Tasdiqlang:</b>
"""

    await message.answer(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("bcast_send:"))
async def broadcast_send_callback(query: CallbackQuery, bot: Bot, db: Database, settings: Settings):
    """Broadcast yuborish tasdiqlandi"""
    if not query.from_user:
        return

    is_admin = query.from_user.id == settings.owner_id or query.from_user.id in settings.admin_ids
    if not is_admin:
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await query.answer("⏳ Broadcast yuborilmoqda...", show_alert=False)

    try:
        # Xabarni extracting
        if not query.message or not query.message.text:
            await query.edit_text("❌ Xabar topilmadi")
            return

        text_parts = query.message.text.split("<pre>")
        if len(text_parts) < 2:
            await query.edit_text("❌ Xabar formatida xato")
            return

        broadcast_text = text_parts[1].split("</pre>")[0]

        # Barcha userlarni olish
        users = await db.list_all_user_ids(include_blocked=False)

        sent = 0
        failed = 0

        # Xabarni har bir userga yuborish
        for user_id in users:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=broadcast_text,
                    parse_mode="HTML"
                )
                sent += 1
            except Exception as e:
                logger.debug(f"Failed to send to {user_id}: {e}")
                failed += 1

            # Rate limit (Telegram API)
            await asyncio.sleep(0.02)

        # Log qil
        await db.create_broadcast_log(
            created_by=query.from_user.id,
            message_text=broadcast_text,
            total_users=sent + failed,
            sent_count=sent,
            failed_count=failed,
            status="done"
        )

        result_text = f"""
✅ <b>BROADCAST YUBORILDI!</b>

📤 Jo'natildi: <code>{sent}</code>
❌ Xatoli: <code>{failed}</code>
📊 Success Rate: <code>{int((sent/(sent+failed)*100) if sent+failed > 0 else 0)}%</code>

⏱️ Tugallandi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""

        await query.edit_text(result_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await query.edit_text("❌ Broadcast jo'natishda xato yuz berdi")


@router.callback_query(F.data == "bcast_cancel")
async def broadcast_cancel_callback(query: CallbackQuery):
    """Broadcast bekor qilish"""
    await query.edit_text("❌ Broadcast bekor qilindi")
    await query.answer()


# ============= MENU NAVIGATION =============


@router.callback_query(F.data == "admin_menu_back")
async def admin_menu_back_callback(query: CallbackQuery, settings: Settings):
    """Admin menyu qayta ko'rsatish"""
    if not query.from_user:
        return

    is_owner = query.from_user.id == settings.owner_id
    menu_text = OWNER_MENU_TEXT if is_owner else ADMIN_MENU_TEXT

    await query.edit_text(
        menu_text,
        reply_markup=await get_admin_menu_keyboard(is_owner),
        parse_mode="HTML"
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_"))
async def admin_placeholder_callback(query: CallbackQuery, settings: Settings):
    """Boshqa admin tugmalari (placeholder)"""
    if not query.from_user:
        return

    is_admin = query.from_user.id == settings.owner_id or query.from_user.id in settings.admin_ids
    if not is_admin:
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    action = query.data.replace("admin_", "")

    messages = {
        'movies': "🎬 Kino boshqaruvi web panelida mavjud\n\n👉 /admin_panel",
        'users': "👥 User boshqaruvi web panelida mavjud\n\n👉 /admin_panel",
        'support': "💬 Support ticketlar web panelida mavjud\n\n👉 /admin_panel",
        'channels': "📡 Kanal sozlash web panelida mavjud\n\n👉 /admin_panel",
        'settings': "⚙️ Sozlamalar web panelida mavjud\n\n👉 /admin_panel",
        'security': "🛡️ Security sozlamalari (owner uchun)",
        'system': "⚡ Sistem ma'lumotlari",
    }

    msg = messages.get(action, "...")
    await query.answer(msg, show_alert=True)
