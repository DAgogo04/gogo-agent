# Commands

The `gogo` command is installed with the package. In a checkout, the `make`
targets are aliases for the same things, plus the eval and tracing tools.

## gogo

| Command | Does |
|---|---|
| `gogo` | chat in the terminal |
| `gogo dashboard` | the live cockpit at localhost:7777 (+ Telegram if `TELEGRAM_BOT_TOKEN` is set) |
| `gogo voice` | talk to it — the "gogo gogo" wake word, or push-to-talk (needs the `[voice]` extra) |
| `gogo telegram` | message it from your phone (needs `TELEGRAM_BOT_TOKEN`) |
| `gogo discord` | answer in a Discord server (needs `DISCORD_BOT_TOKEN`) |
| `gogo whatsapp` | answer WhatsApp messages (needs `WHATSAPP_TOKEN` and a public URL) |
| `gogo brief` | a morning briefing from calendar + mail + memory, run as a loop |
| `gogo gather` | the same job as a graph: four sources fetched together, then one digest |
| `gogo evals turns` | grade your own traced turns with the five turn checks and list the failing ones (`--window today`, `7d` or `all`) |
| `gogo connections` | every integration and its health |
| `gogo connect google` | sign in to Google Calendar (opens your browser) |
| `gogo mcp` | MCP servers, and which account each one knows you as |
| `gogo mcp login <name>` | sign in again — as someone else, or after expiry |
| `gogo mcp logout <name>` | forget a server's token |
| `gogo skill install <url>` | install a skill from a GitHub or Gist link |
| `gogo skill export --to claude,codex` | copy Gogo's skills to Claude Code and Codex (`--project` for `./.claude/skills`, `--force` to replace) |

In the dashboard chat, `/connect google` does the same as its
`gogo connect` command, and `/help` lists the graph workflows.

## make

| Command | Does |
|---|---|
| `make run` | chat with Gogo in the terminal |
| `make dashboard` | the dashboard at localhost:7777 (restart it after pulling backend changes) |
| `make voice` | push-to-talk, or always-on with `GOGO_WAKE_WORD` |
| `make telegram` · `make discord` · `make whatsapp` | the messaging gateways |
| `make brief` · `make gather` | the morning briefing, as a loop or as a graph |
| `make eval` | deterministic evals (0/1, no judge involved) |
| `make eval-judge` | LLM-as-judge evals (scored %, needs an API key) |
| `make gate` | the release gate: deterministic must pass, judge must clear its threshold |
| `make lint` | ruff over the code and the evals |
| `make trace` | trace waterfalls in Phoenix at localhost:6006 |
| `make shootout RUNS="…"` | the same tasks on different models, e.g. `RUNS="kimi:kimi-k3 anthropic:claude-opus-4-8"` |
| `make shootout-coding RUNS="…"` | a coding round through pi, scored by tests |

Tests live in `evals/`, not `tests/`. [evals.md](evals.md) explains the two
kinds.
