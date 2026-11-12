"""Create a Mistral connector for a remote MCP server that needs an API-key header.

Mistral Studio's API-key option sends ``Authorization: Bearer <key>``. Some
servers expect a different header — Google Maps (Maps Experience agent tools)
wants ``X-Goog-Api-Key``. Mistral's Connectors API accepts any header as a
connector-wide ``global_headers`` entry, stored encrypted ("never returned in
clear"). This script creates such a connector, connects it, and lists its
tools so you can see it works.

Keys are asked for with hidden input (or read from MISTRAL_API_KEY /
CONNECTOR_HEADER_VALUE) and are never printed or written anywhere. Standard
library only; run it on your own computer:

    python scripts/create_mistral_connector.py --preset google-maps

The Mistral API key must be allowed to manage connectors; for a *private*
connector, the key Home Assistant uses needs the "Private and shared
connectors" scope to see it.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.mistral.ai/v1"

PRESETS = {
    "google-maps": {
        "name": "google_maps",
        "title": "Google Maps",
        "description": (
            "Google Maps place search with opening hours and ratings, travel "
            "times and distances by car, transit, bike or on foot, places along "
            "a route, and current weather and forecasts for any location."
        ),
        "server": "https://mapstools.googleapis.com/mcp",
        "header": "X-Goog-Api-Key",
        "key_prompt": "Google Maps API key (hidden): ",
    },
}


def _request(method: str, path: str, key: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", "replace")
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, raw[:500]


def _ask(prompt: str, default: str = "") -> str:
    value = input(f"{prompt} [{default}]: " if default else f"{prompt}: ").strip()
    return value or default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--preset", choices=sorted(PRESETS), help="fill in a known server")
    parser.add_argument("--visibility", choices=["private", "shared_workspace"], default="private")
    args = parser.parse_args()

    preset = PRESETS.get(args.preset or "", {})
    name = _ask("Connector name (letters, digits, _ and -)", preset.get("name", ""))
    title = _ask("Title", preset.get("title", name))
    description = _ask("Description (what the assistant can use it for)", preset.get("description", ""))
    server = _ask("MCP server URL", preset.get("server", ""))
    header = _ask("Header name for the key (empty = none)", preset.get("header", ""))
    if not (name and description and server.startswith("https://")):
        print("A name, a description and an https:// server URL are required.")
        return 1

    header_value = ""
    if header:
        header_value = os.environ.get("CONNECTOR_HEADER_VALUE") or getpass.getpass(
            preset.get("key_prompt", f"Value for {header} (hidden): ")
        )
        if not header_value.strip():
            print("No header value given.")
            return 1
    mistral_key = os.environ.get("MISTRAL_API_KEY") or getpass.getpass("Mistral API key (hidden): ")
    if not mistral_key.strip():
        print("No Mistral API key given.")
        return 1

    body: dict = {
        "protocol": "mcp",
        "name": name,
        "title": title,
        "description": description,
        "server": server,
        "visibility": args.visibility,
    }
    shown = dict(body)
    if header:
        body["global_headers"] = {header: {"value": header_value.strip(), "is_secret": True}}
        shown["global_headers"] = {header: {"value": "<hidden>", "is_secret": True}}
    print("\nAbout to create this connector in your Mistral account:")
    print(json.dumps(shown, indent=2))
    if _ask("Create it? (y/n)", "n").lower() != "y":
        print("Nothing created.")
        return 0

    status, created = _request("POST", "/connectors", mistral_key.strip(), body)
    if status >= 400 or not isinstance(created, dict):
        print(f"Create failed: HTTP {status}: {created}")
        return 1
    connector = created.get("id") or created.get("name") or name
    print(f"Created connector {created.get('name')!r} (id {created.get('id')}).")

    # A connector with no login is connected with empty user credentials; the
    # key travels in the connector-wide header set above.
    status, result = _request(
        "POST",
        f"/connectors/{urllib.parse.quote(str(connector))}/user/credentials",
        mistral_key.strip(),
        {"name": "default", "credentials": {"headers": {}}, "is_default": True},
    )
    if status >= 400:
        print(f"Connecting failed: HTTP {status}: {result}")
        print("Open the connector in Mistral Studio and connect it there.")
        return 1
    print("Connected.")

    status, tools = _request(
        "GET", f"/connectors/{urllib.parse.quote(str(connector))}/tools?page_size=100", mistral_key.strip()
    )
    if status >= 400:
        print(f"Listing tools failed: HTTP {status}: {tools}")
        print("The connector exists; check the server URL and header value in Mistral Studio.")
        return 1
    items = tools.get("items", tools) if isinstance(tools, dict) else tools
    names = [t.get("name") for t in items if isinstance(t, dict)] if isinstance(items, list) else []
    print(f"Tools: {', '.join(n for n in names if n) or '(none returned)'}")
    print("Home Assistant picks it up within 10 minutes (or reload the integration).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
