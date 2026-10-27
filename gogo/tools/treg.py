"""treg: live external data for research.

treg is an MCP server at https://treg.to/mcp/ with thousands of endpoints
behind it: search results, company and people data, social profiles, ads,
web pages. It runs on your own treg account: you sign in once in your
browser, and treg bills that account directly.

`gogo connect treg` (or `/connect treg` in the dashboard chat) adds the server
to GOGO_HOME/mcp.json next to any servers already there, then opens treg's
sign-in page. Its tools then load like any MCP server's, named `treg_*`.

A treg API key of your own (KEY_ENV, saved from the Connections page) wins
over whatever mcp.json says: resolve() points the treg server at treg.to with
that key, and the calls are billed to your treg account. Clear the key and
the entry in mcp.json is used again as written. The key is read from the
environment and sent only to treg.
"""

from __future__ import annotations

import importlib.util
import json
import os
from collections.abc import Mapping
from pathlib import Path

NAME = "treg"
URL = "https://treg.to/mcp/"
DOCS = "https://treg.to"
WHAT = "Live data for research: search, companies, people, social, ads and the web."

# A person's own treg key (spec 014). With it, treg is reached at URL, the
# team surface: the team is theirs, so its connected accounts and tools are
# theirs too.
KEY_ENV = "TREG_API_KEY"

OWN_KEY = "Your own treg key: paid by your treg account."


def _has_mcp() -> bool:
    return importlib.util.find_spec("mcp") is not None


def _same_url(spec: dict) -> bool:
    return spec.get("url", "").rstrip("/") == URL.rstrip("/")


def _servers(home: Path) -> list[dict]:
    config = home / "mcp.json"
    if not config.exists():
        return []
    servers = json.loads(config.read_text(encoding="utf-8")).get("servers", [])
    return [s for s in servers if isinstance(s, dict)]


def _is_treg(spec: dict) -> bool:
    return spec.get("name") == NAME or _same_url(spec)


def own_key(env: Mapping[str, str] | None = None) -> bool:
    """Whether a treg key of the person's own is set."""
    return bool((os.environ if env is None else env).get(KEY_ENV, "").strip())


def resolve(servers: list, env: Mapping[str, str] | None = None) -> list:
    """mcp.json's servers as the bridge should connect them.

    With an own key, the treg server (named treg, or at treg's URL) becomes
    treg.to with that key; every other server, and treg without a key, is
    returned exactly as written. mcp.json itself is never rewritten, so
    clearing the key falls back to the entry on disk.
    """
    if not own_key(env):
        return servers
    out, replaced = [], False
    for spec in servers:
        if isinstance(spec, dict) and _is_treg(spec) and not replaced:
            out.append({"name": spec.get("name") or NAME, "url": URL, "auth_env": KEY_ENV})
            replaced = True
        else:
            out.append(spec)
    return out


def unavailable(tools: tuple[str, ...], env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """The unavailable list minus treg's tools when an own key is set: with
    your own account, treg's balance and resources tools are available."""
    if not own_key(env):
        return tools
    return tuple(t for t in tools if not t.startswith(f"{NAME}_"))


def add_server(home: Path) -> tuple[str, dict]:
    """Make sure mcp.json names treg, and say what that took.

    Returns (status, server spec). Status is "added", "present" (already
    there, under any name) or "conflict" (a server named treg points
    somewhere else on purpose, so it is left alone).
    """
    config = home / "mcp.json"
    data = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
    servers = data.setdefault("servers", [])

    for spec in servers:
        if _same_url(spec):
            return "present", spec
    for spec in servers:
        if spec.get("name") == NAME:
            return "conflict", spec

    spec = {"name": NAME, "url": URL, "oauth": True}
    servers.append(spec)
    home.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "added", spec


def _spec(home: Path) -> dict | None:
    servers = _servers(home)
    return (next((s for s in servers if _same_url(s)), None)
            or next((s for s in servers if s.get("name") == NAME), None))


def state(home: Path) -> tuple[str, str]:
    """Where treg stands: "connected", "not_signed_in" or "not_added", and a
    detail line. Files and the environment only, so the Connections page can
    ask on every poll and never opens a browser.

    The server is the one at URL, or the one named treg wherever it points.
    The detail says who pays: an own key bills the person's treg account.
    """
    try:
        spec = _spec(home)
    except (OSError, ValueError, AttributeError):
        return "not_added", f"{home / 'mcp.json'} is not valid JSON"
    if spec is None:
        return "not_added", ""
    if own_key():
        return "connected", OWN_KEY
    if spec.get("auth_env"):
        return "connected", f"using the key in ${spec['auth_env']}"
    if not spec.get("oauth"):
        return "connected", ""
    if not _has_mcp():
        return "not_signed_in", "needs the mcp extra: pip install 'gogo-agent[mcp]'"

    from gogo.tools.mcp_cli import _auth_file, _identity

    token = _auth_file(home, spec["name"])
    if not token.exists():
        return "not_signed_in", ""
    return "connected", f"as {_identity(token)}"


def card(home: Path) -> dict:
    """treg's card on the dashboard's Connections page."""
    where, detail = state(home)
    return {"key": NAME, "name": "treg", "group": "Search & Observability",
            "what": WHAT, "state": where, "detail": detail,
            "configurable": own_key()}


def status(home: Path) -> str:
    """One line for `gogo connections`."""
    where, detail = state(home)
    line = {"connected": "connected", "not_signed_in": "configured · not signed in",
            "not_added": "not connected"}[where]
    if detail:
        line += f" · {detail}"
    if where != "connected":
        line += " · run: gogo connect treg"
    return line


def connect(home: Path) -> str:
    if not _has_mcp():
        return ("treg connects over MCP, which needs an extra: "
                "pip install 'gogo-agent[mcp]' (in a checkout: pip install -e '.[mcp]'). "
                "Then run this again.")

    added, spec = add_server(home)
    name, config = spec["name"], home / "mcp.json"
    if added == "conflict":
        return (f"'{name}' in {config} already points at {spec.get('url')}, not {URL}. "
                "Change it there if you meant your own treg account.")

    done = f"Added treg to {config}. " if added == "added" else ""
    if spec.get("auth_env"):
        return (f"{done}treg is set up as '{name}', using the key in "
                f"${spec['auth_env']}. Restart Gogo to load its tools.")

    from gogo.tools.mcp_cli import _auth_file, _identity, sign_in

    token = _auth_file(home, name)
    if token.exists() and added == "present":
        return (f"treg is already connected as {_identity(token)}. "
                f"To switch accounts: gogo mcp login {name}.")

    ok, message = sign_in(home, name)
    if not ok:
        return f"{done}{message.strip()} Help: {DOCS}"
    return (f"{done}Connected to treg as {_identity(token)}. "
            f"Restart Gogo to load its tools (treg_*). treg bills your own account.")
