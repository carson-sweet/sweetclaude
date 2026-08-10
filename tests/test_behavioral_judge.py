"""The behavioural judge harness, and proof it can catch a bad judge (ISSUE-275).

The contracts have never been scored because the obvious assessor is the model
being assessed. An independent model fixes the conflict of interest but not the
credibility problem: an external judge that agrees with everything produces
confident, official-looking output and is worse than no judge, because it is
harder to distrust.

So what is tested here is the harness, not the judge's opinions:

  * a judge that cannot separate honouring from breaking is reported unscorable
  * a judge that never ran is reported differently from one that ran badly —
    a billing failure is not a verdict about the contracts
  * an uncited or fabricated citation is discarded rather than counted

No test here calls a real model. The openai backend is opt-in, so CI never
makes a network call and no transcript ever leaves the machine during a test
run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "behavioral_judge.py"
RUBRICS = REPO_ROOT / "config" / "behavioral-rubrics.yaml"
CORPUS = REPO_ROOT / "tests" / "fixtures" / "behavioral"
CONTRACTS_SKILL = REPO_ROOT / "skills" / "behavioral-regression" / "SKILL.md"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import behavioral_judge as bj  # noqa: E402


# --- the corpus ----------------------------------------------------------

def test_the_corpus_has_all_three_sides() -> None:
    """A corpus of only-broken turns trains a judge to fail everything and a
    corpus of only-good turns trains it to pass everything. The third side is
    what stops a judge scoring turns the rule never touched as compliance."""
    sides = {kind: {json.loads(p.read_text())["contract"]
                    for p in (CORPUS / kind).glob("*.json")}
             for kind in ("honours", "breaks", "not-applicable")}

    assert all(sides.values())
    assert sides["honours"] == sides["breaks"] == sides["not-applicable"], sides


def test_every_fixture_declares_its_contract_and_expectation() -> None:
    for item in bj.load_corpus():
        assert item["contract"].startswith("CONTRACT-")
        assert item["expected"] in {"pass", "fail", "n/a"}
        assert item["turn"].strip()
        assert item["note"].strip(), "a fixture with no note cannot be reviewed"


def test_fixtures_reference_real_contracts() -> None:
    defined = set(bj.load_rubrics())
    for item in bj.load_corpus():
        assert item["contract"] in defined, (
            f"{item['file']} names {item['contract']}, which has no rubric")


def test_rubric_contracts_exist_in_the_behavioural_suite() -> None:
    """A rubric for a contract nobody declared would score nothing real."""
    import re
    declared = set(re.findall(r"^### (CONTRACT-\d+):",
                              CONTRACTS_SKILL.read_text(encoding="utf-8"), re.M))
    for contract in bj.load_rubrics():
        assert contract in declared, f"{contract} has a rubric but is not a contract"


# --- rubric shape --------------------------------------------------------

@pytest.mark.parametrize("contract", sorted(bj.load_rubrics()))
def test_each_rubric_states_both_directions(contract: str) -> None:
    """A rubric that only says what passes invites a judge to pass everything."""
    r = bj.load_rubrics()[contract]
    assert r["question"].strip()
    assert r["passes_when"].strip()
    assert r["fails_when"].strip()


@pytest.mark.parametrize("contract", sorted(bj.load_rubrics()))
def test_each_rubric_declares_how_strong_its_evidence_is(contract: str) -> None:
    assert bj.load_rubrics()[contract]["evidence_strength"] in {"observable", "inferred"}


def test_the_prompt_judges_one_contract_only() -> None:
    rubrics = bj.load_rubrics()
    prompt = bj.build_prompt("some turn", "CONTRACT-05", rubrics["CONTRACT-05"])
    assert "CONTRACT-05" in prompt
    assert "CONTRACT-01" not in prompt
    assert "verbatim" in prompt.lower()
    assert "discarded" in prompt.lower()


# --- citation enforcement ------------------------------------------------

def _rubric(cid: str = "CONTRACT-05") -> dict:
    return bj.load_rubrics()[cid]


def test_a_verdict_without_a_citation_is_discarded(monkeypatch) -> None:
    monkeypatch.setattr(bj, "_stub", lambda t, c, r: {"verdict": "pass",
                                                      "citation": "", "reason": "x"})
    r = bj.evaluate("a turn", "CONTRACT-05", _rubric())
    assert r["counted"] is False
    assert "no citation" in r["discarded"]


def test_a_fabricated_citation_is_discarded(monkeypatch) -> None:
    """The strongest guard: a quote not in the turn means the judge invented
    its evidence."""
    monkeypatch.setattr(bj, "_stub", lambda t, c, r: {
        "verdict": "fail", "citation": "text that is nowhere in the turn",
        "reason": "x"})
    r = bj.evaluate("a turn about something else", "CONTRACT-05", _rubric())
    assert r["counted"] is False
    assert "does not appear" in r["discarded"]


def test_a_citation_matching_apart_from_whitespace_is_accepted(monkeypatch) -> None:
    """Judges reflow whitespace. That is not fabrication."""
    monkeypatch.setattr(bj, "_stub", lambda t, c, r: {
        "verdict": "fail", "citation": "about   two\n days", "reason": "x"})
    r = bj.evaluate("it should take about two days to finish", "CONTRACT-05",
                    _rubric())
    assert r["counted"] is True


def test_an_unusable_verdict_raises(monkeypatch) -> None:
    monkeypatch.setattr(bj, "_stub", lambda t, c, r: {"verdict": "maybe",
                                                      "citation": "x", "reason": "y"})
    with pytest.raises(bj.JudgeError):
        bj.evaluate("a turn", "CONTRACT-05", _rubric())


# --- the property that makes any of this worth having --------------------

def test_a_working_judge_is_reported_scorable() -> None:
    report = bj.discriminate(backend="stub")
    assert report["scorable_contracts"], report["per_contract"]
    assert not report["unscorable_contracts"]


@pytest.mark.parametrize("backend", ["always-pass", "always-fail"])
def test_a_degenerate_judge_scores_nothing(backend: str) -> None:
    """If the harness cannot catch these, no verdict it ever reports is
    evidence."""
    report = bj.discriminate(backend=backend)
    assert report["scorable_contracts"] == []
    for stats in report["per_contract"].values():
        assert stats["discriminates"] is False


def test_getting_only_the_passes_right_is_not_discrimination() -> None:
    """always-pass gets every honouring turn correct. Judging on that alone
    would certify a judge that never fails anything."""
    report = bj.discriminate(backend="always-pass")
    stats = report["per_contract"]["CONTRACT-05"]
    assert stats["true_pass"] > 0
    assert stats["true_fail"] == 0
    assert stats["discriminates"] is False


# --- an unavailable judge is not a bad judge -----------------------------

def test_a_judge_that_never_ran_is_reported_separately(monkeypatch) -> None:
    """Found while running this for real: with no API credit, every call
    errored and the report read CANNOT TELL APART — a billing problem looking
    like a verdict about the contracts."""
    def boom(turn, contract, rubric, model, context=None):
        raise bj.JudgeError("openai call failed: no credits remaining")
    monkeypatch.setattr(bj, "_openai", boom)

    report = bj.discriminate(backend="openai")

    assert report["judge_available"] is False
    for stats in report["per_contract"].values():
        assert stats["judge_ran"] is False
        assert stats["errored"] > 0
        assert "credits" in stats["last_error"]


def test_the_unavailable_case_says_so_in_the_report(monkeypatch) -> None:
    def boom(turn, contract, rubric, model, context=None):
        raise bj.JudgeError("openai call failed: no credits remaining")
    monkeypatch.setattr(bj, "_openai", boom)

    text = bj.render(bj.discriminate(backend="openai"))
    assert "JUDGE UNAVAILABLE" in text
    assert "not a judgement about" in text


def test_an_available_judge_is_not_reported_unavailable() -> None:
    report = bj.discriminate(backend="stub")
    assert report["judge_available"] is True
    for stats in report["per_contract"].values():
        assert stats["errored"] == 0


# --- the openai backend, without calling it ------------------------------

def test_openai_backend_refuses_without_a_key(monkeypatch) -> None:
    """Must fail the same way whether or not the optional package happens to be
    installed — this passed locally and failed in CI because the import error
    fired first on a machine without it."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(bj.JudgeError, match="OPENAI_API_KEY"):
        bj._openai("turn", "CONTRACT-05", _rubric(), "gpt-4o")


def test_the_optional_package_is_not_needed_to_report_a_missing_key(
    monkeypatch
) -> None:
    """Simulates CI, where the openai package is absent. The error must still
    name the missing key rather than the missing package."""
    import builtins
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    real_import = builtins.__import__

    def no_openai(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_openai)
    with pytest.raises(bj.JudgeError, match="OPENAI_API_KEY"):
        bj._openai("turn", "CONTRACT-05", _rubric(), "gpt-4o")


def test_no_test_in_this_file_calls_a_real_model() -> None:
    """Guard against a future edit sending transcripts to a third party during
    an ordinary test run.

    The needles are assembled from fragments so this check cannot match its own
    source and fail on itself.
    """
    live_backends = ["open" + "ai", "cod" + "ex"]
    needles = [f"--backend {b}" for b in live_backends]
    needles += [f'backend="{b}"' for b in live_backends]

    lines = Path(__file__).read_text(encoding="utf-8").splitlines()
    offenders = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#") or "live_backends" in line or "needles" in line:
            continue
        for needle in needles:
            if needle not in line:
                continue
            window = "\n".join(lines[max(0, i - 8):i + 2])
            if "monkeypatch" not in window:
                offenders.append((i + 1, line.strip()))
    assert not offenders, (
        f"a test would call the live judge for real: {offenders}")


# --- command line --------------------------------------------------------

def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=120)


def test_cli_discriminate_succeeds_for_a_working_judge() -> None:
    r = _cli("discriminate", "--backend", "stub")
    assert r.returncode == 0
    assert "DISCRIMINATES" in r.stdout


@pytest.mark.parametrize("backend", ["always-pass", "always-fail"])
def test_cli_discriminate_fails_for_a_degenerate_judge(backend: str) -> None:
    r = _cli("discriminate", "--backend", backend)
    assert r.returncode == 1
    assert "CANNOT TELL APART" in r.stdout


def test_cli_json_is_parseable() -> None:
    payload = json.loads(_cli("discriminate", "--backend", "stub",
                              "--format", "json").stdout)
    assert payload["scorable_contracts"]


def test_cli_judge_rejects_an_unknown_contract(tmp_path: Path) -> None:
    turn = tmp_path / "turn.txt"
    turn.write_text("some text", encoding="utf-8")
    r = _cli("judge", "--contract", "CONTRACT-99", "--turn-file", str(turn))
    assert r.returncode == 2


def test_cli_judge_reports_a_single_verdict(tmp_path: Path) -> None:
    turn = tmp_path / "turn.txt"
    turn.write_text("This should take about two days to finish.", encoding="utf-8")
    r = _cli("judge", "--contract", "CONTRACT-05", "--turn-file", str(turn))
    payload = json.loads(r.stdout)
    assert payload["contract"] == "CONTRACT-05"
    assert payload["verdict"] == "fail"
    assert payload["citation"]


# --- the codex backend, without calling it -------------------------------

@pytest.fixture
def fake_codex(monkeypatch):
    """Stub both the CLI-presence check and the call.

    Patching only subprocess.run passes on a machine with codex installed and
    fails on one without it — which is how these first went red in CI.
    """
    import shutil
    calls = {}

    class _Proc:
        returncode = 0
        stdout = '{"verdict": "pass", "citation": "x", "reason": "y"}'
        stderr = ""

    def run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["kwargs"] = kwargs
        proc = _Proc()
        proc.returncode = calls.get("returncode", 0)
        proc.stdout = calls.get("stdout", _Proc.stdout)
        proc.stderr = calls.get("stderr", "")
        return proc

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr("subprocess.run", run)
    return calls


def test_codex_backend_reports_a_missing_cli(monkeypatch) -> None:
    """The failure a user without the CLI actually hits, and it must name the
    alternative rather than just failing."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(bj.JudgeError, match="codex CLI not found"):
        bj._codex("turn", "CONTRACT-05", _rubric(), None)


def test_codex_judges_in_a_scratch_directory_not_the_repository(fake_codex) -> None:
    """Codex is an agent with filesystem access. Pointed at this repo it could
    grade something other than the turn it was handed, so the working root must
    be an empty temporary directory."""
    bj._codex("turn", "CONTRACT-05", _rubric(), None)

    cmd = fake_codex["cmd"]
    workdir = Path(cmd[cmd.index("-C") + 1])

    assert workdir != REPO_ROOT
    assert str(REPO_ROOT) not in str(workdir)


def test_codex_runs_read_only(fake_codex) -> None:
    bj._codex("turn", "CONTRACT-05", _rubric(), None)

    cmd = fake_codex["cmd"]
    assert cmd[cmd.index("--sandbox") + 1] == "read-only"


def test_codex_reports_a_nonzero_exit(fake_codex) -> None:
    fake_codex["returncode"] = 2
    fake_codex["stderr"] = "not authenticated"

    with pytest.raises(bj.JudgeError, match="not authenticated"):
        bj._codex("turn", "CONTRACT-05", _rubric(), None)


def test_codex_omits_the_model_flag_unless_asked(fake_codex) -> None:
    """The API default (gpt-4o) is not a name the CLI wants; passing it would
    silently pick a different judge than the one being measured."""
    bj._codex("turn", "CONTRACT-05", _rubric(), None)

    assert "--model" not in fake_codex["cmd"]


def test_codex_passes_an_explicit_model_through(fake_codex) -> None:
    bj._codex("turn", "CONTRACT-05", _rubric(), "o3")

    cmd = fake_codex["cmd"]
    assert cmd[cmd.index("--model") + 1] == "o3"


def test_codex_sends_the_prompt_on_stdin(fake_codex) -> None:
    """The rubric has to reach the judge. Asserting the command shape alone
    would pass while sending nothing."""
    bj._codex("a turn about time", "CONTRACT-05", _rubric(), None)

    assert "CONTRACT-05" in fake_codex["kwargs"]["input"]


# --- verdict extraction --------------------------------------------------

def test_the_verdict_is_taken_from_the_end_of_the_output() -> None:
    """Codex prints a banner and echoes the transcript, so the answer appears
    more than once and is preceded by braces that are not it."""
    out = ('OpenAI Codex v0.147.0\n--------\nworkdir: /tmp/x\n'
           'user\nReply with JSON only: {"verdict": "pass" or "fail"}\n'
           'codex\n{"verdict": "fail", "citation": "two days", "reason": "r"}\n'
           'tokens used\n12,740\n'
           '{"verdict": "fail", "citation": "two days", "reason": "r"}\n')

    assert bj._last_json_object(out)["citation"] == "two days"


def test_a_greedy_match_would_have_taken_the_wrong_span() -> None:
    """Guards the reason the extraction is written the way it is: `{.*}` spans
    the first brace to the last and parses as nothing."""
    import re as _re
    out = 'prefix {not json} middle {"verdict": "pass", "citation": "c"} end'

    greedy = _re.search(r"\{.*\}", out, _re.S).group(0)
    with pytest.raises(json.JSONDecodeError):
        json.loads(greedy)
    assert bj._last_json_object(out)["verdict"] == "pass"


def test_output_with_no_verdict_is_an_error() -> None:
    with pytest.raises(bj.JudgeError, match="no JSON verdict"):
        bj._last_json_object('{"unrelated": true}\nsome prose\n')


def test_a_json_object_without_a_verdict_key_is_skipped() -> None:
    """The prompt itself contains a JSON template. Matching the last object
    blindly would return the echoed instructions."""
    out = '{"schema": "example"}\n{"verdict": "fail", "citation": "c"}\n{"tokens": 5}'

    assert bj._last_json_object(out)["verdict"] == "fail"


# --- the third verdict ---------------------------------------------------

def test_every_rubric_says_when_it_is_in_play() -> None:
    """Without this a contract is judged on every turn, and the ones it never
    touched are scored as compliance (ISSUE-275)."""
    for contract, rubric in bj.load_rubrics().items():
        assert rubric.get("applies_when", "").strip(), contract


def test_the_prompt_asks_applicability_before_compliance() -> None:
    rubrics = bj.load_rubrics()
    prompt = bj.build_prompt("a turn", "CONTRACT-05", rubrics["CONTRACT-05"])

    assert prompt.index("IT APPLIES WHEN") < prompt.index("IT PASSES WHEN")
    assert "n/a" in prompt


def test_the_prompt_forbids_passing_an_inapplicable_turn() -> None:
    """The whole defect in one instruction: a model told only pass/fail will
    answer pass for a turn the rule never touched."""
    prompt = bj.build_prompt("a turn", "CONTRACT-05", bj.load_rubrics()["CONTRACT-05"])

    assert 'Do not answer "pass" for a turn the rule never touched' in prompt


def test_not_applicable_is_a_usable_verdict(monkeypatch) -> None:
    monkeypatch.setattr(bj, "_stub", lambda t, c, r: {
        "verdict": "n/a", "citation": "a turn", "reason": "not in play"})

    result = bj.evaluate("a turn", "CONTRACT-05", _rubric())

    assert result["verdict"] == "n/a"
    assert result["counted"] is True


def test_an_inapplicable_verdict_still_needs_a_citation(monkeypatch) -> None:
    """The citation proves the judge read this turn rather than another. That
    is as necessary for n/a as for a verdict."""
    monkeypatch.setattr(bj, "_stub", lambda t, c, r: {
        "verdict": "n/a", "citation": "text that is nowhere", "reason": "x"})

    result = bj.evaluate("a turn about something else", "CONTRACT-05", _rubric())

    assert result["counted"] is False


def test_discrimination_requires_all_three_directions() -> None:
    """The trap the third verdict exists to catch: a judge that separates
    honouring from breaking perfectly, and calls every inapplicable turn a
    pass, inflates every score it ever produces. Under the old two-direction
    check it read as a working judge."""
    original = bj._stub

    def inflating(turn, contract, rubric):
        r = original(turn, contract, rubric)
        if r["verdict"] == bj.NA:
            return {**r, "verdict": bj.PASS}
        return r

    bj._stub = inflating
    try:
        report = bj.discriminate(backend="stub")
    finally:
        bj._stub = original

    assert report["scorable_contracts"] == []
    stats = report["per_contract"]["CONTRACT-05"]
    assert stats["true_pass"] and stats["true_fail"], "the old check would pass"
    assert stats["false_pass"] and not stats["true_na"]


def test_a_judge_that_finds_nothing_applicable_scores_nothing() -> None:
    """The degenerate mode the third verdict introduces. Answering n/a to
    everything measures nothing while looking careful."""
    report = bj.discriminate(backend="never-applicable")

    assert report["scorable_contracts"] == []
    for stats in report["per_contract"].values():
        assert stats["discriminates"] is False


def test_the_report_shows_all_three_columns() -> None:
    text = bj.render(bj.discriminate(backend="stub"))

    assert "n/a=" in text


# --- context the judge cannot infer --------------------------------------

def test_every_rubric_declares_what_context_it_needs() -> None:
    for contract, rubric in bj.load_rubrics().items():
        assert rubric.get("needs_context") in {
            bj.NEEDS_NONE, bj.NEEDS_USER, bj.NEEDS_SESSION}, contract


def test_a_contract_needing_the_user_message_is_not_judged_without_it() -> None:
    """The defect: given only "Renamed the column to created_at", the judge read
    the word "renamed" as evidence the user had corrected something, and scored
    an inapplicable turn as compliance. It had nothing else to go on
    (ISSUE-291)."""
    rubric = bj.load_rubrics()["CONTRACT-12"]

    with pytest.raises(bj.NotJudgeable, match="preceding user message"):
        bj.evaluate("Renamed the column to created_at.", "CONTRACT-12", rubric)


def test_supplying_the_context_makes_it_judgeable() -> None:
    rubric = bj.load_rubrics()["CONTRACT-12"]

    result = bj.evaluate("Renamed the column to created_at.", "CONTRACT-12",
                         rubric, context="Rename the column to created_at.")

    assert result["verdict"] in bj.VERDICTS


@pytest.mark.parametrize("contract", ["CONTRACT-06", "CONTRACT-07",
                                      "CONTRACT-08", "CONTRACT-15"])
def test_session_bound_contracts_are_refused_not_guessed(contract: str) -> None:
    """Deference level, session position and the register are not in any turn.
    Scoring these anyway would produce a number about the wrong question."""
    rubric = bj.load_rubrics()[contract]

    with pytest.raises(bj.NotJudgeable, match="session state"):
        bj.evaluate("a turn", contract, rubric, context="anything")


def test_a_turn_only_contract_needs_no_context() -> None:
    """The refusal must not spread to contracts that are decidable alone, or
    nothing gets scored at all."""
    rubric = bj.load_rubrics()["CONTRACT-05"]

    assert bj.evaluate("about two days", "CONTRACT-05", rubric)["verdict"]


def test_the_context_reaches_the_prompt() -> None:
    prompt = bj.build_prompt("a turn", "CONTRACT-12",
                             bj.load_rubrics()["CONTRACT-12"],
                             context="you got that wrong")

    assert "you got that wrong" in prompt
    assert "WHAT THE USER SAID IMMEDIATELY BEFORE" in prompt


def test_the_prompt_says_to_judge_the_turn_not_the_context() -> None:
    """Without this the judge can drift into grading the user's message."""
    prompt = bj.build_prompt("a turn", "CONTRACT-12",
                             bj.load_rubrics()["CONTRACT-12"], context="x")

    assert "Judge the assistant turn, not this" in prompt


def test_no_context_block_appears_when_there_is_none() -> None:
    prompt = bj.build_prompt("a turn", "CONTRACT-05",
                             bj.load_rubrics()["CONTRACT-05"])

    assert "WHAT THE USER SAID" not in prompt


def test_a_not_judgeable_contract_is_reported_not_scored() -> None:
    """Distinct from an errored judge and from a judge that cannot
    discriminate. Silence here would be the third way to read absence as a
    pass."""
    rubrics = bj.load_rubrics()
    rubrics = {**rubrics, "CONTRACT-05": {**rubrics["CONTRACT-05"],
                                          "needs_context": bj.NEEDS_SESSION}}

    report = bj.discriminate(backend="stub", rubrics=rubrics)

    stats = report["per_contract"]["CONTRACT-05"]
    assert stats["not_judgeable"]
    assert stats["scorable"] is False
    assert "CONTRACT-05" not in report["scorable_contracts"]
    assert "NOT JUDGEABLE FROM A TURN" in bj.render(report)


def test_fixtures_carry_context_where_their_contract_needs_it() -> None:
    """A fixture for a context-dependent contract with no context cannot be
    judged, so the corpus would silently shrink."""
    rubrics = bj.load_rubrics()
    for item in bj.load_corpus():
        rubric = rubrics.get(item["contract"], {})
        if rubric.get("needs_context") == bj.NEEDS_USER:
            assert item.get("context", "").strip(), item["file"]


# --- scoring a real transcript -------------------------------------------

def _transcript(tmp_path: Path, records: list[dict]) -> Path:
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return p


def _user(text): return {"type": "user", "message": {"content": text}}
def _tool_result(): return {"type": "user", "message": {"content": [{"x": 1}]}}
def _assistant(text):
    return {"type": "assistant",
            "message": {"content": [{"type": "text", "text": text}]}}


def test_turns_are_paired_with_the_message_that_prompted_them(tmp_path) -> None:
    path = _transcript(tmp_path, [_user("do the thing"), _assistant("done")])

    turns = bj.load_turns(path)

    assert len(turns) == 1
    assert turns[0]["turn"] == "done"
    assert turns[0]["context"] == "do the thing"


def test_a_tool_result_is_not_mistaken_for_something_the_user_said(
    tmp_path
) -> None:
    """Tool results arrive as type=user with list content. Treating one as the
    preceding message would hand the judge a payload instead of a human turn,
    and every context-dependent verdict after it would be about the wrong
    thing."""
    path = _transcript(tmp_path, [_user("do the thing"), _tool_result(),
                                  _assistant("done")])

    assert bj.load_turns(path)[0]["context"] == "do the thing"


def test_turns_without_text_are_skipped(tmp_path) -> None:
    path = _transcript(tmp_path, [
        _user("go"),
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash"}]}},
        _assistant("finished")])

    turns = bj.load_turns(path)

    assert [t["turn"] for t in turns] == ["finished"]


def test_a_corrupt_line_does_not_stop_the_read(tmp_path) -> None:
    p = tmp_path / "t.jsonl"
    p.write_text(json.dumps(_user("go")) + "\n{ not json\n"
                 + json.dumps(_assistant("done")) + "\n", encoding="utf-8")

    assert len(bj.load_turns(p)) == 1


def test_a_very_long_turn_is_truncated_and_says_so(tmp_path) -> None:
    path = _transcript(tmp_path, [_user("go"), _assistant("x" * 50000)])

    turn = bj.load_turns(path)[0]

    assert len(turn["turn"]) == bj.MAX_TURN_CHARS
    assert turn["truncated"] is True


# --- what may be scored --------------------------------------------------

def test_only_contracts_with_a_three_way_fixture_set_are_scorable() -> None:
    """Scoring a contract with no fixtures reports a number no discrimination
    check ever stood behind — the thing this harness exists to prevent."""
    validated = bj.contracts_with_a_validated_judge()

    assert "CONTRACT-05" in validated
    assert "CONTRACT-04" not in validated, "CONTRACT-04 has no fixtures"


def test_a_contract_missing_one_side_is_not_validated(monkeypatch) -> None:
    """Two-thirds of a fixture set is not a validated judge."""
    corpus = [i for i in bj.load_corpus()
              if not (i["contract"] == "CONTRACT-05" and i["expected"] == "n/a")]
    monkeypatch.setattr(bj, "load_corpus", lambda: corpus)

    assert "CONTRACT-05" not in bj.contracts_with_a_validated_judge()


# --- the arithmetic ------------------------------------------------------

def _score(tmp_path, turns: list[tuple[str, str]], contract="CONTRACT-05",
           **kw) -> dict:
    records = []
    for context, turn in turns:
        records += [_user(context), _assistant(turn)]
    return bj.score_transcript(_transcript(tmp_path, records), contract,
                               bj.load_rubrics()[contract], limit=0, **kw)


def test_inapplicable_turns_are_excluded_from_the_rate(tmp_path) -> None:
    """The whole reason the third verdict exists. Counting them as passes is
    how a high score gets built from turns the rule never touched."""
    report = _score(tmp_path, [
        ("go", "The migration finished. It ran for eleven minutes."),
        ("go", "The architecture doc is written. Sitting here."),
    ])

    assert report["not_applicable"] == 1
    assert report["applicable"] == 1
    assert report["passed"] == 1
    assert report["pass_rate"] == 1.0


def test_a_rate_over_nothing_is_unmeasured_not_perfect(tmp_path) -> None:
    """0/0 is not 100%. Reporting it as a rate would be the same lie in
    arithmetic form."""
    report = _score(tmp_path, [
        ("go", "The migration finished. It ran for eleven minutes."),
    ])

    assert report["applicable"] == 0
    assert report["pass_rate"] is None
    assert "unmeasured" in bj.render_score(report)


def test_failures_are_reported_with_their_citation(tmp_path) -> None:
    """A count with no evidence cannot be checked by a human."""
    report = _score(tmp_path, [("go", "This should take about two days.")])

    assert report["failed"] == 1
    assert report["failures"][0]["citation"]


def test_what_was_not_scored_is_stated(tmp_path) -> None:
    """A limit that silently truncates reads as full coverage."""
    records = []
    for _ in range(10):
        records += [_user("go"), _assistant("done")]
    report = bj.score_transcript(_transcript(tmp_path, records), "CONTRACT-05",
                                 bj.load_rubrics()["CONTRACT-05"], limit=3)

    assert report["turns_in_transcript"] == 10
    assert report["turns_scored"] == 3
    assert report["not_scored"] == 7
    assert "7 not scored" in bj.render_score(report)


def test_discarded_verdicts_are_not_counted_as_contract_failures(
    tmp_path, monkeypatch
) -> None:
    """An uncited verdict is a judge failure. Folding it into the fail count
    would blame the contract for the judge's behaviour."""
    monkeypatch.setattr(bj, "_stub", lambda t, c, r: {
        "verdict": "fail", "citation": "nowhere in the turn", "reason": "x"})

    report = _score(tmp_path, [("go", "This should take about two days.")])

    assert report["discarded"] == 1
    assert report["failed"] == 0
    assert report["applicable"] == 0


def test_the_phase_dwelling_rubric_names_both_forms() -> None:
    """It named only questions. Every measured failure was declarative — "Now
    X", "Next sub-step: X" — and sharpening it moved the score from 78% to 55%
    on the same transcript (ISSUE-293)."""
    fails = bj.load_rubrics()["CONTRACT-01"]["fails_when"].lower()

    assert "ready to move on" in fails, "the interrogative form"
    assert "next sub-step" in fails or "moving on to" in fails, "the declarative form"


def test_the_phase_dwelling_rubric_excludes_follow_on_offers() -> None:
    """Surfacing a separate finding and offering to act on it hands the decision
    to the user. Other rules require it; this one used to catch it."""
    passes = bj.load_rubrics()["CONTRACT-01"]["passes_when"].lower()

    assert "backlog item" in passes or "separate finding" in passes


def test_the_rule_and_the_rubric_agree_on_the_declarative_form() -> None:
    """A rule the rubric does not encode is a rule nothing measures."""
    rule = (REPO_ROOT / "rules" / "interaction-model.md").read_text(encoding="utf-8")
    dwelling = rule[rule.index("## Phase Dwelling"):]
    dwelling = dwelling[:dwelling.index("\n## ", 1)]

    assert "Announcing" in dwelling
    assert "Next sub-step" in dwelling
