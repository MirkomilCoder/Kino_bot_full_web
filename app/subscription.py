from __future__ import annotations

from typing import List, Tuple

from aiogram import Bot
from .cache import ChannelCache, TTLCache
from .db import ChannelRecord, Database


class SubscriptionService:
    def __init__(self, db: Database, channel_cache: ChannelCache, ttl_seconds: int = 30) -> None:
        self.db = db
        self.channel_cache = channel_cache
        self.user_cache = TTLCache(ttl_seconds)

    async def check(self, bot: Bot, user_id: int, force_refresh: bool = False) -> Tuple[bool, List[ChannelRecord]]:
        if not force_refresh:
            cached = self.user_cache.get(str(user_id))
            if cached is not None:
                ok, missing_ids = cached
                if ok:
                    return True, []
                channels = await self.channel_cache.get_subscription_channels()
                missing = [c for c in channels if c.chat_id in missing_ids]
                return False, missing

        channels = await self.channel_cache.get_subscription_channels()
        if not channels:
            self.user_cache.set(str(user_id), (True, []))
            return True, []

        missing: List[ChannelRecord] = []
        missing_ids = []
        for channel in channels:
            try:
                member = await bot.get_chat_member(channel.chat_id, user_id)
                if member.status in {"left", "kicked"}:
                    missing.append(channel)
                    missing_ids.append(channel.chat_id)
            except Exception:
                # If bot cannot check membership, treat as missing.
                missing.append(channel)
                missing_ids.append(channel.chat_id)

        ok = len(missing) == 0
        # Cache only positive status to avoid stale "not subscribed" after user joins.
        if ok:
            self.user_cache.set(str(user_id), (True, []))
        return ok, missing

    def clear_cache(self) -> None:
        self.user_cache.clear()
