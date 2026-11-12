"""Web search without a stored Mistral agent.

Searches used to go through an "HA Mistral Web Search" agent stored in the
Mistral account, whose instructions ("reply factually and concisely") could not
be changed from the code and produced one-line answers (a news question came
back as a single headline). Each search now sends its instructions with the
request.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import unittest
from types import SimpleNamespace

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from mistral_conversation import conversation as conv_module
from mistral_conversation.const import DOMAIN, WEB_SEARCH_CONV_CACHE_MAX, WEB_SEARCH_INSTRUCTIONS

from .test_audio_models import _RealClientErrorAsync, _Resp
from .test_connectors import _SeqSession


def _entity(session):
    runtime = SimpleNamespace(session=session, headers={"Authorization": "Bearer k"},
                              web_search_conversations={})
    hass = SimpleNamespace(data={DOMAIN: {"entry1": runtime}})
    entity = conv_module.MistralConversationEntity(hass, SimpleNamespace(entry_id="entry1", options={}))
    return entity, runtime


def _reply(conv_id: str, text: str) -> _Resp:
    return _Resp(json_data={"conversation_id": conv_id,
                            "outputs": [{"type": "message.output", "content": text}]})


class InstructionsTests(unittest.TestCase):
    def test_ask_for_complete_answers(self) -> None:
        self.assertIn("top three to five headlines", WEB_SEARCH_INSTRUCTIONS)
        self.assertIn("complete", WEB_SEARCH_INSTRUCTIONS)
        self.assertNotIn("concisely", WEB_SEARCH_INSTRUCTIONS)

    def test_payload_carries_instructions_tool_and_language(self) -> None:
        payload = conv_module._web_search_payload("mistral-small-latest", "news today", "nl")
        self.assertNotIn("agent_id", payload)
        self.assertEqual(payload["model"], "mistral-small-latest")
        self.assertEqual(payload["inputs"], "news today")
        self.assertEqual(payload["tools"], [{"type": "web_search"}])
        self.assertTrue(payload["instructions"].startswith(WEB_SEARCH_INSTRUCTIONS))
        self.assertIn("code 'nl'", payload["instructions"])
        self.assertNotIn("code", conv_module._web_search_payload("m", "q", None)["instructions"][-40:])

    def test_results_prompt_asks_for_a_full_answer(self) -> None:
        content = conv_module._web_search_results_message("news", "a, b, c")["content"]
        self.assertIn("answer my original question fully", content)
        self.assertNotIn("question directly", content)


class ConversationsChatTests(_RealClientErrorAsync):
    async def test_new_search_sends_instructions_and_no_agent(self) -> None:
        session = _SeqSession(_reply("mc-1", "Three headlines."))
        entity, runtime = _entity(session)
        answer = await entity._conversations_chat("mistral-small-latest", "news", "ha-1", language="en")
        self.assertEqual(answer, "Three headlines.")
        self.assertEqual(len(session.calls), 1)  # no agents list/create request
        method, url, kwargs = session.calls[0]
        self.assertEqual((method, url), ("POST", "https://api.mistral.ai/v1/conversations"))
        self.assertNotIn("agent_id", kwargs["json"])
        self.assertIn("code 'en'", kwargs["json"]["instructions"])
        self.assertEqual(runtime.web_search_conversations, {"ha-1": "mc-1"})

    async def test_follow_up_appends_to_the_same_conversation(self) -> None:
        session = _SeqSession(_reply("mc-1", "First."), _reply("mc-1", "And tomorrow."))
        entity, runtime = _entity(session)
        await entity._conversations_chat("mistral-small-latest", "weather today", "ha-1")
        await entity._conversations_chat("mistral-small-latest", "and tomorrow?", "ha-1")
        method, url, kwargs = session.calls[1]
        self.assertEqual(url, "https://api.mistral.ai/v1/conversations/mc-1")
        self.assertEqual(kwargs["json"], {"inputs": "and tomorrow?"})

    async def test_conversation_cache_stays_bounded(self) -> None:
        replies = [_reply(f"mc-{i}", "x") for i in range(WEB_SEARCH_CONV_CACHE_MAX + 3)]
        entity, runtime = _entity(_SeqSession(*replies))
        for i in range(WEB_SEARCH_CONV_CACHE_MAX + 3):
            await entity._conversations_chat("mistral-small-latest", "q", f"ha-{i}")
        self.assertEqual(len(runtime.web_search_conversations), WEB_SEARCH_CONV_CACHE_MAX)
        self.assertNotIn("ha-0", runtime.web_search_conversations)


if __name__ == "__main__":
    unittest.main()
