from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .db import ChannelRecord, Database, MovieRecord


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._data: Dict[str, Tuple[float, object]] = {}

    def get(self, key: str):
        item = self._data.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value) -> None:
        self._data[key] = (time.time() + self.ttl_seconds, value)

    def invalidate(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()


class MovieCache:
    def __init__(self, db: Database, enabled: bool = True) -> None:
        self.db = db
        self.enabled = enabled
        self._part_map: Dict[Tuple[str, int], MovieRecord] = {}
        self._default_map: Dict[str, MovieRecord] = {}
        self._message_map: Dict[Tuple[int, int], Tuple[str, int]] = {}

    async def load(self) -> None:
        if not self.enabled:
            return
        self._part_map.clear()
        self._default_map.clear()
        self._message_map.clear()
        movies = await self.db.list_movies()
        for item in movies:
            self._part_map[(item.code, item.part_number)] = item
            self._message_map[(item.channel_id, item.message_id)] = (item.code, item.part_number)
        for item in movies:
            self._refresh_default(item.code)

    def _refresh_default(self, code: str) -> None:
        candidates = [item for (item_code, _), item in self._part_map.items() if item_code == code]
        if not candidates:
            self._default_map.pop(code, None)
            return
        candidates.sort(key=lambda item: item.part_number)
        self._default_map[code] = candidates[0]

    def get(self, code: str, part_number: Optional[int] = None) -> Optional[MovieRecord]:
        if not self.enabled:
            return None
        if part_number is None:
            return self._default_map.get(code)
        clean_part = int(part_number or 1)
        if clean_part < 1:
            clean_part = 1
        return self._part_map.get((code, clean_part))

    def get_parts(self, code: str) -> List[MovieRecord]:
        if not self.enabled:
            return []
        items = [item for (item_code, _), item in self._part_map.items() if item_code == code]
        items.sort(key=lambda item: item.part_number)
        return items

    def set(self, record: MovieRecord) -> None:
        if not self.enabled:
            return
        key = (record.code, record.part_number)
        old = self._part_map.get(key)
        if old and (old.channel_id, old.message_id) != (record.channel_id, record.message_id):
            self._message_map.pop((old.channel_id, old.message_id), None)

        existing_slot = self._message_map.get((record.channel_id, record.message_id))
        if existing_slot and existing_slot != key:
            self._part_map.pop(existing_slot, None)
            self._refresh_default(existing_slot[0])

        self._part_map[key] = record
        self._message_map[(record.channel_id, record.message_id)] = key
        self._refresh_default(record.code)

    def get_by_message(self, channel_id: int, message_id: int) -> Optional[MovieRecord]:
        if not self.enabled:
            return None
        slot = self._message_map.get((channel_id, message_id))
        if not slot:
            return None
        return self._part_map.get(slot)

    def delete_by_code(self, code: str) -> None:
        if not self.enabled:
            return
        keys = [slot for slot in self._part_map.keys() if slot[0] == code]
        for slot in keys:
            record = self._part_map.pop(slot, None)
            if record:
                self._message_map.pop((record.channel_id, record.message_id), None)
        self._default_map.pop(code, None)

    def delete_part(self, code: str, part_number: int) -> None:
        if not self.enabled:
            return
        clean_part = int(part_number or 1)
        if clean_part < 1:
            clean_part = 1
        slot = (code, clean_part)
        record = self._part_map.pop(slot, None)
        if record:
            self._message_map.pop((record.channel_id, record.message_id), None)
        self._refresh_default(code)

    def delete_by_message_ids(self, channel_id: int, message_ids: Iterable[int]) -> List[str]:
        deleted_codes: List[str] = []
        if not self.enabled:
            return deleted_codes
        touched_codes: set[str] = set()
        for message_id in message_ids:
            key = (channel_id, message_id)
            slot = self._message_map.pop(key, None)
            if slot:
                code = slot[0]
                touched_codes.add(code)
                deleted_codes.append(code)
                self._part_map.pop(slot, None)
        for code in touched_codes:
            self._refresh_default(code)
        return deleted_codes

    def clear(self) -> None:
        self._part_map.clear()
        self._default_map.clear()
        self._message_map.clear()


@dataclass
class CachedChannels:
    movie_channels: List[ChannelRecord]
    subscription_channels: List[ChannelRecord]


class ChannelCache:
    def __init__(self, db: Database, ttl_seconds: int = 30) -> None:
        self.db = db
        self.ttl_seconds = ttl_seconds
        self._movie_cache = TTLCache(ttl_seconds)
        self._sub_cache = TTLCache(ttl_seconds)

    async def get_movie_channels(self) -> List[ChannelRecord]:
        cached = self._movie_cache.get("movie")
        if cached is not None:
            return cached
        channels = await self.db.list_movie_channels()
        self._movie_cache.set("movie", channels)
        return channels

    async def get_subscription_channels(self) -> List[ChannelRecord]:
        cached = self._sub_cache.get("subs")
        if cached is not None:
            return cached
        channels = await self.db.list_subscription_channels()
        self._sub_cache.set("subs", channels)
        return channels

    def invalidate_movie_channels(self) -> None:
        self._movie_cache.invalidate("movie")

    def invalidate_subscription_channels(self) -> None:
        self._sub_cache.invalidate("subs")

    def clear(self) -> None:
        self._movie_cache.clear()
        self._sub_cache.clear()
