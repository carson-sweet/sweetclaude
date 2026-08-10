"""The capability ledger reports every capability, honestly (ISSUE-266).

The ledger is EP-004's deliverable: every declared capability, its
verification tier, and whether it works. The property that matters most is
that nothing can be silently left out — an omitted capability looks exactly
like a working one to whoever reads the table.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SCRIPT = REPO_ROOT / "scripts" / "capability_ledger.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import capability_ledger as led  # noqa: E402


def _manifest(tmp_path: Path, capabilities: dict) -> Path:
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump({"schema_version": 1, "capabilities": capabilities}),
                 encoding="utf-8")
    return p


FULL = {
    "title": "A working capability",
    "delegate_skill": "sweetclaude:doctor",
    "command_entrypoint": {"script": "scripts/doctor.py"},
    "mutates_project": False,
    "verification_commands": ["python3 scripts/doctor.py scan"],
}


# --- the no-omission property -------------------------------------------

def test_every_declared_capability_appears_exactly_once(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, {f"cap.{i}": dict(FULL) for i in range(5)})
    ledger = led.build_ledger(manifest_path=manifest, include_behavioral=False)

    names = [r["capability"] for r in ledger["rows"]]
    assert sorted(names) == sorted(f"cap.{i}" for i in range(5))
    assert len(names) == len(set(names))


def test_a_capability_with_no_verification_is_broken_not_omitted(tmp_path: Path) -> None:
    """The whole point. Dropping it from the table would read as working."""
    entry = dict(FULL)
    entry.pop("verification_commands")
    manifest = _manifest(tmp_path, {"cap.undeclared": entry})

    ledger = led.build_ledger(manifest_path=manifest, include_behavioral=False)

    assert len(ledger["rows"]) == 1
    row = ledger["rows"][0]
    assert row["status"] == led.BROKEN
    assert "no verification_commands" in " ".join(row["reasons"])


def test_counts_sum_to_the_row_total(tmp_path: Path) -> None:
    caps = {"a": dict(FULL), "b": dict(FULL)}
    caps["b"].pop("verification_commands")
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, caps),
                              include_behavioral=False)
    assert sum(ledger["counts"].values()) == len(ledger["rows"])


# --- classification ------------------------------------------------------

def test_a_fully_declared_capability_works(tmp_path: Path) -> None:
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.ok": dict(FULL)}),
                              include_behavioral=False)
    assert ledger["rows"][0]["status"] == led.WORKS
    assert ledger["rows"][0]["reasons"] == []


def test_an_unresolvable_delegate_skill_is_broken(tmp_path: Path) -> None:
    entry = dict(FULL, delegate_skill="sweetclaude:does-not-exist")
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    row = ledger["rows"][0]
    assert row["status"] == led.BROKEN
    assert "does not resolve" in " ".join(row["reasons"])


def test_a_missing_entrypoint_script_is_broken(tmp_path: Path) -> None:
    entry = dict(FULL, command_entrypoint={"script": "scripts/not-a-real-file.py"})
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    assert ledger["rows"][0]["status"] == led.BROKEN


def test_a_mutating_capability_without_rollback_is_broken(tmp_path: Path) -> None:
    """The manifest's own rule, enforced in the report rather than only at
    schema-validation time."""
    entry = dict(FULL, mutates_project=True)
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    row = ledger["rows"][0]
    assert row["status"] == led.BROKEN
    assert "rollback" in " ".join(row["reasons"])


def test_rollback_limitations_make_a_capability_compromised(tmp_path: Path) -> None:
    entry = dict(FULL, mutates_project=True,
                 rollback_support={"supported": True, "limitations": ["no data restore"]})
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    row = ledger["rows"][0]
    assert row["status"] == led.COMPROMISED
    assert "no data restore" in " ".join(row["reasons"])


@pytest.mark.parametrize("behavior", ["escalate", "diagnose_only", "block"])
def test_a_handled_unsupported_state_does_not_downgrade(
    tmp_path: Path, behavior: str
) -> None:
    """Declaring how an edge case is handled is good practice. Marking it as a
    compromise would penalise honest declaration, which is backwards for a
    ledger whose whole purpose is to reward it."""
    entry = dict(FULL, unsupported_states=[{"condition": "weird_layout",
                                            "behavior": behavior}])
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    assert ledger["rows"][0]["status"] == led.WORKS


def test_an_unhandled_unsupported_state_makes_a_capability_compromised(
    tmp_path: Path,
) -> None:
    """A state listed with no defined behavior is a real gap — the capability
    admits it can reach a condition nobody decided what to do about."""
    entry = dict(FULL, unsupported_states=[{"condition": "weird_layout"}])
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    row = ledger["rows"][0]
    assert row["status"] == led.COMPROMISED
    assert "weird_layout" in " ".join(row["reasons"])


def test_low_entrypoint_coverage_makes_a_capability_compromised(tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.json"
    coverage.write_text(json.dumps({"files": {
        "scripts/doctor.py": {"summary": {"percent_covered": 12.0}}}}), encoding="utf-8")

    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": dict(FULL)}),
                              coverage_path=coverage, min_coverage=80.0,
                              include_behavioral=False)
    row = ledger["rows"][0]
    assert row["status"] == led.COMPROMISED
    assert "12%" in " ".join(row["reasons"])
    assert row["coverage"] == 12.0


def test_high_entrypoint_coverage_leaves_a_capability_working(tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.json"
    coverage.write_text(json.dumps({"files": {
        "scripts/doctor.py": {"summary": {"percent_covered": 95.0}}}}), encoding="utf-8")

    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": dict(FULL)}),
                              coverage_path=coverage, include_behavioral=False)
    assert ledger["rows"][0]["status"] == led.WORKS


# --- tiers ---------------------------------------------------------------

def test_a_capability_with_an_executable_is_tier_two(tmp_path: Path) -> None:
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": dict(FULL)}),
                              include_behavioral=False)
    assert ledger["rows"][0]["tier"] == led.TIER_EXECUTABLE


def test_a_capability_without_an_executable_is_tier_one(tmp_path: Path) -> None:
    entry = dict(FULL)
    entry.pop("command_entrypoint")
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    assert ledger["rows"][0]["tier"] == led.TIER_STRUCTURAL


def test_behavioral_rows_are_never_reported_as_passing(tmp_path: Path) -> None:
    """Tier 3 needs a live model. Reporting it as `works` from CI would be a
    claim the ledger cannot support."""
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": dict(FULL)}),
                              include_behavioral=True)
    behavioral = [r for r in ledger["rows"] if r["tier"] == led.TIER_BEHAVIORAL]

    assert behavioral, "no behavioral rows emitted"
    for row in behavioral:
        assert row["status"] == led.UNVERIFIABLE
        assert row["contracts"], f"{row['capability']} lists no contracts"


def test_behavioral_rows_cover_every_interaction_model_section() -> None:
    import re

    sections = re.findall(
        r"^##\s+(.+?)\s*$",
        (REPO_ROOT / "rules" / "interaction-model.md").read_text(encoding="utf-8"),
        re.M)
    rows = led._behavioral_rows()
    covered = {r["title"] for r in rows}
    assert covered == set(sections)


# --- rendering -----------------------------------------------------------

def test_markdown_lists_every_row(tmp_path: Path) -> None:
    caps = {f"cap.{i}": dict(FULL) for i in range(4)}
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, caps),
                              include_behavioral=False)
    md = led.render_markdown(ledger)
    for name in caps:
        assert f"`{name}`" in md


def test_markdown_states_the_no_omission_rule(tmp_path: Path) -> None:
    """The reader has to know an absent row would be a bug, not a pass."""
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": dict(FULL)}),
                              include_behavioral=False)
    assert "never" in led.render_markdown(ledger).lower()


# --- CLI -----------------------------------------------------------------

def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=120)


def test_cli_emits_valid_json() -> None:
    r = _run("--format", "json", "--no-behavioral")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["declared_capabilities"] >= 1


def test_cli_emits_markdown_by_default() -> None:
    r = _run("--no-behavioral")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("# SweetClaude Capability Ledger")


def test_cli_writes_to_a_file(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "ledger.md"
    r = _run("--no-behavioral", "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert out.is_file()


def test_cli_reports_a_missing_manifest(tmp_path: Path) -> None:
    r = _run("--manifest", str(tmp_path / "nope.yaml"))
    assert r.returncode == 2
    assert "not found" in r.stderr


def test_cli_fail_on_broken_exits_nonzero(tmp_path: Path) -> None:
    entry = dict(FULL)
    entry.pop("verification_commands")
    manifest = _manifest(tmp_path, {"cap.undeclared": entry})

    r = _run("--manifest", str(manifest), "--no-behavioral", "--fail-on-broken")

    assert r.returncode == 1
    assert "broken capabilities" in r.stderr


def test_cli_fail_on_broken_passes_when_all_declared(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, {"cap.ok": dict(FULL)})
    r = _run("--manifest", str(manifest), "--no-behavioral", "--fail-on-broken")
    assert r.returncode == 0, r.stderr


# --- the real manifest ---------------------------------------------------

def test_the_shipped_manifest_produces_a_ledger() -> None:
    ledger = led.build_ledger()
    assert ledger["declared_capabilities"] == len(
        (yaml.safe_load(led.MANIFEST.read_text(encoding="utf-8")) or {})["capabilities"]
    )
    assert all(r["status"] in {led.WORKS, led.COMPROMISED, led.BROKEN, led.UNVERIFIABLE}
               for r in ledger["rows"])


# --- explicit verification tier (ISSUE-273) ------------------------------

def test_an_explicit_verification_tier_overrides_inference(tmp_path: Path) -> None:
    """Inferring tier from "has a script" cannot express a capability that is
    non-deterministic by nature. The rubric judge has an executable and is
    still Tier 3."""
    entry = dict(FULL, verification_tier=led.TIER_BEHAVIORAL)
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    assert ledger["rows"][0]["tier"] == led.TIER_BEHAVIORAL


def test_a_tier_three_capability_never_reports_as_working(tmp_path: Path) -> None:
    """The over-claim this ledger exists to prevent: CI certifying something
    only a live model can judge."""
    entry = dict(FULL, verification_tier=led.TIER_BEHAVIORAL)
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    row = ledger["rows"][0]
    assert row["status"] == led.UNVERIFIABLE
    assert any("Tier 3" in r for r in row["reasons"])


def test_a_tier_three_capability_still_reports_real_defects(tmp_path: Path) -> None:
    """Downgrading Tier 3 from works must not also mask a genuine problem."""
    entry = dict(FULL, verification_tier=led.TIER_BEHAVIORAL)
    entry.pop("verification_commands")
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    assert ledger["rows"][0]["status"] == led.BROKEN


def test_an_invalid_declared_tier_falls_back_to_inference(tmp_path: Path) -> None:
    entry = dict(FULL, verification_tier="tier-99-nonsense")
    ledger = led.build_ledger(manifest_path=_manifest(tmp_path, {"cap.x": entry}),
                              include_behavioral=False)
    assert ledger["rows"][0]["tier"] == led.TIER_EXECUTABLE


def test_the_rubric_judge_is_declared_and_reported_broken() -> None:
    """The ledger earning its keep on its first run against main.

    quality.rubric_judge is declared in the manifest and its entrypoint,
    scripts/artifact_judge.py, is not on main — it stays parked under ISSUE-279
    because it predates the three-way verdict, context handling and the Codex
    backend the behavioural judge gained.

    The entry is deliberately kept rather than deleted. A declared capability
    with no implementation is exactly what this ledger exists to surface, and
    the generator's own docstring gives the reason: an omitted capability is
    indistinguishable from a working one. It flips to
    not-mechanically-verifiable when ISSUE-279 lands the judge or retires the
    entry.
    """
    ledger = led.build_ledger(include_behavioral=False)
    row = next(r for r in ledger["rows"] if r["capability"] == "quality.rubric_judge")

    assert row["tier"] == led.TIER_BEHAVIORAL
    assert row["status"] == led.BROKEN
    assert any("artifact_judge.py not found" in r for r in row["reasons"])


# --- the committed table (ISSUE-294) -------------------------------------

COMMITTED_TABLE = REPO_ROOT / "docs" / "user-guide" / "capability-ledger-table.md"


def test_the_committed_table_exists() -> None:
    """The ledger is only useful if its output is somewhere a person reads.
    Generating it into a CI artifact nobody opens is the same as not having it.
    """
    assert COMMITTED_TABLE.is_file()


def test_the_committed_table_covers_every_declared_capability() -> None:
    """The property the whole thing rests on: a capability cannot be dropped
    between the manifest and the table. Omission is indistinguishable from
    working."""
    declared = set(led._load_manifest(led.MANIFEST)["capabilities"])
    text = COMMITTED_TABLE.read_text(encoding="utf-8")

    missing = [c for c in declared if f"`{c}`" not in text]

    assert not missing, f"declared but absent from the table: {sorted(missing)}"


def test_no_capability_is_reported_works_without_a_verification_path() -> None:
    """`works` must never be the default for something nobody checked."""
    for row in led.build_ledger(include_behavioral=False)["rows"]:
        if row["status"] == led.WORKS:
            entry = led._load_manifest(led.MANIFEST)["capabilities"][row["capability"]]
            assert entry.get("verification_commands"), row["capability"]


def test_every_row_carries_a_status_from_the_fixed_vocabulary() -> None:
    valid = {led.WORKS, led.COMPROMISED, led.BROKEN, led.UNVERIFIABLE}

    for row in led.build_ledger(include_behavioral=False)["rows"]:
        assert row["status"] in valid, row


def test_a_non_works_row_always_says_why() -> None:
    """A verdict with no reason cannot be acted on or disputed."""
    for row in led.build_ledger(include_behavioral=False)["rows"]:
        if row["status"] != led.WORKS:
            assert row["reasons"], row["capability"]
