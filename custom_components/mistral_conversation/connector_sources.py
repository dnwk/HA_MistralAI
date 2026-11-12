"""A visible record of connector answers and the sources they used.

Some connector providers require their sources to be shown to the user. For
voice interfaces, Google's terms for Maps Experience agent tools ask for "a
companion UI that shows a verbatim historical record of any AI voice
conversation", with the Google Maps sources immediately after the content
they support, viewable within one interaction, and the disclosure "AI-generated
content might include information from Google Maps."

Home Assistant's companion UI here is a persistent notification: every
assistant turn that used a connector answer with sources adds an entry —
what was said, the assistant's reply verbatim, then the source links — to a
rolling record (newest first, last 20 turns). The record is kept in
``.storage`` so it survives restarts, and each new entry is also fired as a
``mistral_conversation_connector_sources`` event for custom dashboards.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .connectors import ConnectorResult
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SOURCE_RECORD_MAX = 20
SOURCE_EVENT = f"{DOMAIN}_connector_sources"
NOTIFICATION_TITLE = "Mistral AI — connector sources"
# Exact wording required by Google; "Google Maps" must not be changed or translated.
GOOGLE_MAPS_DISCLOSURE = "AI-generated content might include information from Google Maps."
_STORE_VERSION = 1
_GOOGLE_HOST = re.compile(r"^(www\.)?google\.[a-z.]+$")


def is_google_maps_url(url: str) -> bool:
    """Whether a source link points to Google Maps."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if host.startswith("maps.google.") or host == "maps.app.goo.gl":
        return True
    if host == "goo.gl" and path.startswith("/maps"):
        return True
    return bool(_GOOGLE_HOST.match(host)) and path.startswith("/maps")


def record_entry(
    question: str, answer: str, results: Iterable[ConnectorResult], when: str
) -> dict[str, Any] | None:
    """One record entry (JSON-friendly), or None if no result had sources."""
    sources = [
        {"connector": result.connector.title, "title": source.title, "url": source.url}
        for result in results
        for source in result.sources
    ]
    if not sources:
        return None
    return {"time": when, "question": question, "answer": answer, "sources": sources}


def _escape(text: str) -> str:
    return re.sub(r"([\\\[\]*_`])", r"\\\1", text.replace("\n", " ").strip())


def render_record(entries: list[dict[str, Any]]) -> str:
    """Markdown for the notification: disclosure, then entries newest first.

    Each entry shows the question and the reply verbatim, followed directly
    by its source links.
    """
    lines = [
        "Answers from your voice assistant that used your Mistral connectors, "
        "newest first, each followed by the sources it was based on. "
        "AI-generated content might include information from these services."
    ]
    if any(is_google_maps_url(s.get("url", "")) for e in entries for s in e.get("sources", [])):
        lines.append("")
        lines.append(GOOGLE_MAPS_DISCLOSURE)
    for entry in entries:
        links = " · ".join(
            f"[{_escape(str(s.get('title') or s.get('url')))}](<{s.get('url')}>)"
            for s in entry.get("sources", [])
        )
        lines += [
            "",
            "---",
            f"**{_escape(str(entry.get('time', '')))}**",
            "",
            f"**You:** {_escape(str(entry.get('question', '')))}",
            "",
            f"**Assistant:** {_escape(str(entry.get('answer', '')))}",
            "",
            f"Sources: {links}",
        ]
    return "\n".join(lines)


class ConnectorSourceRecord:
    """The rolling record for one config entry, stored and shown in HA."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._notification_id = f"{DOMAIN}_connector_sources_{entry_id}"
        self._store = Store(hass, _STORE_VERSION, f"{DOMAIN}.connector_sources.{entry_id}")
        self._entries: list[dict[str, Any]] | None = None

    async def async_add(
        self, question: str, answer: str, results: Iterable[ConnectorResult], when: datetime
    ) -> bool:
        """Add a turn if it had sources; returns whether anything was recorded."""
        entry = record_entry(question, answer, results, when.strftime("%Y-%m-%d %H:%M"))
        if entry is None:
            return False
        if self._entries is None:
            data = await self._store.async_load()
            stored = data.get("entries") if isinstance(data, dict) else None
            self._entries = [e for e in stored if isinstance(e, dict)] if isinstance(stored, list) else []
        self._entries.insert(0, entry)
        del self._entries[SOURCE_RECORD_MAX:]
        await self._store.async_save({"entries": self._entries})
        persistent_notification.async_create(
            self._hass,
            render_record(self._entries),
            title=NOTIFICATION_TITLE,
            notification_id=self._notification_id,
        )
        self._hass.bus.async_fire(SOURCE_EVENT, entry)
        _LOGGER.debug("Recorded %d connector source(s) for: %s", len(entry["sources"]), question)
        return True
