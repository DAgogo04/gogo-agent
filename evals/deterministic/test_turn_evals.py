"""DETERMINISTIC EVAL — turn checks that grade a person's own turns (spec 015).

Five code checks read one turn's trace and answer pass (1), fail (0) or n/a
(None). The fixtures in evals/fixtures/turns/ are real or rebuilt turns, each
line passed through redact(): the rehearsal turn whose reply said the
research cost "$0.00" while treg charged $0.0089 must fail, and a turn that
truthfully used a free preview must pass.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from gogo.ops import observability as obs
from gogo.ops import turn_evals as te

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "turns"
REHEARSAL = "2026-10-05-rehearsal-zero-claim.jsonl"
V1_TURN = "2026-10-03-v1-research-turn.jsonl"
NOW = datetime(2026, 10, 5, 18, 0).astimezone()  # local-time evening, the fixtures' local day


def _events(name: str) -> list[dict]:
    return [json.loads(line) for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines()]


def _turn(name: str) -> dict:
    turns = obs.group_turns(_events(name))
    assert len(turns) == 1
    return turns[0]


def _scores(turn: dict) -> dict[str, dict]:
    built = obs.build_turn(turn)
    return {s["name"]: s for s in built["scores"] if s["source"] == "code"}


def _tool(name, output, *, ok=None, turn_id="t_abc123", **extra):
    ev = obs.trace_record({"tool": name, "args": {}, "output": output}, turn_id=turn_id)
    if ok is not None:
        ev["ok"] = ok
    return {"type": "tool", **ev, **extra}


def _made(message, reply, events=(), turn_id="t_abc123"):
    return {"turn_id": turn_id, "ts": "2026-10-05T10:00:00+00:00", "user_message": message,
            "reply": reply, "events": list(events)}


def _check(name, turn, usd=0.1):
    return te.CHECKS[name](te.view(turn, usd=usd))


TREG = json.dumps({"status": 200, "endpoint_id": "tomba.companies.similar", "cost_usd": 0.0089})


# ---- B0: the fixtures load --------------------------------------------------

@pytest.mark.parametrize("name", sorted(p.name for p in FIXTURES.glob("*.jsonl")))
def test_every_fixture_loads_through_group_turns(name):
    turn = _turn(name)
    assert turn["reply"] and not turn.get("unfinished")
    # redacted: nothing key-shaped survives
    assert obs.redact(_events(name)) == _events(name)


# ---- 1, 2. spend_claim ------------------------------------------------------

def test_spend_claim_fails_the_rehearsal_turn_and_names_both_figures():
    check = _scores(_turn(REHEARSAL))["spend_claim"]
    assert check["value"] == 0
    assert check["note"] == "reply says $0.00; this turn's treg calls cost $0.0089"


def test_spend_claim_is_na_for_a_price_offered_for_later():
    turn = _made("research mem0", "Want me to enrich them? That'd run ~$0.002 each.",
                 [_tool("treg_call", TREG)])
    assert _check("spend_claim", turn)["value"] is None


def test_spend_claim_checks_a_named_treg_figure_against_the_trace():
    ok = _made("x", "The treg cost was $0.0089.", [_tool("treg_call", TREG)])
    off = _made("x", "The treg cost was $0.40.", [_tool("treg_call", TREG)])
    assert _check("spend_claim", ok)["value"] == 1
    bad = _check("spend_claim", off)
    assert bad["value"] == 0 and "$0.40" in bad["note"] and "$0.0089" in bad["note"]


def test_spend_claim_passes_a_free_claim_when_treg_charged_nothing():
    free = json.dumps({"status": 200, "endpoint_id": "leadscout.companies.lookalike.preview",
                       "cost_usd": 0.0})
    turn = _made("x", "This research cost nothing: it used a free preview.",
                 [_tool("treg_call", free)])
    assert _check("spend_claim", turn)["value"] == 1


# ---- 3. one_report ----------------------------------------------------------

def test_one_report_fails_a_research_turn_with_no_report():
    turn = _made("research the competitors of Letta", "Letta competes with Zep.",
                 [_tool("search_web", "Web results: Letta, Zep")])
    check = _check("one_report", turn)
    assert check["value"] == 0
    asked = _made("research the competitors of Letta and save a report", "Letta competes with Zep.")
    assert _check("one_report", asked)["value"] == 0


def test_one_report_fails_two_reports():
    assert _scores(_turn("two-reports.jsonl"))["one_report"]["value"] == 0


def test_one_report_passes_one_report_or_the_marker():
    turn = _made("research the competitors of Letta", "Letta competes with Zep.",
                 [{"type": "report", "turn_id": "t_abc123", "memory_id": "m1", "title": "Letta"}])
    assert _check("one_report", turn)["value"] == 1
    marker = _made("research the competitors of Letta",
                   "Letta competes with Zep.\n\n<!-- gogo-report v1 -->\n# Letta\n")
    assert _check("one_report", marker)["value"] == 1
    assert _scores(_turn(REHEARSAL))["one_report"]["value"] == 1


def test_one_report_is_na_for_an_everyday_message():
    assert _check("one_report", _made("what's on my calendar", "Nothing today."))["value"] is None


# ---- 4. grounded_numbers ----------------------------------------------------

SOURCE = json.dumps({"revenue_usd": 1200, "share": 0.04, "founded": "2026-10-05",
                     "employees": 37, "growth_pct": 12})


def test_grounded_numbers_matches_other_formats():
    reply = "They earn $1,200 a month, hold $0.04 of share, have 37 staff, grew 12% and launched Oct 5, 2026."
    check = _check("grounded_numbers", _made("x", reply, [_tool("search_web", SOURCE)]))
    assert check["value"] == 1, check["note"]


def test_grounded_numbers_fails_an_invented_figure_and_names_it():
    reply = "They earn $1,200 a month, raised $4.2M, have 37 staff and grew 12%."
    check = _check("grounded_numbers", _made("x", reply, [_tool("search_web", SOURCE)]))
    assert check["value"] == 0 and "$4.2M" in check["note"]


def test_grounded_numbers_is_na_below_three_numbers_and_skips_code_and_lists():
    assert _check("grounded_numbers", _made("x", "They have 37 staff."))["value"] is None
    reply = "1. First\n2. Second\n```\nlimit=55 offset=99 page=12\n```\nThey have 37 staff, the 21st entry."
    assert _check("grounded_numbers", _made("x", reply, [_tool("search_web", SOURCE)]))["value"] is None


def test_grounded_numbers_reads_the_users_message_too():
    reply = "You asked about 2026 budgets of $500, $700 and $900."
    check = _check("grounded_numbers", _made("compare budgets of 500, 700 and 900 for 2026", reply))
    assert check["value"] == 1, check["note"]


# ---- 5. errors_handled ------------------------------------------------------

FAILED = "Search failed: the request timed out"


def test_errors_handled_passes_a_retried_failure():
    turn = _made("x", "Supermemory shipped an SDK.",
                 [_tool("search_web", FAILED), _tool("search_web", "Web results: Supermemory SDK")])
    assert _check("errors_handled", turn)["value"] == 1


def test_errors_handled_passes_a_mentioned_failure():
    turn = _made("x", "The web search didn't work, so this is from memory.", [_tool("search_web", FAILED)])
    assert _check("errors_handled", turn)["value"] == 1
    # the 2026-10-02 reply: "Memory save hit a session error"
    assert _scores(_turn(V1_TURN))["errors_handled"]["value"] == 1


def test_errors_handled_fails_a_silent_failure():
    check = _scores(_turn("silent-failure.jsonl"))["errors_handled"]
    assert check["value"] == 0 and "search_web" in check["note"]


def test_errors_handled_is_na_with_no_failure():
    turn = _made("x", "Done.", [_tool("search_web", "Web results: fine")])
    assert _check("errors_handled", turn)["value"] is None


# ---- 6. under_budget --------------------------------------------------------

def test_under_budget_fails_a_134_turn_at_the_default(monkeypatch):
    monkeypatch.delenv(te.BUDGET_ENV, raising=False)
    check = _scores(_turn("over-budget.jsonl"))["under_budget"]
    assert check["value"] == 0 and check["note"] == "$1.34 is over the $1.00 budget"
    assert _scores(_turn(REHEARSAL))["under_budget"]["value"] == 1


def test_under_budget_reads_the_budget_from_the_environment(monkeypatch):
    monkeypatch.setenv(te.BUDGET_ENV, "2.50")
    check = _scores(_turn("over-budget.jsonl"))["under_budget"]
    assert check["value"] == 1 and "$2.50" in check["note"]
    monkeypatch.setenv(te.BUDGET_ENV, "not a number")
    assert te.budget_usd() == te.DEFAULT_BUDGET_USD


# ---- 7. build_turn ----------------------------------------------------------

def test_build_turn_returns_the_five_code_scores():
    built = obs.build_turn(_turn(REHEARSAL))
    code = [s for s in built["scores"] if s["source"] == "code"]
    assert [s["name"] for s in code] == list(te.TURN_CHECKS)
    assert all(set(s) == {"source", "name", "value", "note"} for s in code)


def test_a_check_that_raises_is_na_and_the_page_still_builds(monkeypatch, tmp_path):
    def broken(_view):
        raise RuntimeError("boom")

    monkeypatch.setitem(te.CHECKS, "spend_claim", broken)
    built = obs.build_turn(_turn(REHEARSAL))
    check = next(s for s in built["scores"] if s["name"] == "spend_claim")
    assert check["value"] is None and check["note"] == "check error"
    (tmp_path / "traces").mkdir()
    (tmp_path / "traces" / "2026-10-05.jsonl").write_text((FIXTURES / REHEARSAL).read_text())
    assert obs.payload(tmp_path, window="all", now=NOW)["turns"]


# ---- 8. an old (v1) trace ---------------------------------------------------

def test_a_v1_trace_gets_the_checks_and_v2_only_checks_are_na():
    scores = _scores(_turn(V1_TURN))
    assert set(scores) == set(te.TURN_CHECKS)
    assert scores["one_report"]["value"] is None and scores["grounded_numbers"]["value"] is None
    assert scores["spend_claim"]["value"] == 1 and scores["under_budget"]["value"] == 1


# ---- 9. Your turns on the Evals page ----------------------------------------

def _home(tmp_path, names):
    (tmp_path / "traces").mkdir(parents=True)
    lines = [line for n in names for line in (FIXTURES / n).read_text(encoding="utf-8").splitlines()]
    (tmp_path / "traces" / "2026-10-05.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def test_the_evals_payload_counts_each_check_per_window(tmp_path):
    home = _home(tmp_path, [V1_TURN, REHEARSAL, "two-reports.jsonl", "silent-failure.jsonl"])
    yours = obs.payload(home, window="7d", now=NOW)["evals"]["your_turns"]
    assert set(yours) == set(obs.WINDOWS)
    rows = {r["name"]: r for r in yours["all"]["checks"]}
    assert list(rows) == list(te.TURN_CHECKS)
    spend = rows["spend_claim"]
    assert (spend["passed"], spend["failed"], spend["na"]) == (1, 1, 2)
    assert spend["pass_rate"] == 0.5
    assert spend["newest_fail"]["turn_id"] == "t_5e1f0c2a9b7d4e36"
    assert spend["newest_fail"]["note"] == "reply says $0.00; this turn's treg calls cost $0.0089"
    # the 2026-10-02 trace's turn ran at 2026-10-03 18:58 UTC: inside 7 days, not today
    assert yours["7d"]["turns"] == 4 and yours["today"]["turns"] == 3
    assert yours["all"]["judge"] == {"judged": 0, "average": None, "passed": 0}
    # the Overview's "your turns n/m": only the 2026-10-02 turn passed every check
    assert (yours["all"]["turns_passed"], yours["all"]["turns_scored"]) == (1, 4)


# ---- 6. the command ---------------------------------------------------------

def test_gogo_evals_turns_prints_the_failing_rehearsal_turn(tmp_path, capsys):
    home = _home(tmp_path, [V1_TURN, REHEARSAL])
    print(te.report(home, "all"))
    out = capsys.readouterr().out
    assert "spend_claim" in out and "t_5e1f0c2a9b7d4e36" in out
    assert "reply says $0.00; this turn's treg calls cost $0.0089" in out
    assert te.cli_main(["--window", "year"]) == 2


def test_the_cli_routes_evals_turns(monkeypatch, capsys):
    import gogo.__main__ as entry

    seen = []
    monkeypatch.setattr(te, "cli_main", lambda argv: seen.append(argv) or 0)
    monkeypatch.setattr("sys.argv", ["gogo", "evals", "turns", "--window", "all"])
    with pytest.raises(SystemExit) as done:
        entry.main()
    assert done.value.code == 0 and seen == [["--window", "all"]]


# ---- 10, 11. the AI judge, on demand (group B) -------------------------------

class _FakeMessages:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def create(self, **kwargs):
        from types import SimpleNamespace

        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.answer)],
                               usage=SimpleNamespace(input_tokens=1200, output_tokens=60))


class _FakeClient:
    def __init__(self, answer='{"addresses_question": 9, "grounded": 3, "reason": "says $0.00; Tomba charged"}'):
        self.messages = _FakeMessages(answer)


@pytest.fixture(autouse=False)
def judged_home(tmp_path):
    te._RECENT.clear()
    return _home(tmp_path, [REHEARSAL])


TID = "t_5e1f0c2a9b7d4e36"


def test_the_judge_prompt_comes_from_the_stored_turn_only(judged_home):
    turn, _ = te.find_turn(judged_home, TID)
    prompt = te.judge_prompt(turn)
    assert "The research cost $0.00" in prompt and "tomba.companies.similar" in prompt
    assert "research with treg the competitors of mem0 and zep.ai" in prompt
    outputs = prompt.split("each cut to 800 characters):")[1]
    assert all(len(line) <= te.OUTPUT_CHARS + 40 for line in outputs.splitlines() if line.startswith("["))


def test_the_judge_writes_one_score_event_with_cost_and_model(judged_home):
    client = _FakeClient()
    event = te.judge_turn(judged_home, TID, client, "claude-haiku-4-5-20251001", "anthropic", now=1e9)
    assert len(client.messages.calls) == 1 and client.messages.calls[0]["max_tokens"] == 300
    assert event["value"] == 0.3 and event["source"] == "judge" and event["check"] == "answer_grounded"
    assert event["judge"] == "claude-haiku-4-5-20251001"
    assert event["cost_usd"] == obs.llm_cost("anthropic", "claude-haiku-4-5-20251001", {"in": 1200, "out": 60})
    lines = [json.loads(x) for p in (judged_home / "traces").glob("*.jsonl")
             for x in p.read_text().splitlines()]
    written = [e for e in lines if e["type"] == "score"]
    assert len(written) == 1 and {k: v for k, v in written[0].items() if k != "ts"} == event
    assert written[0]["ts"]
    ledger = [json.loads(x) for x in (judged_home / "usage.jsonl").read_text().splitlines()]
    assert ledger[0]["kind"] == "judge" and ledger[0]["in"] == 1200
    # the page shows the judge's chip, with the model named in its note
    turn = obs.payload(judged_home, window="all", now=NOW)["turns"][0]
    judge = [s for s in turn["scores"] if s["source"] == "judge"]
    assert judge[0]["value"] == 0.3 and judge[0]["judge"] == "claude-haiku-4-5-20251001"
    assert "judged by claude-haiku-4-5-20251001" in judge[0]["note"]


def test_the_judge_refuses_an_unknown_turn_and_a_repeat_within_a_minute(judged_home):
    with pytest.raises(te.JudgeRefused):
        te.judge_turn(judged_home, "t_ffffffffffffffff", _FakeClient(), "m", "anthropic")
    with pytest.raises(te.JudgeRefused):
        te.judge_turn(judged_home, "../etc/passwd", _FakeClient(), "m", "anthropic")
    te.judge_turn(judged_home, TID, _FakeClient(), "m", "anthropic")
    with pytest.raises(te.JudgeRefused, match="less than a minute"):
        te.judge_turn(judged_home, TID, _FakeClient(), "m", "anthropic")
    # a restarted dashboard still refuses: the score's own timestamp says so
    te._RECENT.clear()
    with pytest.raises(te.JudgeRefused, match="less than a minute"):
        te.judge_turn(judged_home, TID, _FakeClient(), "m", "anthropic")


def test_an_unreadable_verdict_writes_no_score(judged_home):
    with pytest.raises(te.JudgeRefused, match="readable score"):
        te.judge_turn(judged_home, TID, _FakeClient("I think it is fine."), "m", "anthropic")
    assert te.parse_verdict('{"addresses_question": 8, "grounded": 9, "reason": "ok"}')["value"] == 0.8


def test_the_newest_judge_score_wins(judged_home):
    te.judge_turn(judged_home, TID, _FakeClient(), "m", "anthropic", now=1e9)
    te._RECENT.clear()
    with open(next((judged_home / "traces").glob("*.jsonl")), "a") as f:
        f.write(json.dumps({"type": "score", "turn_id": TID, "source": "judge", "name": "answer_grounded",
                            "value": 0.9, "note": "newer", "ts": "2999-01-01T00:00:00+00:00"}) + "\n")
    turn = obs.payload(judged_home, window="all", now=NOW)["turns"][0]
    assert [s["value"] for s in turn["scores"] if s["source"] == "judge"] == [0.9]


def test_the_button_estimate_is_pricings_price_for_the_prompt(judged_home):
    turn, _ = te.find_turn(judged_home, TID)
    offer = te.judge_offer(turn, "anthropic", "claude-haiku-4-5-20251001")
    p_in, p_out = 1.0, 5.0   # pricing.MODEL_PRICING["claude-haiku-4-5-20251001"]
    assert offer["usd"] == round(len(te.judge_prompt(turn)) / 4 / 1e6 * p_in + 300 / 1e6 * p_out, 6)
    payload_turn = obs.payload(judged_home, window="all", now=NOW, provider="anthropic",
                               judge_model="claude-haiku-4-5-20251001")["turns"][0]
    assert payload_turn["judge_offer"] == offer
    assert te.judge_offer({**turn, "turn_id": ""}, "anthropic", "m") is None


# ---- 12. recorded turns, precision checks -----------------------------------
# Rebuilt from recorded traces: each check must only fail when a reader of
# the trace would agree. Names are the turn's UTC time.

FUNDING = "2026-10-05-0323-funding-research.jsonl"
RECALL = "2026-10-05-0417-recall.jsonl"
TWO_SAVES = "2026-10-05-0217-two-saves.jsonl"


def test_live_0323_funding_research_passes_spend_and_numbers():
    """"Aviato lists nothing dated after 2024-11-20" is not a $0 claim, and
    "four Aviato calls at $0.01 each" is $0.04, what the four calls cost.
    "$1.58M" is grounded by Aviato's raw 1575000."""
    scores = _scores(_turn(FUNDING))
    assert scores["spend_claim"]["value"] == 1, scores["spend_claim"]["note"]
    assert scores["grounded_numbers"]["value"] == 1, scores["grounded_numbers"]["note"]
    assert scores["one_report"]["value"] == 1


def test_live_0417_a_question_answered_from_memory_is_not_failed():
    scores = _scores(_turn(RECALL))
    assert scores["one_report"]["value"] is None
    assert scores["one_report"]["note"].startswith("answered from memory")
    grounded = scores["grounded_numbers"]
    assert grounded["value"] is None and "2024-08-01" in grounded["note"]
    assert "not traced" in grounded["note"]


def test_live_0417_numbers_in_a_memory_answer_are_grounded():
    """Retrieved memory is a source: the same reply, with the dates in the
    memory_get answer (as a JSON-escaped non-breaking hyphen too), passes."""
    turn = _turn(RECALL)
    body = json.dumps({"memory": {"id": "mem_r0323", "body": (
        "Letta $10M seed 2024\u201108\u201101; Zep $2.3M 2024-11-20; Cognee $1.58M 2023-12-27; "
        "Mem0 $24M; together $13.88M, 58%; 2025 not covered; cost_usd 0.04")}})
    events = [ev for ev in turn["events"] if ev.get("tool") != "gogo_memory_memory_get"]
    events.append(_tool("gogo_memory_memory_get", body, turn_id=turn["turn_id"]))
    check = _check("grounded_numbers", {**turn, "events": events})
    assert check["value"] == 1, check["note"]


def test_a_turns_own_date_is_not_a_claim():
    # a day either side is the same day somewhere; two days off is a claim
    reply = "Snapshot of 2026-10-06: 25 prompts, 12%, and an earlier one on 2026-10-01."
    turn = _made("x", reply, [_tool("search_web", json.dumps({"prompts": 25, "rate": 0.12}))])
    check = _check("grounded_numbers", turn)
    assert check["value"] == 0 and check["note"].endswith("not found: 2026-10-01")


def test_saying_the_youtube_part_did_not_run_is_a_mention():
    failed = _tool("treg_catalog_call_read",
                   json.dumps({"status": 402, "endpoint_id": "tikhub.youtube.web.search_video"}))
    for reply in ("No comments were pulled.", "The balance was below the $0.002 needed.",
                  "I skipped the video search.", "Comments from YouTube are missing here."):
        assert _check("errors_handled", _made("x", reply, [failed]))["value"] == 1, reply
    assert _check("errors_handled", _made("x", "Here is the brief.", [failed]))["value"] == 0


def test_live_0217_the_models_own_report_save_counts():
    """The model's memory_remember of a whole report plus the harness's save
    is two reports in the Company brain."""
    check = _scores(_turn(TWO_SAVES))["one_report"]
    assert check["value"] == 0 and check["note"] == "2 reports saved in one turn"


def test_one_report_counts_one_memory_once_and_skips_a_refused_save():
    from gogo.memory.reports import MARKER, REFUSAL

    body = {"body": MARKER + "\n# Letta\n## Summary\n- x", "scope": "project:Company brain"}
    saved = _tool("gogo_memory_memory_remember", json.dumps({"memory": {"id": "m1"}}))
    saved["args"] = body
    same = {"type": "report", "turn_id": "t_abc123", "memory_id": "m1", "title": "Letta"}
    msg = "research the competitors of Letta and save a report"
    assert _check("one_report", _made(msg, "Letta.", [saved, same]))["value"] == 1
    refused = _tool("gogo_memory_memory_remember", REFUSAL)
    refused["args"] = body
    other = {**same, "memory_id": "m2"}
    assert _check("one_report", _made(msg, "Letta.", [refused, other]))["value"] == 1
    # a long body is kept in the trace as one trimmed JSON string; the marker survives
    long = obs.trace_record({"tool": "gogo_memory_memory_remember", "args": {**body, "body": body["body"] * 60},
                             "output": json.dumps({"memory": {"id": "m3"}})}, turn_id="t_abc123")
    assert isinstance(long["args"], str)
    assert _check("one_report", _made(msg, "Letta.", [{"type": "tool", **long}, other]))["value"] == 0


def test_spend_claim_reads_counts_scaled_figures_and_nothing():
    calls = [_tool("treg_call", json.dumps({"status": 200, "endpoint_id": "aviato.companies.funding_rounds",
                                            "cost_usd": 0.01})) for _ in range(4)]
    for reply, want in [
            ("The treg cost was four Aviato calls at $0.01 each.", 1),
            ("The treg cost was 4 calls at $0.01 each.", 1),
            ("The treg cost was two Aviato calls at $0.01 each.", 0),
            ("Aviato lists nothing dated after 2024-11-20.", None),
            ("Aviato says Letta raised a $10M seed, and its free tier lists only seeds.", None),
            ("Aviato's lookups were free.", 0),
            ("The Aviato calls cost nothing.", 0),
            ("Feel free to ask for more; Aviato costs $0.01 per call.", None)]:
        assert _check("spend_claim", _made("x", reply, calls))["value"] == want, reply


def test_grounded_numbers_rounds_scaled_figures_both_ways():
    src = json.dumps({"raised": 1575000, "followers": 274812, "arr": "$3.4M", "seats": "12,500"})
    reply = "They raised $1.58M (about $1.6 million), have 275K followers, $3,400,000 in ARR and 12.5K seats."
    check = _check("grounded_numbers", _made("x", reply, [_tool("search_web", src)]))
    assert check["value"] == 1, check["note"]
    off = "They raised $1.7M, have 275K followers and 12.5K seats."
    check = _check("grounded_numbers", _made("x", off, [_tool("search_web", src)]))
    assert check["value"] == 0 and "$1.7M" in check["note"]


NO_REPORT = "2026-10-05-1012-no-report-asked.jsonl"


def test_live_1012_a_turn_that_asked_for_no_report_is_not_failed():
    """"Just answer, no report." with treg_call (the own-key surface) on
    predictleads.companies.financing_events: one_report is n/a, and the
    PredictLeads JSON (an "amount" string, amount_normalized, effective_date)
    grounds the reply's numbers."""
    scores = _scores(_turn(NO_REPORT))
    assert scores["one_report"]["value"] is None
    assert scores["one_report"]["note"] == "the message asked for no report"
    assert scores["grounded_numbers"]["value"] == 1, scores["grounded_numbers"]["note"]
    assert scores["spend_claim"]["value"] == 1, scores["spend_claim"]["note"]


def test_one_report_reads_each_way_of_asking_for_no_report():
    treg = _tool("treg_call", TREG)
    for msg in ("research Letta's funding, just answer", "research mem0's competitors, don't save it",
                "research mem0 without a report", "research mem0, skip the report"):
        assert _check("one_report", _made(msg, "Letta raised.", [treg]))["value"] is None, msg
    assert _check("one_report", _made("research the competitors of mem0", "x", [treg]))["value"] == 0
    # asking for none and saving one anyway fails
    saved = {"type": "report", "turn_id": "t_abc123", "memory_id": "m1", "title": "Letta"}
    check = _check("one_report", _made("research Letta, no report", "x", [treg, saved]))
    assert check["value"] == 0 and check["note"] == "the message asked for no report and one was saved"


def test_grounded_numbers_reads_treg_call_outputs_and_the_traced_spend():
    """A treg_call answer kept as text inside JSON (an MCP text block) is
    decoded, and "$0.04" is grounded by the call's traced cost_usd even when
    the call's output does not repeat its price."""
    body = json.dumps({"data": [{"attributes": {"amount": "$10 million", "amount_normalized": 10000000,
                                                "effective_date": "2024-09-23"}}]})
    wrapped = _tool("treg_call", json.dumps([{"type": "text", "text": body}]), cost_usd=0.04,
                    endpoint_id="predictleads.companies.financing_events", provider="predictleads")
    reply = "Letta raised a $10M seed on Sep 23, 2024. The PredictLeads call cost $0.04."
    check = _check("grounded_numbers", _made("x", reply, [wrapped]))
    assert check["value"] == 1, check["note"]
    for name in ("treg_call", "treg_catalog_call_read"):
        assert te._spend_figures([{"source": "treg", "cost_usd": 0.04, "tool": name}]) == {0.04}


def test_errors_handled_does_not_take_the_word_call_for_treg_call():
    failed = _tool("treg_call", json.dumps({"status": 500, "endpoint_id": "predictleads.companies.financing_events"}))
    assert _check("errors_handled", _made("x", "Here is the call summary.", [failed]))["value"] == 0
    assert _check("errors_handled", _made("x", "PredictLeads returned nothing.", [failed]))["value"] == 1
