# docs — what is in here

This folder holds the documentation, sorted into four groups.

## Start here

- [getting-started.md](getting-started.md) — install, the first run, and
  optional integrations, with a check at the end of every step.
- [tour.md](tour.md) — the dashboard, things to try, the loop, graph workflows
  and skills.
- [status.md](status.md) — what works, what is known-broken, what is
  deliberately not built.

## The rulebook

| file | what it answers |
|---|---|
| [context/conventions.md](context/conventions.md) | how much process a change needs, where capability goes, testing, git, scope |
| [context/design-system.md](context/design-system.md) | how the dashboard looks, and which primitive to use |
| [context/writing-rules.md](context/writing-rules.md) | how docs, UI copy and commit messages are written |
| [context/gotchas.md](context/gotchas.md) | traps already found and fixed |

## Reference — how the system works

| file | what it answers |
|---|---|
| [architecture.md](architecture.md) | the four pillars, and which file is which diagram box |
| [loop-vs-graph.md](loop-vs-graph.md) | when a turn needs shape, and why the loop never changes |
| [agent-graphs-design.md](agent-graphs-design.md) | the graph engine's design and its fail-open rule |
| [providers-registry.md](providers-registry.md) | adding a model provider: one table in `gogo/providers.toml` |
| [memory-backends-playbook.md](memory-backends-playbook.md) | seeing your memories in each provider's own console |
| [benchmarks.md](benchmarks.md) | what has been measured, and how |
| [integrations.md](integrations.md) | voice, Telegram, Apple, Google Calendar, MCP — all opt-in |
| [commands.md](commands.md) | every `gogo` and `make` command |
| [evals.md](evals.md) | the two kinds of eval, the release gate, traces and spend |
| [roadmap.md](roadmap.md) | what is live, what is still a skeleton, upgrade paths |

## Whiteboards

Every whiteboard is an **editable `.excalidraw` source**: download one, drop it
on [excalidraw.com](https://excalidraw.com), and remix it.

| Chart | What it explains |
|---|---|
| [`gogo-architecture.excalidraw`](whiteboards/gogo-architecture.excalidraw) | Gogo itself — harness, loop, memory pillars, LLM Ops (editable rebuild of [the whiteboard](architecture-whiteboard.png)) |
| [`loop-vs-graph.excalidraw`](whiteboards/loop-vs-graph.excalidraw) | Loop vs graph engineering — the ladder, and two timelines from a measured run of `gogo brief` against `gogo gather` ([the write-up](loop-vs-graph.md)) |
| [`memory-anatomy.excalidraw`](whiteboards/memory-anatomy.excalidraw) | the three memory kinds and where each lives |
| [`memory-in-harness.excalidraw`](whiteboards/memory-in-harness.excalidraw) | memory inside the harness |

`scripts/whiteboard/build_*.py` generates the boards so they stay in sync with
the diagrams; edit the builder, not the generated JSON.

## Deliberately not in docs/

- [../examples/](../examples/README.md) — short runnable example setups.
