<a name="readme-top"></a>

<div align="center">
  <img src="custom_components/mistral_conversation/icon@2x.png" alt="Mistral AI Conversation" width="128" height="128">

  <h1>Mistral AI Conversation</h1>
  <p><strong>Home Assistant custom integration — Mistral AI as conversation agent, Voxtral for speech-to-text, and Mistral TTS for text-to-speech.</strong></p>

  <p><em>⚠️ Please note this is not an officially supported integration and is not affiliated with Mistral AI in any way.</em></p>

  [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
  [![HA Version](https://img.shields.io/badge/Home%20Assistant-2025.10%2B-blue?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
  [![Mistral AI](https://img.shields.io/badge/Mistral%20AI-Powered-orange?style=for-the-badge)](https://mistral.ai/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
</div>

---

## Table of Contents

1. [About](#about)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
   - [Creating an API key](#creating-an-api-key)
   - [Setting up the integration](#setting-up-the-integration)
   - [Selecting as voice assistant](#selecting-as-voice-assistant)
6. [Options](#options)
   - [Available models](#available-models)
   - [System prompt](#system-prompt)
   - [Continue conversation (Experimental)](#continue-conversation-experimental)
   - [Web search (Beta)](#web-search-beta)
7. [Controlling devices](#controlling-devices)
8. [Using as a service action](#using-as-a-service-action)
9. [Speech recognition (STT)](#speech-recognition-stt)
10. [Text-to-speech (TTS)](#text-to-speech-tts)
11. [FAQ](#faq)
12. [Design notes](#design-notes)
13. [Release Notes](#release-notes)
14. [License](#license)

---

## About

This integration makes **Mistral AI** available as a fully-featured conversation agent inside Home Assistant's built-in Assist voice pipeline. It also registers **Voxtral** (Mistral's own speech-to-text model) as a native HA STT provider — creating two separate devices, one for conversation and one for transcription, just like the official Google Gemini integration.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Features

| Feature | Status | Description |
|---|---|---|
| Conversation agent in HA Assist | ✅ | Selectable as agent in Voice Assistants |
| Smart home control | ✅ | Control lights, switches, covers, locks, etc. |
| Speech recognition (STT) | ✅ | Voxtral (`voxtral-mini-latest` by default, configurable) via `/v1/audio/transcriptions` |
| Text-to-speech (TTS) | ✅ | Mistral TTS (`voxtral-mini-tts-latest` by default, configurable) via `/v1/audio/speech` |
| Configurable speech models | ✅ | Pick the STT and TTS models from those on your Mistral account, or type any model ID |
| Streaming TTS | ✅ | Low-latency SSE WAV with sentence-level pipelining (≥ v0.4.0) |
| Speech style | ✅ | Speaking pace, emotion, expressiveness and volume boost, as defaults or per `tts.speak` call |
| Live TTS voice list | ✅ | Voices fetched from your Mistral account — presets *and* custom (cloned) voices, in a searchable picker |
| AI Task | ✅ | `ai_task.generate_data` with structured output and image attachments |
| Conversation memory | ✅ | Context kept per session until 5 min idle (HA timeout). |
| Jinja2 system prompt | ✅ | Templates with `{{ now() }}`, `{{ ha_name }}` etc. |
| Multilingual | ✅ | Responds in the user's language |
| Continue conversation | ✅ | Keeps microphone open after questions (Experimental) |
| Web search | ✅ | Model-decided web search via the Agents API, or trigger phrases (Beta) |
| Separate devices | ✅ | Conversation, STT and TTS appear as separate HA devices |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Requirements

| Requirement | Minimum version |
|---|---|
| Home Assistant Core | 2025.10 |
| Python | 3.13 |
| Mistral AI account + API key | — |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Installation

### Via HACS (recommended)

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. URL: `https://github.com/dnwk/HA_MistralAI` — category: **Integration**
3. Search "Mistral AI Conversation" → **Download**
4. **Fully restart** Home Assistant

> This installs this fork, which is based on [SnarfNL/HA_MistralAI](https://github.com/SnarfNL/HA_MistralAI) — see [Design notes](#design-notes) for how they differ. Both install the same `mistral_conversation` integration, so if you added the upstream repository to HACS before, remove it there first to avoid the two overwriting each other.

### Manual

1. Copy `custom_components/mistral_conversation/` to `/config/custom_components/`
2. Remove old `__pycache__` directories if updating from a previous version:
   ```bash
   rm -rf /config/custom_components/mistral_conversation/__pycache__
   ```
3. **Fully restart** Home Assistant (not just reload)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Configuration

### Creating an API key

1. Sign up at [mistral.ai](https://mistral.ai/)
2. Go to [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys)
3. Click **Create new key** and copy it immediately

### Setting up the integration

1. **Settings → Devices & Services → + Add Integration**
2. Search for **Mistral AI Conversation**
3. Enter your API key → **Submit**

### Selecting as voice assistant

1. **Settings → Voice Assistants** → click your assistant
2. Set **Conversation agent** to **Mistral AI Conversation**
3. Optionally set **Speech-to-text** to **Mistral AI STT (Voxtral)**
4. Save

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Options

Click the integration → **Configure** to change settings.

| Option | Default | Description |
|---|---|---|
| **AI model** | `ministral-8b-latest` | Which Mistral model to use |
| **System prompt** | See below | Jinja2 template with AI instructions |
| **Temperature** | `0.7` | Creativity: 0.0 = deterministic, 1.0 = creative |
| **Max tokens** | `1024` | Maximum response length |
| **Control HA** | On | Allow the AI to control exposed devices |
| **Continue conversation** | Off | Keep listening after questions (Experimental) |
| **Web search** | Off | Allow the AI to search the web (Beta) |
| **Web search routing** | `Let the model decide` | How web search is triggered — see below |
| **Web search trigger phrases** | *(empty)* | Optional phrases that force a web search — see below |
| **Speech-to-text model** | `voxtral-mini-latest` | Voxtral transcription model — dropdown lists the Voxtral speech models on your account; any model ID can also be typed |
| **Text-to-speech model** | `voxtral-mini-tts-latest` | Voxtral TTS model — dropdown lists the TTS models on your account; any model ID can also be typed |
| **STT language** | Auto-detect | Language for Voxtral transcription |
| **TTS voice** | `en_paul_neutral` | Fallback default voice — searchable list of your account's voices (custom/cloned voices first, then presets); a voice ID, slug or custom voice name can also be typed |
| **Speaking pace** | Default (not set) | Very slow … Very fast — see [Speech style](#speech-style-pace-emotion-expressiveness) |
| **Emotion** | Default (not set) | Tone of voice, one of 34 emotions (Voxtral 3 voices) — see [Speech style](#speech-style-pace-emotion-expressiveness) |
| **Expressiveness** | *(empty — Mistral's default)* | 1.0–5.0; higher = stronger delivery, less like the chosen voice |
| **Volume boost** | `0 dB` (unchanged) | 0 to +12 dB, applied to the audio in Home Assistant — see [Volume boost](#volume-boost) |
| **TTS mode** | `Streaming` | `Streaming` (SSE WAV with sentence-level pipelining) or `Batch` (single MP3 request) |

### Available models

Verified against Mistral's model lineup, September 2026. All entries use Mistral's `-latest` aliases, which track the current model automatically as Mistral ships new versions (e.g. `mistral-large-latest` now serves Mistral Large 3).

| Model | Speed | Cost | Free tier | Best for |
|---|---|---|---|---|
| `ministral-8b-latest` ⭐ | ★★★★★ | $ | ✅ | Home automation commands — fast, accurate, cheap |
| `ministral-3b-latest` | ★★★★★ | $ | ✅ | Ultra-simple commands, lowest latency |
| `ministral-14b-latest` 🆕 | ★★★★ | $ | ✅ | New (Dec 2025). Strongest of the small edge models |
| `mistral-small-latest` | ★★★★ | $$ | ✅ | Balanced: quality and speed |
| `mistral-medium-latest` | ★★★ | $$$ | ⚠️ | Required for web search; heavier, often rate-limited on free API keys |
| `mistral-large-latest` | ★★★ | $$$$ | ⚠️ | Complex reasoning, long conversations; heavier, often rate-limited on free API keys |

> **Recommendation:** Start with `ministral-8b-latest`. It has excellent instruction-following, handles structured JSON output reliably (needed for device control), and costs a fraction of larger models.
>
> **About the "Free tier" column:** Mistral's free/Experiment API tier gives rate-limited trial access to all models — Mistral doesn't publish an official per-model block list. In practice, though, Medium and Large are the ones most likely to hit those limits or get rejected on a free-tier key, since they're the most expensive per token. If you're on a free key and see errors on Medium or Large, that's most likely why — check your usage tier at [admin.mistral.ai](https://admin.mistral.ai/plateforme/limits).
>
> **Removed:** `open-mistral-nemo` (Mistral Nemo 12B) has been deprecated and retired by Mistral and no longer works — switch to `ministral-8b-latest` or `ministral-3b-latest` if your config still uses it.

### System prompt

The system prompt supports Jinja2 templates:

```jinja2
You are a helpful voice assistant for {{ ha_name }}.
Answer in the same language the user speaks.
Today is {{ now().strftime('%A, %B %d, %Y') }} and the time is {{ now().strftime('%H:%M') }}.
Be concise and friendly.
For straightforward home control commands, briefly confirm the action taken without asking follow-up questions.
Your responses are read aloud by text-to-speech, so reply in plain text.
Do not use markdown formatting that cannot be read aloud, such as asterisks for bold, underscores for italics, backticks, bullet lists, emojis, or headers.
```

**Available template variables:**

| Variable | Description |
|---|---|
| `{{ ha_name }}` | Your Home Assistant location name |
| `{{ now() }}` | Current datetime object |
| `{{ now().strftime(…) }}` | Formatted date/time string |

### Continue conversation (Experimental)

When enabled, the assistant automatically keeps the microphone open after any response that contains a question (`?`). This is implemented using the native `continue_conversation` flag in HA's `ConversationResult` — no separate automation is needed.

> **Note:** This feature requires a satellite device that supports `assist_satellite.start_conversation`. Behaviour may vary between satellite types.

### Web search (Beta)

Web search is only available through Mistral's **Agents API**, which is a separate,
slower endpoint than the regular chat completions call and **cannot carry Home
Assistant tools**. A turn answered by the Agents API therefore cannot control
your devices. Requires an agent-capable model (`mistral-small-latest`,
`mistral-medium-latest` or `mistral-large-latest`).

**Web search routing** controls when that endpoint is used:

| Mode | Behaviour |
|---|---|
| **Let the model decide** (default) | Web search is offered to the model as a tool. It searches only when it judges a search is needed, and Home Assistant tools stay available — so one turn can search *and* control devices. |
| **Always search** | Legacy behaviour: every request goes to the Agents API. Slower, and device control does not work on those turns. |

> **Performance note:** enabling web search with **Always search** routes *every*
> utterance — including "turn on the lamp" — through the Agents API. Use
> **Let the model decide**, or set trigger phrases, to keep ordinary commands on
> the fast path.

**Web search trigger phrases** (optional) is a comma-separated list, for example:

```
search for, look up, google
```

When it is non-empty it **takes precedence over the routing mode**: only utterances
that *start with* one of the phrases search the web (the phrase itself is stripped
from the query), and every other utterance never searches. If several phrases
match, the longest one wins. Matching is case-insensitive. Leave the field empty
to let the routing mode decide.

Trigger phrases are language-specific, so nothing is shipped by default. Dutch
users might use `zoek op, zoek online, google`; German users `suche, google`.

> Note: with trigger phrases set, a matching turn goes straight to the Agents API
> and so cannot control devices — that is the same trade-off as **Always search**,
> just limited to utterances you opt into.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Controlling devices

Enable **Allow AI to control Home Assistant devices** in the options, then expose the entities you want via **Settings → Voice Assistants → Exposed devices**.

Under **Control Home Assistant** you choose which Home Assistant APIs the AI may use:

- **Device control** (Assist) — controls and reads the entities you expose. This is what voice commands need.
- **Home Assistant** — lets the AI manage Home Assistant itself (registries, system logs, automations, integration entries). It is not limited to exposed entities, and Home Assistant only allows it for **admin users**. It is offered only when an admin is chatting (for example in the Assist dialog). Voice satellites, automations and non-admin users have no admin user behind them, so for those requests it is left out and the other selected APIs are used.

### Example commands

| What you say | What happens |
|---|---|
| "Turn off the kitchen light" | `light.turn_off` |
| "Open the blinds" | `cover.open_cover` |
| "Lock the front door" | `lock.lock` |
| "Play something in the living room" | `media_player.media_play` |
| "Activate the movie scene" | `scene.turn_on` |

### Supported domains

`light` · `switch` · `cover` · `media_player` · `fan` · `climate` · `lock` · `alarm_control_panel` · `scene` · `script` · `automation` · `homeassistant`

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Using as a service action

Use `conversation.process` in automations or scripts:

```yaml
action: conversation.process
data:
  agent_id: conversation.mistral_ai_conversation
  text: "What is the temperature in the living room?"
response_variable: result
```

The response text is in `result.response.speech.plain.speech`.

### Example: Smart doorbell notification

```yaml
alias: Smart doorbell notification
sequence:
  - action: conversation.process
    data:
      agent_id: conversation.mistral_ai_conversation
      text: >
        The doorbell rang at {{ now().strftime('%H:%M') }}.
        Write a short, friendly notification message.
    response_variable: ai_result
  - action: notify.mobile_app
    data:
      title: "Doorbell 🔔"
      message: "{{ ai_result.response.speech.plain.speech }}"
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Speech recognition (STT)

A `stt.mistral_ai_stt_voxtral` entity is registered automatically.

### Voxtral specifications

| Property | Value |
|---|---|
| Model | `voxtral-mini-latest` by default — change it under **Configure → Speech-to-text model** |
| Supported format | WAV (16-bit, 16 kHz, mono PCM) |
| Languages | 60+ with auto-detect |
| Pricing | ~$0.003 per minute |

### Setting STT language

In the options, select a language from the dropdown for best accuracy, or leave it on **Auto-detect**.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


---

## Text-to-speech (TTS)

When the integration is installed, a **Mistral AI TTS** entity is registered automatically as a separate HA TTS provider. It uses Mistral's `/v1/audio/speech` endpoint and supports two operating modes (see [TTS modes](#tts-modes) below): low-latency streaming WAV (default, since v0.4.0) and single-shot MP3.

### TTS modes

Selectable via **Settings → Devices & Services → Mistral AI Conversation → Configure → Text-to-speech mode**:

| Mode | Behaviour | First audio | Best for |
|---|---|---|---|
| **Streaming** *(default)* | Server-Sent Events with chunked WAV. Sentences are extracted from the LLM token stream and dispatched to Mistral in parallel (up to 5 concurrent), with audio reassembled in strict order. | ~0.5–1 s | HA Voice satellites (Voice PE, ESPHome) |
| **Batch** | Single non-streaming POST returns the full MP3 in a JSON body before any audio is yielded. | After full synthesis (~3–5 s for long replies) | Direct `tts.speak` service calls; environments where chunked HTTP is problematic |

> **Note:** Direct `tts.speak` service calls always use the batch path regardless of this setting (the service expects a single audio file, not a stream).

### Voxtral TTS specifications

| Property | Value |
|---|---|
| Model | `voxtral-mini-tts-latest` by default — change it under **Configure → Text-to-speech model** |
| Stream container | WAV (24 kHz, 16-bit, mono PCM) |
| Batch container | MP3 (base64-wrapped JSON response) |
| Voices | Fetched live from your account — Mistral presets plus your custom voices |

### Selecting a voice

The voice list is fetched live from Mistral's `/v2/audio/voices` API (falling back to the older `/v1/audio/voices` if v2 is unavailable), so it always reflects your account: all Mistral preset voices plus any custom voices you have created, shown with their human-readable names. If the fetch fails (network error, API issue) a built-in static list of preset voices is used as fallback.

Two places to pick a voice:

1. **Settings → Voice Assistants → your assistant → Text-to-speech voice** — the primary selection, refreshed when the integration (re)loads.
2. **Settings → Devices & Services → Mistral AI Conversation → Configure → Text-to-speech voice** — the fallback default, used when no voice is chosen in the Voice Assistants dialog or when TTS is called from an automation. This dropdown re-fetches the live list every time you open it, so a newly created custom voice appears here without a restart.

The Configure field is a searchable combo box. Custom (cloned) voices are listed first, then Mistral's presets. Each entry shows the voice's name, whether it is a custom voice, its languages and gender when Mistral provides them, and the preset slug — for example `Paul – Neutral (en_us) · en_paul_neutral` or `My voice (custom voice)` — so you can type any of those to find it. You can also type a value that is not in the list:

- a preset slug such as `en_paul_neutral`, or the exact name of one of your custom voices — saved as that voice's ID;
- any other voice ID — saved as typed (useful if the voice list could not be loaded).

The same labels are used in the Voice Assistants voice picker.

### Using a voice in an automation

Pass the voice in `tts.speak` options. A preset slug or any voice ID from your account (including a custom voice's ID) works:

```yaml
action: tts.speak
target:
  entity_id: tts.mistral_ai_tts  # your Mistral AI TTS entity — check under Settings → Entities
data:
  media_player_entity_id: media_player.living_room
  message: "The washing machine is done."
  options:
    voice: en_paul_neutral
```

Without `voice`, the **Text-to-speech voice** from the integration options is used.

> A voice chosen under **Settings → Voice Assistants** always wins for that assistant; the integration's voice setting only applies when none is chosen there, and to `tts.speak` without `voice`. The **Text-to-speech model** and the speech style below always come from the integration options — Voice Assistants has no setting for them.

### Speech style (pace, emotion, expressiveness)

Mistral's speech API has **no speed, pitch or volume settings**. What it offers, and what the integration exposes under **Configure**:

| Setting | Sent to Mistral as | Values |
|---|---|---|
| **Speaking pace** | a `[pace=…]` tag in front of the text (not spoken) | Very slow, Slow, Moderate, Fast, Very fast |
| **Emotion** | an `[emotion=…]` tag in front of the text (not spoken) | amused, angry, anxious, apologetic, appreciative, assertive, bored, calm, confident, confused, critical, curious, determined, disappointed, disgusted, excited, frustrated, grateful, happy, hopeful, playful, proud, reflective, resigned, sad, sarcastic, skeptical, somber, surprised, tense, tired, urgent, warm, wistful |
| **Expressiveness** | the `expressiveness` request field | 1.0–5.0 — higher values give a stronger delivery but sound less like the chosen voice and less stable |

Each is off by default (nothing is sent). The settings apply to Voice Assistant replies and to `tts.speak`, which can override them per call:

```yaml
action: tts.speak
target:
  entity_id: tts.mistral_ai_tts  # your Mistral AI TTS entity
data:
  media_player_entity_id: media_player.living_room
  message: "Someone is at the front door."
  options:
    pace: slow
    emotion: calm
    expressiveness: 2
```

Use `default` (or an empty value) in `options` to turn a setting off for one call. Unknown values are ignored with a warning in the log.

> **Model and voice support.** Mistral documents these tags with its Voxtral TTS 3 model (`voxtral-mini-tts-3-0`). Older presets such as `en_paul_angry` carry their emotion in the voice itself, so an emotion tag has little effect on them. Mistral doesn't say which version `voxtral-mini-tts-latest` points to; if you hear "pace equals slow" read out loud, your model doesn't support tags — pick a Voxtral TTS 3 model under **Text-to-speech model** or switch the setting back to *Default*. For volume, see [Volume boost](#volume-boost) below.

### Volume boost

Mistral's voices can be quiet next to other TTS engines, and its API has no volume setting. **Volume boost** (0 to +12 dB, under **Configure**) makes the integration raise the volume of the audio itself before Home Assistant plays it:

- **0 dB** (the default) leaves the audio exactly as Mistral sends it.
- **+3 to +6 dB** is usually enough and stays clean.
- **Higher values** sound louder but squashed: loud parts are rounded off instead of clipping, and at +12 dB everything above about half of full volume ends up at the maximum.

It applies to Voice Assistant replies and to `tts.speak`, which can override it per call with `options: {volume_boost: 6}` (`0` turns it off for that call). With a boost set, `tts.speak` receives WAV instead of MP3, because the boost needs the raw audio. Only 16-bit PCM audio — what Mistral sends — is boosted; anything else plays unchanged with one warning in the log.

Volume boost is ported from the upstream project ([SnarfNL/HA_MistralAI](https://github.com/SnarfNL/HA_MistralAI), where it was still a draft); this fork adds the per-call override and makes Home Assistant's TTS cache aware of the setting.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## FAQ

**Q: The integration does not appear in the Voice Assistants dropdown.**
A: Make sure you performed a full restart (not just reload) and cleared any `__pycache__` directories.

**Q: I get a 400 Bad Request error.**
A: Check the HA logs for the full error body. A common cause is an invalid model name or a temperature value outside 0.0–1.0.

**Q: Can I use TTS with this integration?**
A: Now that Mistral has a TTS model, yes. Please refer to Text-to-speech (TTS) section for details.

**Q: Device control stopped working after updating to Home Assistant 2026.9.**
A: Fixed in this version. HA 2026.9 changed how tool schemas are built, and older versions of this integration sent them to Mistral in a form it rejected (HTTP 422, usually with nothing obvious in the log). Update the integration and restart.

**Q: The log says "Error getting LLM API ['assist', 'homeassistant'] … Unauthorized".**
A: The *Home Assistant* API is admin-only, and older versions of this integration passed it on for every request, so Home Assistant refused requests from voice satellites and automations. Update the integration: admin-only APIs are now left out for requests without an admin user. If you don't want the AI to manage Home Assistant itself at all, untick *Home Assistant* under **Control Home Assistant**.

**Q: Speech recognition or TTS stopped working after I changed the model.**
A: Check the log: STT and TTS errors name the model that was used. Not every model in the dropdown is guaranteed to work with the endpoint (the list is built from your account's Voxtral models). Switch back to the default — it is always the first entry.

**Q: My cloned voice is not in the list.**
A: The Configure dialog re-fetches your voices each time it opens; the Voice Assistants picker refreshes when the integration reloads. If the list could not be loaded, the built-in presets are shown instead — you can still type your voice's ID in the Configure field.

**Q: How much does it cost?**
A: With `ministral-8b-latest` and typical home use, expect less than €1–2 per month. Voxtral STT adds ~€0.003/minute. See [mistral.ai/pricing](https://mistral.ai/pricing/).

**Q: Does continue conversation work on all satellites?**
A: It requires a satellite that supports the `assist_satellite` integration and `start_conversation`. It has been tested with ESPHome voice satellites. Behaviour on other devices may vary.

**Q: Are my conversations stored?**
A: Mistral AI processes requests via their servers. See their [privacy policy](https://mistral.ai/privacy-policy) for details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Design notes

Decisions behind recent changes, and why they were made.

- **Models follow Mistral's `-latest` aliases.** The chat, STT and TTS defaults use `-latest` aliases, so new model versions arrive without an integration update. The TTS default stays `voxtral-mini-tts-latest` rather than a pinned version: Mistral's model docs list the pinned `voxtral-mini-tts-2603` as deprecated, with retirement planned for 30 April 2027.
- **Speech model lists come from your account, not a fixed list.** Mistral renames and retires audio models often, and its docs don't reliably say which IDs each endpoint accepts. The STT and TTS dropdowns are therefore built from `GET /v1/models`, and any model ID can be typed. Sorting is by name: IDs starting with `voxtral` that contain `tts` are TTS models; for STT only transcription models are listed — IDs containing `transcribe` and the `voxtral-mini` family. Plain `voxtral-small-*` models are chat-with-audio models that the transcription endpoint rejects ("Invalid model"), and realtime models are left out because they use a different (websocket) API. A listed model is not guaranteed to work with the endpoint; the default is always the first entry.
- **Voices are saved by voice ID.** The voice pickers store Mistral's voice ID, as earlier versions did, so existing settings and Voice Assistants selections keep working. Mistral also accepts a preset's slug (such as `en_paul_neutral`) as the voice, so slugs work in `tts.speak`; in the Configure field a typed slug or custom voice name is converted to that voice's ID.
- **Voice Assistants picks the voice; the integration sets everything else.** A voice chosen under Settings → Voice Assistants always wins for that assistant, so the integration's *Text-to-speech voice* is only a fallback: for an assistant with no voice chosen and for `tts.speak` without `voice`. It is kept for that reason (upstream removed it). Voice Assistants has no setting for the TTS model, speech style or volume boost, so those always come from the integration options — the *Text-to-speech model* field is needed even when every assistant has a voice chosen.
- **The voice field accepts typed values, so it shows the stored ID.** Making the voice picker searchable and able to take a typed slug, custom voice name or ID requires Home Assistant's "custom value" select. Once a voice is chosen, that picker displays the stored value — a voice ID such as `01a11755-…` — instead of the voice's label. The setting is correct; this is how Home Assistant's frontend renders such fields, and it was accepted as the price of search and typed entry.
- **Voice list from v2, with a narrow v1 fallback.** Mistral deprecated offset pagination on `GET /v1/audio/voices`, so the list comes from `GET /v2/audio/voices`. v1 is only tried when v2 answers HTTP 400, 404, 405 or 422 (endpoint or request not accepted). For an invalid key, a rate limit or a server error a second request would fail the same way, so none is made.
- **Admin-only Home Assistant APIs are left out for non-admin requests.** Home Assistant marks some LLM APIs as admin-only (such as *Home Assistant*) and, when several are selected, refuses the whole set — and so the whole turn — if the request has no admin user. With *Device control* and *Home Assistant* both selected, every voice command failed with "Error getting LLM API …: Unauthorized". The integration now drops the admin-only APIs for requests without an admin user and keeps the rest, so voice control keeps working while admins chatting in the app still get everything selected. If only admin-only APIs are selected, such requests run without tools.
- **Speech style uses Mistral's tags, and is off until you set it.** Mistral's speech API has no speed, pitch or volume fields, so pace and emotion are sent as inline tags (`[emotion=calm][pace=slow]`) and expressiveness as a request field. Every control defaults to *not set* and sends nothing — "Default" is not even stored — because Mistral documents the tags only for Voxtral TTS 3 and an older model might read a tag aloud. `expressiveness` appears in Mistral's TTS guide but not in its API reference, which is another reason it is only sent when set. Only the values Mistral documents are sent: an unknown tag is accepted by the API but does nothing, so typos are logged and dropped instead. Each streamed sentence is its own request, so the tags are added to every sentence. Pitch is not offered: Mistral has no field for it and changing it locally would need real signal processing. The style is returned in the TTS entity's default options so Home Assistant's TTS cache does not replay audio made with an old setting, and `tts.speak` can override each control per call.
- **Volume is the one thing processed locally, and only upward.** A too-quiet voice can't be fixed from the media player without making everything else too loud, so the *Volume boost* scales the 16-bit PCM inside Home Assistant (standard library only, no `audioop` or numpy). It only boosts (0 to +12 dB): turning speech down is what the media player volume already does well. It uses a static soft clipper rather than a leveller — simple and never hard-clipping, but loud parts get squashed at high settings; at +12 dB everything above about half of full volume reaches the maximum, so +3 to +6 dB is the recommended range. The boost needs raw audio, so `tts.speak` returns WAV instead of MP3 while it is on. The 65,536-entry lookup table is built in an executor, not on the event loop. It is part of the same default options as the speech style, so changing it refreshes cached audio and `volume_boost` can be overridden per call.
- **Web search results are treated as untrusted.** On the round where the model reads search results, every tool is withdrawn, not just web search, so instructions hidden in a web page cannot trigger a device action. Device control still works on the round where the model decides to search.
- **No household data in the web-search agent.** The web-search agent is stored in your Mistral account, so it gets fixed, generic instructions and never your rendered system prompt (which can contain your exposed entities and areas). An existing agent with the same name and model is reused instead of creating a new one on every restart.
- **Upstream changes are ported selectively.** This fork is based on [SnarfNL/HA_MistralAI](https://github.com/SnarfNL/HA_MistralAI) and takes individual changes rather than merging it wholesale. Each ported change is marked *ported from upstream* in the release notes. Taken so far: the Home Assistant 2026.9 tool-schema fix (including AI Task `multiple` fields), the streaming-TTS WAV header fix, the chat model list update, and the volume boost. The volume boost was taken while it was still a draft upstream because it answered a real need here (Mistral's voice being too quiet); this fork added the TTS cache key, the per-call override and building the lookup table off the event loop. Not taken: upstream's removal of the *Text-to-speech voice* option (kept here as the searchable fallback voice) and its pinned `voxtral-mini-tts-2603` TTS model (this fork uses `voxtral-mini-tts-latest`). Upstream's tests depend on its real-Home-Assistant test setup, so ported changes get tests written for this fork's own test stubs.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Release Notes

### Unreleased
- **Added:** *Volume boost* option for text-to-speech (0 to +12 dB, default 0 = unchanged). Mistral has no volume setting, so the integration scales the 16-bit PCM itself with a soft limiter, both for streamed Voice Assistant replies and for `tts.speak` (which then returns WAV instead of MP3). `tts.speak` can override it with the `volume_boost` option, and the setting is part of Home Assistant's TTS cache key, so changing it doesn't replay cached audio at the old volume. +3 to +6 dB stays clean; higher values squash loud parts. *Ported from upstream (draft at the time); the per-call option and cache handling are additions.*
- **Added:** *Speaking pace*, *Emotion* and *Expressiveness* options for text-to-speech. Pace (very slow … very fast) and emotion (34 values such as calm, warm, happy) are sent as Mistral's inline `[pace=…]` / `[emotion=…]` tags, expressiveness (1.0–5.0) as a request field. All are off by default, apply to Voice Assistant replies and `tts.speak`, and can be overridden per call with the `pace`, `emotion` and `expressiveness` options. Mistral offers no speed, pitch or volume setting. Mistral documents the tags for Voxtral TTS 3; with an older TTS model a tag may be read aloud.
- **Fixed:** with the admin-only *Home Assistant* API selected under *Control Home Assistant* (alongside *Device control*), every request without an admin user — voice satellites, automations, non-admin users — failed with "Error getting LLM API ['assist', 'homeassistant'] for mistral_conversation: Unauthorized". Admin-only APIs are now left out for those requests and the other selected APIs are used; admin users still get every selected API. The option's help text explains this.
- **Fixed:** the *Speech-to-text model* dropdown offered `voxtral-small-latest` and `voxtral-small-2507`, which are chat-with-audio models; picking one made every transcription fail with HTTP 400 "Invalid model". The list now only holds transcription models (IDs containing `transcribe`, and the `voxtral-mini` family). A model saved earlier is still shown and can be changed.
- **Changed:** the voice list is fetched from `GET /v2/audio/voices` (cursor pagination with `page_token`), because Mistral deprecated the offset pagination of `GET /v1/audio/voices`. v1 is still used as a fallback if v2 is missing or rejects the request (HTTP 400/404/405/422). A timeout or unreadable response while fetching voices now falls back to the built-in preset list instead of failing.
- **Changed:** the *Text-to-speech voice* option is a searchable combo box. Custom (cloned) voices are listed first, and every voice is labelled with its name, languages, gender and preset slug (e.g. `Paul – Neutral (en_us) · en_paul_neutral`, `My voice (custom voice)`), using the `type`, `slug` and `gender` fields of the voice list. A typed slug or custom voice name is saved as that voice's ID; any other typed voice ID is saved as-is. The Voice Assistants voice picker uses the same labels. Saved voices keep working unchanged.
- **Added:** *Speech-to-text model* and *Text-to-speech model* options (Settings → Devices & Services → Mistral AI Conversation → Configure). Each dropdown lists the Voxtral models available on your Mistral account (from `GET /v1/models`, realtime models excluded) and also accepts any typed model ID. The defaults stay `voxtral-mini-latest` and `voxtral-mini-tts-latest`; existing setups are unchanged. Saving reloads the integration, and STT/TTS error logs now name the model used.
- **Changed:** Chat model list: added `ministral-14b-latest` (Ministral 3 14B); removed `open-mistral-nemo`, which Mistral has retired, and the pinned `mistral-medium-2505` from the web-search models (the `-latest` alias covers it). The model dropdown shows a short note per model on how it fares with a free-tier API key (English, French, Dutch). Setups still on `open-mistral-nemo` need to pick another model. *Ported from upstream.*
- **Fixed:** Streaming TTS stays playable when the first sentence fails. Before, the stream took its WAV header from sentence 0 only, so a failure there left the audio without a header. Each sentence's header is now kept separately and the stream starts with the header of the first sentence that delivers audio; pauses are only inserted between sentences that produced audio. If every sentence fails, an error is raised instead of returning silence; an emoji-only reply still ends silently. *Ported from upstream.*
- **Fixed:** Device control stopped working on Home Assistant 2026.9+. HA now builds tool schemas with `probatio`, and the old conversion turned almost every tool's parameters into the string `"UNSUPPORTED"`, which Mistral rejected with HTTP 422 without an obvious error in the log. Schemas are now converted with `probatio.to_openapi()` when available (falling back to `voluptuous_openapi`), and anything that is still not a JSON object is replaced by an empty schema. The request is also sanitized after tools are attached, which fixes `TypeError: Type is not JSON serializable: _Unsupported`. *Ported from upstream.*
- **Fixed:** `ai_task.generate_data`: a `structure` field using a selector with `multiple: true` is now requested as a JSON array instead of a single value. A response that does not match the requested structure is logged as a warning; the data is still returned. *Ported from upstream.*
- **Changed:** The web-search agent stored in your Mistral account is created with fixed, generic instructions instead of your rendered system prompt, which can include your exposed entities and areas. Before, the first caller's prompt was also used for every later search. An existing agent with the same name and model is now reused, so restarts no longer add a new agent each time. The map from HA conversations to Mistral web-search conversations is capped at 32 entries (oldest dropped first).
- **Security:** Web search results are treated as untrusted content. On the round where the model reads the results, all tools are withdrawn (before, only web search was), so instructions embedded in a web page cannot trigger a device action such as unlocking a door. The results are also fenced with a warning to ignore any instructions inside them. Device control still works on the round where the model decides to search.
- **Fixed:** The voice picker showed at most 10 voices. The voice list endpoint is paginated with a small default page size; every page is now fetched, so all presets and custom voices appear.
- **Changed:** TTS model switched from `voxtral-mini-tts-2603` to `voxtral-mini-tts-latest`, so the integration tracks Mistral's current TTS model automatically.
- **Changed:** TTS voices are now pulled live from `GET /v1/audio/voices` everywhere — the options-flow dropdown (previously a static list) now shows the account's presets and custom voices with human-readable names, re-fetched each time the Configure dialog opens. The static `TTS_VOICES` list remains only as fallback when the fetch fails, and a previously saved legacy voice id still renders as selected.
- **Fixed:** With web search enabled, *every* utterance was routed through the Agents API — including plain device commands. That path never passed Home Assistant tools, so device control silently failed on it (the model replies "I can't perform physical actions"). Web search is now opt-in per turn. Fixes #29.
- **Added:** `web_search_mode` option. Default `model` advertises web search to the model as a tool and services the call against the Agents API, so a turn keeps its HA tools and can search *and* control devices. `always` preserves the previous behaviour.
- **Added:** `web_search_trigger` option — optional comma-separated phrases (empty by default). When set it takes precedence over `web_search_mode`: only utterances starting with a phrase search (phrase stripped, longest match wins, case-insensitive); all others never search.
- **Fixed:** Assistant turns carrying neither text nor tool calls are no longer sent to Mistral — they were rejected with HTTP 400 `Assistant message must have either content or tool_calls, but not none.` (code 3240).
- **Added:** 29 unit tests for trigger resolution, tool-call interception, and the content-less-assistant-turn guard.

---

### 2026.05 — 2026-05-04
- **Changed:** Version numbering from digits to year.month.version format.
- **Added:** New AI task entity that lets Mistral generate structured data, handle image attachments, and respect output schemas defined in HA automations.
- **Added:** Streaming TTS via Mistral's SSE WAV endpoint (`response_format=wav`, `stream=true`). End-of-speech-to-first-audio drops from ~5 s to ~1 s for long responses — audio chunks arrive while synthesis is in progress instead of waiting for the full MP3.
- **Added:** Sentence-level pipelining — incoming LLM tokens are segmented into complete sentences and dispatched to Mistral in parallel (up to 5 concurrent requests bounded by an `asyncio.Semaphore`). Audio is reassembled in strict order with the WAV header from sentence 0 followed by raw PCM samples from sentences 1..N.
- **Added:** `tts_mode` integration option — choose between `stream` (default) and `batch`. Direct `tts.speak` service calls always use the batch path regardless of this setting.
- **Added:** `tests/` directory with 64 unit tests covering `_streaming` helpers (sentence segmenter, SSE parser), const sanity (defaults reference valid values, voice naming convention, WAV header pin), `_pcm_to_wav` (round-trips RIFF/WAVE, fmt subchunk, data subchunk), and `_async_stream_delta` (chat-completions SSE: text deltas, `[DONE]` termination, tool-call accumulation, frame-split tolerance, malformed JSON resilience). Run with `python -m unittest discover -t . -s tests`.
- **Added:** MIT `LICENSE` file at the repo root.
- **Fixed:** `async_unload_entry` now unloads platforms *before* clearing runtime data — previously the order was reversed, which could race with in-flight streaming TTS that resolves `self._runtime` lazily on each chunk.
- **Changed:** Minimum Home Assistant version bumped to **2025.10.0** — required for `async_stream_tts_audio` (HA streaming TTS API, shipped 2025.7).

---

### v0.3.6 — 2026-04-10
- **Changed** :Setting default voices and language has been clarified

### v0.3.5 — 2026-04-10
- **Fixed:** : Update available TTS voices and set new default by @kalon33 in #12
- **Changed:** :Translate in French by @kalon33 in #13

### v0.3.1.2 — 2026-04-09
- **Fixed:** TTS voice list corrected — previous lists contained non-existent voice IDs. Replaced with the complete official list of 20 voices from Mistral TTS documentation, covering English (casual, cheerful, neutral), French, Spanish, German, Italian, Portuguese, Dutch, Arabic, and Hindi. Default changed to `neutral_female`.

---

### v0.3.1.1 — 2026-04-09
- **Fixed:** Mistral TTS returned HTTP 400 `Invalid model` — corrected model name from `mistral-tts-latest` to `voxtral-mini-tts-2603`.
- **Fixed:** TTS API returns base64-encoded audio in a JSON `audio_data` field, not raw bytes — the response is now decoded correctly via `base64.b64decode()`.
- **Fixed:** Voice parameter renamed from `voice` to `voice_id` to match the Mistral API spec.
- **Updated:** Voice list replaced with actual Mistral TTS voices in `language_name_style` format (e.g. `gb_oliver_excited`). New default: `s3_rachel`. Added voices for EN-GB, EN-US, FR, DE, ES, NL, IT, PT.

---

### v0.3.1 — 2026-04-09
- **Fixed (HA 2026.4):** `TypeError: can only concatenate str (not "list") to str` — HA 2026.4 changed `chat_log.async_add_delta_content_stream` to expect the generator to yield plain types directly: `str` for text deltas, `llm.ToolInput` for completed tool calls. Our generator was still yielding wrapper dicts (`{"content": ..., "tool_calls": [...]}`), causing HA to attempt concatenating a list onto a string. Fixed `_async_stream_delta` to yield `str` and `llm.ToolInput` objects directly. Tool calls are still buffered until all arguments are streamed before being yielded.
- **Added:** Text-to-speech (TTS) platform using Mistral TTS (`mistral-tts-latest`) via `/v1/audio/speech`. Returns MP3 audio. Registers as a third separate HA device alongside Conversation and STT.
- **Added:** Six selectable TTS voices: nova (default), alloy, echo, fable, onyx, shimmer — all multilingual.
- **Added:** TTS voice selector in the integration options (Settings → Configure).

---

### v0.2.2.3 — 2026-03-05
- **Fixed:** `422 Unprocessable Entity` from Mistral API — HA tool parameters were being sent in HA's own intermediate list format `[{"type": "string", "name": "area", ...}]` instead of the OpenAI-compatible JSON Schema format Mistral requires (`{"type": "object", "properties": {...}, "required": [...]}`). Added `_ha_params_to_json_schema()` which performs the full conversion, including: `string/integer/float/boolean` primitives, `select` → `enum`, `multi_select` → array of enum, `list` → string array, `dict` → object. The `required` list is only populated for parameters that have `required: true` and no `optional: true`.

---

### v0.2.2.2 — 2026-03-05
- **Fixed:** `TypeError: Type is not JSON serializable: function` — voluptuous validators (`str`, `int`, `bool`, etc.) are Python callables and were ending up as values inside tool parameter schemas. Two-part fix:
  1. `_format_tool` now uses `voluptuous_serialize.convert()` with HA's `cv.custom_serializer` — the same approach used by HA's own OpenAI and Gemini integrations — to produce a proper JSON Schema dict from `tool.parameters`.
  2. `_sanitize` extended to handle non-serializable values (functions, types, voluptuous validators): anything that is not a JSON scalar, dict, or list is now converted to `repr(obj)` instead of being passed through, so a single unexpected value can never crash serialization.

---

### v0.2.2.1 — 2026-03-05
Community contributions merged with priority fix applied.

- **Fixed (priority):** `TypeError: Dict key must be a type serializable with OPT_NON_STR_KEYS` — root cause identified as voluptuous schema objects (`vol.Required`, `vol.Optional`) being used as dict keys in tool parameter schemas from HA's LLM API. A recursive `_sanitize()` helper now converts all dict keys to plain strings before any payload is passed to aiohttp. Applied to messages, tools, and all nested structures.
- **Fixed:** `_convert_chat_log_to_messages` now explicitly casts all `id`, `tool_name`, `content` values to `str`, and `tool_result`/`tool_args` dicts are also sanitized before `json.dumps`.
- **Added (community):** `MistralRuntimeData` dataclass in `__init__.py` — shared `aiohttp.ClientSession` and auth headers stored in `hass.data`, avoiding repeated header construction per request.
- **Added (community):** Re-authentication flow (`async_step_reauth`) — when the API key becomes invalid, HA now shows a re-auth notification instead of leaving the integration broken.
- **Added (community):** Native HA LLM API integration via `CONF_LLM_HASS_API` — replaces the custom `CONF_CONTROL_HA` approach. Device control now uses HA's standard `Assist` API, identical to how Google Gemini and OpenAI integrations work.
- **Added (community):** Streaming responses via `chat_log.async_add_delta_content_stream` — words appear progressively in the HA UI.
- **Added (community):** Tool-call loop (max 10 iterations) for multi-step HA device control commands.
- **Added (community):** Web search option (Beta) — uses Mistral's Agents/Conversations API. Requires `mistral-medium-latest` or `mistral-large-latest`.
- **Added (community):** STT now uses the shared runtime session from `hass.data` instead of creating a new client per request.
- **Kept:** `continue_conversation` (Experimental) — re-integrated into the new streaming architecture. Reads the final speech text from `ConversationResult` and sets `continue_conversation=True` when a `?` is detected.

---

### v0.2.2 — 2026-03-05
- **Fixed:** `TypeError: Dict key must be a type serializable with OPT_NON_STR_KEYS` — caused by a community contribution that passed HA `ChatLog` objects into the aiohttp JSON payload. The `_async_handle_message` method now intentionally ignores the `chat_log` argument and manages its own rolling history using `_make_message()`, which explicitly casts all keys and values to plain Python strings before serialization.
- **Fixed:** `service_data` keys returned by the model are also explicitly cast to `str` as an additional safeguard against non-string keys in nested payload structures.

---

### v0.2.1 — 2026-02-23
- **Fixed:** Service confirmation responses are now fully dynamic and language-aware. The AI generates the confirmation text itself (in whatever language the user is speaking) via a `"confirmation"` field in the JSON action payload. The hardcoded English `_SERVICE_PAST_TENSE` dictionary has been removed entirely.
- **Fixed:** `volume_set` service call was incorrectly blocked — added `volume_set`, `volume_mute`, `select_source`, `select_sound_mode`, `media_next_track`, `media_previous_track` to the media_player allowlist.
- **Fixed:** Service calls with extra parameters (e.g. `volume_level`, `temperature`) now work correctly via a `"service_data"` field in the JSON payload.
- **Improved:** Extended allowlist with `cover.set_cover_position`, `fan.set_percentage`, `fan.set_preset_mode`, `climate.set_temperature`, `climate.set_hvac_mode`, `input_boolean`, `input_number`, and `number` domains.

---

### v0.2.0 — 2026-02-23
**Breaking:** Removed Agent mode — integration now uses Model mode only.

- **Removed:** Agent mode and all Mistral Console agent configuration. All configuration is now done directly in Home Assistant.
- **Added:** `continue_conversation` option — when enabled, the assistant automatically keeps the microphone open after responses containing a question. Implemented natively via HA's `ConversationResult.continue_conversation` flag (no external automation required). Labelled *Experimental*.
- **Updated:** Model list — removed deprecated `ministral-7b-latest` and `open-codestral-mamba`. Added `ministral-8b-latest` (new default) and `ministral-3b-latest`. `ministral-8b-latest` is the recommended model for home automation: fast, cost-effective, and excellent at structured instruction-following.
- **Fixed:** All hardcoded Dutch strings in Python code replaced with English fallbacks. UI labels remain available in both English and Dutch via translation files.
- **Fixed:** Service confirmation messages no longer start with "Done!" / "Klaar!". Format is now e.g. *"Kitchen light has been turned off."*
- **Fixed:** Wrong GitHub URL in documentation corrected from `SnarfNL/mistral_conversation` to `SnarfNL/HA_MistralAI`.
- **Fixed:** Removed "(only in Model mode)" labels from all UI options since Agent mode no longer exists.
- **Optimised:** `_post_chat` error handling consolidated; `HomeAssistantError` and `aiohttp.ClientError` caught in a single handler. Error messages are now in English.
- **Optimised:** History trimming now preserves exactly the last 40 messages (20 turns) using a single slice operation.

---

### v0.1.8 — 2026-02-21
- **Added:** `icon.png` (128 px) and `icon@2x.png` (256 px) — Mistral M-logo on orange rounded-square background.
- **Added:** `images/` folder with 256 px and 512 px versions for submission to the home-assistant/brands repository.
- **Added:** Comprehensive `README.md` modelled after the BlaXun integration.
- **Fixed:** STT and conversation entities now have **separate `DeviceInfo`** with distinct `identifiers`, matching the pattern used by the Google Gemini integration.
- **Fixed:** `MistralSTTEntity` was missing `DeviceInfo` entirely — caused WebSocket handler errors (`Received binary message for non-existing handler`).
- **Fixed:** PCM-to-WAV wrapping now always applied regardless of `metadata.format`, fixing 400 errors on the Voxtral endpoint.
- **Fixed:** Full HTTP response body now logged on any 4xx/5xx from the chat API, making debugging possible.

---

### v0.1.7 — 2026-02-21
- **Fixed:** STT 400 error: HA always delivers raw PCM bytes; the WAV wrapper was incorrectly skipped when `metadata.format == WAV`.
- **Fixed:** Conversation 400 error: error response body was silently discarded; now logged at ERROR level.
- **Fixed:** `HomeAssistantError` raised inside `_post_chat` was not caught by the `aiohttp.ClientError` handler — added combined except clause.
- **Fixed:** `DeviceInfo` added to `MistralSTTEntity` to allow correct HA device registration.

---

### v0.1.6 — 2026-02-21
- **Added:** Speech-to-text (STT) platform using Mistral's **Voxtral Mini** (`voxtral-mini-latest`).
- **Added:** Agent mode — use a pre-configured agent from Mistral Console via `agent_id`.
- **Added:** STT language selector (dropdown with 60+ languages + Auto-detect).
- **Changed:** Conversation and STT entities registered as separate HA devices.

---

### v0.1.5 — 2026-02-21
- **Added:** `icon.png` and `icon@2x.png` in the component directory.
- **Added:** Full `README.md` with installation guide, option descriptions, automation examples and FAQ.

---

### v0.1.4 — 2026-02-21
- **Fixed:** Mistral API rejects `temperature` values above 1.0 — clamped to `0.0–1.0`.
- **Fixed:** Removed `top_p` from API payload (cannot be sent together with `temperature`).
- **Added:** `ConversationEntityFeature.CONTROL` to enable device control.
- **Improved:** JSON extraction from AI response now handles markdown code fences.

---

### v0.1.3 — 2026-02-21
- **Fixed:** `MistralOptionsFlow.__init__` tried to set `self.config_entry` which is a read-only property in HA 2024.x — removed `__init__`.
- **Added:** `_async_handle_message` (HA 2024.6+ API) with `async_process` fallback for older versions.

---

### v0.1.2 — 2026-02-21
- **Fixed:** Conversation agent did not appear in the Voice Assistants dropdown because entities were registered directly instead of via the `conversation` platform.
- **Changed:** Switched to `async_forward_entry_setups` with `PLATFORMS = ["conversation"]`.

---

### v0.1.1 — 2026-02-21
- **Fixed:** 500 error in config flow caused by incorrect OptionsFlow structure.
- **Changed:** Deprecated `conversation.async_set_agent()` replaced by proper platform setup.

---

### v0.1.0 — 2026-02-21
- Initial release.
- Mistral AI selectable as conversation agent in HA Assist.
- Configurable model, system prompt, temperature and max tokens via the UI.
- Home Assistant device control via spoken commands.
- Conversation history per session.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<div align="center">
  Made with ❤️ for the Home Assistant community<br>
  Inspired by the work of <a href="https://github.com/BlaXun/home_assistant_mistral_ai">BlaXun</a>
</div>
