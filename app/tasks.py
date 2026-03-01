from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Iterable

from aiogram import Bot

from .db import Database


async def deletion_worker(bot: Bot, db: Database, interval_seconds: int = 60) -> None:
    while True:
        try:
            due = await db.fetch_due_deletions()
            if due:
                ids: list[int] = []
                for item in due:
                    ids.append(int(item["id"]))
                    try:
                        await bot.delete_message(int(item["chat_id"]), int(item["message_id"]))
                    except Exception:
                        logging.exception("Failed to delete message")
                await db.remove_scheduled(ids)
        except Exception:
            logging.exception("Deletion worker error")

        await asyncio.sleep(interval_seconds)


def compute_delete_at(hours: float) -> dt.datetime:
    return dt.datetime.utcnow() + dt.timedelta(hours=hours)
