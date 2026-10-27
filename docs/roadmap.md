# Roadmap

The whiteboard has boxes beyond the flagship scheduling task. This page says
which ones are live, which are still skeletons, and how each default upgrades
when you outgrow it.

## The boxes beyond the flagship task

These live in [`gogo/tools/experimental.py`](../gogo/tools/experimental.py),
off by default; `GOGO_EXPERIMENTAL=1` registers them.

**Sub-Agents is live.** `delegate_task` hands a coding job to
[pi](https://github.com/earendil-works/pi) — Mario Zechner's minimal
open-source coding agent — through its headless print mode (`pi -p "task"`).
Gogo stays the orchestrator (memory, context, evals); pi is the specialist
contractor (read/bash/edit/write). Try it:

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
GOGO_EXPERIMENTAL=1 uv run gogo
# "have pi fix the failing test in ~/my-project"
```


The rest are still deliberate **skeletons**: the intent is drawn so the diagram
maps to something, but nothing is over-promised. They report "coming soon",
and the dashboard's **Tools** tab lists them under **Coming soon**:

| Whiteboard box | Tool | Status |
|---|---|---|
| Sub-Agents | `delegate_task` | **live** — delegates coding tasks to pi |
| Graph workflows | [`gogo/graph/`](../gogo/graph) | **live** behind `GOGO_GRAPH_WORKFLOWS=1` — [triage-first turns](tour.md#graph-workflows) |
| Terminal tool | `run_command` | skeleton — needs a real sandbox + safety surface first |
| Browser tool | `browse_web` | skeleton — `search_web` already covers read-only lookups |
| Cron Job | `schedule_task` | skeleton — `make brief` + a system cron line covers it today |

A small, readable core is the point, so these come alive one at a time,
tested.

## Upgrade paths

| Default (zero setup) | Upgrade | How |
|---|---|---|
| SQLite FTS5 keyword memory | Supabase pgvector semantic search | `GOGO_SEMANTIC_STORE=supabase` + [sql/init_supabase.sql](../sql/init_supabase.sql) |
| Mock calendar (ICS + SQLite) | Apple / Google Calendar | `GOGO_APPLE_CALENDAR=1` (macOS) or `GOGO_GOOGLE_CALENDAR=1` with `pip install -e '.[gcal]'` — the tool schema stays |
| Hand-built memory pillars | mem0 / Zep / LangMem | `pip install -e '.[arena]'` and set `GOGO_SEMANTIC_STORE` — then race them against each other in the Arena's Memory tab. [Where to see your memories in each provider's own console](memory-backends-playbook.md) |
