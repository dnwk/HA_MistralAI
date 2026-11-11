"""Tests for the TTS volume boost (ported from upstream, plus cache/override).

Mistral has no volume parameter, so the integration scales the 16-bit PCM it
gets back. Covers the gain maths, chunk handling and WAV checks in
``_streaming``, the batch WAV boost, the streaming per-sentence boost, the
``volume_boost`` option (integration setting, per-call override, cache key)
and the options flow.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import asyncio
import base64
import io
import json
import unittest
import wave
from array import array
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from mistral_conversation import _streaming
from mistral_conversation import config_flow
from mistral_conversation import tts as tts_module
from mistral_conversation._streaming import PcmGain, apply_gain, prepare_gain, wav_is_pcm16
from mistral_conversation.const import CONF_TTS_GAIN_DB, DOMAIN, TTS_GAIN_DB_MAX
from mistral_conversation.speech_style import SpeechStyle, default_style_options, speech_style

from .test_audio_models import _Ctx, _entry, _options_flow, _RealClientErrorAsync, _Resp, _Session


def _pcm(values: list[int]) -> bytes:
    return array("h", values).tobytes()


def _values(data: bytes) -> list[int]:
    samples = array("h")
    samples.frombytes(data)
    return list(samples)


def _wav(values: list[int], width: int = 2, rate: int = 24000) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(width)
        writer.setframerate(rate)
        writer.writeframes(_pcm(values) if width == 2 else bytes(len(values)))
    return out.getvalue()


def _wav_samples(data: bytes) -> list[int]:
    with wave.open(io.BytesIO(data), "rb") as reader:
        return _values(reader.readframes(reader.getnframes()))


GAIN_6DB = 10 ** (6 / 20)
KNEE = 0.75 * 32767


class PcmGainTests(unittest.TestCase):
    def test_zero_or_negative_gain_passes_through(self) -> None:
        data = _pcm([1000, -1000, 32767, -32768])
        self.assertEqual(apply_gain(data, 0), data)
        self.assertEqual(apply_gain(data, -3), data)

    def test_quiet_samples_scale_linearly(self) -> None:
        out = _values(apply_gain(_pcm([1000, -1000, 0]), 6))
        self.assertEqual(out, [round(1000 * GAIN_6DB), -round(1000 * GAIN_6DB), 0])

    def test_loud_samples_are_soft_limited_never_clipped(self) -> None:
        out = _values(apply_gain(_pcm([32767, -32768, 8000, 6000]), TTS_GAIN_DB_MAX))
        self.assertTrue(all(abs(v) <= 32767 for v in out))
        self.assertEqual(out[1], -out[0])  # -32768 maps symmetrically
        self.assertGreater(out[2], KNEE)  # 8000 * 4 is compressed above the knee
        self.assertLess(out[2], 32767)
        self.assertEqual(out[3], round(6000 * 10 ** (12 / 20)))  # below the knee: linear

    def test_plus_12_db_flattens_the_loudest_half(self) -> None:
        # Documented limitation: at +12 dB everything above roughly half of
        # full scale ends up at the maximum; at +6 dB nothing reaches it.
        loud = _pcm([17000, 20000, 32767])
        self.assertEqual(set(_values(apply_gain(loud, 12))), {32767})
        self.assertTrue(all(v < 32767 for v in _values(apply_gain(_pcm([32000]), 6))))

    def test_output_is_monotonic(self) -> None:
        inputs = list(range(0, 32767, 997))
        out = _values(apply_gain(_pcm(inputs), 9))
        self.assertEqual(out, sorted(out))

    def test_odd_chunk_boundaries_give_identical_output(self) -> None:
        data = _pcm(list(range(-3000, 3000, 7)))
        gain = PcmGain(6)
        chunked = b"".join(gain.process(data[i : i + 3]) for i in range(0, len(data), 3))
        chunked += gain.flush()
        self.assertEqual(chunked, apply_gain(data, 6))

    def test_odd_trailing_byte_is_flushed_unscaled(self) -> None:
        gain = PcmGain(6)
        self.assertEqual(gain.process(b"\x10"), b"")
        self.assertEqual(gain.flush(), b"\x10")

    def test_prepare_gain_builds_the_cached_table(self) -> None:
        _streaming._gain_table.cache_clear()
        prepare_gain(0)
        self.assertEqual(_streaming._gain_table.cache_info().currsize, 0)
        prepare_gain(5)
        PcmGain(5)
        info = _streaming._gain_table.cache_info()
        self.assertEqual((info.currsize, info.hits), (1, 1))


class WavIsPcm16Tests(unittest.TestCase):
    def test_16_bit_pcm(self) -> None:
        self.assertTrue(wav_is_pcm16(_wav([0, 1])[:44]))

    def test_8_bit_and_short_headers(self) -> None:
        self.assertFalse(wav_is_pcm16(_wav([0, 1], width=1)[:44]))
        self.assertFalse(wav_is_pcm16(b"RIFF"))

    def test_float_format_tag(self) -> None:
        header = bytearray(_wav([0])[:44])
        header[20:22] = (3).to_bytes(2, "little")  # IEEE float
        self.assertFalse(wav_is_pcm16(bytes(header)))


class BoostWavTests(unittest.TestCase):
    def test_boosts_16_bit_wav(self) -> None:
        boosted = tts_module._boost_wav(_wav([1000, -1000]), 6)
        self.assertEqual(_wav_samples(boosted), [round(1000 * GAIN_6DB), -round(1000 * GAIN_6DB)])

    def test_other_audio_is_not_touched(self) -> None:
        self.assertIsNone(tts_module._boost_wav(_wav([1, 2], width=1), 6))
        self.assertIsNone(tts_module._boost_wav(b"not a wav file", 6))


class VolumeBoostOptionTests(unittest.TestCase):
    def test_integration_setting_and_call_override(self) -> None:
        self.assertEqual(speech_style({}, {CONF_TTS_GAIN_DB: 6}).gain_db, 6.0)
        self.assertEqual(speech_style({"volume_boost": 3}, {CONF_TTS_GAIN_DB: 6}).gain_db, 3.0)
        self.assertEqual(speech_style({"volume_boost": 0}, {CONF_TTS_GAIN_DB: 6}).gain_db, 0.0)
        self.assertEqual(speech_style({"volume_boost": "4"}, {}).gain_db, 4.0)

    def test_invalid_values_are_ignored(self) -> None:
        for value in (-3, TTS_GAIN_DB_MAX + 1, "loud"):
            with self.subTest(value=value):
                with self.assertLogs(_streaming.__name__.replace("_streaming", "speech_style"), "WARNING"):
                    self.assertEqual(speech_style({"volume_boost": value}, {}).gain_db, 0.0)

    def test_boost_is_part_of_the_cache_key_options(self) -> None:
        self.assertEqual(default_style_options({CONF_TTS_GAIN_DB: 6}), {"volume_boost": 6.0})
        self.assertEqual(default_style_options({CONF_TTS_GAIN_DB: 0}), {})


def _executor_hass(runtime) -> SimpleNamespace:
    async def run(func, *args):
        return func(*args)

    return SimpleNamespace(
        data={DOMAIN: {"entry1": runtime}},
        async_add_executor_job=AsyncMock(side_effect=run),
    )


def _runtime(session) -> SimpleNamespace:
    return SimpleNamespace(session=session, headers={"Authorization": "Bearer k"})


class BatchBoostTests(_RealClientErrorAsync):
    async def test_boost_requests_wav_and_returns_boosted_wav(self) -> None:
        wav = _wav([1000, -1000])
        session = _Session(_Resp(json_data={"audio_data": base64.b64encode(wav).decode()}))
        entity = tts_module.MistralTTSEntity(_executor_hass(_runtime(session)), _entry({CONF_TTS_GAIN_DB: 6}))
        ext, audio = await entity.async_get_tts_audio("Hi", "en", {})
        self.assertEqual(session.calls[0][1]["json"]["response_format"], "wav")
        self.assertEqual(ext, "wav")
        self.assertEqual(_wav_samples(audio), [round(1000 * GAIN_6DB), -round(1000 * GAIN_6DB)])

    async def test_without_boost_mp3_is_unchanged(self) -> None:
        session = _Session(_Resp(json_data={"audio_data": base64.b64encode(b"mp3").decode()}))
        hass = _executor_hass(_runtime(session))
        entity = tts_module.MistralTTSEntity(hass, _entry({}))
        self.assertEqual(await entity.async_get_tts_audio("Hi", "en", {}), ("mp3", b"mp3"))
        self.assertEqual(session.calls[0][1]["json"]["response_format"], "mp3")
        hass.async_add_executor_job.assert_not_called()

    async def test_unexpected_audio_is_returned_untouched_with_one_warning(self) -> None:
        wav8 = _wav([1, 2], width=1)
        session = _Session(_Resp(json_data={"audio_data": base64.b64encode(wav8).decode()}))
        entity = tts_module.MistralTTSEntity(_executor_hass(_runtime(session)), _entry({CONF_TTS_GAIN_DB: 6}))
        with self.assertLogs(tts_module._LOGGER.name, "WARNING") as logs:
            self.assertEqual(await entity.async_get_tts_audio("Hi", "en", {}), ("wav", wav8))
            await entity.async_get_tts_audio("Hi", "en", {})
        self.assertEqual(len([r for r in logs.records if "volume boost" in r.getMessage()]), 1)


class _SseResp:
    """200 response whose body is Mistral's SSE stream of base64 audio frames."""

    status = 200

    def __init__(self, audio_chunks: list[bytes]) -> None:
        frames = [
            b"event: speech.audio.delta\ndata: "
            + json.dumps({"audio_data": base64.b64encode(chunk).decode()}).encode()
            + b"\n\n"
            for chunk in audio_chunks
        ] + [b"event: speech.audio.done\ndata: {}\n\n"]

        async def iter_any():
            for frame in frames:
                yield frame

        self.content = SimpleNamespace(iter_any=iter_any)


async def _drain(queue: asyncio.Queue) -> list:
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


class StreamingBoostTests(_RealClientErrorAsync):
    async def _sentence(self, wav: bytes, style: SpeechStyle):
        # Split header and PCM across odd-sized SSE frames.
        chunks = [wav[:30], wav[30:51], wav[51:]]
        session = _Session()
        session._resp = _SseResp(chunks)
        session.post = lambda url, **kw: _Ctx(session._resp)
        hass = SimpleNamespace(data={DOMAIN: {"entry1": _runtime(session)}})
        entity = tts_module.MistralTTSEntity(hass, _entry({}))
        queue: asyncio.Queue = asyncio.Queue()
        await entity._stream_one_sentence_into("Hello.", "v", queue, idx=0, style=style)
        items = await _drain(queue)
        header = items[0]
        pcm = b"".join(i for i in items[1:] if isinstance(i, bytes))
        return header, pcm, entity

    async def test_pcm_after_header_is_boosted(self) -> None:
        values = list(range(-2000, 2000, 37))
        wav = _wav(values)
        header, pcm, _ = await self._sentence(wav, SpeechStyle(gain_db=6))
        self.assertEqual(header, ("header", wav[:44]))
        self.assertEqual(pcm, apply_gain(_pcm(values), 6))

    async def test_no_boost_leaves_pcm_untouched(self) -> None:
        values = list(range(-2000, 2000, 37))
        _, pcm, _ = await self._sentence(_wav(values), SpeechStyle())
        self.assertEqual(pcm, _pcm(values))

    async def test_non_pcm16_stream_is_untouched_with_warning(self) -> None:
        wav8 = _wav(list(range(60)), width=1)
        with self.assertLogs(tts_module._LOGGER.name, "WARNING"):
            _, pcm, _ = await self._sentence(wav8, SpeechStyle(gain_db=6))
        self.assertEqual(pcm, wav8[44:])

    async def test_stream_request_prepares_the_table_off_the_loop(self) -> None:
        hass = _executor_hass(_runtime(_Session()))
        entity = tts_module.MistralTTSEntity(hass, _entry({CONF_TTS_GAIN_DB: 6}))
        entity._pipelined_stream = MagicMock(return_value="gen")
        request = SimpleNamespace(options={"voice": "v"}, message_gen="msgs")
        with patch.object(tts_module, "TTSAudioResponse", lambda **kw: kw):
            await entity.async_stream_tts_audio(request)
        hass.async_add_executor_job.assert_awaited_once_with(prepare_gain, 6.0)
        self.assertEqual(entity._pipelined_stream.call_args.args[2].gain_db, 6.0)


class OptionsFlowBoostTests(unittest.IsolatedAsyncioTestCase):
    async def test_zero_is_not_stored(self) -> None:
        saved = await _options_flow({}).async_step_init({CONF_TTS_GAIN_DB: 0})
        self.assertNotIn(CONF_TTS_GAIN_DB, saved)

    async def test_boost_is_stored(self) -> None:
        saved = await _options_flow({}).async_step_init({CONF_TTS_GAIN_DB: 6})
        self.assertEqual(saved[CONF_TTS_GAIN_DB], 6)

    async def test_slider(self) -> None:
        selector, vol = MagicMock(), MagicMock()
        with (
            patch.object(config_flow, "selector", selector),
            patch.object(config_flow, "vol", vol),
            patch.object(config_flow, "async_fetch_voice_items", AsyncMock(return_value=None)),
            patch.object(config_flow, "async_fetch_audio_models", AsyncMock(return_value=([], []))),
        ):
            await _options_flow({CONF_TTS_GAIN_DB: 4}).async_step_init(None)
        optional = {c.args[0]: c.kwargs for c in vol.Optional.call_args_list if c.args}
        self.assertEqual(optional[CONF_TTS_GAIN_DB]["default"], 4)
        slider = [
            c.kwargs
            for c in selector.NumberSelectorConfig.call_args_list
            if c.kwargs.get("unit_of_measurement") == "dB"
        ]
        self.assertEqual(len(slider), 1)
        self.assertEqual((slider[0]["min"], slider[0]["max"], slider[0]["step"]), (0, TTS_GAIN_DB_MAX, 1))


if __name__ == "__main__":
    unittest.main()
