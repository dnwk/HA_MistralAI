"""Fetch the account voice list (presets + custom) from the Mistral API.

Shared by the TTS entity (Voice Assistants picker) and the options flow
(default-voice dropdown) so both always reflect the live account state.

GET /v1/audio/voices is *paginated* and its server-side default page size is
small (10 items observed empirically, August 2026), so every request must
send explicit ``limit``/``offset`` params and keep fetching until ``total``
is reached. It also accepts ``type`` (all|preset|custom) — passed explicitly
as ``all`` so presets and cloned voices are both returned regardless of what
the server default happens to be.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import aiohttp

from .const import MISTRAL_API_BASE

_LOGGER = logging.getLogger(__name__)

# Voices requested per page. The API caps page size server-side; anything we
# ask beyond the cap degrades gracefully because pagination continues until
# `total` is reached or a page comes back empty.
_PAGE_LIMIT = 100

# Safety cap on pages fetched (guards against a server that keeps returning
# items without ever satisfying the `total` check). 50 × 100 = 5000 voices.
_MAX_PAGES = 50


@dataclass(frozen=True)
class VoiceItem:
    """One voice from the account list.

    ``languages`` is the voice's language metadata (BCP-47-ish codes, e.g.
    ``["en"]`` or ``["en-GB"]``). Empty tuple = unknown — typical for custom
    cloned voices without metadata; callers should treat those as usable in
    any language.
    """

    voice_id: str
    name: str
    languages: tuple[str, ...] = ()


def _item_languages(item: dict) -> tuple[str, ...]:
    """Extract language metadata, tolerating both plural and singular keys."""
    langs = item.get("languages")
    if isinstance(langs, str):
        langs = [langs]
    if not langs:
        single = item.get("language")
        langs = [single] if single else []
    return tuple(str(lang) for lang in langs if lang)


async def async_fetch_voice_items(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
) -> list[VoiceItem] | None:
    """Return every voice (presets + custom) from GET /v1/audio/voices.

    ``voice_id`` is the UUID accepted by /v1/audio/speech; ``name`` is the
    human-readable label. Returns None on any failure — network error,
    non-2xx, empty list — so callers can fall back to the static
    TTS_VOICES list.
    """
    items: list[VoiceItem] = []
    seen: set[str] = set()
    offset = 0

    for _ in range(_MAX_PAGES):
        try:
            async with session.get(
                f"{MISTRAL_API_BASE}/audio/voices",
                params={"type": "all", "limit": _PAGE_LIMIT, "offset": offset},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    _LOGGER.warning(
                        "Mistral voices fetch HTTP %s — body=%s", resp.status, body
                    )
                    return None
                data = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.warning("Mistral voices fetch failed: %s", err)
            return None

        page_items = data.get("items") or []
        for item in page_items:
            vid = item.get("id")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            items.append(
                VoiceItem(
                    voice_id=vid,
                    name=item.get("name") or vid,
                    languages=_item_languages(item),
                )
            )

        if not page_items:
            break
        offset += len(page_items)
        total = data.get("total")
        if isinstance(total, int) and offset >= total:
            break

    if not items:
        _LOGGER.warning("Mistral voices list empty")
        return None

    _LOGGER.debug("Loaded %d Mistral voices from account", len(items))
    return items
