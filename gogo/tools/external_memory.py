"""An external memory server, connected over MCP.

The agent's own memory is local (`<home>/memory`, a SQLite fact store). Any
MCP server that publishes the `memory.remember` / `memory.search` /
`memory.get` tools can be connected as an additional memory layer: facts the
agent keeps and the research reports it writes can be mirrored there, so
other tools pointed at the same server can read them. Nothing is hardcoded:
the server is whichever one in `<home>/mcp.json` actually offers those
tools, or (to break a tie) the entry explicitly marked `"memory": true`.

This module only adapts the MCP seam the rest of the app already has:
consolidation gets a `remember` callable, a research turn gets a read-first
`search`/`get` pair. No server configured, or none with the memory tools,
and every accessor returns None, so the agent stays fully local.
"""

from __future__ import annotations

import json

REMEMBER = "memory.remember"
SEARCH = "memory.search"
GET = "memory.get"


def _server(bridge) -> str | None:
    """The connected memory server's name, or None.

    Prefer an mcp.json entry explicitly marked `"memory": true`; otherwise
    the one connected server that publishes `memory.remember`.
    """
    if bridge is None:
        return None
    try:
        servers = json.loads(bridge.config_path.read_text(encoding="utf-8")).get("servers", [])
    except (OSError, ValueError, AttributeError):
        servers = []
    marked = [s.get("name") for s in servers
              if isinstance(s, dict) and s.get("memory") is True and s.get("name")]
    listed = getattr(bridge, "_listed", {}) or {}

    def live(name) -> bool:
        try:
            return bool(name) and bridge.connected(name)
        except Exception:  # a stale entry must not disable local memory
            return False

    for name in marked:
        if live(name) and (not listed or REMEMBER in listed.get(name, [])):
            return name
    for name, tool_names in listed.items():
        if REMEMBER in tool_names and live(name):
            return name
    return None


def remember_via(bridge):
    """A remember(body, scope, kind=None) for consolidation and research
    reports, or None when no memory server is connected. It returns the new
    memory's id and raises when the send failed: the bridge reports a
    failure as text, which is not this JSON."""
    server = _server(bridge)
    if server is None:
        return None

    def remember(body: str, scope: str, kind: str | None = None) -> str | None:
        if kind is None:
            # A company-research finding is knowledge about the world; a
            # research report names its own kind, semantic.
            kind = "reference" if scope.startswith("project:") else "fact"
        text = bridge.call(server, REMEMBER, {"body": body, "kind": kind, "scope": scope})
        try:
            return json.loads(text)["memory"]["id"]
        except (ValueError, KeyError, TypeError):
            raise RuntimeError(text[:200]) from None

    return remember


def search_via(bridge):
    """A search(args) for a research turn's read-first step, or None when no
    memory server is connected. It returns the server's answer as text, the
    same text the model would see from the tool, and raises when that is not
    a search response."""
    server = _server(bridge)
    if server is None:
        return None

    def search(args: dict) -> str:
        text = bridge.call(server, SEARCH, args)
        try:
            found = isinstance(json.loads(text).get("entries"), list)
        except (ValueError, KeyError, TypeError):
            found = False
        if not found:
            raise RuntimeError(text[:200])
        return text

    return search


def get_via(bridge):
    """A get(memory_id) for the read-first step's earlier reports, or None
    when no memory server is connected. It returns memory.get's answer as
    text and raises when that is not a memory."""
    server = _server(bridge)
    if server is None:
        return None

    def get(memory_id: str) -> str:
        text = bridge.call(server, GET, {"id": memory_id})
        try:
            found = isinstance(json.loads(text), dict)
        except ValueError:
            found = False
        if not found:
            raise RuntimeError(text[:200])
        return text

    return get


def tool_name(bridge, tool: str) -> str | None:
    """The name the model calls one of the memory server's tools by, such as
    myserver_memory_remember, or None when no memory server is connected."""
    server = _server(bridge)
    if server is None:
        return None
    from gogo.tools.mcp_client import _model_safe_name

    return _model_safe_name(server, tool)
