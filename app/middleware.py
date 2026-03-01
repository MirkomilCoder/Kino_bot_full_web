from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Awaitable

from aiogram.dispatcher.middlewares.base import BaseMiddleware


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logging.exception("Unhandled exception")
            bot = data.get("bot")
            settings = data.get("settings")
            if bot and settings and getattr(settings, "log_chat_id", None):
                try:
                    await bot.send_message(settings.log_chat_id, "Bot error: check logs.")
                except Exception:
                    logging.exception("Failed to send error log")
            return None
