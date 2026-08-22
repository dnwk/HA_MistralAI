"""Fetch the account voice list (presets + custom) from the Mistral API.

Shared by the TTS entity (Voice Assistants picker) and the options flow
(default-voice dropdown) so both always reflect the live account state.
"""
from __future__ import annotations

import logging

import aiohttp

from .const import MISTRAL_API_BASE

_LOGGER = logging.getLogger(__name__)


async def async_fetch_voice_items(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
) -> list[tuple[str, str]] | None:
    """Return [(voice_id, display_name)] from GET /v1/audio/voices.

    voice_id is the UUID accepted by /v1/audio/speech; display_name is the
    human-readable name. Returns None on any failure — network error,
    non-2xx, empty list — so callers can fall back to the static
    TTS_VOICES list.
    """
    try:
        async with session.get(
            f"{MISTRAL_API_BASE}/audio/voices",
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

    items = data.get("items") or []
    voices = [
        (item["id"], item.get("name") or item["id"])
        for item in items
        if item.get("id")
    ]
    if not voices:
        _LOGGER.warning("Mistral voices list empty")
        return None

    _LOGGER.debug("Loaded %d Mistral voices from account", len(voices))
    return voices
