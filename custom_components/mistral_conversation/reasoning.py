"""Mistral's reasoning models: thinking chunks and reasoning effort.

Reasoning models (Mistral Large 4, Medium 3.5, Small 4) think before they
answer and return that reasoning as ``thinking`` chunks. In a streamed chat
completion, ``delta.content`` is a list of chunks while the model thinks, for
example ``[{"type": "thinking", "thinking": [{"type": "text", "text": "…"}]}]``,
and a plain string once it answers. The reasoning must never be spoken, so
``split_content`` separates it from the answer text.

``reasoning_effort`` sets how much such a model thinks. Which values a model
accepts differs (Large 4: low/medium/high; Small 4 and Medium 3.5: none/high),
and an alias such as ``mistral-large-latest`` can move to another model at any
time. So a request whose effort Mistral rejects is sent once more without it,
and the effort is left out for that model until Home Assistant restarts: a
wrong setting costs one extra request and a warning, never a failed reply.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from .const import REASONING_EFFORTS

_LOGGER = logging.getLogger(__name__)

# (model, effort) pairs Mistral refused, kept until Home Assistant restarts.
_REJECTED: set[tuple[str, str]] = set()


def split_content(content: Any) -> tuple[str, str]:
    """Split message content into (answer text, reasoning text).

    ``content`` is a string (an ordinary answer) or a list of chunks. Text
    chunks form the answer and thinking chunks the reasoning; other chunk
    types, such as citations, are left out of both.
    """
    if isinstance(content, str):
        return content, ""
    if isinstance(content, dict):
        content = [content]
    if not isinstance(content, list):
        return "", ""
    answer: list[str] = []
    thinking: list[str] = []
    for chunk in content:
        if isinstance(chunk, str):
            answer.append(chunk)
        elif isinstance(chunk, dict):
            kind = chunk.get("type")
            if kind == "text":
                answer.append(str(chunk.get("text") or ""))
            elif kind == "thinking":
                thinking.append(_chunk_text(chunk.get("thinking")))
    return "".join(answer), "".join(thinking)


def _chunk_text(value: Any) -> str:
    """Text of a thinking chunk's ``thinking`` field (a string or text chunks)."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(
            str(c.get("text") or "") if isinstance(c, dict) else str(c)
            for c in value
            if isinstance(c, (dict, str))
        )
    return ""


def effort_for(model: str, effort: Any) -> str | None:
    """The reasoning effort to send with a request to ``model``, or None."""
    if effort not in REASONING_EFFORTS or (model, effort) in _REJECTED:
        return None
    return effort


def _effort_in(payload: dict[str, Any]) -> Any:
    args = payload.get("completion_args")
    if isinstance(args, dict) and args.get("reasoning_effort"):
        return args["reasoning_effort"]
    return payload.get("reasoning_effort")


def without_effort(payload: dict[str, Any]) -> dict[str, Any]:
    """A copy of ``payload`` without a reasoning effort."""
    out = {k: v for k, v in payload.items() if k != "reasoning_effort"}
    args = out.get("completion_args")
    if isinstance(args, dict) and "reasoning_effort" in args:
        out["completion_args"] = {k: v for k, v in args.items() if k != "reasoning_effort"}
    return out


async def _effort_rejected(resp: Any, payload: dict[str, Any]) -> bool:
    """True when Mistral refused the request because of its reasoning effort."""
    effort = _effort_in(payload)
    if not effort or resp.status not in (400, 422):
        return False
    body = await resp.text()
    if "reasoning_effort" not in body and "reasoning effort" not in body.lower():
        return False
    model = str(payload.get("model"))
    _REJECTED.add((model, str(effort)))
    _LOGGER.warning(
        "Mistral model %s does not accept reasoning effort '%s'; it is left out "
        "for this model until Home Assistant restarts. Mistral said: %s",
        model,
        effort,
        body[:300],
    )
    return True


@asynccontextmanager
async def post_with_effort_fallback(
    session: Any, url: str, payload: dict[str, Any], **kwargs: Any
) -> AsyncIterator[Any]:
    """POST ``payload``; if Mistral rejects its reasoning effort, retry without.

    Yields the response like ``session.post``. A response whose body was read
    to check it can be read again (aiohttp keeps the body).
    """
    async with session.post(url, json=payload, **kwargs) as resp:
        if not await _effort_rejected(resp, payload):
            yield resp
            return
    async with session.post(url, json=without_effort(payload), **kwargs) as resp:
        yield resp
