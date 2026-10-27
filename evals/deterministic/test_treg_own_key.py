"""DETERMINISTIC EVAL — a person's own treg key.

With TREG_API_KEY set, the treg MCP server is reached at treg.to with that
key, whatever mcp.json says; without it, mcp.json's entry is used as written.
These pin that rule, the card's line in each state, the Configure button,
the unavailable-tools list, the key probe, and that a cost treg reports on a
direct call still reaches the receipt. Offline: the probe's HTTP call is
stubbed.
"""

from __future__ import annotations

import io
import json
import re
import urllib.error
from pathlib import Path

import pytest

from gogo import integrations
from gogo.ops import receipt
from gogo.tools import treg

# an existing treg entry pointing at another URL (a custom/relay deployment)
OTHER = {"name": "treg", "url": "http://10.0.0.1:8788/treg/mcp/", "auth_env": "OTHER_TOKEN"}
MEMORY = {"name": "memory", "url": "https://mcp.example.com/memory", "auth_env": "MEMORY_API_KEY"}
OWN = {"name": "treg", "url": "https://treg.to/mcp/", "auth_env": "TREG_API_KEY"}
KEY = "treg_secret_key_0123456789"


def _write(home: Path, servers: list) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "mcp.json").write_text(json.dumps({"servers": servers}), encoding="utf-8")


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("TREG_API_KEY", raising=False)


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("TREG_API_KEY", KEY)


# --- resolve(): the one switch -------------------------------------------------

def test_without_a_key_every_server_is_connected_as_written(no_key):
    servers = [MEMORY, OTHER]
    assert treg.resolve(servers) == servers


def test_with_a_key_treg_goes_straight_to_treg_and_nothing_else_changes(with_key):
    assert treg.resolve([MEMORY, OTHER]) == [MEMORY, OWN]


def test_the_own_key_surface_is_the_team_one():
    """An own key's team is the person's, so it gets /mcp/, the surface a
    laptop signs in to."""
    assert treg.URL == "https://treg.to/mcp/"


def test_a_treg_entry_at_treg_url_under_another_name_is_the_one_switched(with_key):
    oauth = {"name": "data", "url": "https://treg.to/mcp", "oauth": True}
    assert treg.resolve([oauth]) == [{"name": "data", "url": treg.URL, "auth_env": "TREG_API_KEY"}]


def test_a_blank_key_is_no_key(monkeypatch):
    monkeypatch.setenv("TREG_API_KEY", "  ")
    assert treg.resolve([OTHER]) == [OTHER]


def test_the_bridge_connects_the_resolved_servers(tmp_path, with_key, monkeypatch):
    """MCPBridge.start runs mcp.json through resolve(), and mcp.json on disk is
    never rewritten: clearing the key falls back to the entry on disk."""
    from gogo.tools import mcp_client

    _write(tmp_path, [MEMORY, OTHER])
    before = (tmp_path / "mcp.json").read_bytes()
    seen = []

    async def connect_all(self, servers):
        seen.append(servers)
        return {}

    monkeypatch.setattr(mcp_client.MCPBridge, "_connect_all", connect_all)
    # _deadline imports the mcp extra, which CI does not install.
    monkeypatch.setattr(mcp_client.MCPBridge, "_deadline", lambda self, servers: 5.0)
    bridge = mcp_client.MCPBridge(tmp_path / "mcp.json")
    try:
        bridge.start()
    finally:
        bridge.close()
    assert seen == [[MEMORY, OWN]]
    assert (tmp_path / "mcp.json").read_bytes() == before
    monkeypatch.delenv("TREG_API_KEY")
    assert treg.resolve(json.loads(before)["servers"]) == [MEMORY, OTHER]


# --- the card ------------------------------------------------------------------

def test_an_own_key_card_says_the_treg_account_pays(tmp_path, with_key):
    _write(tmp_path, [OWN])
    card = treg.card(tmp_path)
    assert card["detail"] == "Your own treg key: paid by your treg account."
    assert card["configurable"] is True


@pytest.mark.parametrize("env", [None, KEY])
def test_no_card_names_an_environment_variable(tmp_path, monkeypatch, env):
    if env:
        monkeypatch.setenv("TREG_API_KEY", env)
    else:
        monkeypatch.delenv("TREG_API_KEY", raising=False)
    _write(tmp_path, [{"name": "treg", "url": "https://treg.to/mcp/", "oauth": True}])
    text = json.dumps(treg.card(tmp_path))
    assert "$" not in text and not re.search(r"\b[A-Z][A-Z0-9_]{3,}\b", text), text
    assert KEY not in text


def test_a_laptop_oauth_card_is_unchanged(tmp_path, no_key):
    _write(tmp_path, [{"name": "treg", "url": "https://treg.to/mcp/", "oauth": True}])
    assert treg.card(tmp_path)["configurable"] is False
    _write(tmp_path, [])
    card = treg.card(tmp_path)
    assert card["state"] == "not_added" and card["configurable"] is False


def test_the_page_offers_configure_and_draws_treg_once():
    views = (Path(treg.__file__).parents[1] / "ops" / "static" / "js" / "views.js").read_text(encoding="utf-8")
    assert "item.configurable" in views and "openConnectionModal('${esc(item.key)}')" in views
    assert "drawnAsMcp" in views


# --- the unavailable tools -----------------------------------------------------

def test_treg_tools_leave_the_unavailable_list_with_an_own_key(with_key):
    assert treg.unavailable(("treg_balance", "treg_resources_list", "x_y")) == ("x_y",)


def test_without_a_key_the_unavailable_list_stands(no_key):
    names = ("treg_balance", "treg_resources_list")
    assert treg.unavailable(names) == names


def test_the_prompt_reads_the_filtered_list(tmp_path, with_key):
    import inspect

    from gogo.runtime import session

    assert "unavailable(self.settings.unavailable_tools)" in inspect.getsource(session)


# --- the registry row and the probe --------------------------------------------

def test_the_registry_row_has_the_key_field_only():
    row = next(i for i in integrations.registry() if i.key == "treg")
    assert [(f.name, f.secret) for f in row.env] == [("TREG_API_KEY", True)]
    assert row.reload is integrations.ReloadMode.AGENT


def test_the_probe_asks_treg_directly_with_the_key(monkeypatch):
    seen = {}

    class Answer(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        seen["url"], seen["token"] = request.full_url, request.get_header("X-treg-token")
        return Answer(b"[]")

    monkeypatch.setattr(integrations.urllib.request, "urlopen", urlopen)
    integrations._treg_probe({"TREG_API_KEY": KEY})
    assert seen == {"url": "https://treg.to/tools", "token": KEY}


def test_a_refused_key_says_so_and_never_echoes_it(monkeypatch):
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, f"bad {KEY}", {}, None)

    monkeypatch.setattr(integrations.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(integrations, "_save_health", lambda: None)
    monkeypatch.setattr(integrations, "_write_updates", lambda *a: pytest.fail("a failed test must not save"))
    result = integrations.apply_integration("treg", {"TREG_API_KEY": KEY})
    assert not result.ok and "did not accept" in result.error and KEY not in result.error


# --- cost without a relay ------------------------------------------------------

def test_a_direct_treg_cost_reaches_the_receipt():
    """The cost is read from the tool's own result, so a direct call still
    shows its cost and endpoint."""
    event = {"args": {"endpoint": "tikhub.tiktok.user.profile"},
             "output": json.dumps({"cost_usd": 0.004, "call_id": "c1", "data": {}})}
    assert receipt.tool_cost(event) == (0.004, "tikhub")
