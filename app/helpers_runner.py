from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.types import Message

from .config import load_settings
from .crypto import Crypto
from .db import Database
from .logging_setup import setup_logging
from .texts import HELPER_START_TEXT


def build_dispatcher(main_link: str) -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
    async def start(message: Message) -> None:
        await message.answer(HELPER_START_TEXT.format(link=main_link))

    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def any_message(message: Message) -> None:
        await message.answer(HELPER_START_TEXT.format(link=main_link))

    return dp


async def run_helper(token: str, main_link: str) -> None:
    bot = Bot(token=token, parse_mode=None)
    dp = build_dispatcher(main_link)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


async def main() -> None:
    setup_logging()
    settings = load_settings()

    crypto = Crypto(settings.db_encryption_key)
    db = Database(settings.database_url, crypto)
    await db.init()

    helpers = await db.list_helpers()
    if not helpers:
        raise RuntimeError("Helper botlar DBda topilmadi.")

    tasks = [asyncio.create_task(run_helper(helper.token, settings.main_bot_link)) for helper in helpers]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
