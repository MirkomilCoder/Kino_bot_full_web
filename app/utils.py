from __future__ import annotations

import re
from typing import Optional

from .db import ChannelRecord

CODE_RE = re.compile(r"^\d+$")
CODE_TAG_RE = re.compile(r"^kod\s*:\s*(\d+)$", re.IGNORECASE)
TYPE_TAG_RE = re.compile(r"^type\s*:\s*(movie|serial)$", re.IGNORECASE)
PART_TAG_RE = re.compile(r"^(?:qism|qismi|part)\s*:\s*(\d+)$", re.IGNORECASE)


def extract_code_from_caption(caption: Optional[str]) -> Optional[str]:
    code, _, _ = parse_movie_caption_meta(caption)
    return code


def parse_movie_caption_meta(caption: Optional[str]) -> tuple[Optional[str], str, int]:
    content_kind = "movie"
    part_number = 1
    if not caption:
        return None, content_kind, part_number
    lines = [line.strip() for line in caption.splitlines() if line.strip()]
    if not lines:
        return None, content_kind, part_number

    code: Optional[str] = None
    for line in lines:
        type_match = TYPE_TAG_RE.match(line)
        if type_match:
            content_kind = type_match.group(1).lower()
            continue
        part_match = PART_TAG_RE.match(line)
        if part_match:
            try:
                parsed_part = int(part_match.group(1))
            except ValueError:
                parsed_part = 1
            part_number = max(1, parsed_part)
            continue
        code_match = CODE_TAG_RE.match(line)
        if code_match:
            code = code_match.group(1)

    if code is None:
        for line in reversed(lines):
            if CODE_RE.match(line):
                code = line
                break

    if content_kind != "serial":
        content_kind = "movie"
        part_number = 1

    return code, content_kind, part_number


def extract_code_from_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    candidate = text.strip()
    if CODE_RE.match(candidate):
        return candidate
    return None


def format_channel_line(channel: ChannelRecord) -> str:
    if channel.username:
        return f"@{channel.username}"
    if channel.invite_link:
        return channel.invite_link
    if channel.title:
        return f"{channel.title} ({channel.chat_id})"
    return str(channel.chat_id)


def channel_join_link(channel: ChannelRecord) -> Optional[str]:
    if channel.username:
        return f"https://t.me/{channel.username}"
    if channel.invite_link:
        return channel.invite_link
    return None


def channel_button_text(channel: ChannelRecord) -> str:
    if channel.title:
        return channel.title[:48]
    if channel.username:
        return f"@{channel.username}"
    return str(channel.chat_id)


def mask_token(token: str) -> str:
    if len(token) < 10:
        return "****"
    return f"{token[:6]}...{token[-4:]}"
