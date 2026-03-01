from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.types import Message

from .config import load_settings
from .logging_setup import setup_logging
from .texts import HELPER_START_TEXT


async def main() -> None:
    setup_logging()
    settings = load_settings()

    token = os.getenv("HELPER_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HELPER_BOT_TOKEN is required for helper bot")

    bot = Bot(token=token, parse_mode=None)
    dp = Dispatcher()

    @dp.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
    async def start(message: Message) -> None:
        await message.answer(HELPER_START_TEXT.format(link=settings.main_bot_link))

    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def any_message(message: Message) -> None:
        await message.answer(HELPER_START_TEXT.format(link=settings.main_bot_link))

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
