"""Config flow for Mistral AI Conversation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import llm, selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CHAT_MODELS,
    CONF_CONTINUE_CONVERSATION,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_PROMPT,
    CONF_STT_MODEL,
    CONF_TEMPERATURE,
    CONF_TTS_EMOTION,
    CONF_TTS_EXPRESSIVENESS,
    CONF_TTS_GAIN_DB,
    CONF_TTS_MODE,
    CONF_TTS_MODEL,
    CONF_TTS_PACE,
    CONF_TTS_VOICE,
    CONF_WEB_SEARCH,
    CONF_WEB_SEARCH_MODE,
    CONF_WEB_SEARCH_TRIGGER,
    DEFAULT_CONTINUE_CONVERSATION,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_STT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TTS_MODE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    DEFAULT_WEB_SEARCH,
    DEFAULT_WEB_SEARCH_MODE,
    DEFAULT_WEB_SEARCH_TRIGGER,
    DOMAIN,
    MISTRAL_API_BASE,
    TTS_EMOTIONS,
    TTS_EXPRESSIVENESS_MAX,
    TTS_EXPRESSIVENESS_MIN,
    TTS_GAIN_DB_MAX,
    TTS_MODES,
    TTS_PACES,
    TTS_STYLE_DEFAULT,
    WEB_SEARCH_MODES,
)
from .audio_models import (
    async_fetch_audio_models,
    configured_model,
    model_choices,
)
from .stt import LANGUAGE_OPTIONS
from .voices import (
    VoiceItem,
    async_fetch_voice_items,
    resolve_voice,
    static_voice_items,
    voice_choices,
)

_LOGGER = logging.getLogger(__name__)


class MistralConversationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await self._test_api_key(user_input[CONF_API_KEY])
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Mistral AI Conversation",
                    data={CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "api_key_url": "https://console.mistral.ai/api-keys"
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle reauth when API key becomes invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog to re-enter the API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await self._test_api_key(user_input[CONF_API_KEY])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def _test_api_key(self, api_key: str) -> str | None:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{MISTRAL_API_BASE}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    return "invalid_auth"
                if resp.status != 200:
                    return "cannot_connect"
        except aiohttp.ClientConnectorError:
            return "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error testing API key")
            return "unknown"
        return None

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "MistralOptionsFlow":
        return MistralOptionsFlow()


class MistralOptionsFlow(config_entries.OptionsFlow):
    """Options flow — HA injects self.config_entry as a read-only property."""

    # Voice list fetched when the form was shown; used on submit to turn a
    # typed slug or custom-voice name into that voice's ID.
    _voice_items: list[VoiceItem] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            # Clean up empty LLM API selection
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)
            # Typed model IDs: trim whitespace; a blank entry means "use the
            # default", so drop it instead of storing an empty string.
            for key in (CONF_STT_MODEL, CONF_TTS_MODEL):
                value = (user_input.get(key) or "").strip()
                if value:
                    user_input[key] = value
                else:
                    user_input.pop(key, None)
            # Voice: a picked entry is already a voice ID; typed text (a slug
            # such as en_paul_neutral, or a custom voice's name) is mapped to
            # the matching voice's ID. Blank falls back to the default voice.
            voice = (user_input.get(CONF_TTS_VOICE) or "").strip()
            if voice:
                user_input[CONF_TTS_VOICE] = resolve_voice(
                    voice, self._voice_items or static_voice_items()
                )
            else:
                user_input.pop(CONF_TTS_VOICE, None)
            # Speech style: "default" / empty means "send nothing", so it is
            # not stored at all.
            for key in (CONF_TTS_PACE, CONF_TTS_EMOTION):
                if user_input.get(key) in (None, "", TTS_STYLE_DEFAULT):
                    user_input.pop(key, None)
            if user_input.get(CONF_TTS_EXPRESSIVENESS) is None:
                user_input.pop(CONF_TTS_EXPRESSIVENESS, None)
            if not user_input.get(CONF_TTS_GAIN_DB):
                user_input.pop(CONF_TTS_GAIN_DB, None)
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        session = async_get_clientsession(self.hass)
        auth = {"Authorization": f"Bearer {self.config_entry.data[CONF_API_KEY]}"}

        # Voices and audio models are independent lookups; fetch both at once
        # so opening the dialog costs one round-trip of latency, not two.
        voice_items, (stt_models, tts_models) = await asyncio.gather(
            async_fetch_voice_items(session, auth),
            async_fetch_audio_models(session, auth),
        )

        # STT/TTS model dropdowns: default first, then the account's Voxtral
        # models, then the saved value if it is not listed. custom_value lets
        # the user type any model ID Mistral accepts.
        current_stt_model = configured_model(opts, CONF_STT_MODEL, DEFAULT_STT_MODEL)
        current_tts_model = configured_model(opts, CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        stt_model_options = model_choices(
            DEFAULT_STT_MODEL, stt_models, current_stt_model
        )
        tts_model_options = model_choices(
            DEFAULT_TTS_MODEL, tts_models, current_tts_model
        )

        # TTS voice options — live account list: custom (cloned) voices first,
        # then presets, each with a searchable label (name, languages, slug).
        # Falls back to the built-in presets if the fetch fails. The saved
        # voice is preselected even if it was saved as a slug, and kept in the
        # list if it matches nothing.
        self._voice_items = voice_items
        voice_pairs, current_voice = voice_choices(
            voice_items, opts.get(CONF_TTS_VOICE) or DEFAULT_TTS_VOICE
        )
        voice_options = [
            selector.SelectOptionDict(label=label, value=value)
            for value, label in voice_pairs
        ]

        # Build LLM API options list
        hass_apis = [
            selector.SelectOptionDict(label=api.name, value=api.id)
            for api in llm.async_get_apis(self.hass)
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    # ── Model ─────────────────────────────────────────────
                    vol.Optional(
                        CONF_MODEL,
                        default=opts.get(CONF_MODEL, DEFAULT_MODEL),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=CHAT_MODELS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="model",
                        )
                    ),
                    # ── System prompt ─────────────────────────────────────
                    vol.Optional(
                        CONF_PROMPT,
                        default=opts.get(CONF_PROMPT, DEFAULT_PROMPT),
                    ): selector.TemplateSelector(),
                    # ── LLM API (Home Assistant device control) ───────────
                    vol.Optional(
                        CONF_LLM_HASS_API,
                        description={
                            "suggested_value": opts.get(CONF_LLM_HASS_API),
                        },
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=hass_apis,
                            multiple=True,
                        )
                    ),
                    # ── Temperature ───────────────────────────────────────
                    vol.Optional(
                        CONF_TEMPERATURE,
                        default=opts.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0,
                            max=1.0,
                            step=0.05,
                            mode=selector.NumberSelectorMode.SLIDER,
                        )
                    ),
                    # ── Max tokens ────────────────────────────────────────
                    vol.Optional(
                        CONF_MAX_TOKENS,
                        default=opts.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=64,
                            max=8192,
                            step=64,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    # ── Continue conversation (experimental) ──────────────
                    vol.Optional(
                        CONF_CONTINUE_CONVERSATION,
                        default=opts.get(
                            CONF_CONTINUE_CONVERSATION, DEFAULT_CONTINUE_CONVERSATION
                        ),
                    ): selector.BooleanSelector(),
                    # ── Web search (beta) ─────────────────────────────────
                    vol.Optional(
                        CONF_WEB_SEARCH,
                        default=opts.get(CONF_WEB_SEARCH, DEFAULT_WEB_SEARCH),
                    ): selector.BooleanSelector(),
                    # ── Web search routing ────────────────────────────────
                    # 'model': the model calls a web_search tool when it needs
                    # one, keeping HA tools available on the same turn.
                    # 'always': legacy — every turn goes to the Agents API,
                    # which is slower and carries no HA tools.
                    vol.Optional(
                        CONF_WEB_SEARCH_MODE,
                        default=opts.get(
                            CONF_WEB_SEARCH_MODE, DEFAULT_WEB_SEARCH_MODE
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=WEB_SEARCH_MODES,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="web_search_mode",
                        )
                    ),
                    # ── Web search trigger phrases (optional) ─────────────
                    # Comma-separated. When set, these take precedence over the
                    # routing mode: only utterances starting with one of them
                    # search (phrase stripped), everything else never does.
                    # Empty = let the mode above decide.
                    vol.Optional(
                        CONF_WEB_SEARCH_TRIGGER,
                        default=opts.get(
                            CONF_WEB_SEARCH_TRIGGER, DEFAULT_WEB_SEARCH_TRIGGER
                        ),
                    ): selector.TextSelector(),
                    # ── Speech-to-text model ──────────────────────────────
                    vol.Optional(
                        CONF_STT_MODEL,
                        default=current_stt_model,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=stt_model_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            custom_value=True,
                        )
                    ),
                    # ── Text-to-speech model ──────────────────────────────
                    vol.Optional(
                        CONF_TTS_MODEL,
                        default=current_tts_model,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=tts_model_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            custom_value=True,
                        )
                    ),
                    # ── TTS voice (fallback default) ──────────────────────
                    # Primary voice selection is in Settings → Voice Assistants.
                    # This setting is used as fallback when no voice is chosen
                    # there, or when TTS is called directly from an automation.
                    # custom_value renders a searchable combo box that also
                    # accepts a typed voice ID, slug or custom voice name.
                    vol.Optional(
                        CONF_TTS_VOICE,
                        default=current_voice,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=voice_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            custom_value=True,
                        )
                    ),
                    # ── Speech style (pace / emotion / expressiveness) ────
                    # Mistral has no speed, pitch or volume fields: pace and
                    # emotion are inline tags, expressiveness a request field.
                    # "default" sends nothing. tts.speak can override each.
                    vol.Optional(
                        CONF_TTS_PACE,
                        default=opts.get(CONF_TTS_PACE, TTS_STYLE_DEFAULT),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[TTS_STYLE_DEFAULT, *TTS_PACES],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="tts_pace",
                        )
                    ),
                    vol.Optional(
                        CONF_TTS_EMOTION,
                        default=opts.get(CONF_TTS_EMOTION, TTS_STYLE_DEFAULT),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[TTS_STYLE_DEFAULT, *TTS_EMOTIONS],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="tts_emotion",
                        )
                    ),
                    # Empty = Mistral's own default (suggested_value, not a
                    # default, so the field can be cleared again).
                    vol.Optional(
                        CONF_TTS_EXPRESSIVENESS,
                        description={
                            "suggested_value": opts.get(CONF_TTS_EXPRESSIVENESS),
                        },
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=TTS_EXPRESSIVENESS_MIN,
                            max=TTS_EXPRESSIVENESS_MAX,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    # ── TTS volume boost ──────────────────────────────────
                    # Mistral has no volume parameter, so the audio is scaled
                    # here. 0 = unchanged (the default).
                    vol.Optional(
                        CONF_TTS_GAIN_DB,
                        default=opts.get(CONF_TTS_GAIN_DB, 0),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=TTS_GAIN_DB_MAX,
                            step=1,
                            unit_of_measurement="dB",
                            mode=selector.NumberSelectorMode.SLIDER,
                        )
                    ),
                    # ── TTS mode (stream vs batch) ────────────────────────
                    # 'stream' uses Mistral's SSE WAV endpoint with sentence
                    # pipelining for low time-to-first-audio. 'batch' issues a
                    # single mp3 request. Direct tts.speak service calls
                    # always use batch regardless of this setting.
                    vol.Optional(
                        CONF_TTS_MODE,
                        default=opts.get(CONF_TTS_MODE, DEFAULT_TTS_MODE),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=TTS_MODES,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="tts_mode",
                        )
                    ),
                }
            ),
        )
