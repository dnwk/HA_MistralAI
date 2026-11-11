"""Constants for the Mistral AI Conversation integration."""

DOMAIN = "mistral_conversation"

# ---------------------------------------------------------------------------
# Config keys
# ---------------------------------------------------------------------------
CONF_MODEL = "model"
CONF_PROMPT = "prompt"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_CONTINUE_CONVERSATION = "continue_conversation"
CONF_WEB_SEARCH = "web_search"
CONF_WEB_SEARCH_MODE = "web_search_mode"
CONF_WEB_SEARCH_TRIGGER = "web_search_trigger"
CONF_STT_LANGUAGE = "stt_language"
CONF_STT_MODEL = "stt_model"
CONF_TTS_MODEL = "tts_model"
CONF_TTS_VOICE = "tts_voice"
CONF_TTS_MODE = "tts_mode"
CONF_TTS_PACE = "tts_pace"
CONF_TTS_EMOTION = "tts_emotion"
CONF_TTS_EXPRESSIVENESS = "tts_expressiveness"
CONF_TTS_GAIN_DB = "tts_gain_db"
# Note: device control uses HA's native CONF_LLM_HASS_API from homeassistant.const

# tts_mode values
TTS_MODE_STREAM = "stream"
TTS_MODE_BATCH = "batch"
TTS_MODES = [TTS_MODE_STREAM, TTS_MODE_BATCH]

# web_search_mode values
#   model  — the model decides per turn by calling a `web_search` tool. Keeps
#            HA tools available, so one turn can both search and control devices.
#   always — legacy behaviour: every turn goes to the Agents API (no HA tools).
WEB_SEARCH_MODE_MODEL = "model"
WEB_SEARCH_MODE_ALWAYS = "always"
WEB_SEARCH_MODES = [WEB_SEARCH_MODE_MODEL, WEB_SEARCH_MODE_ALWAYS]

# Name and instructions of the server-side Mistral Agent that services web
# searches. The instructions are deliberately STATIC and generic: the agent
# object persists in the user's Mistral account, so the rendered HA system
# prompt (which can include the exposed entity/area list) must never be used
# here — that would store a snapshot of the home's layout with a third party.
WEB_SEARCH_AGENT_NAME = "HA Mistral Web Search"
WEB_SEARCH_AGENT_INSTRUCTIONS = (
    "You are a web search assistant for a smart-home voice interface. Use web "
    "search to answer the user's query, then reply factually and concisely in "
    "the language of the query. Plain prose only, suitable for text-to-speech: "
    "no markdown, no lists, no citations."
)

# Cap on remembered HA-conversation → Mistral-conversation mappings (oldest
# evicted first). Bounds memory over long uptimes; an evicted mapping just
# means the next search in that HA conversation starts a fresh Mistral thread.
WEB_SEARCH_CONV_CACHE_MAX = 32

# Name of the synthetic function tool the model calls to request a web search.
# Mistral's built-in {"type": "web_search"} tool is NOT accepted by
# /v1/chat/completions (HTTP 400 "WebSearchTool connector is not supported",
# code 1800) even though the API reference lists it in the `tools` union — it is
# only honoured on /v1/agents and /v1/conversations. So we expose web search as
# an ordinary function tool and service the call ourselves via the Agents API.
WEB_SEARCH_TOOL_NAME = "web_search"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "ministral-8b-latest"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.7  # Mistral range: 0.0–1.0
DEFAULT_CONTINUE_CONVERSATION = False
DEFAULT_WEB_SEARCH = False
DEFAULT_WEB_SEARCH_MODE = WEB_SEARCH_MODE_MODEL
# Optional comma-separated trigger phrases. When non-empty they are LEADING:
# an utterance starting with one of them is sent straight to the Agents API
# (phrase stripped), and anything else skips web search entirely. Empty (the
# default) leaves routing to `web_search_mode`. Opt-in by design — trigger
# phrases are language-specific, so shipping a list would only fit some users.
DEFAULT_WEB_SEARCH_TRIGGER = ""
DEFAULT_STT_LANGUAGE = ""  # empty = Voxtral auto-detect
DEFAULT_TTS_VOICE = "en_paul_neutral"
DEFAULT_TTS_MODE = TTS_MODE_STREAM

DEFAULT_PROMPT = (
    "You are a helpful voice assistant for a smart home called {{ ha_name }}.\n"
    "Answer in the same language the user speaks.\n"
    "Be concise and friendly.\n"
    "For straightforward home control commands, briefly confirm the action "
    "taken without asking follow-up questions.\n"
    "Your responses are read aloud by text-to-speech, so reply in plain text.\n"
    "Do not use markdown formatting that cannot be read aloud, such as "
    "asterisks for bold, underscores for italics, backticks, bullet lists, emojis, "
    "or headers.\n"
    "Today is {{ now().strftime('%A, %B %d, %Y') }}."
)

# ---------------------------------------------------------------------------
# Available chat models
# Ordered by suitability for home automation (fast + instruction-following first)
#
# Status verified against Mistral's model lifecycle docs, September 2026:
#   - "-latest" aliases always resolve to Mistral's current model for that
#     name, so they track new releases automatically (e.g. mistral-large-latest
#     now serves Mistral Large 3, ministral-8b-latest now serves the Ministral 3
#     generation). Only dated/pinned model IDs (e.g. mistral-medium-2505) go
#     stale — avoid pinning those in this list.
#   - "open-mistral-nemo" (Mistral Nemo 12B) is deprecated & retired per
#     Mistral's model lifecycle table and has been removed from this list.
#     Existing configs still set to it should switch to ministral-8b-latest
#     or ministral-3b-latest.
#   - "ministral-14b-latest" (Ministral 3 14B, released December 2025) is new:
#     the largest model in the Ministral 3 edge family, comparable in quality
#     to the old Mistral Small 3.2 but still cheap and fast.
#   - Free/"Experiment" tier API keys get rate-limited trial access to all
#     models per Mistral's own docs, but Mistral does not publish which
#     models get throttled or blocked first, or exactly how hard. In
#     practice the pricier models (Medium, Large) are the ones most likely
#     to hit those limits on a free-tier key — see the model dropdown in the
#     options dialog for a per-model note.
# ---------------------------------------------------------------------------
CHAT_MODELS = [
    "ministral-8b-latest",  # Best for HA: fast, great instruction following, low cost
    "ministral-3b-latest",  # Ultra-fast, lightweight, simple commands
    "ministral-14b-latest",  # New (Ministral 3, Dec 2025): strongest small/edge model
    "mistral-small-latest",  # Balanced: speed + quality (Mistral Small 4)
    "mistral-medium-latest",  # Required for web search via Agents API; pricier — often rate-limited on free-tier keys
    "mistral-large-latest",  # Most capable, best for complex reasoning; pricier — often rate-limited on free-tier keys
]

# Models that support the Agents/Conversations API (required for web search)
AGENT_CAPABLE_MODELS = [
    "mistral-small-latest",
    "mistral-medium-latest",
    "mistral-large-latest",
]

# ---------------------------------------------------------------------------
# STT
# ---------------------------------------------------------------------------
# Default speech-to-text model; overridable via the CONF_STT_MODEL option.
DEFAULT_STT_MODEL = "voxtral-mini-latest"

# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------
# Default text-to-speech model; overridable via the CONF_TTS_MODEL option.
DEFAULT_TTS_MODEL = "voxtral-mini-tts-latest"

# Available voices per Mistral TTS documentation (voxtral-mini-tts-2603)
TTS_VOICES = [
    "en_paul_angry",
    "en_paul_cheerful",
    "en_paul_confident",
    "en_paul_excited",
    "en_paul_frustrated",
    "en_paul_happy",
    "en_paul_neutral",
    "en_paul_sad",
    "fr_marie_angry",
    "fr_marie_curious",
    "fr_marie_excited",
    "fr_marie_happy",
    "fr_marie_neutral",
    "fr_marie_sad",
    "gb_jane_confused",
    "gb_jane_curious",
    "gb_jane_frustrated",
    "gb_jane_jealousy",
    "gb_jane_neutral",
    "gb_jane_sad",
    "gb_jane_sarcasm",
    "gb_jane_shameful",
    "gb_oliver_angry",
    "gb_oliver_cheerful",
    "gb_oliver_confident",
    "gb_oliver_curious",
    "gb_oliver_excited",
    "gb_oliver_neutral",
    "gb_oliver_sad",
]

# --- Speech style ---------------------------------------------------------
# Mistral TTS has no speed/pitch/volume fields. Delivery is steered with
# inline tags at the start of the input text ("[emotion=calm][pace=slow]Hi"),
# which are not spoken, and an `expressiveness` request field (1.0-5.0).
# Values per Mistral's TTS guide (emotion-tags page), November 2026. Unknown
# tag values are accepted by the API but have no effect, so only these are
# offered. "default" in the options dropdowns means: send nothing.
TTS_STYLE_DEFAULT = "default"
TTS_PACES = ["very-slow", "slow", "moderate", "fast", "very-fast"]
TTS_EMOTIONS = [
    "amused", "angry", "anxious", "apologetic", "appreciative", "assertive",
    "bored", "calm", "confident", "confused", "critical", "curious",
    "determined", "disappointed", "disgusted", "excited", "frustrated",
    "grateful", "happy", "hopeful", "playful", "proud", "reflective",
    "resigned", "sad", "sarcastic", "skeptical", "somber", "surprised",
    "tense", "tired", "urgent", "warm", "wistful",
]
TTS_EXPRESSIVENESS_MIN = 1.0
TTS_EXPRESSIVENESS_MAX = 5.0

# Volume boost in dB, applied to the audio inside Home Assistant because
# Mistral has no volume parameter. 0 = unchanged (the default).
TTS_GAIN_DB_MAX = 12

# --- Streaming ----------------------------------------------------------
# Cap on concurrently in-flight Mistral TTS requests (one per sentence).
# Bounds memory and outbound concurrency if the LLM emits many sentences in
# a burst.
TTS_MAX_INFLIGHT_SENTENCES = 2

# Don't fire TTS for sentences shorter than this — avoids spamming the API
# on stray "OK." or single-word fragments and waiting on TTFB for nothing.
TTS_MIN_SENTENCE_CHARS = 12

# Standard PCM-WAV header size for Mistral's streaming WAV: RIFF(8) + WAVE(4)
# + fmt subchunk(24) + data subchunk header(8) = 44 bytes. Verified
# empirically against api.mistral.ai with response_format=wav, stream=true.
TTS_WAV_HEADER_SIZE = 44

# Silence (zero PCM samples) inserted between sentences in streaming mode to
# give natural pauses at sentence boundaries. Without it, the per-sentence
# requests concatenate with no audible gap because each Mistral call ends
# right at the last phoneme. Mistral's streaming WAV is 24 kHz × 16-bit ×
# mono = 48000 bytes / second, so 14400 bytes ≈ 300 ms of silence — within
# the natural 200–400 ms range of a human inter-sentence pause.
TTS_INTER_SENTENCE_SILENCE_BYTES = 14_400

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
MISTRAL_API_BASE = "https://api.mistral.ai/v1"
# Only used for endpoints that moved to v2 (GET /v2/audio/voices).
MISTRAL_API_V2_BASE = "https://api.mistral.ai/v2"

# Max tool-call round-trips to prevent infinite loops
MAX_TOOL_ITERATIONS = 10
