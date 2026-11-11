"""Fetch the account voice list (presets + custom) from the Mistral API.

Shared by the TTS entity (Voice Assistants picker) and the options flow
(default-voice dropdown) so both always reflect the live account state.

GET /v1/audio/voices is *paginated* and its server-side default page size is
small (10 items observed empirically, August 2026), so every request must
send explicit ``limit``/``offset`` params and keep fetching until ``total``
is reached. It also accepts ``type`` (all|preset|custom) — passed explicitly
as ``all`` so presets and cloned voices are both returned regardless of what
the server default happens to be.

Each item carries ``type`` ("preset" or "custom" — a cloned voice), and
presets may carry a ``slug`` such as ``en_paul_neutral`` or ``voice_478``.
/v1/audio/speech accepts either the voice ``id`` or a preset's slug as
``voice_id``. The pickers keep using the ``id`` (what earlier versions saved),
but labels include the slug so a voice can be found by typing it.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass

import aiohttp

from .const import MISTRAL_API_BASE, TTS_VOICES

_LOGGER = logging.getLogger(__name__)

# Older preset names/slugs are <language>_<speaker>_<emotion>, e.g.
# en_paul_neutral. Those get a readable label ("Paul – Neutral"); any other
# name (newer presets such as "Sheila", custom voices) is shown as-is.
_PRESET_SLUG = re.compile(r"^([a-z]{2})_([a-z]+)_([a-z]+)$")

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
    # True for a voice cloned/saved in the account (API ``type: custom``).
    custom: bool = False
    # Preset slug accepted as voice_id (e.g. "en_paul_neutral"); None if absent.
    slug: str | None = None
    gender: str | None = None


def _optional_str(value: object) -> str | None:
    return (value.strip() or None) if isinstance(value, str) else None


def _pretty_preset(name: str) -> str | None:
    """'en_paul_neutral' -> 'Paul – Neutral'; None for any other name."""
    match = _PRESET_SLUG.match(name)
    if not match:
        return None
    return f"{match.group(2).title()} – {match.group(3).title()}"


def voice_label(item: VoiceItem) -> str:
    """Searchable picker label for a voice.

    Holds the readable name, whether it is a custom voice, its languages and
    gender when known, and the preset slug, so typing any of those in the
    combo box finds it. Examples:
    ``Paul – Neutral (en_us) · en_paul_neutral``,
    ``Sheila (en_us; female) · voice_478``, ``My voice (custom voice)``.
    """
    pretty = _pretty_preset(item.name)
    display = pretty or item.name
    handle = item.slug or (item.name if pretty else None)
    details: list[str] = []
    if item.custom:
        details.append("custom voice")
    if item.languages:
        details.append(", ".join(item.languages))
    if item.gender:
        details.append(item.gender)
    label = display
    if details:
        label += f" ({'; '.join(details)})"
    if handle and handle != display:
        label += f" · {handle}"
    return label


def static_voice_items() -> list[VoiceItem]:
    """The built-in preset list, used when the account list can't be fetched."""
    return [VoiceItem(voice_id=v, name=v, slug=v) for v in TTS_VOICES]


def resolve_voice(value: str, items: Iterable[VoiceItem] | None) -> str:
    """Map a typed or saved voice to the ``voice_id`` of a listed voice.

    Matches the voice ID first, then (case-insensitive) the slug, the name
    or the picker label — so "en_paul_neutral" or a custom voice's name both
    work. An unmatched value is returned trimmed: it may be a valid voice ID
    that is simply not in the list (or the list could not be fetched).
    """
    value = value.strip()
    pool = list(items or ())
    if not value or not pool:
        return value
    for item in pool:
        if item.voice_id == value:
            return item.voice_id
    folded = value.casefold()
    for item in pool:
        keys = (item.slug, item.name, voice_label(item))
        if any(key and key.casefold() == folded for key in keys):
            return item.voice_id
    return value


def voice_choices(
    items: list[VoiceItem] | None, current: str
) -> tuple[list[tuple[str, str]], str]:
    """``(value, label)`` pairs for the options dropdown, and the value to preselect.

    Custom voices come first, then presets, each alphabetical by label. Without
    an account list the built-in presets are offered. The saved value is
    resolved against the list (so a saved slug preselects that voice); if it
    still matches nothing it is appended so it stays selected.
    """
    pool = items or static_voice_items()
    ordered = sorted(pool, key=lambda i: (not i.custom, voice_label(i).casefold()))
    choices = [(item.voice_id, voice_label(item)) for item in ordered]
    selected = resolve_voice(current, pool)
    if selected and selected not in {value for value, _ in choices}:
        choices.append((selected, f"{selected} (not in voice list)"))
    return choices, selected


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
                    custom=item.get("type") == "custom",
                    slug=_optional_str(item.get("slug")),
                    gender=_optional_str(item.get("gender")),
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
