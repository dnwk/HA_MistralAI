"""Speech-to-text and text-to-speech model selection.

The STT and TTS models default to Mistral's ``-latest`` aliases but can be
overridden in the integration options. The options dropdown suggests the
Voxtral models the account actually has (from GET /v1/models) and also
accepts any typed model ID, because Mistral renames and retires audio models
often enough that a hard-coded list would go stale.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

import aiohttp

from .const import MISTRAL_API_BASE

_LOGGER = logging.getLogger(__name__)


def configured_model(options: Mapping[str, Any], key: str, default: str) -> str:
    """Return the model ID stored under ``key``, or ``default`` if unset/blank."""
    value = options.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def split_audio_models(items: Iterable[Any]) -> tuple[list[str], list[str]]:
    """Split /v1/models entries into sorted (stt_ids, tts_ids).

    Only Voxtral models are kept, including their aliases. IDs containing
    ``tts`` are text-to-speech, the rest speech-to-text. Realtime models are
    skipped: they use a streaming websocket API, not the endpoints this
    integration calls.
    """
    stt: set[str] = set()
    tts: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        aliases = item.get("aliases")
        ids = [item.get("id"), *(aliases if isinstance(aliases, list) else [])]
        for model_id in ids:
            if not isinstance(model_id, str) or not model_id.startswith("voxtral"):
                continue
            if "realtime" in model_id:
                continue
            (tts if "tts" in model_id else stt).add(model_id)
    return sorted(stt), sorted(tts)


def model_choices(default: str, live: Iterable[str], current: str) -> list[str]:
    """Dropdown entries: the default first, then live models, then ``current``.

    ``current`` (the saved value) is appended when it is not already listed,
    so a custom or no-longer-listed model still shows as selected.
    """
    choices = [default]
    for model_id in live:
        if model_id not in choices:
            choices.append(model_id)
    if current and current not in choices:
        choices.append(current)
    return choices


async def async_fetch_audio_models(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Return the account's (stt_ids, tts_ids); both empty on any failure."""
    try:
        async with session.get(
            f"{MISTRAL_API_BASE}/models",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status >= 400:
                _LOGGER.warning("Mistral models list HTTP %s", resp.status)
                return [], []
            data = await resp.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.warning("Mistral models list failed: %s: %s", type(err).__name__, err)
        return [], []

    items = data.get("data") if isinstance(data, dict) else data
    return split_audio_models(items if isinstance(items, list) else [])
