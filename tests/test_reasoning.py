"""Reasoning models: thinking kept out of the reply, and the reasoning effort.

On a live install ``mistral-large-latest`` started streaming its reasoning as
lists of ``thinking`` chunks. The stream parser turned each list into text, so
a news answer became 16,576 characters of ``[{'type': 'thinking', ...}]`` that
the satellite read aloud.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from homeassistant.components import conversation as ha_conversation
from mistral_conversation import conversation as conv_module
from mistral_conversation import reasoning
from mistral_conversation.connectors import MistralConnector, connector_payload
from mistral_conversation.const import CONF_REASONING_EFFORT, DOMAIN

from .test_audio_models import _RealClientErrorAsync, _Resp
from .test_connectors import _SeqSession

# Exactly what the live stream sent, chunk by chunk.
THINKING_1 = [{"type": "thinking", "thinking": [{"type": "text", "text": "The user wants news"}], "closed": True}]
THINKING_2 = [{"type": "thinking", "thinking": [{"type": "text", "text": " headlines."}], "closed": True}]
CLOSING = [
    {"type": "thinking", "thinking": [{"type": "text", "text": " Done."}], "closed": True},
    {"type": "text", "text": "Here are today's"},
]


class SplitContentTests(unittest.TestCase):
    def test_plain_string_is_the_answer(self) -> None:
        self.assertEqual(reasoning.split_content("Hello."), ("Hello.", ""))

    def test_thinking_chunk_is_not_answer(self) -> None:
        self.assertEqual(reasoning.split_content(THINKING_1), ("", "The user wants news"))

    def test_closing_thinking_and_first_text(self) -> None:
        self.assertEqual(reasoning.split_content(CLOSING), ("Here are today's", " Done."))

    def test_thinking_as_plain_string(self) -> None:
        self.assertEqual(
            reasoning.split_content([{"type": "thinking", "thinking": "hmm"}]), ("", "hmm")
        )

    def test_other_chunks_are_left_out(self) -> None:
        content = [{"type": "tool_reference", "title": "x", "url": "https://x"}, {"type": "text", "text": "A"}]
        self.assertEqual(reasoning.split_content(content), ("A", ""))

    def test_single_chunk_and_odd_values(self) -> None:
        self.assertEqual(reasoning.split_content({"type": "text", "text": "A"}), ("A", ""))
        self.assertEqual(reasoning.split_content(None), ("", ""))
        self.assertEqual(reasoning.split_content(42), ("", ""))


class _StreamResp:
    def __init__(self, deltas: list) -> None:
        frames = [
            f"data: {json.dumps({'choices': [{'delta': d}]})}\n\n".encode() for d in deltas
        ] + [b"data: [DONE]\n\n"]

        async def iter_any():
            for frame in frames:
                yield frame

        self.content = SimpleNamespace(iter_any=iter_any)


async def _collect(deltas) -> list[dict]:
    return [d async for d in conv_module._async_stream_delta(_StreamResp(deltas))]


class StreamParserTests(unittest.IsolatedAsyncioTestCase):
    DELTAS = (
        {"role": "assistant", "content": THINKING_1},
        {"content": THINKING_2},
        {"content": CLOSING},
        {"content": " top headlines."},
    )

    async def test_reasoning_is_never_content(self) -> None:
        with patch.object(conv_module, "_THINKING_CONTENT", False):
            out = await _collect(self.DELTAS)
        content = "".join(d.get("content", "") for d in out)
        self.assertEqual(content, "Here are today's top headlines.")
        self.assertNotIn("thinking", content)
        self.assertFalse(any("thinking_content" in d for d in out))

    async def test_reasoning_goes_to_thinking_content_when_supported(self) -> None:
        with patch.object(conv_module, "_THINKING_CONTENT", True):
            out = await _collect(self.DELTAS)
        thinking = "".join(d.get("thinking_content", "") for d in out)
        self.assertEqual(thinking, "The user wants news headlines. Done.")
        self.assertEqual("".join(d.get("content", "") for d in out), "Here are today's top headlines.")
        # Each delta carries one kind of data only.
        for d in out:
            self.assertLessEqual(len(d), 1)

    async def test_plain_models_unchanged(self) -> None:
        out = await _collect([{"role": "assistant", "content": "Hi"}, {"content": " there."}])
        self.assertEqual(out, [{"role": "assistant"}, {"content": "Hi"}, {"content": " there."}])

    def test_thinking_support_is_detected_from_ha(self) -> None:
        # The test stubs have no dataclass, so it is off here; real HA has the field.
        self.assertFalse(conv_module._supports_thinking_content())


class EffortForTests(unittest.TestCase):
    def setUp(self) -> None:
        reasoning._REJECTED.clear()

    def test_values(self) -> None:
        self.assertIsNone(reasoning.effort_for("m", None))
        self.assertIsNone(reasoning.effort_for("m", "default"))
        self.assertIsNone(reasoning.effort_for("m", "max"))
        self.assertEqual(reasoning.effort_for("m", "low"), "low")

    def test_rejected_pair_is_left_out(self) -> None:
        reasoning._REJECTED.add(("m", "low"))
        self.assertIsNone(reasoning.effort_for("m", "low"))
        self.assertEqual(reasoning.effort_for("m", "high"), "high")
        self.assertEqual(reasoning.effort_for("other", "low"), "low")

    def test_without_effort(self) -> None:
        self.assertEqual(reasoning.without_effort({"model": "m", "reasoning_effort": "low"}), {"model": "m"})
        self.assertEqual(
            reasoning.without_effort({"completion_args": {"temperature": 0.3, "reasoning_effort": "low"}}),
            {"completion_args": {"temperature": 0.3}},
        )


REJECTED_BODY = '{"detail":[{"type":"literal_error","loc":["body","reasoning_effort"],"msg":"Input should be low, medium or high"}]}'


class FallbackTests(_RealClientErrorAsync):
    def setUp(self) -> None:
        super().setUp()
        reasoning._REJECTED.clear()

    async def _post(self, session, payload):
        async with reasoning.post_with_effort_fallback(session, "https://api/x", payload, headers={}) as resp:
            return resp.status, await resp.text()

    async def test_rejected_effort_is_retried_without_it(self) -> None:
        session = _SeqSession(_Resp(status=422, text=REJECTED_BODY), _Resp(status=200, text="ok"))
        payload = {"model": "mistral-large-latest", "reasoning_effort": "none", "messages": []}
        with self.assertLogs(reasoning._LOGGER.name, "WARNING") as logs:
            status, body = await self._post(session, payload)
        self.assertEqual((status, body), (200, "ok"))
        self.assertEqual(len(session.calls), 2)
        self.assertNotIn("reasoning_effort", session.calls[1][2]["json"])
        self.assertEqual(session.calls[1][2]["headers"], {})
        self.assertIn("does not accept reasoning effort 'none'", logs.records[0].getMessage())
        self.assertIsNone(reasoning.effort_for("mistral-large-latest", "none"))

    async def test_rejected_effort_in_completion_args(self) -> None:
        session = _SeqSession(_Resp(status=400, text=REJECTED_BODY), _Resp(status=200, text="ok"))
        payload = {"model": "m", "completion_args": {"temperature": 0.3, "reasoning_effort": "low"}}
        with self.assertLogs(reasoning._LOGGER.name, "WARNING"):
            await self._post(session, payload)
        self.assertEqual(session.calls[1][2]["json"]["completion_args"], {"temperature": 0.3})

    async def test_other_errors_are_not_retried(self) -> None:
        session = _SeqSession(_Resp(status=400, text="bad messages"))
        status, body = await self._post(session, {"model": "m", "reasoning_effort": "low"})
        self.assertEqual((status, body), (400, "bad messages"))
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(reasoning.effort_for("m", "low"), "low")

    async def test_no_effort_no_retry(self) -> None:
        session = _SeqSession(_Resp(status=422, text=REJECTED_BODY))
        status, _ = await self._post(session, {"model": "m"})
        self.assertEqual(status, 422)
        self.assertEqual(len(session.calls), 1)


class PayloadTests(unittest.TestCase):
    def test_web_search_payload(self) -> None:
        with_effort = conv_module._web_search_payload("m", "q", None, "low")
        self.assertEqual(with_effort["completion_args"]["reasoning_effort"], "low")
        self.assertNotIn("reasoning_effort", conv_module._web_search_payload("m", "q", None)["completion_args"])

    def test_connector_payload(self) -> None:
        connector = MistralConnector("id", "cal", "Calendar", "")
        self.assertEqual(
            connector_payload("m", connector, "r", None, "high")["completion_args"],
            {"reasoning_effort": "high"},
        )
        self.assertNotIn("completion_args", connector_payload("m", connector, "r", None))


class SearchSendsEffortTests(_RealClientErrorAsync):
    def setUp(self) -> None:
        super().setUp()
        reasoning._REJECTED.clear()

    async def test_web_search_uses_the_configured_effort(self) -> None:
        reply = _Resp(json_data={"conversation_id": "mc-1", "outputs": [{"type": "message.output", "content": "A."}]})
        session = _SeqSession(reply)
        runtime = SimpleNamespace(session=session, headers={}, web_search_conversations={})
        hass = SimpleNamespace(data={DOMAIN: {"entry1": runtime}})
        entry = SimpleNamespace(entry_id="entry1", options={CONF_REASONING_EFFORT: "low"})
        entity = conv_module.MistralConversationEntity(hass, entry)
        await entity._conversations_chat("mistral-large-latest", "news", "ha-1")
        self.assertEqual(session.calls[0][2]["json"]["completion_args"]["reasoning_effort"], "low")


class ToolResultTests(unittest.TestCase):
    """HA renamed ToolResultContent.tool_result to result (and warns on the old name)."""

    def _chat_log(self, result_attr: str):
        call = SimpleNamespace(id="c1", tool_name="HassTurnOn", tool_args={"name": "lamp"})
        assistant = ha_conversation.AssistantContent()
        assistant.content = None
        assistant.tool_calls = [call]
        res = ha_conversation.ToolResultContent()
        res.tool_call_id = "c1"
        res.tool_name = "HassTurnOn"
        setattr(res, result_attr, {"success": True})
        return SimpleNamespace(content=[assistant, res])

    def test_new_name(self) -> None:
        messages = conv_module._convert_chat_log_to_messages(self._chat_log("result"))
        self.assertEqual(json.loads(messages[-1]["content"]), {"success": True})

    def test_old_name(self) -> None:
        messages = conv_module._convert_chat_log_to_messages(self._chat_log("tool_result"))
        self.assertEqual(json.loads(messages[-1]["content"]), {"success": True})


if __name__ == "__main__":
    unittest.main()
