"""Configuration — every knob is an env var, documented in .env.example.

No settings framework: a dataclass read once at startup. If you can read this
file, you know everything Gogo can be configured to do.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from dotenv import find_dotenv, load_dotenv

# The names, never the values, that were set before any .env loaded. Once the
# files below have loaded, os.environ cannot say where a value came from, and
# the setup page has to say whether a model key came from the environment or
# from a file (spec 013).
STARTUP_ENV_NAMES = frozenset(name for name, value in os.environ.items() if value)


def _load_env() -> str:
    """Find the user's .env the way the user expects: from where they ARE.

    Bare `load_dotenv()` searches upward from the file that called it, not from
    the working directory. Inside a git checkout that is invisible — config.py
    lives in the project, so walking up from it lands on the project's .env and
    everything works. Installed from PyPI it walks up from site-packages,
    reaches the filesystem root, and finds nothing: the user stands in a folder
    holding a perfectly good .env and Gogo reports "No API key". Reported from
    a clean install on 2026-07-31, from inside the repo folder itself.

    usecwd=True is the whole fix. The walk upward is kept on purpose, so
    running `gogo` from a subdirectory of your project still finds the .env at
    its root — the same rule git, npm and pytest already taught everyone.

    Returns the path that was loaded (empty string if none) so `gogo connections`
    and the first-run error can say WHICH file was read, rather than leaving
    people guessing between three .env files.
    """
    path = find_dotenv(usecwd=True)
    if path:
        load_dotenv(path)
    return path


DOTENV_PATH = _load_env()


class HomeChoice(NamedTuple):
    """Where Gogo keeps its state, and which rule chose it."""
    path: Path
    rule: str   # "GOGO_HOME", "legacy" (a folder's ./.gogo) or "global" (~/.gogo)


# Printed to people with a legacy ./.gogo. It copies the folder's contents, not
# the folder: `cp -R ./.gogo ~/.gogo` puts the copy at ~/.gogo/.gogo whenever
# ~/.gogo already exists. It copies, never moves (public hard rule 1).
COPY_COMMAND = "mkdir -p ~/.gogo && cp -R ./.gogo/. ~/.gogo/"


def resolve_home(env: Mapping[str, str] | None = None, cwd: Path | None = None,
                 user_home: Path | None = None) -> HomeChoice:
    """Gogo's home is decided by the first rule that matches (spec 002):

    1. GOGO_HOME is set: use it.
    2. ./.gogo/state.db exists and ~/.gogo/state.db does not: keep using the
       folder's ./.gogo. A person's older memory answers until they copy it.
    3. Otherwise: ~/.gogo, so the same assistant answers from every folder.

    Rule 2 checks for ~/.gogo/state.db, not for the ~/.gogo folder. A ~/.gogo
    holding unrelated files must not hide a person's real memory, and copying
    the old folder creates state.db, so the copy is what moves them over.
    """
    env = os.environ if env is None else env
    cwd = Path.cwd() if cwd is None else cwd
    user_home = Path.home() if user_home is None else user_home
    if env.get("GOGO_HOME"):
        return HomeChoice(Path(env["GOGO_HOME"]), "GOGO_HOME")
    legacy, global_home = cwd / ".gogo", user_home / ".gogo"
    if (legacy / "state.db").exists() and not (global_home / "state.db").exists():
        return HomeChoice(legacy, "legacy")
    return HomeChoice(global_home, "global")


def home_notice(cwd: Path | None = None, user_home: Path | None = None,
                env: Mapping[str, str] | None = None) -> str:
    """The one line people with a legacy ./.gogo see at startup, or ""."""
    cwd = Path.cwd() if cwd is None else cwd
    choice = resolve_home(env=env, cwd=cwd, user_home=user_home)
    legacy = cwd / ".gogo"
    if choice.rule == "legacy":
        return ("Gogo is using ./.gogo (your memory from before v0.2). To move it to "
                f"~/.gogo, where Gogo looks from any folder: {COPY_COMMAND}")
    if (choice.rule == "global" and (legacy / "state.db").exists()
            and legacy.resolve() != choice.path.resolve()):
        return ("Gogo is using ~/.gogo and ignoring ./.gogo in this folder, which holds "
                "older memory. Nothing in it was moved or deleted.")
    return ""


def describe_home(choice: HomeChoice) -> str:
    """One line for `gogo connections`: the resolved home and why."""
    why = {"GOGO_HOME": "set by GOGO_HOME",
           "legacy": "older memory in this folder, used until you copy it",
           "global": "the default"}[choice.rule]
    return f"{choice.path.resolve()} ({why})"


def _load_home_env() -> str:
    """Load <home>/.env, so a global install finds its key from any folder.

    The working directory's .env loads first (_load_env above) and may set
    GOGO_HOME, so the home is resolved after it. This file loads last and never
    overrides a value already set: a project's own .env always wins. Gogo reads
    no .env outside these two places.

    Returns the path that was loaded, or "" when there is none or it is the
    same file the working directory already supplied.
    """
    path = resolve_home().path / ".env"
    if not path.is_file():
        return ""
    if DOTENV_PATH and Path(DOTENV_PATH).resolve() == path.resolve():
        return ""
    load_dotenv(path, override=False)
    return str(path)


HOME_DOTENV_PATH = _load_home_env()


def env_write_target(cwd: Path | None = None, env: Mapping[str, str] | None = None,
                     user_home: Path | None = None) -> tuple[Path, bool]:
    """The one .env every dashboard save writes to, and whether it is <home>/.env
    (spec 013). Pure: it creates nothing.

    A save goes where the next start reads it first. When a .env is found from
    the working directory upward, that file wins over <home>/.env (spec 002),
    so a value written to the home file would be hidden by any line the
    project's file already holds. When no such file exists, the save goes to
    <home>/.env, so Gogo finds it from every folder.
    """
    cwd = Path.cwd() if cwd is None else cwd
    if found := find_env_upward(cwd):
        return Path(found), False
    return resolve_home(env=env, cwd=cwd, user_home=user_home).path / ".env", True


def env_write_path() -> Path:
    """env_write_target() for a save that is about to happen: the home folder is
    created if it is missing. The file itself is created by the first save:
    python-dotenv's set_key writes through a temporary file, so a new .env
    starts with mode 600."""
    path, _ = env_write_target()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def find_env_upward(start: Path) -> str:
    """The nearest .env in `start` or a folder above it, or "". This is the
    walk find_dotenv(usecwd=True) makes from the working directory, with the
    starting folder passed in so the evals can point it anywhere."""
    for folder in (start, *start.parents):
        candidate = folder / ".env"
        if candidate.is_file():
            return str(candidate)
    return ""


@dataclass
class Settings:
    # --- LLM: pick a provider, set its key. See gogo/loop/models.py PROVIDERS.
    provider: str = field(default_factory=lambda: os.getenv("GOGO_PROVIDER", "anthropic"))
    # Explicit overrides (optional): key, endpoint, and model ids. Left empty,
    # the provider's own key env var and default models are used.
    api_key: str = field(default_factory=lambda: os.getenv("GOGO_API_KEY", ""))
    base_url: str | None = field(default_factory=lambda: os.getenv("GOGO_BASE_URL") or None)
    model: str = field(default_factory=lambda: os.getenv("GOGO_MODEL", ""))
    # Cheap model used by the retrieval gate and the consolidation summarizer.
    small_model: str = field(default_factory=lambda: os.getenv("GOGO_SMALL_MODEL", ""))
    # Providers the user turned off in the dashboard (comma-separated ids).
    # Disabled providers are hidden from pickers/switchers; the ACTIVE provider
    # can't be disabled (guarded in integrations.apply_provider_disabled).
    disabled_providers: frozenset[str] = field(default_factory=lambda: frozenset(
        p.strip() for p in os.getenv("GOGO_DISABLED_PROVIDERS", "").split(",") if p.strip()))

    # --- Home: where Gogo keeps its state (memory DB, calendar, outbox, traces).
    # ~/.gogo by default, so the same assistant answers from every folder; a
    # folder's older ./.gogo keeps answering until it is copied. resolve_home()
    # above has the rules. Every file Gogo writes is in it, so you can look.
    home: Path = field(default_factory=lambda: resolve_home().path)

    # --- Loop guardrails
    # 15, not 10: a research turn that fails a lookup or two and then fetches
    # per item (five videos' comments) needs more than ten steps. Hitting the
    # limit no longer loses the turn either way: the loop makes one tools-off
    # call for an answer from what it gathered (gogo/loop/agent.py).
    max_iterations: int = field(default_factory=lambda: int(os.getenv("GOGO_MAX_ITERATIONS", "15")))
    # Headroom matters for REASONING models (kimi-k3, gpt-5.x, gemini-*-pro):
    # they spend output tokens thinking before the answer, so a low cap makes
    # them hit stop_reason=max_tokens mid-thought and return an EMPTY reply
    # (watched kimi-k3 do exactly that at 2048). 8192 leaves room to think AND
    # answer; it's a ceiling, not a target, so efficient models still cost the same.
    max_tokens: int = field(default_factory=lambda: int(os.getenv("GOGO_MAX_TOKENS", "8192")))
    # Working memory is a SLIDING WINDOW (like context RAM): only the last N
    # turns go into the prompt. Older turns aren't lost — they're in state.db,
    # distilled into facts by consolidation, and pulled back by the retrieval
    # gate when relevant. Without this cap a long thread (esp. the always-on
    # Telegram session) resends its whole history every turn until it explodes.
    history_turns: int = field(default_factory=lambda: int(os.getenv("GOGO_HISTORY_TURNS", "12")))
    # Tools a deployment does not offer, comma-separated as the model names
    # them (<server>_<tool> for MCP). The system prompt says not to call them.
    # Empty on a laptop; a hosted container is started with treg's balance and
    # resources_list here, which the relay refuses by design (spec 009 E).
    # A treg key of the person's own lifts treg's two (spec 014, treg.unavailable).
    unavailable_tools: tuple[str, ...] = field(default_factory=lambda: tuple(
        t.strip() for t in os.getenv("GOGO_UNAVAILABLE_TOOLS", "").split(",") if t.strip()))

    # --- Memory
    # Consolidate (distill chats into durable facts) only after N new exchanges.
    consolidate_every: int = field(default_factory=lambda: int(os.getenv("GOGO_CONSOLIDATE_EVERY", "6")))
    retrieval_top_k: int = field(default_factory=lambda: int(os.getenv("GOGO_RETRIEVAL_TOP_K", "4")))
    # 'sqlite' (default, zero setup) or 'supabase' (pgvector upgrade path — see launch-rag).
    semantic_store: str = field(default_factory=lambda: os.getenv("GOGO_SEMANTIC_STORE", "sqlite"))
    # 'sqlite' (default, zero setup) or 'notion' (episodes live in a Notion database).
    episodic_store: str = field(default_factory=lambda: os.getenv("GOGO_EPISODIC_STORE", "sqlite"))

    # --- Tools
    # Sync created events into Apple Calendar (a dedicated "Gogo" calendar)
    # via AppleScript. Opt-in because it writes to your real calendar app.
    apple_calendar: bool = field(
        default_factory=lambda: os.getenv("GOGO_APPLE_CALENDAR", "") in ("1", "true", "yes")
    )
    # Mirror locally-created events to Google Calendar. SQLite + ICS remain the
    # source of truth; this is only an opt-in write target.
    google_calendar: bool = field(
        default_factory=lambda: os.getenv("GOGO_GOOGLE_CALENDAR", "") in ("1", "true", "yes")
    )
    google_calendar_id: str = field(
        default_factory=lambda: os.getenv("GOGO_GOOGLE_CALENDAR_ID", "") or "primary"
    )
    # Give the agent read/write access to Apple Calendar, Mail, Reminders, Notes
    # (macOS; first use triggers the system Automation permission prompts).
    apple_tools: bool = field(
        default_factory=lambda: os.getenv("GOGO_APPLE_TOOLS", "") in ("1", "true", "yes")
    )
    # Read-only GitHub access through the `gh` CLI's own auth (no token here).
    # Off by default and deliberately so: every registered tool ships in every
    # prompt, and reading PRs is maintainer capability, not assistant capability.
    # The gather workflow calls gogo/tools/github.py as a library and does NOT
    # need this on — the switch only decides whether the MODEL can reach it.
    gh_tool: bool = field(
        default_factory=lambda: os.getenv("GOGO_GH_TOOL", "") in ("1", "true", "yes")
    )
    # owner/name to assume when a call omits it — for when Gogo runs outside a
    # checkout, where `gh` has no remote to infer from.
    gh_repo: str = field(default_factory=lambda: os.getenv("GOGO_GH_REPO", ""))
    # Register the experimental tools (delegate_task -> pi sub-agent, ...). Env is
    # the global switch; the arena sets this per-race so a coding race can hand
    # work to pi WITHOUT flipping it on for the whole process.
    experimental: bool = field(
        default_factory=lambda: os.getenv("GOGO_EXPERIMENTAL", "") in ("1", "true", "yes")
    )
    # Route every message through the triage graph workflow first (a small model
    # classifies it; trivial messages get a fast small-model reply, real tasks
    # run the normal loop as a graph node). Any failure anywhere fails open to
    # the plain loop, so this can never make Gogo worse — only faster/cheaper.
    graph_workflows: bool = field(
        default_factory=lambda: os.getenv("GOGO_GRAPH_WORKFLOWS", "") in ("1", "true", "yes")
    )

    # --- Optional gateway
    telegram_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    whatsapp_token: str = field(default_factory=lambda: os.getenv("WHATSAPP_TOKEN", ""))
    whatsapp_phone_number_id: str = field(
        default_factory=lambda: os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    )

    # --- Tracing (JSONL always; OTel exports if an endpoint is set)
    otel_endpoint: str = field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )

    def ensure_home(self) -> Path:
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "traces").mkdir(exist_ok=True)
        (self.home / "outbox").mkdir(exist_ok=True)
        return self.home


def load_settings() -> Settings:
    return Settings()
