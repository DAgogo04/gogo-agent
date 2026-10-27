# Conventions

How changes get made in gogo-agent, for humans and coding agents alike. A rule
that a test can enforce belongs in the test instead of here; the CI workflows
under `.github/workflows/` are the list of what actually blocks a merge.

## 1. Language

Everything written into the repo is English: code, comments, docs, commit
messages, and issue and PR titles. Conversation can be in any language.

## 2. How much process a change needs

Process scales with how much work is thrown away if the change is wrong, and
with whether it changes something other code depends on. Line count does not
decide it.

| Tier | Examples | What to do |
|---|---|---|
| **Direct** | a bug fix, a copy change, a provider row, a skill, a test | Open the PR. The eval and the review are the guardrails. |
| **Short plan** | a tool behind an extra, a gateway, a dashboard view | Comment a 5–10 line plan on the issue before writing code, so a maintainer can point at the right rung early. |
| **Proposal** | a new top-level package; a change to the loop, the memory interfaces, the graph engine or the tool-call contract; a new core tool; anything that adds to every prompt | Write a design doc in `docs/` and get a maintainer's yes before any code. [agent-graphs-design.md](../agent-graphs-design.md) is the precedent and shows the bar. |

If you are unsure which tier you are in, ask on the issue. That conversation
costs less than a rejected PR.

## 3. Where new capability goes: the footprint ladder

The core is a narrow waist, and capability belongs at the edges. Every tool
Gogo registers is sent to the model on every call, so the bar for adding one
is deliberately high. Start at the top of this ladder and move down only when
the rung above cannot do the job:

1. **Extend something that already exists.** A new provider is one table in
   `gogo/providers.toml` plus a logo — see
   [providers-registry.md](../providers-registry.md). A new memory backend
   matches an existing interface.
2. **A skill**: `skills/contributed/<name>/SKILL.md`. It is Markdown with no
   Python, and it costs no context until the model needs it.
3. **A CLI and a README.** Gogo can already run any program on your machine,
   and a command-line tool with docs beside it costs nothing until it is used.
4. **A tool behind an extra**: `gogo/tools/`, with heavy dependencies gated by
   an extra and off by default.
5. **A gateway**: one file in `gogo/gateway/`. Gateways only move text: in
   through `gogo.respond()` and out again, with no memory, tools or loop logic.
6. **A new core tool, as a last resort.** It has to earn its place in every
   prompt.

The ladder has no rung for a new top-level package (like `gogo/graph/`). That
is an architecture decision and needs a proposal (§2).

## 4. Testing

- `evals/deterministic/` holds 0/1 tests that run offline with no API key.
  `evals/judge/` holds scored LLM-judge evals. The two never mix: one is a unit
  test, and the other is a scored opinion.
- Every behaviour change gets a deterministic eval. A bug fix adds the case
  that would have caught the bug.
- **Prove the test can fail.** Break the thing it guards, watch it go red, put
  it back. A test that has never failed has never been tested. Say in the PR
  what you broke.
- Three shapes that pass forever, all three found in this repo: comparing a
  value to the constant that sets it (`assert payload["X"] == module.X` holds
  for every value of `X`, zero included); resting on a number that happens to
  equal a library default; and a `pytest.raises(match=...)` needle that matches
  pytest's `tmp_path`, which spells the test's own name, rather than the
  message the code writes. Pin the literal, or assert the behaviour.
- Never assert that a string appears in source. A test that greps for a
  function's name passes whether or not the function works, and keeps passing
  after it is deleted and written again wrong. Import it and call it.
- Write a guard as a closed set: allow what is named, refuse the rest. A guard
  that enumerates the ways to go wrong is a guess about an open set.
- A new route in `gogo/ops/dashboard.py` needs two things beyond its handler:
  a pin in `evals/deterministic/test_dashboard_routes.py`, and a decision in
  `hosted/core/policy.py` about whether the hosted gateway passes, filters or
  blocks it. `test_route_contract.py` fails until you make that decision, and
  it does not guess a default for you.
- Run `make gate` and `make lint` before you push. CI runs the deterministic
  tier. The judge tier needs a key, so only `make gate` runs it.
- The dashboard's JavaScript has no test runner. Verify a frontend change in a
  browser, as [gogo/ops/static/README.md](../../gogo/ops/static/README.md)
  describes.

## 5. Git, commits and PRs

- `main` is protected. Every change lands through a PR whose checks pass, and a
  maintainer squash-merges it.
- **A commit message is about the code, not the conversation.** The subject
  says what changed, in under about 70 characters. The body says why, in a few
  lines, and then stops. Leave out who asked for it, what you tried first and
  the story of the session: a stranger reading `git log` wants the change.
  Reasoning worth keeping goes in a code comment next to the code it explains.
- One logical change per commit. A `uv.lock` change only rides along with a
  `pyproject.toml` change.
- A PR says how it was tested: the commands, and what you saw.

## 6. examples/

`examples/` holds material that is not the product, with one job:

- **`examples/` holds short, self-contained setups.** Each one is a file a
  stranger can run in one command to see exactly one thing, like
  `tiny_memory_agent.py`, which shows the loop's three steps with nothing else
  in frame.

`evals/deterministic/test_rulebook.py` enforces the first three rules:

1. **Nothing under `gogo/` or `evals/` imports from `examples/`.** The
   dependency runs one way, always.
2. **`examples/` never ships.** The wheel packages only `gogo/`, and the source
   distribution excludes `examples/`.
3. **`make gate` never depends on examples.** A third-party SDK shipping a
   breaking release is their problem, not a red CI. A server that a test needs
   lives in `evals/fixtures/`.
4. **No new default dependencies.** Use the stdlib or an extra that already
   exists, or state the `pip install` in the file's own header.
5. **Anything that uses someone else's SDK carries a dated header** naming the
   version it was verified against. A silently rotted example is worse than no
   example.

**Whiteboards.** `docs/whiteboards/` holds only boards that explain this
codebase. The drawing toolkit is `scripts/whiteboard/`, and it never ships.

## 7. Dependencies and extras

The default install is the stdlib plus the Anthropic and OpenAI clients. An
optional feature goes behind an extra in `pyproject.toml`, and it fails with an
install hint, not a crash, when the extra is missing. A new core dependency
needs a discussion on an issue first.

## 8. Scope and framing

Scheduling is the flagship example task, but the project is growing toward a
full assistant. New providers, tools, gateways and integrations are welcome
when they are self-contained, tested, and keep the core legible. We decline
complexity that muddies how the system works or bloats the default path, and
we prefer opt-in extras.

Docs name providers neutrally (Anthropic, OpenAI, Gemini, DeepSeek, Kimi, GLM,
OpenRouter): no ranking, and no "open-source versus closed" framing.

## 9. The rulebook: what each file holds and how it grows

| File | Holds | How it grows |
|---|---|---|
| `docs/context/conventions.md` | process, testing, git, scope | Replace, never append. |
| `docs/architecture.md` | the system, and which file is which box | Present tense. A change that makes a sentence false fixes it in the same PR. |
| `docs/context/design-system.md` | how the dashboard looks, and which primitive to use | Changes with the design files. |
| `docs/context/writing-rules.md` | how we write English for a reader | A rule arrives with the Bad/Good pair that produced it. A rule that two others cover is deleted. |
| `docs/context/gotchas.md` | traps someone already stepped on | The only append-only file. Every entry has a date and a `Retire when:`; 40 entries at most (test). Anyone deletes an entry that no longer holds. |
| `docs/status.md` | what works, what is known-broken, what is deliberately not built | Rewritten whole, never appended; 120 lines at most (test). It holds no decisions. |

A rule that can become a test becomes one: write the test, add the check to
the CI workflow, and delete the sentence here.
