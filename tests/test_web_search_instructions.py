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
from datetime import date
from types import SimpleNamespace

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from mistral_conversation import conversation as conv_module
from mistral_conversation.const import (
    DOMAIN,
    WEB_SEARCH_ANSWER_NUDGE,
    WEB_SEARCH_CONV_CACHE_MAX,
    WEB_SEARCH_INSTRUCTIONS,
)

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


class EmptySearchAnswerTests(unittest.TestCase):
    """Searches came back empty-handed when the model put today's date in the query."""

    def test_tool_description_discourages_dates(self) -> None:
        description = conv_module._web_search_tool_def()["function"]["parameters"]["properties"]["query"]["description"]
        self.assertIn("Do not add today's date", description)

    def test_instructions_fall_back_to_recent_results(self) -> None:
        self.assertIn("most recent relevant results", WEB_SEARCH_INSTRUCTIONS)
        self.assertIn("say when they are from", WEB_SEARCH_INSTRUCTIONS)


class EmptyAnswerLoggingTests(_RealClientErrorAsync):
    async def test_answer_is_logged_at_debug(self) -> None:
        session = _SeqSession(_reply("mc-1", "Headline one. Headline two."))
        entity, _ = _entity(session)
        with self.assertLogs(conv_module._LOGGER.name, "DEBUG") as logs:
            await entity._conversations_chat("mistral-small-latest", "latest news", "ha-1")
        self.assertTrue(any("web search answer (27 chars" in r.getMessage() for r in logs.records))


def _search_only(conv_id: str) -> _Resp:
    """A reply holding the search run but no answer message, as seen in HA."""
    return _Resp(json_data={"conversation_id": conv_id, "outputs": [
        {"type": "tool.execution", "name": "web_search",
         "arguments": '{"query": "latest news"}', "info": {"results": 0}},
    ]})


class MissingAnswerTests(_RealClientErrorAsync):
    """Mistral ran the search but returned no message.output entry."""

    async def test_asks_once_more_in_the_same_conversation(self) -> None:
        session = _SeqSession(_search_only("mc-1"), _reply("mc-1", "Headline one. Headline two."))
        entity, _ = _entity(session)
        answer = await entity._conversations_chat("mistral-large-latest", "latest news", "ha-1")
        self.assertEqual(answer, "Headline one. Headline two.")
        self.assertEqual(len(session.calls), 2)
        method, url, kwargs = session.calls[1]
        self.assertEqual((method, url), ("POST", "https://api.mistral.ai/v1/conversations/mc-1"))
        self.assertEqual(kwargs["json"], {"inputs": WEB_SEARCH_ANSWER_NUDGE})

    async def test_asks_only_once(self) -> None:
        session = _SeqSession(_search_only("mc-1"), _search_only("mc-1"))
        entity, _ = _entity(session)
        answer = await entity._conversations_chat("mistral-large-latest", "latest news", "ha-1")
        self.assertEqual(answer, "")
        self.assertEqual(len(session.calls), 2)

    async def test_failed_follow_up_returns_no_answer(self) -> None:
        session = _SeqSession(_search_only("mc-1"), _Resp(status=500, text="busy"))
        entity, _ = _entity(session)
        with self.assertLogs(conv_module._LOGGER.name, "WARNING") as logs:
            answer = await entity._conversations_chat("mistral-large-latest", "latest news", "ha-1")
        self.assertEqual(answer, "")
        self.assertIn("follow-up failed", logs.records[-1].getMessage())

    async def test_search_run_is_logged(self) -> None:
        session = _SeqSession(_search_only("mc-1"), _reply("mc-1", "x"))
        entity, _ = _entity(session)
        with self.assertLogs(conv_module._LOGGER.name, "DEBUG") as logs:
            await entity._conversations_chat("mistral-large-latest", "latest news", "ha-1")
        first = logs.records[0].getMessage()
        self.assertIn("entries ['tool.execution']", first)
        self.assertIn("web_search(", first)
        self.assertIn("'results': 0", first)

    async def test_reply_without_conversation_id_is_not_retried(self) -> None:
        session = _SeqSession(_Resp(json_data={"outputs": []}))
        entity, _ = _entity(session)
        self.assertEqual(await entity._conversations_chat("m", "q", "ha-1"), "")
        self.assertEqual(len(session.calls), 1)


class StripTodayTests(unittest.TestCase):
    """The model put today's date in news queries despite the tool description."""

    TODAY = date(2026, 11, 11)

    def clean(self, query: str, said: str = "What are today's top news headlines?") -> str:
        return conv_module._strip_today(query, said, self.TODAY)

    def test_written_dates_are_removed(self) -> None:
        for query in (
            "latest news headlines November 11 2026",
            "latest news headlines November 11, 2026",
            "latest news headlines for Nov 11th 2026",
            "latest news headlines 11 November 2026",
            "latest news headlines on the 11th of November",
            "latest news headlines 2026-11-11",
            "latest news headlines 11/11/2026",
        ):
            with self.subTest(query=query):
                self.assertNotIn("11", self.clean(query).replace("the", ""))
                self.assertTrue(self.clean(query).startswith("latest news headlines"))

    def test_plain_form(self) -> None:
        self.assertEqual(self.clean("top news headlines November 11 2026"), "top news headlines")

    def test_other_dates_stay(self) -> None:
        self.assertEqual(self.clean("news November 10 2026"), "news November 10 2026")
        self.assertEqual(self.clean("news 2026-11-12"), "news 2026-11-12")

    def test_user_mentioned_a_date(self) -> None:
        query = "news November 11 2026"
        self.assertEqual(self.clean(query, said="News on November 11?"), query)
        self.assertEqual(self.clean(query, said="news from the 11th"), query)

    def test_nothing_left_keeps_the_query(self) -> None:
        self.assertEqual(self.clean("November 11 2026"), "November 11 2026")

    def test_no_real_date_leaves_query(self) -> None:
        self.assertEqual(conv_module._strip_today("news November 11 2026", "news", object()),
                         "news November 11 2026")
