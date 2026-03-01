from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import Iterable, List, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .crypto import Crypto

metadata = MetaData()

movies = Table(
    "movies",
    metadata,
    Column("code", String(32), primary_key=True),
    Column("file_id", Text, nullable=False),
    Column("file_unique_id", String(128), nullable=True),
    Column("file_type", String(16), nullable=False),
    Column("channel_id", BigInteger, nullable=False),
    Column("message_id", BigInteger, nullable=False),
    Column("added_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)
Index("ix_movies_channel_message", movies.c.channel_id, movies.c.message_id)

movie_meta = Table(
    "movie_meta",
    metadata,
    Column("code", String(32), primary_key=True),
    Column("caption", Text, nullable=True),
    Column("updated_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)

movie_parts = Table(
    "movie_parts",
    metadata,
    Column("code", String(32), primary_key=True),
    Column("part_number", Integer, primary_key=True, default=1),
    Column("content_kind", String(16), nullable=False, default="movie"),
    Column("file_id", Text, nullable=False),
    Column("file_unique_id", String(128), nullable=True),
    Column("file_type", String(16), nullable=False),
    Column("channel_id", BigInteger, nullable=False),
    Column("message_id", BigInteger, nullable=False),
    Column("caption", Text, nullable=True),
    Column("added_at", DateTime, default=dt.datetime.utcnow, nullable=False),
    Column("updated_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)
Index("ix_movie_parts_channel_message", movie_parts.c.channel_id, movie_parts.c.message_id, unique=True)
Index("ix_movie_parts_code", movie_parts.c.code)

bot_settings = Table(
    "bot_settings",
    metadata,
    Column("setting_key", String(64), primary_key=True),
    Column("setting_value", Text, nullable=False),
    Column("updated_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)

movie_channels = Table(
    "movie_channels",
    metadata,
    Column("chat_id", BigInteger, primary_key=True),
    Column("title", Text, nullable=True),
    Column("username", String(64), nullable=True),
    Column("added_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)

subscription_channels = Table(
    "subscription_channels",
    metadata,
    Column("chat_id", BigInteger, primary_key=True),
    Column("title", Text, nullable=True),
    Column("username", String(64), nullable=True),
    Column("invite_link", Text, nullable=True),
    Column("added_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)

users = Table(
    "users",
    metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("first_name", Text, nullable=True),
    Column("last_name", Text, nullable=True),
    Column("username", String(64), nullable=True),
    Column("joined_at", DateTime, default=dt.datetime.utcnow, nullable=False),
    Column("last_seen", DateTime, default=dt.datetime.utcnow, nullable=False),
)
Index("ix_users_last_seen", users.c.last_seen)

blocked_users = Table(
    "blocked_users",
    metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("reason", Text, nullable=True),
    Column("blocked_by", BigInteger, nullable=True),
    Column("blocked_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)

helpers = Table(
    "helpers",
    metadata,
    Column("bot_id", BigInteger, primary_key=True),
    Column("token", Text, nullable=False),
    Column("username", String(64), nullable=True),
    Column("first_name", Text, nullable=True),
    Column("added_at", DateTime, default=dt.datetime.utcnow, nullable=False),
)

scheduled_deletions = Table(
    "scheduled_deletions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chat_id", BigInteger, nullable=False),
    Column("message_id", BigInteger, nullable=False),
    Column("delete_at", DateTime, nullable=False),
)
Index("ix_scheduled_delete_at", scheduled_deletions.c.delete_at)

support_tickets = Table(
    "support_tickets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, nullable=False),
    Column("first_name", Text, nullable=True),
    Column("last_name", Text, nullable=True),
    Column("username", String(64), nullable=True),
    Column("message_text", Text, nullable=False),
    Column("status", String(16), nullable=False, default="open"),
    Column("answer_text", Text, nullable=True),
    Column("answered_by", BigInteger, nullable=True),
    Column("created_at", DateTime, default=dt.datetime.utcnow, nullable=False),
    Column("answered_at", DateTime, nullable=True),
)
Index("ix_support_tickets_status", support_tickets.c.status)
Index("ix_support_tickets_user", support_tickets.c.user_id)

admin_sessions = Table(
    "admin_sessions",
    metadata,
    Column("token_hash", String(128), primary_key=True),
    Column("username", String(64), nullable=False),
    Column("created_at", DateTime, default=dt.datetime.utcnow, nullable=False),
    Column("expires_at", DateTime, nullable=False),
)
Index("ix_admin_sessions_expires", admin_sessions.c.expires_at)

broadcast_logs = Table(
    "broadcast_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_by", BigInteger, nullable=True),
    Column("message_text", Text, nullable=True),
    Column("status", String(16), nullable=False, default="queued"),
    Column("total_users", Integer, nullable=False, default=0),
    Column("sent_count", Integer, nullable=False, default=0),
    Column("failed_count", Integer, nullable=False, default=0),
    Column("error_text", Text, nullable=True),
    Column("created_at", DateTime, default=dt.datetime.utcnow, nullable=False),
    Column("completed_at", DateTime, nullable=True),
)
Index("ix_broadcast_logs_created_at", broadcast_logs.c.created_at)


@dataclass
class MovieRecord:
    code: str
    file_id: str
    file_type: str
    channel_id: int
    message_id: int
    caption: Optional[str] = None
    part_number: int = 1
    content_kind: str = "movie"


@dataclass
class ChannelRecord:
    chat_id: int
    title: Optional[str]
    username: Optional[str]
    invite_link: Optional[str] = None


@dataclass
class HelperRecord:
    bot_id: int
    token: str
    username: Optional[str]
    first_name: Optional[str]


@dataclass
class SupportTicketRecord:
    id: int
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    message_text: str
    status: str
    answer_text: Optional[str]
    answered_by: Optional[int]
    created_at: dt.datetime
    answered_at: Optional[dt.datetime]


class Database:
    def __init__(self, database_url: str, crypto: Crypto) -> None:
        self.engine: AsyncEngine = create_async_engine(database_url, future=True)
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)
        self.crypto = crypto

    async def init(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        await self._migrate_legacy_movies()

    async def dispose(self) -> None:
        await self.engine.dispose()

    def _legacy_movie_stmt(self):
        return (
            select(
                movies.c.code,
                movies.c.file_id,
                movies.c.file_type,
                movies.c.channel_id,
                movies.c.message_id,
                movie_meta.c.caption,
                func.cast(1, Integer).label("part_number"),
                func.cast("movie", String).label("content_kind"),
            )
            .select_from(movies.outerjoin(movie_meta, movies.c.code == movie_meta.c.code))
        )

    def _movie_parts_stmt(self):
        return select(
            movie_parts.c.code,
            movie_parts.c.file_id,
            movie_parts.c.file_type,
            movie_parts.c.channel_id,
            movie_parts.c.message_id,
            movie_parts.c.caption,
            movie_parts.c.part_number,
            movie_parts.c.content_kind,
        )

    def _row_to_movie(self, data) -> Optional[MovieRecord]:
        file_id = self.crypto.decrypt(data["file_id"])
        if not file_id:
            return None
        return MovieRecord(
            code=data["code"],
            file_id=file_id,
            file_type=data["file_type"],
            channel_id=int(data["channel_id"]),
            message_id=int(data["message_id"]),
            caption=data.get("caption"),
            part_number=int(data.get("part_number") or 1),
            content_kind=(data.get("content_kind") or "movie"),
        )

    async def _migrate_legacy_movies(self) -> None:
        async with self.session() as session:
            parts_count_result = await session.execute(select(func.count()).select_from(movie_parts))
            parts_count = int(parts_count_result.scalar() or 0)
            if parts_count > 0:
                return

            legacy_result = await session.execute(self._legacy_movie_stmt())
            rows = legacy_result.fetchall()
            if not rows:
                return

            for row in rows:
                data = row._mapping
                await session.execute(
                    insert(movie_parts).values(
                        code=data["code"],
                        part_number=1,
                        content_kind="movie",
                        file_id=data["file_id"],
                        file_unique_id=None,
                        file_type=data["file_type"],
                        channel_id=int(data["channel_id"]),
                        message_id=int(data["message_id"]),
                        caption=data.get("caption"),
                        added_at=dt.datetime.utcnow(),
                        updated_at=dt.datetime.utcnow(),
                    )
                )
            await session.commit()

    async def _sync_legacy_for_code(self, session, code: str) -> None:
        result = await session.execute(
            self._movie_parts_stmt()
            .where(movie_parts.c.code == code)
            .order_by(movie_parts.c.part_number.asc())
            .limit(1)
        )
        row = result.fetchone()
        await session.execute(delete(movies).where(movies.c.code == code))
        await session.execute(delete(movie_meta).where(movie_meta.c.code == code))
        if not row:
            return
        data = row._mapping
        await session.execute(
            insert(movies).values(
                code=code,
                file_id=data["file_id"],
                file_unique_id=None,
                file_type=data["file_type"],
                channel_id=int(data["channel_id"]),
                message_id=int(data["message_id"]),
                added_at=dt.datetime.utcnow(),
            )
        )
        caption = (data.get("caption") or "").strip()
        if caption:
            await session.execute(
                insert(movie_meta).values(
                    code=code,
                    caption=caption,
                    updated_at=dt.datetime.utcnow(),
                )
            )

    async def add_movie(
        self,
        code: str,
        file_id: str,
        file_unique_id: Optional[str],
        file_type: str,
        channel_id: int,
        message_id: int,
        caption: Optional[str] = None,
        *,
        content_kind: str = "movie",
        part_number: int = 1,
    ) -> None:
        clean_kind = (content_kind or "movie").strip().lower()
        if clean_kind not in {"movie", "serial"}:
            clean_kind = "movie"
        clean_part = int(part_number or 1)
        if clean_part < 1:
            clean_part = 1

        enc_file_id = self.crypto.encrypt(file_id)
        async with self.session() as session:
            await session.execute(
                delete(movie_parts).where(
                    (movie_parts.c.code == code) & (movie_parts.c.part_number == clean_part)
                )
            )
            await session.execute(
                insert(movie_parts).values(
                    code=code,
                    part_number=clean_part,
                    content_kind=clean_kind,
                    file_id=enc_file_id,
                    file_unique_id=file_unique_id,
                    file_type=file_type,
                    channel_id=channel_id,
                    message_id=message_id,
                    caption=caption.strip() if caption and caption.strip() else None,
                    added_at=dt.datetime.utcnow(),
                    updated_at=dt.datetime.utcnow(),
                )
            )
            await self._sync_legacy_for_code(session, code)
            await session.commit()

    async def set_movie_caption(self, code: str, caption: Optional[str], part_number: int = 1) -> None:
        clean_part = int(part_number or 1)
        if clean_part < 1:
            clean_part = 1
        caption_value = caption.strip() if caption and caption.strip() else None

        async with self.session() as session:
            await session.execute(
                update(movie_parts)
                .where((movie_parts.c.code == code) & (movie_parts.c.part_number == clean_part))
                .values(
                    caption=caption_value,
                    updated_at=dt.datetime.utcnow(),
                )
            )
            await self._sync_legacy_for_code(session, code)
            await session.commit()

    async def get_movie(self, code: str) -> Optional[MovieRecord]:
        async with self.session() as session:
            result = await session.execute(
                self._movie_parts_stmt()
                .where(movie_parts.c.code == code)
                .order_by(movie_parts.c.part_number.asc())
                .limit(1)
            )
            row = result.fetchone()
            if row:
                return self._row_to_movie(row._mapping)

            legacy = await session.execute(self._legacy_movie_stmt().where(movies.c.code == code).limit(1))
            row = legacy.fetchone()
            if not row:
                return None
            return self._row_to_movie(row._mapping)

    async def get_movie_part(self, code: str, part_number: int) -> Optional[MovieRecord]:
        clean_part = int(part_number or 1)
        if clean_part < 1:
            clean_part = 1
        async with self.session() as session:
            result = await session.execute(
                self._movie_parts_stmt().where(
                    (movie_parts.c.code == code) & (movie_parts.c.part_number == clean_part)
                )
            )
            row = result.fetchone()
            if row:
                return self._row_to_movie(row._mapping)
            if clean_part != 1:
                return None
            legacy = await session.execute(self._legacy_movie_stmt().where(movies.c.code == code).limit(1))
            row = legacy.fetchone()
            if not row:
                return None
            return self._row_to_movie(row._mapping)

    async def list_movie_parts(self, code: str) -> List[MovieRecord]:
        async with self.session() as session:
            result = await session.execute(
                self._movie_parts_stmt()
                .where(movie_parts.c.code == code)
                .order_by(movie_parts.c.part_number.asc())
            )
            rows = result.fetchall()
            if rows:
                items: List[MovieRecord] = []
                for row in rows:
                    record = self._row_to_movie(row._mapping)
                    if record:
                        items.append(record)
                return items

            legacy = await session.execute(self._legacy_movie_stmt().where(movies.c.code == code).limit(1))
            row = legacy.fetchone()
            if not row:
                return []
            record = self._row_to_movie(row._mapping)
            return [record] if record else []

    async def get_movie_by_message(self, channel_id: int, message_id: int) -> Optional[MovieRecord]:
        async with self.session() as session:
            result = await session.execute(
                self._movie_parts_stmt().where(
                    (movie_parts.c.channel_id == channel_id) & (movie_parts.c.message_id == message_id)
                )
            )
            row = result.fetchone()
            if row:
                return self._row_to_movie(row._mapping)

            legacy = await session.execute(
                self._legacy_movie_stmt().where(
                    (movies.c.channel_id == channel_id) & (movies.c.message_id == message_id)
                )
            )
            row = legacy.fetchone()
            if not row:
                return None
            return self._row_to_movie(row._mapping)

    async def list_movies(self) -> List[MovieRecord]:
        async with self.session() as session:
            result = await session.execute(
                self._movie_parts_stmt().order_by(movie_parts.c.code.asc(), movie_parts.c.part_number.asc())
            )
            rows = result.fetchall()
            if not rows:
                legacy = await session.execute(self._legacy_movie_stmt().order_by(movies.c.code.asc()))
                rows = legacy.fetchall()
            items: List[MovieRecord] = []
            for row in rows:
                record = self._row_to_movie(row._mapping)
                if record:
                    items.append(record)
            return items

    async def list_movies_paginated(
        self,
        limit: int = 25,
        offset: int = 0,
        query: Optional[str] = None,
        content_kind: Optional[str] = None,
    ) -> List[MovieRecord]:
        stmt = (
            self._movie_parts_stmt()
            .order_by(movie_parts.c.added_at.desc(), movie_parts.c.part_number.asc())
            .limit(limit)
            .offset(offset)
        )
        if query:
            q = query.strip()
            if q:
                stmt = stmt.where(movie_parts.c.code.ilike(f"%{q}%"))
        if content_kind in {"movie", "serial"}:
            stmt = stmt.where(movie_parts.c.content_kind == content_kind)

        async with self.session() as session:
            result = await session.execute(stmt)
            rows = result.fetchall()
            if not rows and content_kind != "serial":
                fallback = (
                    self._legacy_movie_stmt()
                    .order_by(movies.c.added_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                if query:
                    q = query.strip()
                    if q:
                        fallback = fallback.where(movies.c.code.ilike(f"%{q}%"))
                result = await session.execute(fallback)
                rows = result.fetchall()
            items: List[MovieRecord] = []
            for row in rows:
                record = self._row_to_movie(row._mapping)
                if record:
                    items.append(record)
            return items

    async def list_code_overview(
        self,
        limit: int = 30,
        query: Optional[str] = None,
        content_kind: Optional[str] = None,
    ) -> List[dict]:
        stmt = (
            select(
                movie_parts.c.code.label("code"),
                movie_parts.c.content_kind.label("content_kind"),
                func.count().label("parts_count"),
                func.max(movie_parts.c.part_number).label("max_part"),
                func.max(movie_parts.c.added_at).label("last_added"),
            )
            .group_by(movie_parts.c.code, movie_parts.c.content_kind)
            .order_by(func.max(movie_parts.c.added_at).desc())
            .limit(limit)
        )
        if query:
            q = query.strip()
            if q:
                stmt = stmt.where(movie_parts.c.code.ilike(f"%{q}%"))
        if content_kind in {"movie", "serial"}:
            stmt = stmt.where(movie_parts.c.content_kind == content_kind)

        async with self.session() as session:
            result = await session.execute(stmt)
            rows = [dict(row._mapping) for row in result.fetchall()]
            if rows:
                return rows
            if content_kind == "serial":
                return []
            legacy_stmt = (
                select(
                    movies.c.code.label("code"),
                    func.cast("movie", String).label("content_kind"),
                    func.cast(1, Integer).label("parts_count"),
                    func.cast(1, Integer).label("max_part"),
                    movies.c.added_at.label("last_added"),
                )
                .order_by(movies.c.added_at.desc())
                .limit(limit)
            )
            if query:
                q = query.strip()
                if q:
                    legacy_stmt = legacy_stmt.where(movies.c.code.ilike(f"%{q}%"))
            legacy_result = await session.execute(legacy_stmt)
            return [dict(row._mapping) for row in legacy_result.fetchall()]

    async def count_movies_filtered(
        self,
        query: Optional[str] = None,
        content_kind: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(movie_parts)
        if query:
            q = query.strip()
            if q:
                stmt = stmt.where(movie_parts.c.code.ilike(f"%{q}%"))
        if content_kind in {"movie", "serial"}:
            stmt = stmt.where(movie_parts.c.content_kind == content_kind)
        async with self.session() as session:
            result = await session.execute(stmt)
            count = int(result.scalar() or 0)
            if count > 0:
                return count
            if content_kind == "serial":
                return 0
            legacy_stmt = select(func.count()).select_from(movies)
            if query:
                q = query.strip()
                if q:
                    legacy_stmt = legacy_stmt.where(movies.c.code.ilike(f"%{q}%"))
            legacy_result = await session.execute(legacy_stmt)
            return int(legacy_result.scalar() or 0)

    async def delete_movie_by_code(self, code: str) -> int:
        async with self.session() as session:
            result_parts = await session.execute(delete(movie_parts).where(movie_parts.c.code == code))
            await session.execute(delete(movie_meta).where(movie_meta.c.code == code))
            result = await session.execute(delete(movies).where(movies.c.code == code))
            await session.commit()
            return (result.rowcount or 0) + (result_parts.rowcount or 0)

    async def delete_movie_part(self, code: str, part_number: int) -> int:
        clean_part = int(part_number or 1)
        if clean_part < 1:
            clean_part = 1
        async with self.session() as session:
            result = await session.execute(
                delete(movie_parts).where(
                    (movie_parts.c.code == code) & (movie_parts.c.part_number == clean_part)
                )
            )
            await self._sync_legacy_for_code(session, code)
            await session.commit()
            return result.rowcount or 0

    async def delete_movies_by_message_ids(self, channel_id: int, message_ids: Iterable[int]) -> int:
        ids = list(message_ids)
        if not ids:
            return 0
        async with self.session() as session:
            parts_code_result = await session.execute(
                select(movie_parts.c.code).where(
                    (movie_parts.c.channel_id == channel_id) & (movie_parts.c.message_id.in_(ids))
                )
            )
            part_codes = [row[0] for row in parts_code_result.fetchall()]

            result_parts = await session.execute(
                delete(movie_parts).where(
                    (movie_parts.c.channel_id == channel_id) & (movie_parts.c.message_id.in_(ids))
                )
            )

            code_result = await session.execute(
                select(movies.c.code).where(
                    (movies.c.channel_id == channel_id) & (movies.c.message_id.in_(ids))
                )
            )
            legacy_codes = [row[0] for row in code_result.fetchall()]
            codes = sorted(set(part_codes + legacy_codes))
            if codes:
                await session.execute(delete(movie_meta).where(movie_meta.c.code.in_(codes)))

            result = await session.execute(
                delete(movies).where(
                    (movies.c.channel_id == channel_id) & (movies.c.message_id.in_(ids))
                )
            )

            for code in codes:
                await self._sync_legacy_for_code(session, code)

            await session.commit()
            return (result.rowcount or 0) + (result_parts.rowcount or 0)

    async def add_movie_channel(self, chat_id: int, title: Optional[str], username: Optional[str]) -> None:
        async with self.session() as session:
            await session.execute(delete(movie_channels).where(movie_channels.c.chat_id == chat_id))
            await session.execute(
                insert(movie_channels).values(
                    chat_id=chat_id,
                    title=title,
                    username=username,
                    added_at=dt.datetime.utcnow(),
                )
            )
            await session.commit()

    async def list_movie_channels(self) -> List[ChannelRecord]:
        async with self.session() as session:
            result = await session.execute(select(movie_channels).order_by(movie_channels.c.added_at.desc()))
            return [
                ChannelRecord(
                    chat_id=int(row._mapping["chat_id"]),
                    title=row._mapping["title"],
                    username=row._mapping["username"],
                )
                for row in result.fetchall()
            ]

    async def remove_movie_channel(self, chat_id: int) -> int:
        async with self.session() as session:
            result = await session.execute(delete(movie_channels).where(movie_channels.c.chat_id == chat_id))
            await session.commit()
            return result.rowcount or 0

    async def add_subscription_channel(
        self,
        chat_id: int,
        title: Optional[str],
        username: Optional[str],
        invite_link: Optional[str],
    ) -> None:
        enc_invite = self.crypto.encrypt(invite_link) if invite_link else None
        async with self.session() as session:
            await session.execute(delete(subscription_channels).where(subscription_channels.c.chat_id == chat_id))
            await session.execute(
                insert(subscription_channels).values(
                    chat_id=chat_id,
                    title=title,
                    username=username,
                    invite_link=enc_invite,
                    added_at=dt.datetime.utcnow(),
                )
            )
            await session.commit()

    async def list_subscription_channels(self) -> List[ChannelRecord]:
        async with self.session() as session:
            result = await session.execute(
                select(subscription_channels).order_by(subscription_channels.c.added_at.desc())
            )
            items: List[ChannelRecord] = []
            for row in result.fetchall():
                data = row._mapping
                invite_link = self.crypto.decrypt(data["invite_link"])
                items.append(
                    ChannelRecord(
                        chat_id=int(data["chat_id"]),
                        title=data["title"],
                        username=data["username"],
                        invite_link=invite_link,
                    )
                )
            return items

    async def remove_subscription_channel(self, chat_id: int) -> int:
        async with self.session() as session:
            result = await session.execute(
                delete(subscription_channels).where(subscription_channels.c.chat_id == chat_id)
            )
            await session.commit()
            return result.rowcount or 0

    async def upsert_user(
        self,
        user_id: int,
        first_name: Optional[str],
        last_name: Optional[str],
        username: Optional[str],
    ) -> None:
        async with self.session() as session:
            updated = await session.execute(
                update(users)
                .where(users.c.user_id == user_id)
                .values(
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    last_seen=dt.datetime.utcnow(),
                )
            )
            if (updated.rowcount or 0) == 0:
                await session.execute(
                    insert(users).values(
                        user_id=user_id,
                        first_name=first_name,
                        last_name=last_name,
                        username=username,
                        joined_at=dt.datetime.utcnow(),
                        last_seen=dt.datetime.utcnow(),
                    )
                )
            await session.commit()

    async def get_user(self, user_id: int) -> Optional[dict]:
        async with self.session() as session:
            result = await session.execute(
                select(
                    users,
                    blocked_users.c.reason.label("blocked_reason"),
                    blocked_users.c.blocked_at.label("blocked_at"),
                    blocked_users.c.blocked_by.label("blocked_by"),
                )
                .select_from(users.outerjoin(blocked_users, users.c.user_id == blocked_users.c.user_id))
                .where(users.c.user_id == user_id)
            )
            row = result.fetchone()
            if not row:
                return None
            data = dict(row._mapping)
            data["is_blocked"] = data.get("blocked_reason") is not None or data.get("blocked_at") is not None
            return data

    def _build_user_query_filter(self, query: Optional[str]):
        if not query:
            return None
        q = query.strip()
        if not q:
            return None
        if q.lstrip("-").isdigit():
            return users.c.user_id == int(q)
        like_q = f"%{q.lower()}%"
        return or_(
            func.lower(func.coalesce(users.c.first_name, "")).like(like_q),
            func.lower(func.coalesce(users.c.last_name, "")).like(like_q),
            func.lower(func.coalesce(users.c.username, "")).like(like_q),
        )

    async def list_users(self, limit: int = 20) -> List[dict]:
        return await self.list_users_paginated(limit=limit, offset=0, query=None, include_blocked=True)

    async def list_users_paginated(
        self,
        limit: int = 50,
        offset: int = 0,
        query: Optional[str] = None,
        include_blocked: bool = True,
    ) -> List[dict]:
        stmt = (
            select(
                users,
                blocked_users.c.reason.label("blocked_reason"),
                blocked_users.c.blocked_at.label("blocked_at"),
                blocked_users.c.blocked_by.label("blocked_by"),
            )
            .select_from(users.outerjoin(blocked_users, users.c.user_id == blocked_users.c.user_id))
            .order_by(users.c.last_seen.desc())
            .limit(limit)
            .offset(offset)
        )
        query_filter = self._build_user_query_filter(query)
        if query_filter is not None:
            stmt = stmt.where(query_filter)
        if not include_blocked:
            stmt = stmt.where(blocked_users.c.user_id.is_(None))

        async with self.session() as session:
            result = await session.execute(stmt)
            items: List[dict] = []
            for row in result.fetchall():
                data = dict(row._mapping)
                data["is_blocked"] = data.get("blocked_reason") is not None or data.get("blocked_at") is not None
                items.append(data)
            return items

    async def count_users(self) -> int:
        async with self.session() as session:
            result = await session.execute(select(func.count()).select_from(users))
            return int(result.scalar() or 0)

    async def count_users_filtered(self, query: Optional[str] = None, include_blocked: bool = True) -> int:
        stmt = select(func.count()).select_from(
            users.outerjoin(blocked_users, users.c.user_id == blocked_users.c.user_id)
        )
        query_filter = self._build_user_query_filter(query)
        if query_filter is not None:
            stmt = stmt.where(query_filter)
        if not include_blocked:
            stmt = stmt.where(blocked_users.c.user_id.is_(None))
        async with self.session() as session:
            result = await session.execute(stmt)
            return int(result.scalar() or 0)

    async def list_all_user_ids(self, include_blocked: bool = False) -> List[int]:
        stmt = select(users.c.user_id).select_from(
            users.outerjoin(blocked_users, users.c.user_id == blocked_users.c.user_id)
        )
        if not include_blocked:
            stmt = stmt.where(blocked_users.c.user_id.is_(None))
        async with self.session() as session:
            result = await session.execute(stmt)
            return [int(row[0]) for row in result.fetchall()]

    async def is_user_blocked(self, user_id: int) -> bool:
        async with self.session() as session:
            result = await session.execute(
                select(blocked_users.c.user_id).where(blocked_users.c.user_id == user_id)
            )
            return result.fetchone() is not None

    async def block_user(self, user_id: int, blocked_by: Optional[int], reason: Optional[str]) -> None:
        async with self.session() as session:
            await session.execute(delete(blocked_users).where(blocked_users.c.user_id == user_id))
            await session.execute(
                insert(blocked_users).values(
                    user_id=user_id,
                    blocked_by=blocked_by,
                    reason=(reason or "").strip() or None,
                    blocked_at=dt.datetime.utcnow(),
                )
            )
            await session.commit()

    async def unblock_user(self, user_id: int) -> int:
        async with self.session() as session:
            result = await session.execute(delete(blocked_users).where(blocked_users.c.user_id == user_id))
            await session.commit()
            return result.rowcount or 0

    async def count_blocked_users(self) -> int:
        async with self.session() as session:
            result = await session.execute(select(func.count()).select_from(blocked_users))
            return int(result.scalar() or 0)

    async def count_movies(self) -> int:
        async with self.session() as session:
            result = await session.execute(select(func.count(func.distinct(movie_parts.c.code))))
            count = int(result.scalar() or 0)
            if count > 0:
                return count
            legacy = await session.execute(select(func.count()).select_from(movies))
            return int(legacy.scalar() or 0)

    async def count_channels(self) -> int:
        async with self.session() as session:
            result = await session.execute(select(func.count()).select_from(movie_channels))
            return int(result.scalar() or 0)

    async def count_subscription_channels(self) -> int:
        async with self.session() as session:
            result = await session.execute(select(func.count()).select_from(subscription_channels))
            return int(result.scalar() or 0)

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        async with self.session() as session:
            result = await session.execute(
                select(bot_settings.c.setting_value).where(bot_settings.c.setting_key == key).limit(1)
            )
            row = result.fetchone()
            if not row:
                return default
            return str(row[0])

    async def set_setting(self, key: str, value: str) -> None:
        clean_value = str(value)
        async with self.session() as session:
            await session.execute(delete(bot_settings).where(bot_settings.c.setting_key == key))
            await session.execute(
                insert(bot_settings).values(
                    setting_key=key,
                    setting_value=clean_value,
                    updated_at=dt.datetime.utcnow(),
                )
            )
            await session.commit()

    async def get_bool_setting(self, key: str, default: bool = False) -> bool:
        value = await self.get_setting(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    async def set_bool_setting(self, key: str, value: bool) -> None:
        await self.set_setting(key, "1" if value else "0")

    async def get_dynamic_admin_ids(self) -> List[int]:
        raw = await self.get_setting("dynamic_admin_ids", default="[]")
        if raw is None:
            return []
        text = str(raw).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                ids = []
                for item in parsed:
                    try:
                        ids.append(int(item))
                    except Exception:
                        continue
                return sorted(set(ids))
        except Exception:
            pass
        # fallback: comma separated
        parts = [p.strip() for p in text.split(",") if p.strip()]
        ids: List[int] = []
        for part in parts:
            if part.lstrip("-").isdigit():
                ids.append(int(part))
        return sorted(set(ids))

    async def set_dynamic_admin_ids(self, user_ids: Iterable[int]) -> None:
        normalized = sorted(set(int(uid) for uid in user_ids))
        await self.set_setting("dynamic_admin_ids", json.dumps(normalized))

    async def add_dynamic_admin(self, user_id: int) -> List[int]:
        ids = await self.get_dynamic_admin_ids()
        if user_id not in ids:
            ids.append(user_id)
            ids = sorted(set(ids))
            await self.set_dynamic_admin_ids(ids)
        return ids

    async def remove_dynamic_admin(self, user_id: int) -> List[int]:
        ids = await self.get_dynamic_admin_ids()
        ids = [uid for uid in ids if uid != user_id]
        await self.set_dynamic_admin_ids(ids)
        return sorted(set(ids))

    async def add_helper(self, bot_id: int, token: str, username: Optional[str], first_name: Optional[str]) -> None:
        enc_token = self.crypto.encrypt(token)
        async with self.session() as session:
            await session.execute(delete(helpers).where(helpers.c.bot_id == bot_id))
            await session.execute(
                insert(helpers).values(
                    bot_id=bot_id,
                    token=enc_token,
                    username=username,
                    first_name=first_name,
                    added_at=dt.datetime.utcnow(),
                )
            )
            await session.commit()

    async def list_helpers(self) -> List[HelperRecord]:
        async with self.session() as session:
            result = await session.execute(select(helpers))
            items: List[HelperRecord] = []
            for row in result.fetchall():
                data = row._mapping
                token = self.crypto.decrypt(data["token"])
                if not token:
                    continue
                items.append(
                    HelperRecord(
                        bot_id=int(data["bot_id"]),
                        token=token,
                        username=data["username"],
                        first_name=data["first_name"],
                    )
                )
            return items

    async def remove_helper(self, bot_id: int) -> int:
        async with self.session() as session:
            result = await session.execute(delete(helpers).where(helpers.c.bot_id == bot_id))
            await session.commit()
            return result.rowcount or 0

    async def schedule_delete(self, chat_id: int, message_id: int, delete_at: dt.datetime) -> None:
        async with self.session() as session:
            await session.execute(
                insert(scheduled_deletions).values(
                    chat_id=chat_id,
                    message_id=message_id,
                    delete_at=delete_at,
                )
            )
            await session.commit()

    async def fetch_due_deletions(self, now: Optional[dt.datetime] = None, limit: int = 100) -> List[dict]:
        if now is None:
            now = dt.datetime.utcnow()
        async with self.session() as session:
            result = await session.execute(
                select(scheduled_deletions)
                .where(scheduled_deletions.c.delete_at <= now)
                .order_by(scheduled_deletions.c.delete_at.asc())
                .limit(limit)
            )
            return [dict(row._mapping) for row in result.fetchall()]

    async def remove_scheduled(self, ids: Iterable[int]) -> int:
        ids_list = list(ids)
        if not ids_list:
            return 0
        async with self.session() as session:
            result = await session.execute(
                delete(scheduled_deletions).where(scheduled_deletions.c.id.in_(ids_list))
            )
            await session.commit()
            return result.rowcount or 0

    async def create_support_ticket(
        self,
        user_id: int,
        first_name: Optional[str],
        last_name: Optional[str],
        username: Optional[str],
        message_text: str,
    ) -> int:
        async with self.session() as session:
            result = await session.execute(
                insert(support_tickets).values(
                    user_id=user_id,
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    message_text=message_text,
                    status="open",
                    created_at=dt.datetime.utcnow(),
                )
            )
            ticket_id = result.inserted_primary_key[0] if result.inserted_primary_key else None
            if ticket_id is None:
                fetch = await session.execute(select(func.max(support_tickets.c.id)))
                ticket_id = int(fetch.scalar() or 0)
            await session.commit()
            return int(ticket_id)

    async def get_support_ticket(self, ticket_id: int) -> Optional[SupportTicketRecord]:
        async with self.session() as session:
            result = await session.execute(
                select(support_tickets).where(support_tickets.c.id == ticket_id).limit(1)
            )
            row = result.fetchone()
            if not row:
                return None
            data = row._mapping
            return SupportTicketRecord(
                id=int(data["id"]),
                user_id=int(data["user_id"]),
                first_name=data["first_name"],
                last_name=data["last_name"],
                username=data["username"],
                message_text=data["message_text"],
                status=data["status"],
                answer_text=data["answer_text"],
                answered_by=int(data["answered_by"]) if data["answered_by"] is not None else None,
                created_at=data["created_at"],
                answered_at=data["answered_at"],
            )

    async def list_support_tickets(
        self,
        status: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
    ) -> List[SupportTicketRecord]:
        stmt = select(support_tickets)
        if status:
            stmt = stmt.where(support_tickets.c.status == status)
        stmt = stmt.order_by(support_tickets.c.created_at.desc()).limit(limit).offset(offset)

        async with self.session() as session:
            result = await session.execute(stmt)
            items: List[SupportTicketRecord] = []
            for row in result.fetchall():
                data = row._mapping
                items.append(
                    SupportTicketRecord(
                        id=int(data["id"]),
                        user_id=int(data["user_id"]),
                        first_name=data["first_name"],
                        last_name=data["last_name"],
                        username=data["username"],
                        message_text=data["message_text"],
                        status=data["status"],
                        answer_text=data["answer_text"],
                        answered_by=int(data["answered_by"]) if data["answered_by"] is not None else None,
                        created_at=data["created_at"],
                        answered_at=data["answered_at"],
                    )
                )
            return items

    async def count_support_tickets(self, status: Optional[str] = None) -> int:
        stmt = select(func.count()).select_from(support_tickets)
        if status:
            stmt = stmt.where(support_tickets.c.status == status)
        async with self.session() as session:
            result = await session.execute(stmt)
            return int(result.scalar() or 0)

    async def mark_support_ticket_answered(
        self,
        ticket_id: int,
        answer_text: str,
        answered_by: Optional[int],
    ) -> int:
        async with self.session() as session:
            result = await session.execute(
                update(support_tickets)
                .where(support_tickets.c.id == ticket_id)
                .values(
                    status="answered",
                    answer_text=answer_text,
                    answered_by=answered_by,
                    answered_at=dt.datetime.utcnow(),
                )
            )
            await session.commit()
            return result.rowcount or 0

    async def create_admin_session(self, token_hash: str, username: str, expires_at: dt.datetime) -> None:
        async with self.session() as session:
            await session.execute(
                insert(admin_sessions).values(
                    token_hash=token_hash,
                    username=username,
                    created_at=dt.datetime.utcnow(),
                    expires_at=expires_at,
                )
            )
            await session.commit()

    async def get_admin_session(self, token_hash: str) -> Optional[dict]:
        now = dt.datetime.utcnow()
        async with self.session() as session:
            result = await session.execute(
                select(admin_sessions)
                .where(admin_sessions.c.token_hash == token_hash)
                .where(admin_sessions.c.expires_at > now)
                .limit(1)
            )
            row = result.fetchone()
            if not row:
                return None
            return dict(row._mapping)

    async def delete_admin_session(self, token_hash: str) -> int:
        async with self.session() as session:
            result = await session.execute(
                delete(admin_sessions).where(admin_sessions.c.token_hash == token_hash)
            )
            await session.commit()
            return result.rowcount or 0

    async def purge_expired_admin_sessions(self, now: Optional[dt.datetime] = None) -> int:
        if now is None:
            now = dt.datetime.utcnow()
        async with self.session() as session:
            result = await session.execute(
                delete(admin_sessions).where(admin_sessions.c.expires_at <= now)
            )
            await session.commit()
            return result.rowcount or 0

    async def create_broadcast_log(
        self,
        created_by: Optional[int],
        message_text: str,
        total_users: int,
        status: str = "queued",
    ) -> int:
        async with self.session() as session:
            result = await session.execute(
                insert(broadcast_logs).values(
                    created_by=created_by,
                    message_text=message_text,
                    status=status,
                    total_users=total_users,
                    sent_count=0,
                    failed_count=0,
                    created_at=dt.datetime.utcnow(),
                )
            )
            log_id = result.inserted_primary_key[0] if result.inserted_primary_key else None
            if log_id is None:
                fetch = await session.execute(select(func.max(broadcast_logs.c.id)))
                log_id = int(fetch.scalar() or 0)
            await session.commit()
            return int(log_id)

    async def update_broadcast_log(
        self,
        log_id: int,
        *,
        status: Optional[str] = None,
        sent_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        total_users: Optional[int] = None,
        error_text: Optional[str] = None,
        completed_at: Optional[dt.datetime] = None,
    ) -> int:
        values = {}
        if status is not None:
            values["status"] = status
        if sent_count is not None:
            values["sent_count"] = sent_count
        if failed_count is not None:
            values["failed_count"] = failed_count
        if total_users is not None:
            values["total_users"] = total_users
        if error_text is not None:
            values["error_text"] = error_text
        if completed_at is not None:
            values["completed_at"] = completed_at
        if not values:
            return 0

        async with self.session() as session:
            result = await session.execute(
                update(broadcast_logs).where(broadcast_logs.c.id == log_id).values(**values)
            )
            await session.commit()
            return result.rowcount or 0

    async def list_broadcast_logs(self, limit: int = 20) -> List[dict]:
        async with self.session() as session:
            result = await session.execute(
                select(broadcast_logs).order_by(broadcast_logs.c.created_at.desc()).limit(limit)
            )
            return [dict(row._mapping) for row in result.fetchall()]

    async def reset_all_data(self) -> None:
        async with self.session() as session:
            await session.execute(delete(movies))
            await session.execute(delete(movie_meta))
            await session.execute(delete(movie_parts))
            await session.execute(delete(bot_settings))
            await session.execute(delete(movie_channels))
            await session.execute(delete(subscription_channels))
            await session.execute(delete(users))
            await session.execute(delete(blocked_users))
            await session.execute(delete(helpers))
            await session.execute(delete(scheduled_deletions))
            await session.execute(delete(support_tickets))
            await session.execute(delete(admin_sessions))
            await session.execute(delete(broadcast_logs))
            await session.commit()
