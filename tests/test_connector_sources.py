"""Tests for connector sources and their visible record in Home Assistant.

Some connector providers (Google Maps among them) require their sources to be
shown, for voice interfaces in a companion UI with a verbatim record of the
conversation. Covers reading sources from a Conversations reply, Google Maps
detection, the Markdown record, storing and showing it, and a full turn.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from mistral_conversation import connector_sources as cs
from mistral_conversation import conversation as conv_module
from mistral_conversation.connectors import (
    ConnectorResult,
    ConnectorSource,
    MistralConnector,
    connector_reply,
)

MAPS = MistralConnector("id-maps", "google_maps", "Google Maps", "")
WIKI = MistralConnector("id-wiki", "wiki", "Wiki", "")
CAFE = ConnectorSource("Café Lumière", "https://maps.google.com/?cid=123")
WHEN = datetime(2026, 11, 11, 18, 30)


class ConnectorReplyTests(unittest.TestCase):
    def test_tool_reference_chunks_become_sources(self) -> None:
        data = {"outputs": [{"type": "message.output", "content": [
            {"type": "text", "text": "Café Lumière is open until 22:00."},
            {"type": "tool_reference", "tool": "search_places", "title": "Café Lumière",
             "url": "https://maps.google.com/?cid=123"},
            {"type": "tool_reference", "tool": "x", "title": "dup", "url": "https://maps.google.com/?cid=123"},
            {"type": "tool_reference", "tool": "x", "title": "no url"},
        ]}]}
        answer, sources = connector_reply(data)
        self.assertEqual(answer, "Café Lumière is open until 22:00.")
        self.assertEqual(sources, (CAFE,))

    def test_source_lines_are_moved_out_of_the_answer(self) -> None:
        text = (
            "It takes about 25 minutes by car.\n"
            "SOURCE: Route to Airport | https://www.google.com/maps/dir/a/b\n"
            "source:  Weather |  https://example.com/w \n"
            "SOURCE: bad | ftp://nope"
        )
        answer, sources = connector_reply({"outputs": [{"type": "message.output", "content": text}]})
        self.assertEqual(answer, "It takes about 25 minutes by car.\nSOURCE: bad | ftp://nope")
        self.assertEqual(
            sources,
            (
                ConnectorSource("Route to Airport", "https://www.google.com/maps/dir/a/b"),
                ConnectorSource("Weather", "https://example.com/w"),
            ),
        )

    def test_no_sources(self) -> None:
        self.assertEqual(connector_reply({"outputs": [{"content": "Plain."}]}), ("Plain.", ()))
        self.assertEqual(connector_reply(None), ("", ()))


class GoogleMapsUrlTests(unittest.TestCase):
    def test_google_maps_links(self) -> None:
        for url in ("https://maps.google.com/?cid=1", "https://www.google.com/maps/place/x",
                    "https://google.co.uk/maps/dir/a", "https://maps.app.goo.gl/abc",
                    "https://goo.gl/maps/abc", "https://maps.google.de/x"):
            with self.subTest(url=url):
                self.assertTrue(cs.is_google_maps_url(url))

    def test_other_links(self) -> None:
        for url in ("https://www.google.com/search?q=maps", "https://example.com/maps",
                    "https://notgoogle.com/maps", "https://goo.gl/abc", "not a url"):
            with self.subTest(url=url):
                self.assertFalse(cs.is_google_maps_url(url))


def _entry(question="Is Café Lumière open?", answer="Yes, until 22:00.", url=CAFE.url, title=CAFE.title):
    return {"time": "2026-11-11 18:30", "question": question, "answer": answer,
            "sources": [{"connector": "Google Maps", "title": title, "url": url}]}


class RecordTests(unittest.TestCase):
    def test_entry_only_when_there_are_sources(self) -> None:
        self.assertIsNone(cs.record_entry("q", "a", [ConnectorResult(WIKI, "r", "x")], "t"))
        entry = cs.record_entry("q", "a", [ConnectorResult(MAPS, "r", "x", (CAFE,))], "t")
        self.assertEqual(entry, {"time": "t", "question": "q", "answer": "a",
                                 "sources": [{"connector": "Google Maps", "title": CAFE.title, "url": CAFE.url}]})

    def test_render_puts_sources_right_after_the_verbatim_reply(self) -> None:
        text = cs.render_record([_entry()])
        reply = text.index("**Assistant:** Yes, until 22:00.")
        sources = text.index("Sources: [Café Lumière](<https://maps.google.com/?cid=123>)")
        self.assertLess(text.index("**You:** Is Café Lumière open?"), reply)
        self.assertLess(reply, sources)
        self.assertNotIn("**", text[reply + len("**Assistant:** Yes, until 22:00."):sources])

    def test_google_maps_disclosure_only_when_needed(self) -> None:
        self.assertIn(cs.GOOGLE_MAPS_DISCLOSURE, cs.render_record([_entry()]))
        other = cs.render_record([_entry(url="https://example.com/a")])
        self.assertNotIn(cs.GOOGLE_MAPS_DISCLOSURE, other)
        self.assertIn("might include information from these services", other)

    def test_newest_first_and_markdown_escaped(self) -> None:
        text = cs.render_record([_entry(question="new *bold* [x]"), _entry(question="old")])
        self.assertLess(text.index("new"), text.index("old"))
        self.assertIn(r"new \*bold\* \[x\]", text)


class _FakeStore:
    def __init__(self, data=None) -> None:
        self.data = data
        self.saved = None
        self.loads = 0

    async def async_load(self):
        self.loads += 1
        return self.data

    async def async_save(self, data) -> None:
        self.saved = data


class SourceRecordTests(unittest.IsolatedAsyncioTestCase):
    def _record(self, stored=None):
        hass = SimpleNamespace(bus=MagicMock())
        store = _FakeStore(stored)
        with patch.object(cs, "Store", lambda *a: store):
            record = cs.ConnectorSourceRecord(hass, "entry1")
        return record, store, hass

    async def test_adds_saves_shows_and_fires(self) -> None:
        record, store, hass = self._record({"entries": [_entry(question="older")]})
        with patch.object(cs.persistent_notification, "async_create") as create:
            added = await record.async_add("Is Café Lumière open?", "Yes, until 22:00.",
                                           [ConnectorResult(MAPS, "r", "x", (CAFE,))], WHEN)
        self.assertTrue(added)
        self.assertEqual([e["question"] for e in store.saved["entries"]], ["Is Café Lumière open?", "older"])
        args, kwargs = create.call_args
        self.assertIs(args[0], hass)
        self.assertIn(cs.GOOGLE_MAPS_DISCLOSURE, args[1])
        self.assertEqual(kwargs["notification_id"], "mistral_conversation_connector_sources_entry1")
        hass.bus.async_fire.assert_called_once()
        event, data = hass.bus.async_fire.call_args.args
        self.assertEqual(event, "mistral_conversation_connector_sources")
        self.assertEqual(data["time"], "2026-11-11 18:30")

    async def test_keeps_the_last_twenty_and_loads_once(self) -> None:
        record, store, _ = self._record(None)
        with patch.object(cs.persistent_notification, "async_create"):
            for i in range(25):
                await record.async_add(f"q{i}", "a", [ConnectorResult(MAPS, "r", "x", (CAFE,))], WHEN)
        self.assertEqual(len(store.saved["entries"]), cs.SOURCE_RECORD_MAX)
        self.assertEqual(store.saved["entries"][0]["question"], "q24")
        self.assertEqual(store.loads, 1)

    async def test_nothing_without_sources(self) -> None:
        record, store, hass = self._record()
        with patch.object(cs.persistent_notification, "async_create") as create:
            added = await record.async_add("q", "a", [ConnectorResult(WIKI, "r", "x")], WHEN)
        self.assertFalse(added)
        create.assert_not_called()
        hass.bus.async_fire.assert_not_called()
        self.assertEqual(store.loads, 0)


def _entity():
    runtime = SimpleNamespace(session=None, headers={})
    hass = SimpleNamespace(data={"mistral_conversation": {"entry1": runtime}})
    entry = SimpleNamespace(entry_id="entry1", options={})
    return conv_module.MistralConversationEntity(hass, entry)


def _result(speech: str):
    return SimpleNamespace(response=SimpleNamespace(speech={"plain": {"speech": speech}}))


class RecordFromTurnTests(unittest.IsolatedAsyncioTestCase):
    async def test_records_question_and_spoken_reply(self) -> None:
        entity = _entity()
        entity._source_record = MagicMock(async_add=AsyncMock())
        user_input = SimpleNamespace(text="Is Café Lumière open?")
        results = [ConnectorResult(MAPS, "r", "x", (CAFE,))]
        with patch.object(conv_module.dt_util, "now", lambda: WHEN):
            await entity._async_record_sources(user_input, _result("Yes, until ten."), results)
        entity._source_record.async_add.assert_awaited_once_with(
            "Is Café Lumière open?", "Yes, until ten.", results, WHEN
        )

    async def test_skipped_without_sources_and_never_raises(self) -> None:
        entity = _entity()
        entity._source_record = MagicMock(async_add=AsyncMock(side_effect=RuntimeError("disk full")))
        user_input = SimpleNamespace(text="q")
        await entity._async_record_sources(user_input, _result("a"), [ConnectorResult(WIKI, "r", "x")])
        entity._source_record.async_add.assert_not_awaited()
        with patch.object(conv_module._LOGGER, "exception") as log:
            await entity._async_record_sources(user_input, "odd", [ConnectorResult(MAPS, "r", "x", (CAFE,))])
        log.assert_called_once()

    async def test_full_turn_records_sources(self) -> None:
        entity = _entity()
        entity._source_record = MagicMock(async_add=AsyncMock())
        chat_log = MagicMock()
        chat_log.async_provide_llm_data = AsyncMock()
        chat_log.llm_api = None
        chat_log.unresponded_tool_results = False
        chat_log.conversation_id = "conv-1"
        user_input = SimpleNamespace(
            text="Is Café Lumière open?", language="en", context=None,
            as_llm_context=lambda d: "ctx", extra_system_prompt=None, agent_id="agent",
        )
        calls = {"n": 0}

        async def fake_stream(payload, chat_log, user_input, intercept_tool=None, intercepted=None,
                              connector_names=(), connector_calls=None):
            calls["n"] += 1
            if calls["n"] == 1:
                connector_calls.append(("connector_google_maps", "Is Café Lumière open now?"))

        run = AsyncMock(return_value=[ConnectorResult(MAPS, "Is Café Lumière open now?", "Open until 22:00.", (CAFE,))])
        with patch.object(conv_module, "async_fetch_connectors", AsyncMock(return_value=[MAPS])), \
                patch.object(entity, "_stream_and_collect", fake_stream), \
                patch.object(entity, "_async_run_connectors", run), \
                patch.object(conv_module, "_convert_chat_log_to_messages", lambda log: []), \
                patch.object(conv_module.conversation, "async_get_result_from_chat_log",
                             lambda ui, log: _result("It's open until ten tonight.")), \
                patch.object(conv_module.dt_util, "now", lambda: WHEN):
            await entity._async_handle_message(user_input, chat_log)
        entity._source_record.async_add.assert_awaited_once()
        question, reply, results, when = entity._source_record.async_add.await_args.args
        self.assertEqual((question, reply, when), ("Is Café Lumière open?", "It's open until ten tonight.", WHEN))
        self.assertEqual(results[0].sources, (CAFE,))


if __name__ == "__main__":
    unittest.main()
