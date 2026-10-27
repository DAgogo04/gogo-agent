# Status

**What is true right now.** Rewritten whole when it changes, never appended to
— a status file that grows is a changelog, and git already is one.

Read this before opening a PR or filing an issue: most of what is already
known-broken is below, and half of it already has a fix in flight.

**Last updated:** 2026-09-23

---

## What works

The four pillars run: the loop, memory (semantic + episodic + procedural with
a retrieval gate), tools, and both eval tiers. `gogo`, `gogo dashboard`,
`gogo voice`, `gogo telegram`, `gogo discord`, `gogo brief` and
`gogo connect google` all start.

**The deterministic evals pass offline**, with no API key; the live evals
skip without one. CI runs the offline tier on every change along with
ruff, the skills validator, and a check that `.env.example` still matches the
integrations registry.

**Versioning lives in `gogo/__init__.py`**.

**The dashboard uses the local design system in this repo**, and
`test_design_system.py` keeps it from drifting. See
[context/design-system.md](context/design-system.md).

## Known broken

Nothing here is a surprise. If you hit one of these, the issue exists.

| What | Notes |
|---|---|
| The model picker can offer models that 404 on use | treat the picker as a list of things that *might* work |
| Some providers' tool calls can fail on Chat Completions | provider-specific |
| Google Calendar sign-in needs your own `~/.gogo/credentials.json` | run `gogo connect google` with your own OAuth client |

**Providers are the recurring theme.** Three of the items above are one
provider or another, and there is no single place that says which providers
are known-good today. Until there is, treat the model picker as a list of
things that *might* work.

## What is deliberately not built

Not a framework and not a multi-agent system — true of `gogo/`, see
[architecture.md](architecture.md). Everything runs on your own machine.

Additionally, and worth stating because people ask:

- **No Windows CI.** Every Windows claim in this repo is untested.
- **The judge evals are not in CI.** `make gate` runs deterministic evals at
  100% plus a judge threshold, and CI runs only the first half. The judge tier
  needs an API key, which CI does not have.
- **No provider smoke check.** Nothing verifies that a model in the picker
  resolves, which is why #137 reached a user.

## Open questions

1. **Local memory vs optional external servers.** This repo's memory is
   local, single-machine, and yours. Optional MCP servers can extend memory
   and tools, but none are configured or required out of the box.

## Not in the repo

Deliberately absent, so nobody goes looking:

- Session handoffs — this file replaces them
- Plans and specs — they belong with the work, not in `docs/`
