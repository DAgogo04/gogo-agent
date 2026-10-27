# Connect it to your life

Everything here is opt-in and behind its own extra. None of it changes the
loop — a gateway moves text in and out, an integration is a tool the agent
may call. The four pillars work with none of this installed.

Moved out of the README, which had grown to 569 lines for a project whose
promise is that you can read it in an afternoon. Nothing was rewritten.

## Talk to it

```bash
uv pip install -e '.[voice]'
gogo voice        # hands-free: always-listening for "gogo gogo"
```

**Hands-free by default.** `gogo voice` listens for the wake word **"gogo gogo"** — a tiny
Whisper model scans the mic; when it hears the phrase, the big model takes over for your
command and speaks the reply. Change or disable it:

```bash
GOGO_WAKE_WORD="hey gogo"  gogo voice     # any phrase, no training
GOGO_WAKE_WORD=""          gogo voice     # push-to-talk instead (Enter, speak, Enter)
```

The matcher is ~15 transparent lines with a deterministic eval; it accepts cross-script
variants (`"gogo gogo,ゴーゴー"`). A trained openWakeWord model is the efficient v2 upgrade.

**A beautiful voice.** Out of the box it uses macOS `say` — and Gogo auto-picks the nicest
voice you have, preferring a downloaded Premium/Enhanced one (System Settings ▸ Accessibility
▸ Spoken Content ▸ System Voice) over the robotic built-ins. For the real neural upgrade,
install [Kokoro](https://github.com/hexgrad/kokoro) — a fully local, offline British-butler
voice that's picked up automatically, no env var needed:

```bash
uv pip install '.[voice-neural]'          # neural Kokoro (bm_george); pulls torch (~2GB)
```

Override either engine with `GOGO_VOICE` (a `say` voice name, or a Kokoro voice like `bf_emma`).

## Phone to laptop

```bash
pip install -e '.[telegram]'
# message @BotFather, /newbot, put the token in .env, then:
make telegram
```

Text your bot from anywhere and your laptop runs the turn — long-polling, so no
public URL or webhook. Set `TELEGRAM_ALLOWED_USER` to lock it to just you.

## Brief me on my week (Apple Calendar + Mail)

```bash
GOGO_APPLE_TOOLS=1 make brief      # macOS; grant the permission prompts once
```

Gogo reads your **real** Calendar.app (including events invited by email) and
recent Apple Mail, cross-references your memory, and writes a focus-first briefing
with clickable `message://` links. Cron it for a morning greeting:

```
30 7 * * *  cd ~/gogo-agent && make brief
```

It runs through the normal harness, so it animates on the dashboard like any turn.

## Mirror created events to Google Calendar

The local SQLite database and `calendar.ics` stay authoritative. To also write
`create_event` results to Google Calendar, install the opt-in extra and configure
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc):

```bash
pip install -e '.[gcal]'
# Keep the downloaded client file OUTSIDE the repo — it is only an input to
# gcloud, which stores the resulting credentials in ~/.config/gcloud/.
gcloud auth application-default login \
  --client-id-file=~/.config/gogo/gcal-client.json \
  --scopes=https://www.googleapis.com/auth/calendar.events
GOGO_GOOGLE_CALENDAR=1 gogo
```

Nothing secret ever needs to live in the repo: the client file is read once by
`gcloud`, and the credentials it mints land in `~/.config/gcloud/`. (`.gitignore`
also blocks `credentials.json` and `*token*.json` as a second line of defence.)

The target defaults to the signed-in user's `primary` calendar; set
`GOGO_GOOGLE_CALENDAR_ID` for another calendar. `list_events` still reads the
local database. Google failures never roll back the local event, and attendee
notifications are suppressed (`sendUpdates=none`).

## Connect MCP servers

Gogo's own memory is local. Each fact is also written to `~/.gogo/memory/`,
one file per fact; episodes, `MEMORY.md` and `state.db` are never copied
there. Optional MCP servers extend the agent: `~/.gogo/mcp.json` lists the
remote servers you connect to, and their tools load like any built-in tool.

```bash
pip install -e '.[mcp]'
```

Add a server by hand in `~/.gogo/mcp.json`, or use `gogo connect <name>` for
a server that needs a browser sign-in (or `/connect <name>` in the dashboard
chat). `gogo mcp` shows the configured servers and the account you are
signed in as.

### Carry your skills too

```bash
gogo skill export --to claude,codex    # ~/.claude/skills/ and ~/.codex/skills/
gogo skill export --project            # ./.claude/skills/, which Muse Code also reads
```

Each skill folder is copied as it is. A copy you changed in the other agent is
kept unless you pass `--force`. Skills that call Gogo's own tools (a
calendar skill calls `create_event`) arrive as instructions without those
tools behind them.

## Live data for research (treg)

[treg](https://treg.to) is an MCP server with thousands of endpoints behind
it: search results, keyword data, companies and people, social profiles, ad
libraries, web pages. With it connected, a question like "research the
competitors of mem0" is answered from live sources rather than the model's
memory.

```bash
pip install -e '.[mcp]'
gogo connect treg            # or /connect treg in the dashboard chat
```

That adds `{"name": "treg", "url": "https://treg.to/mcp/", "oauth": true}` to
`~/.gogo/mcp.json`, next to any servers already there, and opens treg's own
sign-in page once. Restart Gogo and its tools appear as `treg_*`. Running it
again adds nothing; a server you named `treg` that points somewhere else is
left alone, and the command says so. On your own machine treg is your own
account and bills you directly. The **Connections** page shows treg as
connected, not signed in or not added, with a Connect button that runs the
same `/connect treg` in the chat.

`TREG_API_KEY` works the same on your own machine: when it is set in `.env`,
Gogo reaches the `treg` server in `mcp.json` at treg.to with that key instead
of the sign-in, and the key is sent only to treg.

## Let Jev decide which memories earn a slot

```bash
TYPESAFE_API_KEY=...      # typesafe.ai
GOGO_SLOT_GATE=jev
```

With both set, Jev scores every retrieved memory against your message and only
the ones that change the answer go into the prompt; it also scores facts before
consolidation stores them. One call per turn, about a quarter of a second. Leave
either unset, or let TypeSafe be unreachable, and Gogo behaves as before. The
TypeSafe card on Connections sets both.

## Connect MCP servers

```bash
pip install -e '.[mcp]'
```

Create `~/.gogo/mcp.json` and any Model Context Protocol server's tools appear to
the agent, namespaced `<server>_<tool>` (and in the dashboard's Tools ▸ MCP tab):

```json
{"servers": [{"name": "fs", "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}]}
```

**Node-free demo** — a tiny self-contained Python MCP server ships in the repo:

```bash
cp examples/mcp.demo.json .gogo/mcp.json   # points at evals/fixtures/mcp_demo_server.py
make dashboard                               # demo_word_count / demo_reverse_text appear in Tools
```

Same pattern scales to any server, yours or a vendor's — no changes to Gogo's code.

### Remote servers (Streamable HTTP)

A server that is already running somewhere else is named by `url` instead of
`command`. This is the MCP spec's transport for remote servers; the older
HTTP+SSE transport is deprecated and is not supported.

```json
{"servers": [{"name": "gogo_memory",
              "url": "https://your-host/mcp",
              "auth_env": "GOGO_MEMORY_API_KEY"}]}
```

`auth_env` names an **environment variable**; its value is sent as
`Authorization: Bearer <value>`. The credential never goes in `mcp.json` —
that file gets pasted into bug reports, and a bearer token in one is a leaked
credential. If the variable is not exported, Gogo says so by name rather than
connecting anonymously and letting the server's 401 look like an outage.

A remote server that restarts forgets every session it had, and answers the
next call with HTTP 404 "Session not found". Gogo then opens a new session and
sends that call once more, as the MCP spec asks of a client. Calls that find
the session gone at the same moment share one new session.

### Signing in instead of holding a key

A server that speaks MCP's authorization spec needs no key at all. Say so, and
Gogo opens your browser on first use:

```json
{"servers": [{"name": "gogo_memory",
              "url": "https://your-host/mcp",
              "oauth": true}]}
```

Nothing is issued out of band and nothing is pasted anywhere. Gogo registers
itself with the server, catches the redirect on `127.0.0.1:41765`, and keeps
the result in `~/.gogo/mcp-auth/<server>.json`, written `0600` — one file per
server, so a corrupt one costs a single connection rather than all of them.
Delete that file to sign out.

`oauth` and `auth_env` are two answers to one question, so naming both is
refused rather than resolved by precedence.

### Which account am I signed in as?

```bash
gogo mcp                      # every server, and the account each knows you as
gogo mcp login gogo_memory    # sign in again — as someone else, or after expiry
gogo mcp logout gogo_memory   # forget the token
```

Two agents pointed at the same server as two different people look exactly
like a broken server: you write something in one and the other cannot find it.
`gogo mcp` prints the email, so the mismatch is visible in one line instead of
inferred from missing memories.

`login` signs out first on purpose. Without that the stored token is still
valid, the server never asks who you are, and "sign in as someone else"
silently keeps the account you were trying to leave.

Headless or over SSH there is no browser to open: the authorization URL is
printed, and you can finish the sign-in from any machine that has one.

Try it against the demo server, no remote host required:

```bash
python evals/fixtures/mcp_demo_server.py --http --port 8931
# .gogo/mcp.json → {"servers": [{"name": "demo", "url": "http://127.0.0.1:8931/mcp"}]}
```

Requires `mcp>=2.1` (`pip install -e '.[mcp]'`). The 1.x SDK spelled this
transport differently and the remote branch does not work on it.

