from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from .cache import ChannelCache, MovieCache
from .config import load_settings
from .crypto import Crypto
from .db import Database
from .handlers import admin, channel, support, user
from .logging_setup import setup_logging
from .middleware import ErrorMiddleware
from .subscription import SubscriptionService
from .tasks import deletion_worker


async def main() -> None:
    setup_logging()
    settings = load_settings()

    crypto = Crypto(settings.db_encryption_key)
    db = Database(settings.database_url, crypto)
    await db.init()

    channel_cache = ChannelCache(db)
    movie_cache = MovieCache(db, enabled=settings.movie_cache_enabled)
    await movie_cache.load()

    subscription_service = SubscriptionService(db, channel_cache, ttl_seconds=settings.subscription_cache_ttl)

    bot = Bot(token=settings.main_bot_token, parse_mode=None)
    dp = Dispatcher()
    dp.update.outer_middleware(ErrorMiddleware())

    dp.include_router(channel.router)
    dp.include_router(admin.router)
    dp.include_router(support.router)
    dp.include_router(user.router)

    dp["db"] = db
    dp["settings"] = settings
    dp["movie_cache"] = movie_cache
    dp["subscription_service"] = subscription_service
    dp["channel_cache"] = channel_cache

    asyncio.create_task(deletion_worker(bot, db))

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
