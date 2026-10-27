# Getting started

Five steps take you from nothing to a Gogo that remembers you. Each step ends
with a check, so you know it worked before you move on. Everything runs on your
own machine.

## 1. Install

```bash
pip install gogo-agent
```

To read or change the code, clone it instead:

```bash
git clone https://github.com/DAgogo04/gogo-agent && cd gogo-agent
uv venv && uv pip install -e .
```

### Other ways to run it

In a checkout, `uv run gogo …` needs no venv activation. Three ways to run it:

| Command | When |
|---|---|
| `uv run gogo dashboard` | quick start, zero activation (recommended) |
| `source .venv/bin/activate` → `gogo dashboard` | activate once, bare `gogo` all session |
| `uv tool install .` → `gogo dashboard` | install `gogo` **globally**, forever |

**Check:** `gogo connections` prints a list of integrations.

## 2. Add one key

```bash
cp .env.example .env
```

Set `GOGO_PROVIDER=` and paste that provider's key. Anthropic is the default;
OpenAI, Gemini, DeepSeek, MiniMax, Kimi, GLM, OpenRouter, OpenCode Zen and
OpenCode Go work the same way. You can also paste a key in the dashboard
later. Either way the key stays in a `.env` on your machine and is never sent
to the browser.

Gogo reads a model key from three places, and the first one that has it wins:
environment variables set before Gogo starts, the `.env` in the folder you run
Gogo from (or the nearest folder above it), and `~/.gogo/.env`. A key you paste
in the dashboard goes to the folder's `.env` when there is one, and to
`~/.gogo/.env` when there is not, so Gogo finds it from any folder. When Gogo
finds no key, the dashboard's "Set up Gogo" page lists the paths it checked,
and `gogo connections` prints the same list under "Model key". A git worktree
does not see the main checkout's `.env`: start Gogo in the main checkout, or
copy the key's line into `~/.gogo/.env`.

**Check:** run `gogo` and say hi. It answers in the terminal.

## 3. Open the dashboard

```bash
gogo dashboard          # → http://localhost:7777
```

`gogo` and `gogo dashboard` are two doors into the **same** Gogo. The dashboard
is a small web server on your machine (`127.0.0.1`): the browser is the UI, and
the same process runs every turn. Set `TELEGRAM_BOT_TOKEN` and it starts your
Telegram bot too.

**Check:** send a message from the chat dock and watch the Overview diagram
light up as it flows through the harness.

## 4. Watch it remember

Say *"Remember that Sam prefers morning meetings."* Quit, and restart. Then
say *"Book a meeting with Sam next week."*

**Check:** it books 9am, and **Memory ▸ Semantic** lists the fact. Your memory
is one file: `~/.gogo/state.db`, the same from every folder. Set `GOGO_HOME`
to keep it somewhere else. If you ran Gogo before v0.2, your memory is in the
`.gogo/` folder you ran it from, and Gogo keeps using it there until you copy
it: `mkdir -p ~/.gogo && cp -R ./.gogo/. ~/.gogo/`.

## 5. Live data for research (optional)

[treg](https://treg.to) is an MCP server with search results, keyword data,
companies, people, social profiles and web pages behind it. With it
connected, research questions are answered from live sources on your own
treg account:

```bash
pip install 'gogo-agent[mcp]'           # in a checkout: uv pip install -e '.[mcp]'
gogo connect treg                       # or /connect treg in the dashboard chat
```

**Check:** `gogo connections` lists treg as connected, and so does the
**Connections** page. More in
[integrations](integrations.md#live-data-for-research-treg).

## Next

- [The tour](tour.md): the dashboard's tabs, things to try, and the loop up close.
- [Integrations](integrations.md): voice, Telegram, calendars and MCP servers.
- [Commands](commands.md): every `gogo` and `make` command.
