"""Tests for speaking pace, emotion and expressiveness.

Covers resolving the style from integration options and tts.speak options,
the inline tags and request field sent to Mistral (batch and streaming), the
TTS entity's supported/default options, and the options flow.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import base64
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from homeassistant.exceptions import HomeAssistantError
from mistral_conversation import config_flow
from mistral_conversation import tts as tts_module
from mistral_conversation.const import (
    CONF_TTS_EMOTION,
    CONF_TTS_EXPRESSIVENESS,
    CONF_TTS_PACE,
    DOMAIN,
    TTS_EMOTIONS,
    TTS_PACES,
)
from mistral_conversation import speech_style as speech_style_module
from mistral_conversation.speech_style import (
    SpeechStyle,
    default_style_options,
    speech_style,
)

STYLE_LOGGER = speech_style_module._LOGGER.name

from .test_audio_models import (
    _entry,
    _options_flow,
    _RealClientErrorAsync,
    _Resp,
    _runtime,
    _Session,
)

ENTRY_STYLE = {CONF_TTS_PACE: "slow", CONF_TTS_EMOTION: "calm", CONF_TTS_EXPRESSIVENESS: 2.5}


class SpeechStyleTests(unittest.TestCase):
    def test_nothing_set(self) -> None:
        self.assertEqual(speech_style(None, {}), SpeechStyle())

    def test_integration_options(self) -> None:
        self.assertEqual(
            speech_style({}, ENTRY_STYLE),
            SpeechStyle(pace="slow", emotion="calm", expressiveness=2.5),
        )

    def test_call_options_win(self) -> None:
        style = speech_style({"pace": "fast", "expressiveness": 4}, ENTRY_STYLE)
        self.assertEqual(style, SpeechStyle(pace="fast", emotion="calm", expressiveness=4.0))

    def test_call_can_turn_a_control_off(self) -> None:
        style = speech_style({"pace": "default", "emotion": ""}, ENTRY_STYLE)
        self.assertEqual(style, SpeechStyle(expressiveness=2.5))

    def test_values_are_normalised(self) -> None:
        style = speech_style({"pace": " Very-Slow ", "expressiveness": "1.5"}, {})
        self.assertEqual(style, SpeechStyle(pace="very-slow", expressiveness=1.5))

    def test_invalid_values_are_ignored(self) -> None:
        with self.assertLogs(STYLE_LOGGER, "WARNING") as logs:
            style = speech_style(
                {"pace": "warp", "emotion": "ecstatic", "expressiveness": 9}, {}
            )
        self.assertEqual(style, SpeechStyle())
        self.assertEqual(len(logs.records), 3)

    def test_non_numeric_expressiveness(self) -> None:
        with self.assertLogs(STYLE_LOGGER, "WARNING"):
            self.assertIsNone(speech_style({"expressiveness": "loud"}, {}).expressiveness)
        self.assertIsNone(speech_style({"expressiveness": " "}, {}).expressiveness)

    def test_bounds_are_inclusive(self) -> None:
        self.assertEqual(speech_style({"expressiveness": 1}, {}).expressiveness, 1.0)
        self.assertEqual(speech_style({"expressiveness": 5}, {}).expressiveness, 5.0)

    def test_every_documented_value_is_accepted(self) -> None:
        for pace in TTS_PACES:
            self.assertEqual(speech_style({"pace": pace}, {}).pace, pace)
        for emotion in TTS_EMOTIONS:
            self.assertEqual(speech_style({"emotion": emotion}, {}).emotion, emotion)


class ApplyTests(unittest.TestCase):
    def test_emotion_then_pace(self) -> None:
        self.assertEqual(
            SpeechStyle(pace="slow", emotion="calm").apply("Hello."),
            "[emotion=calm][pace=slow]Hello.",
        )

    def test_single_tag_and_none(self) -> None:
        self.assertEqual(SpeechStyle(pace="fast").apply("Hi"), "[pace=fast]Hi")
        self.assertEqual(SpeechStyle().apply("Hi"), "Hi")

    def test_payload_fields(self) -> None:
        self.assertEqual(SpeechStyle(expressiveness=3.0).payload_fields(), {"expressiveness": 3.0})
        self.assertEqual(SpeechStyle(pace="slow").payload_fields(), {})

    def test_default_style_options(self) -> None:
        self.assertEqual(
            default_style_options(ENTRY_STYLE),
            {"pace": "slow", "emotion": "calm", "expressiveness": 2.5},
        )
        self.assertEqual(default_style_options({CONF_TTS_PACE: "default"}), {})


class TtsEntityStyleTests(_RealClientErrorAsync):
    def _entity(self, options: dict, resp: _Resp):
        session = _Session(resp)
        hass = SimpleNamespace(data={DOMAIN: {"entry1": _runtime(session)}})
        return tts_module.MistralTTSEntity(hass, _entry(options)), session

    def test_supported_and_default_options(self) -> None:
        entity, _ = self._entity(ENTRY_STYLE, _Resp())
        self.assertEqual(
            entity.supported_options,
            ["voice", "pace", "emotion", "expressiveness", "volume_boost"],
        )
        defaults = entity.default_options
        self.assertEqual(defaults["pace"], "slow")
        self.assertEqual(defaults["emotion"], "calm")
        self.assertEqual(defaults["expressiveness"], 2.5)

    def test_no_style_keys_when_unset(self) -> None:
        entity, _ = self._entity({}, _Resp())
        self.assertEqual(set(entity.default_options), {"voice"})

    async def test_batch_request_carries_style(self) -> None:
        audio = base64.b64encode(b"mp3").decode()
        entity, session = self._entity(ENTRY_STYLE, _Resp(json_data={"audio_data": audio}))
        await entity.async_get_tts_audio("Lights are on.", "en", {"pace": "fast"})
        payload = session.calls[0][1]["json"]
        self.assertEqual(payload["input"], "[emotion=calm][pace=fast]Lights are on.")
        self.assertEqual(payload["expressiveness"], 2.5)

    async def test_batch_request_without_style_is_unchanged(self) -> None:
        audio = base64.b64encode(b"mp3").decode()
        entity, session = self._entity({}, _Resp(json_data={"audio_data": audio}))
        await entity.async_get_tts_audio("Lights are on.", "en", {})
        payload = session.calls[0][1]["json"]
        self.assertEqual(payload["input"], "Lights are on.")
        self.assertNotIn("expressiveness", payload)

    async def test_each_streamed_sentence_carries_style(self) -> None:
        entity, session = self._entity({}, _Resp(status=400, text="stop"))
        style = SpeechStyle(pace="slow", emotion="warm", expressiveness=2.0)
        with self.assertRaises(HomeAssistantError):
            await entity._stream_one_sentence_into(
                "Second sentence.", "v", MagicMock(), idx=1, style=style
            )
        payload = session.calls[0][1]["json"]
        self.assertEqual(payload["input"], "[emotion=warm][pace=slow]Second sentence.")
        self.assertEqual(payload["expressiveness"], 2.0)
        self.assertTrue(payload["stream"])

    async def test_stream_request_passes_resolved_style(self) -> None:
        entity, _ = self._entity(ENTRY_STYLE, _Resp())
        entity._pipelined_stream = MagicMock(return_value="gen")
        request = SimpleNamespace(options={"voice": "v", "emotion": "happy"}, message_gen="msgs")
        with patch.object(tts_module, "TTSAudioResponse", lambda **kw: kw):
            response = await entity.async_stream_tts_audio(request)
        self.assertEqual(response["data_gen"], "gen")
        args = entity._pipelined_stream.call_args.args
        self.assertEqual(args[:2], ("msgs", "v"))
        self.assertEqual(args[2], SpeechStyle(pace="slow", emotion="happy", expressiveness=2.5))


class OptionsFlowStyleTests(unittest.IsolatedAsyncioTestCase):
    async def test_defaults_are_not_stored(self) -> None:
        saved = await _options_flow({}).async_step_init(
            {CONF_TTS_PACE: "default", CONF_TTS_EMOTION: "", CONF_TTS_EXPRESSIVENESS: None}
        )
        for key in (CONF_TTS_PACE, CONF_TTS_EMOTION, CONF_TTS_EXPRESSIVENESS):
            self.assertNotIn(key, saved)

    async def test_values_are_stored(self) -> None:
        saved = await _options_flow({}).async_step_init(dict(ENTRY_STYLE))
        self.assertEqual({k: saved[k] for k in ENTRY_STYLE}, ENTRY_STYLE)

    async def test_form_fields(self) -> None:
        selector = MagicMock()
        vol = MagicMock()
        with (
            patch.object(config_flow, "selector", selector),
            patch.object(config_flow, "vol", vol),
            patch.object(config_flow, "async_fetch_voice_items", AsyncMock(return_value=None)),
            patch.object(
                config_flow, "async_fetch_audio_models", AsyncMock(return_value=([], []))
            ),
        ):
            await _options_flow({CONF_TTS_PACE: "fast", CONF_TTS_EXPRESSIVENESS: 3.0}).async_step_init(None)
        optional = {c.args[0]: c.kwargs for c in vol.Optional.call_args_list if c.args}
        self.assertEqual(optional[CONF_TTS_PACE]["default"], "fast")
        self.assertEqual(optional[CONF_TTS_EMOTION]["default"], "default")
        self.assertEqual(
            optional[CONF_TTS_EXPRESSIVENESS]["description"], {"suggested_value": 3.0}
        )
        keys = {
            c.kwargs.get("translation_key"): c.kwargs["options"]
            for c in selector.SelectSelectorConfig.call_args_list
            if c.kwargs.get("translation_key") in ("tts_pace", "tts_emotion")
        }
        self.assertEqual(keys["tts_pace"], ["default", *TTS_PACES])
        self.assertEqual(keys["tts_emotion"], ["default", *TTS_EMOTIONS])


if __name__ == "__main__":
    unittest.main()
