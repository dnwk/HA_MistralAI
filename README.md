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
   - [Reasoning effort](#reasoning-effort)
   - [System prompt](#system-prompt)
   - [Continue conversation (Experimental)](#continue-conversation-experimental)
   - [Web search (Beta)](#web-search-beta)
   - [Mistral connectors](#mistral-connectors)
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
| Mistral connectors | ✅ | The connectors (MCP servers) in your Mistral account are available to the assistant |
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
| **Reasoning effort** | Default (not set) | How much a reasoning model thinks before answering: None, Low, Medium or High — see [Reasoning effort](#reasoning-effort) |
| **Control HA** | On | Allow the AI to control exposed devices |
| **Continue conversation** | Off | Keep listening after questions (Experimental) |
| **Web search** | Off | Allow the AI to search the web (Beta) |
| **Web search routing** | `Let the model decide` | How web search is triggered — see below |
| **Web search trigger phrases** | *(empty)* | Optional phrases that force a web search — see below |
| **Use my Mistral connectors** | On | Offer the connectors in your Mistral account as tools — see [Mistral connectors](#mistral-connectors) |
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
>
> **Reasoning models:** in November 2026 `mistral-large-latest` started answering like Mistral's reasoning models (Mistral Large 4), which think before they answer. That makes replies slower; see [Reasoning effort](#reasoning-effort).

### Reasoning effort

Mistral's reasoning models (Mistral Large 4, Medium 3.5 and Small 4) think before they answer. The thinking is never spoken: it is kept apart from the reply and shown separately in the Assist debug view (Settings → Voice assistants → ⋮ → Debug). On Home Assistant versions without a place for it in the chat log, it is dropped.

Thinking takes time. On one live news question with `mistral-large-latest`, it was about 2 seconds before deciding to search, then about 5 seconds before answering, on top of the search itself. **Reasoning effort** sets how much the model thinks:

| Setting | Accepted by | Effect |
|---|---|---|
| **Default** | every model | Nothing is sent; Mistral's default applies |
| **None** | Medium 3.5, Small 4 | Minimal thinking, no thinking in the response |
| **Low** | Large 4 | The least thinking Large 4 allows (it doesn't accept None) |
| **Medium** | Large 4 | In between |
| **High** | Large 4, Medium 3.5, Small 4 | Most thorough, slowest; Mistral's recommendation for agentic and code tasks |

For a voice assistant on `mistral-large-latest`, **Low** is the fastest choice. The setting applies to every text request the integration makes: replies, web searches, connector requests and AI tasks. If a model doesn't accept the chosen level, or doesn't reason at all, Mistral rejects the request; it is then sent again without the setting, and the setting is left out for that model until Home Assistant restarts, with one warning in the log.

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

**Example: a home and information assistant.** The default prompt asks for concise answers everywhere, which turns information questions into one-liners (a request for news headlines came back as a single headline). This prompt keeps device confirmations short but gives complete answers to news, markets and other questions:

```jinja2
You are the voice assistant for the smart home called {{ ha_name }}. You have two jobs: you control and report on the home, and you answer questions about the wider world.

Today is {{ now().strftime('%A, %B %d, %Y') }} and the time is {{ now().strftime('%H:%M') }}.

How you speak:
Reply in the language the user speaks. Everything you say is read aloud by text-to-speech, so use plain spoken sentences only: no markdown, lists, bullet points, emojis, headings, links or web addresses. Say numbers the way a person would: round sensibly ("about six thousand nine hundred points", "up one point three percent") and say units in full ("21 degrees", "15 minutes"). Be warm and natural, but don't pad your answers.

Controlling and checking the home:
For clear commands, act right away and confirm in one short sentence, for example "The living room lights are on." Use the home's live data for any question about devices, rooms, sensors or the weather at home. If a command is ambiguous, for example several devices match or the room is unclear, ask one short question instead of guessing. If a request would unlock a door, open the garage or disarm an alarm and it wasn't clearly asked for, check first.

Answering questions:
For news, sports, prices, markets, travel, opening hours, weather elsewhere, or anything else that changes over time, look it up with your tools (web search and the user's connected services) instead of relying on memory. Give a complete answer, not just one fact. For news, give the top three to five headlines, one short sentence each, and say which outlet they come from. For prices and markets, give the figure, the change and when it applies, and say exactly what the figure is; for example, an index level is not the same as a fund's share price. For general knowledge you are confident about, answer directly without searching. Keep information answers to about three to six sentences. If you are unsure or the information may be out of date, say so briefly. Never invent facts, figures or headlines. Always finish with a complete sentence.

Offering more:
End a news or information answer with one short closing sentence that wraps up, followed by a short question offering more, such as "Want more on any of these?" Confirmations of device commands don't need a question. Only end with a question when you want an answer, because a question keeps the microphone listening.

Ending the conversation:
If the user says they don't need anything more, for example "no thanks", "no", "that's all", "I'm good", "that's enough" or "stop", reply with a short goodbye such as "Okay, enjoy your evening." with no question at all. After that, don't offer more for the rest of this conversation: if they ask something new, answer it and end with a closing sentence, not a question.
```

Every information answer ends with a short wrap-up and an offer such as "Want more on any of these?". Because it ends in a question, the satellite keeps listening for your answer when *Continue conversation* is on — see below. The offer is unconditional on purpose: phrased as "if there is clearly more to say", the model often left it out and the answer stopped after the last fact.

Saying you're done ("no thanks", "that's all") gets a goodbye without a question, so the satellite stops listening, and no more offers for the rest of that conversation. A new wake word starts a new conversation, where offers resume.

### Continue conversation (Experimental)

When enabled, the assistant automatically keeps the microphone open after any response that contains a question (`?`). This is implemented using the native `continue_conversation` flag in HA's `ConversationResult` — no separate automation is needed. Together with a prompt that ends information answers with a short offer (see the example above), you can answer "yes" or ask a follow-up without the wake word.

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

### Mistral connectors

A *connector* is an MCP server registered in your Mistral account (in Mistral Studio or through Mistral's Connectors API) — for example a calendar, mail, wiki or your own MCP server. With **Use my Mistral connectors** on (the default), every usable connector in the account is offered to the assistant as a tool, so you can ask things like "what's on my calendar today?" by voice.

How it works:

1. The integration reads your connector list (`GET /v1/connectors`) on the first conversation turn and then every 10 minutes, so a newly added connector shows up without a restart. Connectors that are not connected/authenticated or are blocked are skipped.
2. Each connector becomes a tool named `connector_<name>`, described with the connector's title, description and tool names. The model decides when to use it, like web search.
3. When it does, the integration sends your request to Mistral's Conversations API with that connector attached (`store: false`). **Mistral runs the connector's tools** and returns an answer; nothing runs inside Home Assistant.
4. The answer goes back to the model as untrusted data, and all tools are withdrawn for the rest of that turn (the same rule as web search), so text inside a mail or document cannot trigger a device action.
5. If the connector's answer was based on **sources** (links), they are shown in Home Assistant — see [Connector sources](#connector-sources).

#### Connector sources

Some services (Google Maps among them) require their sources to be shown, and for voice assistants Google requires a screen with a verbatim record of the conversation. When a connector answer comes with source links, the integration adds the turn to a **Mistral AI — connector sources** notification (Home Assistant's 🔔 Notifications):

- what you said and the assistant's reply, **verbatim**, followed directly by the **source links** (titles as the service returned them);
- the disclosure *"AI-generated content might include information from Google Maps."* whenever a Google Maps link is among the sources, and a general one otherwise;
- newest first, the last 20 such turns. The record is saved in Home Assistant's storage, so it survives restarts; dismissing the notification only hides it until the next sourced answer.

Each new entry is also fired as a `mistral_conversation_connector_sources` event (`time`, `question`, `answer`, `sources` with `connector`, `title`, `url`) for your own dashboards or automations.

Sources come from Mistral's citation chunks (`tool_reference`) and, as a fallback, from `SOURCE: <title> | <url>` lines the connector request asks the model to add (they are removed from the spoken answer). Whether a connector returns links depends on the service; turns without sources are not recorded. The connector option's help text in **Configure** carries the same disclosure.

Requirements and limits:

- **Which connectors are visible** depends on your API key's *Connector access* scope. The default scope only covers connectors shared with your workspace; to use your **private** connectors, create the key with the *Private and shared connectors* scope.
- **Connect OAuth connectors in Mistral Studio first.** Mistral's API cannot pass OAuth tokens, so a connector that needs a login must be connected there.
- **Chat model:** connectors run on the Conversations API. If your chat model is Mistral Small, Medium or Large, it runs the connector too; with a Ministral model, connector requests run on `mistral-small-latest` instead, so connectors work whichever chat model you pick.
- **Actions happen without a confirmation step.** A connector that can act (send a message, create an event) does so when the assistant asks it to; confirmation prompts can't be answered by voice. Only connect services you are happy to use by voice, and turn the option off if needed.
- Up to 3 connector calls are run per model round; each may take up to 60 s.
- Connectors are in Mistral's Public Preview, so the API may change.
- Connectors you set up in Le Chat appear only if Mistral's API lists them for your key; Mistral's docs describe Studio/API connectors.

#### Testing and troubleshooting connectors

Test connectors in Home Assistant itself — your API key stays there:

1. Update the integration (HACS) and **fully restart** Home Assistant.
2. Check that **Use my Mistral connectors** is on under **Configure** (it is on by default).
3. Ask the assistant something one of your connectors can answer, for example *"what's on my calendar today?"*.

If nothing seems to happen, turn on debug logging for the integration — from the integration's ⋮ menu → **Enable debug logging**, or in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.mistral_conversation: debug
```

Then look for these lines in **Settings → System → Logs**:

| Log line | Level | Meaning |
|---|---|---|
| `Mistral connectors available: gmail, calendar` | debug | The connectors offered to the assistant. `none` means the API key sees no usable connector — check its *Private and shared connectors* scope, and that the connectors are connected in Mistral Studio. |
| `Skipping connector …: not connected/authenticated` / `…: blocked by …` | debug | A connector Mistral reports as unusable; connect or unblock it in Mistral Studio. |
| `Calling Mistral connector <name> (model …): <request>` | debug | The model chose a connector; shows the request and which model ran it. |
| `Could not read the Mistral connector list …` | warning (once) | The connector list request failed; it is retried every minute and the last good list is kept. |
| `Mistral connector <name> failed: HTTP …` | warning | Mistral rejected or failed a connector call; the message includes Mistral's reason. |

Turn debug logging off again afterwards: the `Calling Mistral connector` line contains your request text.

#### Suggested connectors

Mistral runs connectors from its own cloud, so a connector must be a **remote** MCP server — a public HTTP URL. Local MCP servers that run as a program on your computer won't work unless you host them publicly. The list below only includes servers **run by the service's own vendor** (checked November 2026); community wrappers of someone else's API are left out because they come and go. None of these has been tried with this integration yet.

Mistral Studio can connect three kinds of server: **no login**, **API key** (sent as a header, for example `Authorization: Bearer …`), and **OAuth** (Studio asks for an OAuth client ID and secret).

**No setup needed — good first tests**

| Server | What you can ask | URL | Changes things? |
|---|---|---|---|
| **[Kiwi.com](https://www.kiwi.com/ag/pages/mcp/)** flight search | *"Cheapest flight to Lisbon next weekend?"* | `https://mcp.kiwi.com` | no (search; booking is a link) |
| **Exa** search | Web questions; works with a Ministral chat model too, unlike *Web search* | `https://mcp.exa.ai/mcp` | no — free with rate limits; add an Exa API key in an `x-api-key` header for more |
| **AfterShip** package tracking | *"Where is my parcel 1Z…?"* | `https://mcp.aftership.com/tracking/public` | no — free for personal use, rate-limited; endpoint found in a directory listing, not yet on AfterShip's own docs |

**API key**

| Server | What you can ask | URL | Key |
|---|---|---|---|
| **[AccuWeather](https://developer.accuweather.com/documentation/weather-mcp-client-connection)** | Forecasts and conditions anywhere, beyond your home weather entity | `https://dataservice.accuweather.com/mcp` | AccuWeather API key in the `Authorization` header |
| **[Xweather](https://www.xweather.com/blog/introducing-the-xweather-mcp-server)** | Forecasts, alerts, radar-type data | `https://mcp.api.xweather.com/mcp` | existing Xweather API credentials (paid) |
| **[Google Maps](https://developers.google.com/maps/ai/grounding-lite)** — *Maps Experience agent tools*, formerly Grounding Lite | Places, routes and travel times, weather anywhere: *"how long to drive to the airport?"* | `https://mapstools.googleapis.com/mcp` | Google Maps API key in the `X-Goog-Api-Key` header — see [Setting up Google Maps](#setting-up-google-maps) |
| **[Tavily](https://docs.tavily.com/documentation/mcp)** search | Web questions | `https://mcp.tavily.com/mcp/` | Tavily API key (in the URL as `?tavilyApiKey=…`) or OAuth |

**OAuth — lists, notes, calendar, mail**

| Server | What you can ask | URL | Changes things? |
|---|---|---|---|
| **Todoist** (by Doist) | *"Add batteries to my shopping list"*, *"what's due today?"* | `https://ai.todoist.net/mcp` | **yes** — adds and completes tasks |
| **Notion** | Household notes, recipes, lists, databases | `https://mcp.notion.com/mcp` | **yes** — creates and edits pages |
| **[Google Calendar](https://developers.google.com/workspace/calendar/api/guides/configure-mcp-server)** | *"What's on tomorrow?"* | `https://calendarmcp.googleapis.com/mcp/v1` | **yes** — creates, updates, deletes events |
| **[Gmail](https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server)** | *"Any mail from the school today?"* | `https://gmailmcp.googleapis.com/mcp/v1` | **yes** — drafts at least |
| **[Google Drive](https://developers.google.com/workspace/drive/api/guides/configure-mcp-server)** | Find and read household documents | `https://drivemcp.googleapis.com/mcp/v1` | **yes** with write scopes; ask for `drive.readonly` |

Google's servers are in Developer Preview and need a Google Cloud project with the matching *… MCP API* enabled (separately from the normal API) and an OAuth client whose ID and secret you enter in Mistral Studio. Notion and Todoist register their own OAuth client; if Studio still asks for an ID and secret, follow its prompts.

**One connector for many apps**

- **[Zapier MCP](https://docs.zapier.com/mcp/get-started/quickstart)** — create a server at mcp.zapier.com, pick exactly which actions it exposes (for example *add to Google Tasks*, *play on Spotify*, *send me an SMS*), and use the server URL it generates as the connector URL. Treat that URL as a password. Choosing actions there is also the easiest way to keep write actions out today. Each call uses 2 Zapier tasks.
- **[Pipedream MCP](https://pipedream.com/docs/connect/mcp/developers)** — thousands of apps behind `https://remote.mcp.pipedream.net/v3`, but it needs a Pipedream project, OAuth client credentials and per-user headers; aimed at developers, and in beta.

#### Setting up Google Maps

Google's MCP server for Maps is called **Maps Experience agent tools** (formerly *Maps Grounding Lite*). Its tools: `search_places` (places with AI summaries and Maps links), `compute_routes` (distance and travel time — no turn-by-turn directions), `search_along_route`, `lookup_weather` (current conditions, forecasts up to 10 days, air quality), `resolve_names` and `resolve_maps_urls`.

**Check Google's terms first.** The [product page](https://developers.google.com/maps/ai/grounding-lite) sets rules that matter for a voice assistant on Mistral:

- **No training on the data.** The tools may not be used "with any models that use the data input into the model for any model training or improvement". On Mistral's free *Experiment* plan, API requests may be used for training unless you opt out: Mistral Admin Console → **Privacy** → turn off the *Anonymous improvement data* toggle ([Mistral help](https://help.mistral.ai/en/articles/455207-can-i-opt-out-of-my-input-or-output-data-being-used-for-training)). Scale plans are opted out by default.
- **Sources and disclosure for voice.** For voice interfaces Google requires a companion UI that shows "a verbatim historical record of any AI voice conversation" with the Google Maps sources immediately after the content they support, and a disclosure that answers might include information from Google Maps. The integration provides this as the [connector sources](#connector-sources) notification, with Google's disclosure wording, plus the same disclosure in the connector option's help text. It depends on Mistral passing Google's links back (as citations or `SOURCE:` lines); after your first Maps questions, check that the notification shows them. The [Google Maps Platform Terms](https://cloud.google.com/maps-platform/terms) remain yours to check.
- **No caching or storing** of Google Maps content by the LLM. Connector calls are sent with `store: false`.

**Cost.** Each tool call is one request. The first 10,000 requests a month are free, then $7 per 1,000 (*Essentials*); *Pro* options such as more than 5 results, live traffic or pollen cost $14 per 1,000 after 5,000 free. Quota: 300 requests per minute per project. A household voice assistant normally stays well inside the free tier.

**In Google Cloud (about 10 minutes):**

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create or pick a project.
2. **Enable billing** for it (**Billing** → link a billing account). Google asks for a card even when usage stays free.
3. **Enable the API:** **APIs & Services → Library**, search *Maps Experience agent tools* (service `mapstools.googleapis.com`) → **Enable**. With the gcloud CLI: `gcloud services enable mapstools.googleapis.com --project=PROJECT_ID`.
4. **Create the key:** **Google Maps Platform → Keys & Credentials → Create credentials → API key**, then open it:
   - **API restrictions → Restrict key** → select only *Maps Experience agent tools*. The API must be enabled on both the project and the key.
   - **Application restrictions:** leave *None*. Mistral's cloud calls Google from addresses you can't list, so an IP restriction would block it; the API restriction and a budget alert are the protection.
5. **Add a budget alert:** **Billing → Budgets & alerts → Create budget** (for example 5 in your currency), so unexpected use is noticed.

**In Mistral:**

6. On the *Experiment* plan, turn off training on your data (see above).
7. **Create the connector with the key as a header.** Studio's API-key option sends `Authorization: Bearer …`, which Google doesn't accept — Google wants `X-Goog-Api-Key`. If Studio's connector form lets you add a custom header with that name, use it. Otherwise run the helper script in this repository on your own computer:

   ```bash
   python scripts/create_mistral_connector.py --preset google-maps
   ```

   It asks for your Google Maps key and Mistral API key with hidden input, shows what it will create, creates a **private** connector named `google_maps` with the Google key stored as an encrypted connector-wide header (Mistral's `global_headers`, "never returned in clear"), connects it and lists its tools. Use `--visibility shared_workspace` to share it with your workspace instead. The keys are never printed or saved.
8. The API key Home Assistant uses needs the *Private and shared connectors* scope to see a private connector.

**In Home Assistant:** within 10 minutes (or after reloading the integration), the debug log shows `Mistral connectors available: … google_maps`. Ask *"how long does it take to drive to the airport?"* or *"is there a pharmacy open near me?"* — for "near me", say your town or address, because the connector doesn't know where your home is.

**Looked at but not listed:** Instacart's MCP server needs a partner agreement; Microsoft's official Outlook mail/calendar servers need a Microsoft 365 Copilot business tenant; Tesla/Tessie and 17TRACK servers found were community-built.

**Before you add one:**

- **Check what Home Assistant already covers.** Your weather entity answers weather at home, and calendar or to-do entities exposed to Assist are answered by Home Assistant directly, without sending the data through Mistral. Connectors add the most where Home Assistant has nothing: travel, parcels, mail, notes.
- **Write tools act without confirmation.** Todoist, Notion, Calendar, Gmail and Drive can change things, a voice assistant can mishear, and the integration offers all of a connector's tools. Use read-only scopes where the service offers them, or a Zapier server limited to the actions you want.
- Previews and free tiers change; Mistral's [connector troubleshooting article](https://help.mistral.ai/en/articles/457412-how-do-i-fix-mcp-connector-connection-errors) covers common connection errors.
- Connectors you already connected in Le Chat (its directory has 60+ vendor integrations) appear only if Mistral's API lists them for your key — check the debug log.

**Finding more:** prefer a vendor's own developer docs ("MCP server" in their API documentation) and [Mistral's Le Chat connector directory](https://docs.mistral.ai/le-chat/knowledge-integrations/connectors/mcp-connectors). [free-remote-mcp-servers](https://github.com/shortformkit/free-remote-mcp-servers) lists keyless remote servers and re-tests them weekly, but most are community-run; check who operates a server before giving it access to your accounts.

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

> **Pace and emotion need a Voxtral TTS 3 model.** Mistral documents these tags with Voxtral TTS 3 (`voxtral-mini-tts-3-0`). Older models read them aloud — `voxtral-mini-tts-latest` (the default) was heard saying "pace equals fast". So pace and emotion are only sent when the **Text-to-speech model** is Voxtral TTS 3 or later; with any other model they are left out and the log says so once. To use them, pick `voxtral-mini-tts-3-0` (or a later version) under **Text-to-speech model**. Expressiveness and the volume boost don't depend on the model. Older presets such as `en_paul_angry` carry their emotion in the voice itself, so an emotion tag has little effect on them. For volume, see [Volume boost](#volume-boost) below.

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

**Q: The assistant doesn't use my Mistral connectors.**
A: Turn on debug logging and look for `Mistral connectors available: …` — see [Testing and troubleshooting connectors](#testing-and-troubleshooting-connectors). The usual causes are an API key without the *Private and shared connectors* scope (it then only sees connectors shared with your workspace), a connector that isn't connected in Mistral Studio yet, or the *Use my Mistral connectors* option being off.

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
- **Speech style uses Mistral's tags, and is off until you set it.** Mistral's speech API has no speed, pitch or volume fields, so pace and emotion are sent as inline tags (`[emotion=calm][pace=slow]`) and expressiveness as a request field. Every control defaults to *not set* and sends nothing — "Default" is not even stored. Pace and emotion tags are additionally only sent when the TTS model ID names Voxtral TTS 3 or later (`…-tts-3`, `…-tts-3-0`): older models speak the tags as text, as `voxtral-mini-tts-latest` did on a live install ("pace equals fast"). An alias like `-latest` or a dated ID like `-tts-2603` doesn't reveal the version, so it is treated as not supporting tags; the rule accepts only one- or two-digit versions so that a date is never mistaken for one. When tags are left out, the log says so once per TTS entity. `expressiveness` appears in Mistral's TTS guide but not in its API reference, which is another reason it is only sent when set. Only the values Mistral documents are sent: an unknown tag is accepted by the API but does nothing, so typos are logged and dropped instead. Each streamed sentence is its own request, so the tags are added to every sentence. Pitch is not offered: Mistral has no field for it and changing it locally would need real signal processing. The style is returned in the TTS entity's default options so Home Assistant's TTS cache does not replay audio made with an old setting, and `tts.speak` can override each control per call.
- **Volume is the one thing processed locally, and only upward.** A too-quiet voice can't be fixed from the media player without making everything else too loud, so the *Volume boost* scales the 16-bit PCM inside Home Assistant (standard library only, no `audioop` or numpy). It only boosts (0 to +12 dB): turning speech down is what the media player volume already does well. It uses a static soft clipper rather than a leveller — simple and never hard-clipping, but loud parts get squashed at high settings; at +12 dB everything above about half of full volume reaches the maximum, so +3 to +6 dB is the recommended range. The boost needs raw audio, so `tts.speak` returns WAV instead of MP3 while it is on. The 65,536-entry lookup table is built in an executor, not on the event loop. It is part of the same default options as the speech style, so changing it refreshes cached audio and `volume_boost` can be overridden per call.
- **Streamed answers end with half a second of silence.** Mistral's audio stops exactly on the last sound of the last word, and many satellites and speakers drop the final fraction of a second of a stream, so answers sounded cut off. The integration already adds 300 ms between sentences; it now also adds 500 ms after the last one, sized from the audio format. Batch mode (one MP3) is unchanged, because padding an MP3 would mean re-encoding it.
- **Web search asks again when Mistral returns no answer, and leaves today's date out.** News questions were answered "I can't fetch the news right now". The first suspect was the query: with today's date in the system prompt, the chat model wrote searches like "top news headlines November 11 2026". So the search tool asks the model not to add today's date, and the search instructions say to fall back to the most recent relevant results and say when they are from. That alone did not fix it. The debug log then showed what actually happened: Mistral ran the search, but its reply held only the search step (`tool.execution`) and no answer message, so there was no text to pass on. Mistral's docs don't say when this happens. The integration now asks once more in the same Mistral conversation, which still holds the search results ("Now answer my question from what your search found…"). It retries only once, so a persistent failure costs one extra request, not a loop. The model also kept adding the date despite the tool description, so the code now removes today's date from the queries the model writes. It is kept when you mentioned a date yourself (any digit, or the month's name), and only English month names and numeric dates are recognised. In the first live test after this change, the date was removed and Mistral answered on the first request, so a query pinned to today's date appears to be what made Mistral skip its answer; the retry stays as a safety net. The debug log shows each search reply's entry types and what the search step returned; an empty answer is still logged as a warning.
- **A reasoning model's thinking is kept out of the reply, and its effort is a setting.** In November 2026 `mistral-large-latest` started streaming its reasoning: Mistral's reasoning models send `delta.content` as a list of `thinking` chunks while they think and as a plain string once they answer. The stream parser converted whatever arrived to text, so a news answer became 16,576 characters of `[{'type': 'thinking', …}]` that the satellite read aloud, after 37 seconds. Only text chunks are now the reply. The reasoning goes into Home Assistant's `thinking_content`, which the debug view shows and the voice pipeline never speaks; where Home Assistant has no such field, it is dropped. It is not sent back to Mistral on later turns, although Mistral recommends replaying it for quality: one conversation can involve several models (connector requests fall back to `mistral-small-latest`, and the chat model can be changed), and Mistral doesn't say whether a model that doesn't reason accepts thinking chunks in its history. The *Reasoning effort* option exists because thinking costs seconds on every voice reply. It is not set by default, so nothing changes until you choose a level. Accepted levels differ by model (Large 4: low/medium/high; Small 4 and Medium 3.5: none/high), and an alias such as `mistral-large-latest` can move to another model at any time. So a request whose effort Mistral rejects (HTTP 400/422 naming `reasoning_effort`) is sent once more without it, and the effort is left out for that model until restart: a wrong level costs one extra request and a warning, never a failed reply. The same effort is sent on replies, web searches (in `completion_args`), connector requests and AI tasks.
- **Tool results are read from `result.data`, with a fallback for older Home Assistant.** Home Assistant 2026.11 keeps a tool's outcome as an `llm.ToolResult` (`data` plus an `error` flag) and deprecates the old `tool_result`, which logs a warning on every use and stops working in 2027.11. The integration sends the model the `data`, as `tool_result` used to give it, and adds `"error": true` to a failed tool's data when the data doesn't already describe the error; Home Assistant versions without `result` still use `tool_result`. Whatever the result holds, it is made JSON-safe before sending, so an unexpected type can't fail the turn again.
- **Declining an offer ends it, through the prompt.** The example prompt's unconditional "Want more…?" kept coming back after the user had said "no thanks". The prompt now says to answer a decline with a goodbye that has no question, and not to offer more for the rest of that conversation. It is a prompt rule, not code: *Continue conversation* keeps listening whenever the reply contains "?", so a goodbye without one closes the microphone, and the model sees the earlier turns of the conversation, so it knows an offer was declined. Offers resume in a new conversation (a new wake word), so declining once doesn't switch them off for good. If the model still slips in a question, the fallback is a code change: remember the decline per conversation and stop continuing it whatever the reply says.
- **Web search results are treated as untrusted.** On the round where the model reads search results, every tool is withdrawn, not just web search, so instructions hidden in a web page cannot trigger a device action. Device control still works on the round where the model decides to search.
- **Mistral connectors are offered as tools, run by Mistral, and treated like web search.** Home Assistant's chat-completions call can't take connectors (Mistral only supports them on its Conversations and Agents APIs), and rewriting every turn onto the Conversations API would mean a new streaming and tool-call loop. So, like web search, each connector is a synthetic function on the normal turn, and a call is serviced by a separate stateless Conversations request (`store: false`, no stored agent) with only that connector attached; Mistral executes the MCP tools server-side. Decisions taken with it: **all** usable connectors on the account are offered and the option is **on by default**, because the goal is that every connector you set up is available by voice — nothing changes on an account without connectors; connectors reported as not authenticated or blocked are skipped, and ones with unknown status are offered; one tool per connector (named `connector_<name>`, never shadowing a Home Assistant tool) so the model can pick by description; the connector request gets fixed, generic instructions and only the request text the model wrote — no entity list or system prompt; results are fenced as untrusted and all tools are withdrawn for the rest of the turn, so a mail or document can't steer device control; a Ministral chat model hands connector calls to `mistral-small-latest`, because Mistral documents connectors only with its Small/Medium/Large models; no confirmation step, because it can't be answered by voice — a pending confirmation is reported as "nothing was done"; every tool of a connector is offered, including tools that change things (a per-connector setting to leave out write tools was considered and deferred for now — the README's *Suggested connectors* marks which ones can make changes, and the option can be switched off); the list is cached for 10 minutes (1 minute after a failed read, keeping the last good list) to avoid a request on every turn.
- **Your Mistral API key is never handled outside Home Assistant.** Testing against a live account is done in Home Assistant itself or with a script that reads the key from your own terminal; the key is not pasted into chats or files.
- **Header-based connectors are created with a helper script.** Mistral Studio's API-key option only sends `Authorization: Bearer`, but some servers want another header (Google Maps: `X-Goog-Api-Key`). Mistral's Connectors API accepts any header as an encrypted connector-wide `global_headers` entry, so `scripts/create_mistral_connector.py` creates the connector that way, connects it with empty credentials and lists its tools. It runs on your own computer, asks for keys with hidden input and never prints or saves them; it shows the request and asks before creating anything. It defaults to a *private* connector.
- **Google Maps is documented with its terms, not just its setup.** Google's terms for Maps Experience agent tools forbid models that train on the input and require a companion UI with sources for voice use. The README states that Mistral's Experiment plan needs the training opt-out, rather than presenting the setup as complete.
- **Connector sources are shown in a persistent notification.** To meet source-display rules such as Google's for voice ("a companion UI that shows a verbatim historical record", sources "immediately" after the content they support, "viewable within one user interaction"), the companion UI is a Home Assistant persistent notification: always one tap away in the sidebar, needs no dashboard setup, and renders links. It holds the question and the spoken reply verbatim, then the links, newest first, last 20 turns; it is backed by `.storage` because notifications themselves don't survive a restart. Google's disclosure sentence is used verbatim and untranslated, as its terms require, and only when a Google Maps link is present. Sources are taken from Mistral's `tool_reference` citations and, because it isn't documented whether connector answers carry those, from `SOURCE:` lines the connector model is asked to append; those lines are stripped from what is spoken. Only turns with sources are recorded, to keep the notification meaningful. An event is fired as well for anyone who wants a dashboard instead. Recording never breaks a reply: a failure is logged and the answer is still spoken.
- **Web search uses no stored agent, and asks for complete answers.** Searches used to go through an "HA Mistral Web Search" agent stored in your Mistral account. Its instructions were fixed when it was created ("reply factually and concisely"), so they couldn't be improved from the code, and they turned information questions into one-liners. Each search now starts a Conversations request with the model, the instructions and the `web_search` tool in the request itself, like connectors — so a wording change applies at once and nothing new is stored as an agent. The instructions stay generic (never your rendered system prompt, which can contain your exposed entities and areas) and ask for a complete answer: three to five headlines for news, the figure, change, date and what the figure measures for markets. The search result goes to the chat model, which shapes the final reply to your own prompt; the prompt that hands the result over asks for a full answer in that style instead of a "direct" one. Follow-ups in the same conversation still continue the same Mistral conversation. The old agent is not deleted automatically; you can remove it in Mistral Studio.
- **Upstream changes are ported selectively.** This fork is based on [SnarfNL/HA_MistralAI](https://github.com/SnarfNL/HA_MistralAI) and takes individual changes rather than merging it wholesale. Each ported change is marked *ported from upstream* in the release notes. Taken so far: the Home Assistant 2026.9 tool-schema fix (including AI Task `multiple` fields), the streaming-TTS WAV header fix, the chat model list update, and the volume boost. The volume boost was taken while it was still a draft upstream because it answered a real need here (Mistral's voice being too quiet); this fork added the TTS cache key, the per-call override and building the lookup table off the event loop. Not taken: upstream's removal of the *Text-to-speech voice* option (kept here as the searchable fallback voice) and its pinned `voxtral-mini-tts-2603` TTS model (this fork uses `voxtral-mini-tts-latest`). Upstream's tests depend on its real-Home-Assistant test setup, so ported changes get tests written for this fork's own test stubs.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Release Notes

### Unreleased
- **Fixed:** with a reasoning model, such as `mistral-large-latest` since November 2026, the model's thinking was read aloud as raw text (`[{'type': 'thinking', …}]`) before the answer. Only the answer is spoken now; the thinking appears separately in the Assist debug view. AI tasks had the same problem and are fixed too.
- **Added:** *Reasoning effort* option (Default, None, Low, Medium, High) for Mistral's reasoning models: less thinking means faster replies. It applies to replies, web searches, connector requests and AI tasks. A level the model doesn't accept is dropped for that model with one warning, so the request still succeeds. See [Reasoning effort](#reasoning-effort).
- **Fixed:** Home Assistant's warning that the integration uses the deprecated `ToolResultContent.tool_result`. The first attempt broke every turn in which the model used a Home Assistant tool, such as a weather forecast, on Home Assistant 2026.11 ("Unexpected error during intent recognition"; in the log, "Object of type ToolResult is not JSON serializable"). There, `result` is a `ToolResult` object, not the data itself. The tool's data is now read from it, with failed tools marked as errors.
- **Changed:** the README's example prompt answers "no thanks" or "that's all" with a goodbye that has no question, so the satellite stops listening, and stops offering more for the rest of that conversation.
- **Fixed:** news questions answered "I can't fetch the news right now". Mistral sometimes ran the search but returned only the search step and no answer message; the integration now asks for the answer once more in the same Mistral conversation. Today's date is removed from the search queries the model writes, unless you mentioned a date. Searches fall back to the most recent results and say when they are from. Empty search answers are logged as a warning; the debug log shows each search answer and what the search step returned.
- **Fixed:** streamed answers no longer sound cut off at the end: half a second of silence follows the last sentence, so players that drop the tail of a stream don't clip the last word.
- **Changed:** the README's example prompt always ends information answers with a wrap-up and an offer of more, so the satellite keeps listening for a follow-up.
- **Changed:** web search no longer uses an agent stored in your Mistral account. Each search sends its instructions with the request, and those now ask for a complete answer (for news, three to five headlines; for markets, the figure, change, date and what it measures) instead of a concise one. The prompt that passes search results to the chat model asks for a full answer in the style of your prompt. This fixes one-line replies to news and information questions. The old "HA Mistral Web Search" agent is no longer used and can be deleted in Mistral Studio. README: example system prompt for a home and information assistant.
- **Added:** connector sources are shown in Home Assistant. When a connector answer comes with source links, the turn (question and reply verbatim, then the links) is added to a *Mistral AI — connector sources* notification, newest first, last 20 turns, saved across restarts, with Google's disclosure when Google Maps is a source; a `mistral_conversation_connector_sources` event is fired too. Sources come from Mistral's citations and from `SOURCE:` lines the connector model is asked to add, which are no longer spoken. The connector option's help text carries the disclosure.
- **Added:** `scripts/create_mistral_connector.py` — creates a Mistral connector for a remote MCP server that needs an API-key header Mistral Studio can't set (for example Google Maps' `X-Goog-Api-Key`), connects it and lists its tools. Keys are asked for with hidden input and never printed. README: step-by-step *Setting up Google Maps*, including Google's terms and costs.
- **Added:** *Use my Mistral connectors* (on by default). Every usable connector (MCP server) registered in your Mistral account is offered to the assistant as a tool; when the model uses one, the request runs through Mistral's Conversations API with that connector attached (`store: false`) and Mistral executes it. Results are treated as untrusted and all tools are withdrawn for the rest of that turn. The connector list (`GET /v1/connectors`) is cached for 10 minutes; unauthenticated or blocked connectors are skipped. With a Ministral chat model, connector requests run on `mistral-small-latest`. Private connectors need an API key with the *Private and shared connectors* scope; OAuth connectors must be connected in Mistral Studio. Connectors are in Mistral's Public Preview. Testing steps and the log lines to look for are in [Testing and troubleshooting connectors](#testing-and-troubleshooting-connectors).
- **Fixed:** with *Speaking pace* or *Emotion* set, TTS models that don't understand Mistral's speech tags read them aloud ("pace equals fast" with `voxtral-mini-tts-latest`). The tags are now only sent when the *Text-to-speech model* is Voxtral TTS 3 or later (such as `voxtral-mini-tts-3-0`); otherwise they are left out with one warning in the log. Expressiveness and the volume boost are unaffected.
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
