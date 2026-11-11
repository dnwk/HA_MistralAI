"""Tests for leaving out admin-only LLM APIs on requests without an admin user.

Home Assistant refuses a merged LLM API ("Unauthorized") when any selected API
requires an admin and the request has no admin user — voice satellites and
automations have no user at all. Seen on a live install with "Device control"
and "Home Assistant" both selected.
"""
# ruff: noqa: I001 - import order below is intentional: `_ha_stubs` must run
# before the `mistral_conversation` import so Home Assistant is stubbed first.
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from . import _ha_stubs  # noqa: F401  side-effect: install HA stubs

from homeassistant.const import CONF_LLM_HASS_API
from mistral_conversation import conversation as conv_module

ASSIST = SimpleNamespace(id="assist", requires_admin=False)
HOME_ASSISTANT = SimpleNamespace(id="homeassistant", requires_admin=True)
APIS = [ASSIST, HOME_ASSISTANT]

ADMIN = SimpleNamespace(is_admin=True)
NON_ADMIN = SimpleNamespace(is_admin=False)


def _hass(user=None) -> SimpleNamespace:
    return SimpleNamespace(auth=SimpleNamespace(async_get_user=AsyncMock(return_value=user)))


def _ctx(user_id: str | None) -> SimpleNamespace:
    return SimpleNamespace(user_id=user_id)


class ApisForRequestTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, api_ids, context, *, user=None, apis=APIS):
        hass = _hass(user)
        with patch.object(conv_module.llm, "async_get_apis", lambda _hass: apis):
            result = await conv_module._apis_for_request(hass, api_ids, context)
        return result, hass

    async def test_nothing_selected(self) -> None:
        for value in (None, [], ""):
            with self.subTest(value=value):
                result, _ = await self._run(value, _ctx(None))
                self.assertEqual(result, value)

    async def test_no_admin_only_api_selected_skips_user_lookup(self) -> None:
        result, hass = await self._run(["assist"], _ctx(None))
        self.assertEqual(result, ["assist"])
        hass.auth.async_get_user.assert_not_called()

    async def test_voice_request_without_user_keeps_device_control(self) -> None:
        result, _ = await self._run(["assist", "homeassistant"], _ctx(None))
        self.assertEqual(result, ["assist"])

    async def test_no_context_at_all(self) -> None:
        result, _ = await self._run(["assist", "homeassistant"], None)
        self.assertEqual(result, ["assist"])

    async def test_only_admin_api_selected_leaves_none(self) -> None:
        result, _ = await self._run(["homeassistant"], _ctx(None))
        self.assertIsNone(result)
        result, _ = await self._run("homeassistant", _ctx(None))
        self.assertIsNone(result)

    async def test_non_admin_user(self) -> None:
        result, hass = await self._run(["assist", "homeassistant"], _ctx("u1"), user=NON_ADMIN)
        self.assertEqual(result, ["assist"])
        hass.auth.async_get_user.assert_awaited_once_with("u1")

    async def test_unknown_user(self) -> None:
        result, _ = await self._run(["assist", "homeassistant"], _ctx("gone"), user=None)
        self.assertEqual(result, ["assist"])

    async def test_admin_user_keeps_everything(self) -> None:
        result, _ = await self._run(["assist", "homeassistant"], _ctx("u1"), user=ADMIN)
        self.assertEqual(result, ["assist", "homeassistant"])
        result, _ = await self._run("homeassistant", _ctx("u1"), user=ADMIN)
        self.assertEqual(result, "homeassistant")

    async def test_older_home_assistant_without_requires_admin(self) -> None:
        old_apis = [SimpleNamespace(id="assist"), SimpleNamespace(id="homeassistant")]
        result, _ = await self._run(["assist", "homeassistant"], _ctx(None), apis=old_apis)
        self.assertEqual(result, ["assist", "homeassistant"])


class _StopAfterLlmData(conv_module.conversation.ConverseError):
    """Ends the turn right after async_provide_llm_data, like a real ConverseError."""

    def as_conversation_result(self):
        return "stopped"


class HandleMessageTests(unittest.IsolatedAsyncioTestCase):
    async def test_voice_turn_gets_only_non_admin_apis(self) -> None:
        hass = _hass(None)
        entry = SimpleNamespace(
            entry_id="entry1",
            options={CONF_LLM_HASS_API: ["assist", "homeassistant"]},
        )
        with patch.object(
            conv_module, "ConversationEntityFeature", SimpleNamespace(CONTROL=1)
        ):
            entity = conv_module.MistralConversationEntity(hass, entry)
        chat_log = MagicMock()
        chat_log.async_provide_llm_data = AsyncMock(side_effect=_StopAfterLlmData())
        user_input = SimpleNamespace(
            context=_ctx(None),
            as_llm_context=lambda domain: "llm-context",
            extra_system_prompt=None,
        )
        with patch.object(conv_module.llm, "async_get_apis", lambda _hass: APIS):
            result = await entity._async_handle_message(user_input, chat_log)
        self.assertEqual(result, "stopped")
        args = chat_log.async_provide_llm_data.await_args.args
        self.assertEqual(args[0], "llm-context")
        self.assertEqual(args[1], ["assist"])


if __name__ == "__main__":
    unittest.main()
