"""Speaking pace, emotion and expressiveness for Mistral TTS.

Mistral's speech endpoint has no speed, pitch or volume fields. Delivery is
steered with:

* inline tags at the start of the input — ``[emotion=calm][pace=slow]`` —
  which Mistral does not speak, and
* an ``expressiveness`` request field from 1.0 to 5.0 ("higher values trade
  voice similarity and stability for stronger delivery").

A volume boost (0 to +12 dB) is not a Mistral field: the integration scales
the returned 16-bit PCM itself (see ``_streaming.PcmGain``). It lives here so
it is resolved, overridden and cache-keyed exactly like the other controls.

Each can be set in the integration options (the default for every request,
including Voice Assistant replies) and overridden per call through
``tts.speak`` options ``pace``, ``emotion``, ``expressiveness`` and
``volume_boost``. Values that are not on Mistral's documented lists or out of
range are ignored with a warning rather than sent, so a typo never ends up
spoken or silently ignored by the API.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .const import (
    CONF_TTS_EMOTION,
    CONF_TTS_EXPRESSIVENESS,
    CONF_TTS_GAIN_DB,
    CONF_TTS_PACE,
    TTS_EMOTIONS,
    TTS_EXPRESSIVENESS_MAX,
    TTS_EXPRESSIVENESS_MIN,
    TTS_GAIN_DB_MAX,
    TTS_PACES,
    TTS_STYLE_DEFAULT,
)

_LOGGER = logging.getLogger(__name__)

# tts.speak option name -> integration option key.
STYLE_OPTIONS: dict[str, str] = {
    "pace": CONF_TTS_PACE,
    "emotion": CONF_TTS_EMOTION,
    "expressiveness": CONF_TTS_EXPRESSIVENESS,
    "volume_boost": CONF_TTS_GAIN_DB,
}


@dataclass(frozen=True)
class SpeechStyle:
    """The style sent with one TTS request; all fields optional."""

    pace: str | None = None
    emotion: str | None = None
    expressiveness: float | None = None
    # Applied locally to the returned audio, never sent to Mistral. 0 = off.
    gain_db: float = 0.0

    def apply(self, text: str) -> str:
        """Prefix ``text`` with the inline tags (emotion first, as in Mistral's docs)."""
        tags = ""
        if self.emotion:
            tags += f"[emotion={self.emotion}]"
        if self.pace:
            tags += f"[pace={self.pace}]"
        return tags + text

    def payload_fields(self) -> dict[str, Any]:
        """Extra request-body fields."""
        if self.expressiveness is None:
            return {}
        return {"expressiveness": self.expressiveness}


def _choice(value: Any, allowed: list[str], name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text or text == TTS_STYLE_DEFAULT:
        return None
    if text in allowed:
        return text
    _LOGGER.warning("Ignoring unknown TTS %s %r (allowed: %s)", name, value, ", ".join(allowed))
    return None


def _expressiveness(value: Any) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        _LOGGER.warning("Ignoring TTS expressiveness %r: not a number", value)
        return None
    if not TTS_EXPRESSIVENESS_MIN <= number <= TTS_EXPRESSIVENESS_MAX:
        _LOGGER.warning(
            "Ignoring TTS expressiveness %s: must be %s-%s",
            number,
            TTS_EXPRESSIVENESS_MIN,
            TTS_EXPRESSIVENESS_MAX,
        )
        return None
    return number


def _gain_db(value: Any) -> float:
    """Volume boost in dB; 0.0 (off) when unset, invalid or out of range."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        _LOGGER.warning("Ignoring TTS volume boost %r: not a number", value)
        return 0.0
    if not 0 <= number <= TTS_GAIN_DB_MAX:
        _LOGGER.warning(
            "Ignoring TTS volume boost %s dB: must be 0-%s", number, TTS_GAIN_DB_MAX
        )
        return 0.0
    return number


def speech_style(
    call_options: Mapping[str, Any] | None, entry_options: Mapping[str, Any]
) -> SpeechStyle:
    """Resolve the style for one request.

    A ``tts.speak`` option (``pace``, ``emotion``, ``expressiveness``,
    ``volume_boost``) wins over the integration option; an explicit
    ``"default"`` or empty value (or ``volume_boost: 0``) in the call turns
    that control off for the call.
    """
    call_options = call_options or {}

    def pick(name: str) -> Any:
        if name in call_options:
            return call_options[name]
        return entry_options.get(STYLE_OPTIONS[name])

    return SpeechStyle(
        pace=_choice(pick("pace"), TTS_PACES, "pace"),
        emotion=_choice(pick("emotion"), TTS_EMOTIONS, "emotion"),
        expressiveness=_expressiveness(pick("expressiveness")),
        gain_db=_gain_db(pick("volume_boost")),
    )


def default_style_options(entry_options: Mapping[str, Any]) -> dict[str, Any]:
    """The integration's style settings as ``tts.speak``-style options.

    Returned from the TTS entity's ``default_options`` so Home Assistant
    includes them in its TTS cache key: changing a setting then produces new
    audio instead of replaying cached audio in the old style.
    """
    style = speech_style(None, entry_options)
    options: dict[str, Any] = {}
    if style.pace:
        options["pace"] = style.pace
    if style.emotion:
        options["emotion"] = style.emotion
    if style.expressiveness is not None:
        options["expressiveness"] = style.expressiveness
    if style.gain_db > 0:
        options["volume_boost"] = style.gain_db
    return options
