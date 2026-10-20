"""Contract for docs/design/remediation-ledger.yaml, the ledger of 2026-10-20 docs audit findings that drives 5.1.0 remediation."""

import re
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parents[1]
LEDGER_PATH = ROOT / "docs" / "design" / "remediation-ledger.yaml"

ID_PATTERN = re.compile(r"^R-\d{3}$")
REF_PATTERN = re.compile(r"[\w./-]+\.[A-Za-z0-9]+:\d+")
FORBIDDEN_ACCEPTANCE_WORDS = ("should", "maybe", "consider", "tbd")

REQUIRED_KEYS = {
    "id", "source", "docs", "claim", "evidence", "class", "disposition",
    "phase", "acceptance", "test_level", "status",
}
OPTIONAL_KEYS = {"duplicate_of", "decision", "commits", "notes"}
SOURCES = {"A", "B", "C", "D", "phase0"}
CLASSES = {"doc-wrong", "code-bug", "unimplemented-promise", "inert-enforcement"}
DISPOSITIONS = {"fix-doc", "fix-code", "implement", "retire-claim"}
TEST_LEVELS = {"contract", "unit", "live", "docs-claims"}
STATUSES = {"open", "red", "green", "closed", "duplicate"}
REQUIRED_DECISIONS = ("progressive_disclosure", "setup_promises", "release_split", "work_types")
INERT_HOOKS = (
    "test-guardian.sh",
    "tdd-prewrite-guardian.sh",
    "auto-test-runner.sh",
    "wip-limit.sh",
    "preflight-guard.sh",
    "phase-dwelling-guard.sh",
)


@pytest.fixture(scope="module")
def ledger():
    assert LEDGER_PATH.is_file(), f"ledger missing: {LEDGER_PATH}"
    data = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "ledger top level must be a mapping"
    return data


@pytest.fixture(scope="module")
def rows(ledger):
    value = ledger.get("rows")
    assert isinstance(value, list), "rows must be a list"
    return value


@pytest.fixture(scope="module")
def tracked_files():
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return set(out.splitlines())


def rid(row):
    return row.get("id", "<no id>") if isinstance(row, dict) else "<non-mapping row>"


def text_of(row, *keys):
    return " ".join(str(row.get(k, "")) for k in keys).lower()


def find_rows(rows, predicate):
    return [r for r in rows if predicate(r)]


def test_ledger_file_exists():
    assert LEDGER_PATH.is_file(), f"ledger missing: {LEDGER_PATH}"


def test_top_level_shape(ledger):
    assert ledger.get("schema_version") == 1
    assert isinstance(ledger.get("decisions"), dict)
    assert isinstance(ledger.get("rows"), list)


def test_row_count_minimum(rows):
    assert len(rows) >= 150, f"expected at least 150 rows, found {len(rows)}"


def test_rows_have_exact_key_sets(rows):
    for row in rows:
        assert isinstance(row, dict), f"{rid(row)}: row must be a mapping"
        keys = set(row)
        missing = REQUIRED_KEYS - keys
        unknown = keys - REQUIRED_KEYS - OPTIONAL_KEYS
        assert not missing, f"{rid(row)}: missing keys {sorted(missing)}"
        assert not unknown, f"{rid(row)}: unknown keys {sorted(unknown)}"


def test_ids_match_pattern_and_are_unique(rows):
    seen = set()
    for row in rows:
        value = row.get("id")
        assert isinstance(value, str) and ID_PATTERN.match(value), f"{rid(row)}: id must match ^R-\\d{{3}}$"
        assert value not in seen, f"{value}: duplicate id"
        seen.add(value)


def test_enumerated_fields_are_valid(rows):
    for row in rows:
        assert row.get("source") in SOURCES, f"{rid(row)}: bad source {row.get('source')!r}"
        assert row.get("class") in CLASSES, f"{rid(row)}: bad class {row.get('class')!r}"
        assert row.get("disposition") in DISPOSITIONS, f"{rid(row)}: bad disposition {row.get('disposition')!r}"
        assert row.get("status") in STATUSES, f"{rid(row)}: bad status {row.get('status')!r}"


def test_phase_is_int_between_2_and_5(rows):
    for row in rows:
        phase = row.get("phase")
        assert type(phase) is int and 2 <= phase <= 5, f"{rid(row)}: phase must be int 2..5, got {phase!r}"


def test_docs_entries_are_tracked_paths_with_positive_lines(rows, tracked_files):
    for row in rows:
        docs = row.get("docs")
        assert isinstance(docs, list) and docs, f"{rid(row)}: docs must be a non-empty list"
        for entry in docs:
            assert isinstance(entry, dict) and set(entry) == {"path", "line"}, (
                f"{rid(row)}: docs entries need exactly path and line"
            )
            assert entry["path"] in tracked_files, f"{rid(row)}: {entry['path']!r} is not tracked by git"
            line = entry["line"]
            assert type(line) is int and line > 0, f"{rid(row)}: line must be a positive int, got {line!r}"


def test_claim_and_evidence_are_non_empty_strings(rows):
    for row in rows:
        claim = row.get("claim")
        evidence = row.get("evidence")
        assert isinstance(claim, str) and claim.strip(), f"{rid(row)}: claim must be a non-empty string"
        assert isinstance(evidence, str) and evidence.strip(), f"{rid(row)}: evidence must be a non-empty string"


def test_evidence_cites_path_line_reference(rows):
    for row in rows:
        assert REF_PATTERN.search(str(row.get("evidence", ""))), (
            f"{rid(row)}: evidence must cite at least one path:line reference"
        )


def test_acceptance_is_testable_statement(rows):
    for row in rows:
        acceptance = row.get("acceptance")
        assert isinstance(acceptance, str) and acceptance.strip(), f"{rid(row)}: acceptance must be a non-empty string"
        for word in FORBIDDEN_ACCEPTANCE_WORDS:
            assert not re.search(rf"\b{word}\b", acceptance, re.IGNORECASE), (
                f"{rid(row)}: acceptance must not contain {word!r}"
            )


def test_test_level_is_non_empty_list_from_allowed_set(rows):
    for row in rows:
        levels = row.get("test_level")
        assert isinstance(levels, list) and levels, f"{rid(row)}: test_level must be a non-empty list"
        bad = set(levels) - TEST_LEVELS
        assert not bad, f"{rid(row)}: unknown test_level values {sorted(bad)}"


def test_duplicate_of_required_iff_duplicate_and_valid(rows):
    by_id = {r.get("id"): r for r in rows}
    for row in rows:
        is_dup = row.get("status") == "duplicate"
        has_ref = "duplicate_of" in row
        assert is_dup == has_ref, f"{rid(row)}: duplicate_of is required iff status is duplicate"
        if is_dup:
            target = row["duplicate_of"]
            assert target in by_id, f"{rid(row)}: duplicate_of {target!r} does not exist"
            assert target != row["id"], f"{rid(row)}: cannot duplicate itself"
            assert by_id[target].get("status") != "duplicate", (
                f"{rid(row)}: duplicate_of {target} is itself a duplicate"
            )


def test_decision_required_iff_retire_claim_and_resolves(rows, ledger):
    decisions = ledger.get("decisions", {})
    for row in rows:
        retire = row.get("disposition") == "retire-claim"
        assert retire == ("decision" in row), f"{rid(row)}: decision is required iff disposition is retire-claim"
        if retire:
            assert row["decision"] in decisions, f"{rid(row)}: decision {row['decision']!r} not in decisions"


def test_commits_required_iff_closed(rows):
    for row in rows:
        closed = row.get("status") == "closed"
        assert closed == ("commits" in row), f"{rid(row)}: commits is required iff status is closed"
        if closed:
            commits = row["commits"]
            assert isinstance(commits, list) and commits, f"{rid(row)}: commits must be a non-empty list"
            for sha in commits:
                assert isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{7,40}", sha), (
                    f"{rid(row)}: bad commit sha {sha!r}"
                )


def test_inert_enforcement_consistency(rows):
    for row in find_rows(rows, lambda r: r.get("class") == "inert-enforcement"):
        assert row.get("disposition") == "fix-code", f"{rid(row)}: inert-enforcement requires fix-code"
        assert row.get("phase") in {2, 3}, f"{rid(row)}: inert-enforcement requires phase 2 or 3"
        levels = set(row.get("test_level", []))
        assert {"contract", "live"} <= levels, f"{rid(row)}: inert-enforcement requires contract and live"


def test_code_bug_consistency(rows):
    for row in find_rows(rows, lambda r: r.get("class") == "code-bug"):
        assert row.get("disposition") == "fix-code", f"{rid(row)}: code-bug requires fix-code"
        assert set(row.get("test_level", [])) & {"contract", "unit"}, f"{rid(row)}: code-bug requires contract or unit"


def test_unimplemented_promise_consistency(rows):
    for row in find_rows(rows, lambda r: r.get("class") == "unimplemented-promise"):
        disposition = row.get("disposition")
        assert disposition in {"implement", "retire-claim"}, (
            f"{rid(row)}: unimplemented-promise requires implement or retire-claim"
        )
        if disposition == "implement":
            assert row.get("phase") in {3, 4}, f"{rid(row)}: implement requires phase 3 or 4"
        else:
            assert row.get("phase") == 5, f"{rid(row)}: retire-claim requires phase 5"
            assert "docs-claims" in row.get("test_level", []), f"{rid(row)}: retire-claim requires docs-claims"


def test_doc_wrong_consistency(rows):
    for row in find_rows(rows, lambda r: r.get("class") == "doc-wrong"):
        assert row.get("disposition") == "fix-doc", f"{rid(row)}: doc-wrong requires fix-doc"
        assert row.get("phase") == 5, f"{rid(row)}: doc-wrong requires phase 5"
        assert "docs-claims" in row.get("test_level", []), f"{rid(row)}: doc-wrong requires docs-claims"


def test_fix_doc_rows_are_never_before_phase_5(rows):
    for row in find_rows(rows, lambda r: r.get("disposition") == "fix-doc"):
        assert row.get("phase") == 5, f"{rid(row)}: fix-doc rows must be phase 5"


def test_required_decisions_present(ledger):
    decisions = ledger.get("decisions")
    assert isinstance(decisions, dict)
    for key in REQUIRED_DECISIONS:
        value = decisions.get(key)
        assert isinstance(value, str) and value.strip(), f"decisions.{key} must be a non-empty string"


def test_progressive_disclosure_rows_are_retired(rows):
    pattern = re.compile(r"progressive[ _]disclosure", re.IGNORECASE)
    for row in rows:
        if pattern.search(text_of(row, "claim", "notes")):
            assert row.get("disposition") == "retire-claim", (
                f"{rid(row)}: progressive disclosure rows must be retire-claim"
            )
            assert row.get("decision") == "progressive_disclosure", (
                f"{rid(row)}: progressive disclosure rows must use decision progressive_disclosure"
            )


def assert_promise_row(rows, pattern, disposition, decision=None):
    regex = re.compile(pattern, re.IGNORECASE)
    matches = find_rows(rows, lambda r: regex.search(str(r.get("claim", ""))))
    assert matches, f"no row claim matches {pattern!r}"
    ok = [
        r for r in matches
        if r.get("disposition") == disposition and (decision is None or r.get("decision") == decision)
    ]
    assert ok, (
        f"rows {[rid(r) for r in matches]} match {pattern!r} but none has disposition "
        f"{disposition}" + (f" and decision {decision}" if decision else "")
    )


def test_presnapshot_branch_promise_is_implemented(rows):
    assert_promise_row(rows, r"pre-sweetclaude", "implement")


def test_mode_interview_promise_is_implemented(rows):
    assert_promise_row(rows, r"mode (interview|question)", "implement")


def test_git_init_offer_promise_is_retired(rows):
    assert_promise_row(rows, r"git init", "retire-claim", "setup_promises")


def test_strategy_folder_promise_is_retired(rows):
    assert_promise_row(rows, r"strategy/", "retire-claim", "setup_promises")


def test_deference_question_promise_is_retired(rows):
    assert_promise_row(rows, r"deference", "retire-claim", "setup_promises")


@pytest.mark.parametrize("hook", INERT_HOOKS)
def test_known_inert_hook_is_covered(rows, hook):
    covering = find_rows(
        rows,
        lambda r: r.get("class") == "inert-enforcement" and hook in text_of(r, "claim", "evidence"),
    )
    assert covering, f"no inert-enforcement row names {hook}"


def test_phase0_skill_library_sync_is_closed_with_commit(rows):
    matches = find_rows(
        rows,
        lambda r: r.get("source") == "phase0"
        and "skill-library" in text_of(r, "claim")
        and "sync" in text_of(r, "claim"),
    )
    assert matches, "no phase0 row mentions skill-library and sync"
    assert any(
        r.get("status") == "closed" and any(str(c).startswith("2089fc75") for c in r.get("commits", []))
        for r in matches
    ), f"{[rid(r) for r in matches]}: none closed with commit 2089fc75"


def test_phase0_upgrade_instructions_are_closed_with_commit(rows):
    matches = find_rows(
        rows,
        lambda r: r.get("source") == "phase0" and "upgrade" in text_of(r, "claim"),
    )
    assert matches, "no phase0 row mentions upgrade"
    assert any(
        r.get("status") == "closed" and any(str(c).startswith("803585a5") for c in r.get("commits", []))
        for r in matches
    ), f"{[rid(r) for r in matches]}: none closed with commit 803585a5"


def test_no_duplicate_first_path_and_claim_among_non_duplicates(rows):
    seen = {}
    for row in find_rows(rows, lambda r: r.get("status") != "duplicate"):
        docs = row.get("docs") or [{}]
        key = (docs[0].get("path"), str(row.get("claim", "")).strip())
        assert key not in seen, f"{rid(row)}: same first docs path and claim as {seen[key]}"
        seen[key] = rid(row)
