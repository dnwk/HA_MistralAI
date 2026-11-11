"""Tests for the searchable TTS voice picker.

Covers parsing of ``type``/``slug``/``gender`` from GET /v1/audio/voices, the
picker labels, matching typed values (slug, custom voice name) to a voice ID,
the options-flow voice field, and the Voice Assistants picker labels.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from mistral_conversation import config_flow
from mistral_conversation import tts as tts_module
from mistral_conversation import voices
from mistral_conversation.const import CONF_TTS_VOICE, DEFAULT_TTS_VOICE, TTS_VOICES
from mistral_conversation.voices import VoiceItem

from .test_audio_models import (
    _ClientError,
    _Ctx,
    _options_flow,
    _RealClientErrorAsync,
    _Resp,
)

PAUL = VoiceItem("uuid-paul", "en_paul_neutral", ("en_us",), slug="en_paul_neutral")
SHEILA = VoiceItem("uuid-sheila", "Sheila", ("en_us",), slug="voice_478", gender="female")
CLONE = VoiceItem("uuid-clone", "My Voice", custom=True)
ITEMS = [PAUL, SHEILA, CLONE]

V2_URL = "https://api.mistral.ai/v2/audio/voices"
V1_URL = "https://api.mistral.ai/v1/audio/voices"


class _SeqSession:
    """Answers each GET with the next response (or raises the next exception)."""

    def __init__(self, *responses) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs) -> _Ctx:
        self.calls.append((url, dict(kwargs["params"])))
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _Ctx(nxt)


def _v2_page(items: list[dict], token: str | None) -> _Resp:
    return _Resp(json_data={"data": items, "next_page_token": token})


class FetchVoiceItemsTests(_RealClientErrorAsync):
    async def test_parses_type_slug_and_gender(self) -> None:
        session = _SeqSession(
            _v2_page(
                [
                    {
                        "id": "uuid-sheila",
                        "name": "Sheila",
                        "type": "preset",
                        "slug": "voice_478",
                        "gender": "female",
                        "languages": ["en_us"],
                    },
                    {"id": "uuid-clone", "name": "My Voice", "type": "custom", "slug": None},
                    {"id": "uuid-old", "name": "en_paul_neutral"},
                ],
                None,
            )
        )
        items = await voices.async_fetch_voice_items(session, {})
        self.assertEqual(
            items,
            [
                VoiceItem("uuid-sheila", "Sheila", ("en_us",), slug="voice_478", gender="female"),
                VoiceItem("uuid-clone", "My Voice", custom=True),
                VoiceItem("uuid-old", "en_paul_neutral"),
            ],
        )
        self.assertEqual(session.calls, [(V2_URL, {"type": "all", "page_size": 100})])

    async def test_v2_follows_page_tokens(self) -> None:
        session = _SeqSession(
            _v2_page([{"id": "a", "name": "A"}], "tok-1"),
            _v2_page([{"id": "b", "name": "B"}], "tok-2"),
            _v2_page([{"id": "c", "name": "C"}, {"id": "a", "name": "A"}], None),
        )
        items = await voices.async_fetch_voice_items(session, {})
        self.assertEqual([i.voice_id for i in items], ["a", "b", "c"])
        self.assertEqual(
            [params.get("page_token") for _, params in session.calls],
            [None, "tok-1", "tok-2"],
        )

    async def test_v2_stops_on_repeated_token(self) -> None:
        session = _SeqSession(
            _v2_page([{"id": "a", "name": "A"}], "same"),
            _v2_page([{"id": "b", "name": "B"}], "same"),
        )
        items = await voices.async_fetch_voice_items(session, {})
        self.assertEqual([i.voice_id for i in items], ["a", "b"])
        self.assertEqual(len(session.calls), 2)

    async def test_v2_stops_on_empty_page(self) -> None:
        session = _SeqSession(
            _v2_page([{"id": "a", "name": "A"}], "tok-1"),
            _v2_page([], "tok-2"),
        )
        items = await voices.async_fetch_voice_items(session, {})
        self.assertEqual([i.voice_id for i in items], ["a"])
        self.assertEqual(len(session.calls), 2)

    async def test_falls_back_to_v1_when_v2_unavailable(self) -> None:
        for status in (400, 404, 405, 422):
            with self.subTest(status=status):
                session = _SeqSession(
                    _Resp(status=status, text="nope"),
                    _Resp(json_data={"items": [{"id": "a", "name": "A"}], "total": 2}),
                    _Resp(json_data={"items": [{"id": "b", "name": "B"}], "total": 2}),
                )
                items = await voices.async_fetch_voice_items(session, {})
                self.assertEqual([i.voice_id for i in items], ["a", "b"])
                self.assertEqual(
                    session.calls[1:],
                    [
                        (V1_URL, {"type": "all", "limit": 100, "offset": 0}),
                        (V1_URL, {"type": "all", "limit": 100, "offset": 1}),
                    ],
                )

    async def test_account_or_server_errors_do_not_fall_back(self) -> None:
        for status in (401, 403, 429, 500):
            with self.subTest(status=status):
                session = _SeqSession(_Resp(status=status, text="err"))
                self.assertIsNone(await voices.async_fetch_voice_items(session, {}))
                self.assertEqual(len(session.calls), 1)

    async def test_v1_fallback_error_returns_none(self) -> None:
        session = _SeqSession(_Resp(status=404), _Resp(status=500, text="down"))
        self.assertIsNone(await voices.async_fetch_voice_items(session, {}))

    async def test_network_errors_return_none(self) -> None:
        for exc in (_ClientError("down"), TimeoutError(), ValueError("bad json")):
            with self.subTest(exc=type(exc).__name__):
                session = _SeqSession(exc)
                self.assertIsNone(await voices.async_fetch_voice_items(session, {}))

    async def test_empty_list_returns_none(self) -> None:
        session = _SeqSession(_v2_page([], None))
        self.assertIsNone(await voices.async_fetch_voice_items(session, {}))


class VoiceLabelTests(unittest.TestCase):
    def test_old_style_preset(self) -> None:
        self.assertEqual(voices.voice_label(PAUL), "Paul – Neutral (en_us) · en_paul_neutral")

    def test_old_style_preset_without_slug_field(self) -> None:
        item = VoiceItem("uuid-paul", "en_paul_neutral")
        self.assertEqual(voices.voice_label(item), "Paul – Neutral · en_paul_neutral")

    def test_new_style_preset(self) -> None:
        self.assertEqual(voices.voice_label(SHEILA), "Sheila (en_us; female) · voice_478")

    def test_custom_voice(self) -> None:
        self.assertEqual(voices.voice_label(CLONE), "My Voice (custom voice)")

    def test_plain_name(self) -> None:
        self.assertEqual(voices.voice_label(VoiceItem("x", "Bob")), "Bob")


class ResolveVoiceTests(unittest.TestCase):
    def test_voice_id(self) -> None:
        self.assertEqual(voices.resolve_voice("uuid-sheila", ITEMS), "uuid-sheila")

    def test_slug_case_insensitive(self) -> None:
        self.assertEqual(voices.resolve_voice("EN_PAUL_NEUTRAL", ITEMS), "uuid-paul")
        self.assertEqual(voices.resolve_voice("voice_478", ITEMS), "uuid-sheila")

    def test_custom_voice_name(self) -> None:
        self.assertEqual(voices.resolve_voice("  my voice ", ITEMS), "uuid-clone")

    def test_label(self) -> None:
        self.assertEqual(
            voices.resolve_voice("Sheila (en_us; female) · voice_478", ITEMS), "uuid-sheila"
        )

    def test_unknown_value_kept(self) -> None:
        self.assertEqual(voices.resolve_voice(" some-other-id ", ITEMS), "some-other-id")

    def test_blank_and_no_items(self) -> None:
        self.assertEqual(voices.resolve_voice("   ", ITEMS), "")
        self.assertEqual(voices.resolve_voice("en_paul_neutral", None), "en_paul_neutral")


class VoiceChoicesTests(unittest.TestCase):
    def test_custom_voices_first_then_presets(self) -> None:
        choices, _ = voices.voice_choices(ITEMS, "uuid-paul")
        self.assertEqual(
            [value for value, _ in choices], ["uuid-clone", "uuid-paul", "uuid-sheila"]
        )

    def test_default_slug_preselects_live_voice(self) -> None:
        _, selected = voices.voice_choices(ITEMS, DEFAULT_TTS_VOICE)
        self.assertEqual(selected, "uuid-paul")

    def test_unknown_saved_voice_is_kept(self) -> None:
        choices, selected = voices.voice_choices(ITEMS, "gone-id")
        self.assertEqual(selected, "gone-id")
        self.assertEqual(choices[-1], ("gone-id", "gone-id (not in voice list)"))

    def test_static_fallback(self) -> None:
        choices, selected = voices.voice_choices(None, DEFAULT_TTS_VOICE)
        self.assertEqual(sorted(value for value, _ in choices), sorted(TTS_VOICES))
        self.assertEqual(selected, DEFAULT_TTS_VOICE)
        self.assertIn(
            (DEFAULT_TTS_VOICE, "Paul – Neutral · en_paul_neutral"), choices
        )


class OptionsFlowVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def _show_form(self, flow, voice_items):
        selector = MagicMock()
        selector.SelectOptionDict = dict
        vol = MagicMock()
        with (
            patch.object(config_flow, "selector", selector),
            patch.object(config_flow, "vol", vol),
            patch.object(
                config_flow, "async_fetch_voice_items", AsyncMock(return_value=voice_items)
            ),
            patch.object(
                config_flow, "async_fetch_audio_models", AsyncMock(return_value=([], []))
            ),
        ):
            await flow.async_step_init(None)
        return selector, vol

    @staticmethod
    def _voice_config(selector: MagicMock):
        for c in selector.SelectSelectorConfig.call_args_list:
            options = c.kwargs.get("options") or []
            if options and isinstance(options[0], dict) and "uuid-paul" in {
                o["value"] for o in options
            }:
                return c.kwargs
        raise AssertionError("no voice selector config")

    @staticmethod
    def _voice_default(vol: MagicMock):
        for c in vol.Optional.call_args_list:
            if c.args and c.args[0] == CONF_TTS_VOICE:
                return c.kwargs.get("default")
        raise AssertionError("no vol.Optional for the voice")

    async def test_voice_field_is_searchable_combo_box(self) -> None:
        selector, vol = await self._show_form(_options_flow({}), ITEMS)
        config = self._voice_config(selector)
        self.assertTrue(config["custom_value"])
        self.assertEqual(
            config["options"][0], {"label": "My Voice (custom voice)", "value": "uuid-clone"}
        )
        # Nothing saved yet: the default slug preselects the live voice.
        self.assertEqual(self._voice_default(vol), "uuid-paul")

    async def test_typed_values_are_saved_as_voice_ids(self) -> None:
        cases = {
            "en_paul_neutral": "uuid-paul",
            " my voice ": "uuid-clone",
            "uuid-sheila": "uuid-sheila",
            "unlisted-id": "unlisted-id",
        }
        for typed, expected in cases.items():
            with self.subTest(typed=typed):
                flow = _options_flow({})
                await self._show_form(flow, ITEMS)
                saved = await flow.async_step_init({CONF_TTS_VOICE: typed})
                self.assertEqual(saved[CONF_TTS_VOICE], expected)

    async def test_blank_voice_is_dropped(self) -> None:
        flow = _options_flow({})
        await self._show_form(flow, ITEMS)
        saved = await flow.async_step_init({CONF_TTS_VOICE: "  "})
        self.assertNotIn(CONF_TTS_VOICE, saved)

    async def test_typed_slug_kept_when_list_unavailable(self) -> None:
        flow = _options_flow({})
        await self._show_form(flow, None)
        saved = await flow.async_step_init({CONF_TTS_VOICE: "gb_jane_neutral"})
        self.assertEqual(saved[CONF_TTS_VOICE], "gb_jane_neutral")


class VoiceAssistantsPickerTests(unittest.TestCase):
    def test_live_voices_use_picker_labels(self) -> None:
        with patch.object(tts_module, "Voice", SimpleNamespace):
            result = tts_module._sorted_voices(ITEMS, "en")
        self.assertEqual(
            {(v.voice_id, v.name) for v in result},
            {(item.voice_id, voices.voice_label(item)) for item in ITEMS},
        )

    def test_static_voices_use_picker_labels(self) -> None:
        with patch.object(tts_module, "Voice", SimpleNamespace):
            result = tts_module._static_voices("fr")
        self.assertEqual(result[0].voice_id[:3], "fr_")
        self.assertIn(
            ("en_paul_neutral", "Paul – Neutral · en_paul_neutral"),
            {(v.voice_id, v.name) for v in result},
        )


if __name__ == "__main__":
    unittest.main()
