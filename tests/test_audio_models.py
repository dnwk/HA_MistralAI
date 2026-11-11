"""Tests for user-configurable STT/TTS models.

Covers the pure helpers in ``audio_models.py``, the options flow (dropdown
contents and how a typed model ID is saved), and that the STT and TTS
entities send the configured model to Mistral.

``aiohttp`` is a MagicMock under the HA stubs, so ``aiohttp.ClientError`` is
swapped for a real exception class for the duration of each test; otherwise
an ``except aiohttp.ClientError`` clause would itself raise TypeError.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import base64
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from homeassistant.exceptions import HomeAssistantError
from mistral_conversation import audio_models, config_flow
from mistral_conversation import stt as stt_module
from mistral_conversation import tts as tts_module
from mistral_conversation.const import (
    CONF_STT_MODEL,
    CONF_TTS_MODEL,
    DEFAULT_STT_MODEL,
    DEFAULT_TTS_MODEL,
    DOMAIN,
)


class _ClientError(Exception):
    """Real stand-in for ``aiohttp.ClientError``."""


class _Resp:
    def __init__(self, status: int = 200, json_data=None, text: str = "") -> None:
        self.status = status
        self._json = json_data
        self._text = text

    async def json(self):
        if isinstance(self._json, Exception):
            raise self._json
        return self._json

    async def text(self) -> str:
        return self._text


class _Ctx:
    def __init__(self, resp: _Resp) -> None:
        self._resp = resp

    async def __aenter__(self) -> _Resp:
        return self._resp

    async def __aexit__(self, *exc) -> bool:
        return False


class _Session:
    """Records every request; answers with ``resp`` or raises ``exc``."""

    def __init__(self, resp: _Resp | None = None, exc: Exception | None = None) -> None:
        self._resp = resp or _Resp()
        self._exc = exc
        self.calls: list[tuple[str, dict]] = []

    def _request(self, url: str, **kwargs) -> _Ctx:
        self.calls.append((url, kwargs))
        if self._exc is not None:
            raise self._exc
        return _Ctx(self._resp)

    get = _request
    post = _request


class _RealClientErrorAsync(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        patcher = patch.object(sys.modules["aiohttp"], "ClientError", _ClientError)
        patcher.start()
        self.addCleanup(patcher.stop)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class ConfiguredModelTests(unittest.TestCase):
    def test_missing_uses_default(self) -> None:
        self.assertEqual(audio_models.configured_model({}, "k", "dflt"), "dflt")

    def test_blank_uses_default(self) -> None:
        self.assertEqual(audio_models.configured_model({"k": "   "}, "k", "dflt"), "dflt")

    def test_non_string_uses_default(self) -> None:
        self.assertEqual(audio_models.configured_model({"k": None}, "k", "dflt"), "dflt")

    def test_value_is_trimmed(self) -> None:
        self.assertEqual(
            audio_models.configured_model({"k": " voxtral-x \n"}, "k", "dflt"),
            "voxtral-x",
        )


class SplitAudioModelsTests(unittest.TestCase):
    def test_splits_voxtral_models_and_aliases(self) -> None:
        items = [
            {"id": "ministral-8b-2512", "aliases": ["ministral-8b-latest"]},
            {"id": "voxtral-mini-2602", "aliases": ["voxtral-mini-latest"]},
            {"id": "voxtral-mini-tts-2603", "aliases": ["voxtral-mini-tts-latest"]},
            {"id": "voxtral-mini-transcribe-realtime-2602", "aliases": []},
            {"id": "voxtral-mini-tts-realtime-3-0"},
            "not-a-dict",
            {"id": None, "aliases": "not-a-list"},
        ]
        stt, tts = audio_models.split_audio_models(items)
        self.assertEqual(stt, ["voxtral-mini-2602", "voxtral-mini-latest"])
        self.assertEqual(tts, ["voxtral-mini-tts-2603", "voxtral-mini-tts-latest"])

    def test_duplicates_collapse(self) -> None:
        items = [
            {"id": "voxtral-mini-latest"},
            {"id": "voxtral-mini-2602", "aliases": ["voxtral-mini-latest"]},
        ]
        stt, _ = audio_models.split_audio_models(items)
        self.assertEqual(stt, ["voxtral-mini-2602", "voxtral-mini-latest"])


class ModelChoicesTests(unittest.TestCase):
    def test_default_first_then_live_without_duplicates(self) -> None:
        self.assertEqual(
            audio_models.model_choices("d", ["a", "d", "b"], "d"),
            ["d", "a", "b"],
        )

    def test_saved_custom_value_is_appended(self) -> None:
        self.assertEqual(
            audio_models.model_choices("d", ["a"], "custom"),
            ["d", "a", "custom"],
        )

    def test_saved_value_already_listed_is_not_repeated(self) -> None:
        self.assertEqual(audio_models.model_choices("d", ["a"], "a"), ["d", "a"])

    def test_no_live_models(self) -> None:
        self.assertEqual(audio_models.model_choices("d", [], "d"), ["d"])


class FetchAudioModelsTests(_RealClientErrorAsync):
    async def test_success(self) -> None:
        session = _Session(
            _Resp(
                json_data={
                    "object": "list",
                    "data": [
                        {"id": "voxtral-mini-2602", "aliases": ["voxtral-mini-latest"]},
                        {"id": "voxtral-mini-tts-2603"},
                        {"id": "mistral-small-latest"},
                    ],
                }
            )
        )
        stt, tts = await audio_models.async_fetch_audio_models(session, {"A": "b"})
        self.assertEqual(stt, ["voxtral-mini-2602", "voxtral-mini-latest"])
        self.assertEqual(tts, ["voxtral-mini-tts-2603"])
        url, kwargs = session.calls[0]
        self.assertTrue(url.endswith("/models"))
        self.assertEqual(kwargs["headers"], {"A": "b"})

    async def test_http_error_returns_empty(self) -> None:
        session = _Session(_Resp(status=500))
        self.assertEqual(await audio_models.async_fetch_audio_models(session, {}), ([], []))

    async def test_client_error_returns_empty(self) -> None:
        session = _Session(exc=_ClientError("down"))
        self.assertEqual(await audio_models.async_fetch_audio_models(session, {}), ([], []))

    async def test_timeout_returns_empty(self) -> None:
        session = _Session(exc=TimeoutError())
        self.assertEqual(await audio_models.async_fetch_audio_models(session, {}), ([], []))

    async def test_invalid_json_returns_empty(self) -> None:
        session = _Session(_Resp(json_data=ValueError("not json")))
        self.assertEqual(await audio_models.async_fetch_audio_models(session, {}), ([], []))

    async def test_unexpected_shape_returns_empty(self) -> None:
        session = _Session(_Resp(json_data={"data": "nope"}))
        self.assertEqual(await audio_models.async_fetch_audio_models(session, {}), ([], []))


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


def _options_flow(options: dict) -> config_flow.MistralOptionsFlow:
    flow = config_flow.MistralOptionsFlow()
    flow.hass = SimpleNamespace()
    flow.config_entry = SimpleNamespace(
        options=options, data={config_flow.CONF_API_KEY: "key"}
    )
    flow.async_create_entry = lambda title, data: data
    flow.async_show_form = lambda **kwargs: kwargs
    return flow


class OptionsFlowSaveTests(unittest.IsolatedAsyncioTestCase):
    async def test_typed_model_ids_are_trimmed(self) -> None:
        saved = await _options_flow({}).async_step_init(
            {CONF_STT_MODEL: "  voxtral-mini-2602 ", CONF_TTS_MODEL: "voxtral-mini-tts-3-0"}
        )
        self.assertEqual(saved[CONF_STT_MODEL], "voxtral-mini-2602")
        self.assertEqual(saved[CONF_TTS_MODEL], "voxtral-mini-tts-3-0")

    async def test_blank_model_ids_are_dropped(self) -> None:
        saved = await _options_flow({}).async_step_init(
            {CONF_STT_MODEL: "   ", CONF_TTS_MODEL: "", "other": 1}
        )
        self.assertNotIn(CONF_STT_MODEL, saved)
        self.assertNotIn(CONF_TTS_MODEL, saved)
        self.assertEqual(saved["other"], 1)


class OptionsFlowFormTests(unittest.IsolatedAsyncioTestCase):
    async def _show_form(self, options: dict, stt_live: list, tts_live: list):
        selector = MagicMock()
        vol = MagicMock()
        with (
            patch.object(config_flow, "selector", selector),
            patch.object(config_flow, "vol", vol),
            patch.object(
                config_flow, "async_fetch_voice_items", AsyncMock(return_value=None)
            ),
            patch.object(
                config_flow,
                "async_fetch_audio_models",
                AsyncMock(return_value=(stt_live, tts_live)),
            ),
        ):
            await _options_flow(options).async_step_init(None)
        return selector, vol

    @staticmethod
    def _custom_value_option_lists(selector: MagicMock) -> list[list[str]]:
        return [
            c.kwargs["options"]
            for c in selector.SelectSelectorConfig.call_args_list
            if c.kwargs.get("custom_value")
        ]

    @staticmethod
    def _optional_default(vol: MagicMock, key: str):
        for c in vol.Optional.call_args_list:
            if c.args and c.args[0] == key:
                return c.kwargs.get("default")
        raise AssertionError(f"no vol.Optional for {key}")

    async def test_defaults_and_live_models(self) -> None:
        selector, vol = await self._show_form(
            {},
            ["voxtral-mini-2602", "voxtral-mini-latest"],
            ["voxtral-mini-tts-3-0", "voxtral-mini-tts-latest"],
        )
        self.assertEqual(
            self._custom_value_option_lists(selector),
            [
                [DEFAULT_STT_MODEL, "voxtral-mini-2602"],
                [DEFAULT_TTS_MODEL, "voxtral-mini-tts-3-0"],
            ],
        )
        self.assertEqual(self._optional_default(vol, CONF_STT_MODEL), DEFAULT_STT_MODEL)
        self.assertEqual(self._optional_default(vol, CONF_TTS_MODEL), DEFAULT_TTS_MODEL)

    async def test_saved_custom_model_stays_selected_when_fetch_fails(self) -> None:
        selector, vol = await self._show_form(
            {CONF_STT_MODEL: "my-stt", CONF_TTS_MODEL: "my-tts"}, [], []
        )
        self.assertEqual(
            self._custom_value_option_lists(selector),
            [[DEFAULT_STT_MODEL, "my-stt"], [DEFAULT_TTS_MODEL, "my-tts"]],
        )
        self.assertEqual(self._optional_default(vol, CONF_STT_MODEL), "my-stt")
        self.assertEqual(self._optional_default(vol, CONF_TTS_MODEL), "my-tts")


# ---------------------------------------------------------------------------
# Entities send the configured model
# ---------------------------------------------------------------------------


def _runtime(session: _Session) -> SimpleNamespace:
    return SimpleNamespace(session=session, headers={"Authorization": "Bearer k"})


def _entry(options: dict) -> SimpleNamespace:
    return SimpleNamespace(entry_id="entry1", options=options)


async def _one_chunk():
    yield b"\x00\x00" * 160


class SttModelTests(_RealClientErrorAsync):
    async def _transcribe(self, options: dict) -> tuple[MagicMock, _Session]:
        session = _Session(_Resp(json_data={"text": "hello"}))
        hass = SimpleNamespace(data={DOMAIN: {"entry1": _runtime(session)}})
        entity = stt_module.MistralSTTEntity(hass, _entry(options))
        form_data = MagicMock()
        metadata = SimpleNamespace(language="en", sample_rate=16000, channel=1, bit_rate=16)
        with (
            patch.object(stt_module.aiohttp, "FormData", form_data),
            patch.object(stt_module, "SpeechResult", lambda text, state: (text, state)),
            patch.object(
                stt_module, "SpeechResultState", SimpleNamespace(SUCCESS="ok", ERROR="err")
            ),
        ):
            result = await entity.async_process_audio_stream(metadata, _one_chunk())
        self.assertEqual(result, ("hello", "ok"))
        return form_data.return_value, session

    @staticmethod
    def _model_field(form: MagicMock) -> str:
        for c in form.add_field.call_args_list:
            if c.args and c.args[0] == "model":
                return c.args[1]
        raise AssertionError("no model field")

    async def test_default_model(self) -> None:
        form, _ = await self._transcribe({})
        self.assertEqual(self._model_field(form), DEFAULT_STT_MODEL)

    async def test_configured_model(self) -> None:
        form, _ = await self._transcribe({CONF_STT_MODEL: "voxtral-mini-2602"})
        self.assertEqual(self._model_field(form), "voxtral-mini-2602")


class TtsModelTests(_RealClientErrorAsync):
    def _entity(self, options: dict, resp: _Resp) -> tuple:
        session = _Session(resp)
        hass = SimpleNamespace(data={DOMAIN: {"entry1": _runtime(session)}})
        return tts_module.MistralTTSEntity(hass, _entry(options)), session

    async def test_batch_uses_default_model(self) -> None:
        audio = base64.b64encode(b"mp3").decode()
        entity, session = self._entity({}, _Resp(json_data={"audio_data": audio}))
        self.assertEqual(await entity.async_get_tts_audio("Hi", "en", {}), ("mp3", b"mp3"))
        self.assertEqual(session.calls[0][1]["json"]["model"], DEFAULT_TTS_MODEL)

    async def test_batch_uses_configured_model(self) -> None:
        audio = base64.b64encode(b"mp3").decode()
        entity, session = self._entity(
            {CONF_TTS_MODEL: "voxtral-mini-tts-3-0"}, _Resp(json_data={"audio_data": audio})
        )
        await entity.async_get_tts_audio("Hi", "en", {})
        self.assertEqual(session.calls[0][1]["json"]["model"], "voxtral-mini-tts-3-0")

    async def test_streaming_uses_configured_model(self) -> None:
        # A 400 ends the request right after it is sent; only the payload matters.
        entity, session = self._entity(
            {CONF_TTS_MODEL: "voxtral-mini-tts-3-0"}, _Resp(status=400, text="bad model")
        )
        with self.assertRaises(HomeAssistantError):
            await entity._stream_one_sentence_into("Hello there.", "v", MagicMock(), idx=0)
        payload = session.calls[0][1]["json"]
        self.assertEqual(payload["model"], "voxtral-mini-tts-3-0")
        self.assertTrue(payload["stream"])


if __name__ == "__main__":
    unittest.main()
