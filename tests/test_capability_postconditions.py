"""Declared postconditions are executed, not just declared (ISSUE-299).

Every capability in config/capability-manifest.yaml declares a postcondition
as prose. Nothing ran it. What the manifest declared as executable was
`verification_commands`, and for 43 of the 51 tier-1 skill capabilities that
pointed at tests/test_skill_contracts.py — a corpus-wide structural suite that
asserts frontmatter, licences and reference resolution. It passes whether or
not the postcondition holds, so `project.deactivate` could claim a green
verification path while nothing had ever checked that .sweetclaude/disabled
gets written.

The harness here runs the skill's own code block against a fixture project and
asserts the declared postcondition against the result. Two properties matter
more than coverage:

  * The block is selected by matching its content, not its index, so a skill
    edit that removes the code fails the check loudly instead of silently
    selecting a neighbouring block.
  * Breaking a skill must break its check. A harness that passes by running
    nothing is the defect this issue exists to close, so the mutation tests
    below are not optional extras — they are the reason to believe the rest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from postcondition_verify import (
    BlockNotFound,
    PostconditionFailed,
    resolve_skill_markdown,
    verify_capability,
)

REPO_ROOT = Path(__file__).parents[1]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimally configured project — enough for a skill block to run."""
    p = tmp_path / "proj"
    (p / ".sweetclaude" / "state").mkdir(parents=True)
    return p


# --- the real check ------------------------------------------------------

def test_deactivate_writes_the_disabled_marker(project: Path) -> None:
    """skill-library/configure/off runs `touch .sweetclaude/disabled`; its postcondition says
    so. Until now nothing asserted the two agreed."""
    result = verify_capability("project.deactivate", project)
    assert result.passed, result.detail
    assert (project / ".sweetclaude" / "disabled").exists()


# --- the harness cannot pass by running nothing --------------------------

def test_a_broken_skill_block_fails_the_check(project: Path, tmp_path: Path) -> None:
    """The mutation this whole issue turns on. The block still matches the
    selector and still runs — it just no longer leaves the project in the
    state the postcondition claims. That is the regression a structural suite
    cannot see, so it is the one the harness must catch.

    The mutation appends a clobber rather than editing the selected line: a
    mutation that changes the line itself is a different failure, covered by
    test_a_missing_block_fails_loudly below.
    """
    skills = tmp_path / "skills" / "off"
    skills.mkdir(parents=True)
    original = (REPO_ROOT / "skill-library" / "configure" / "off" / "SKILL.md").read_text(encoding="utf-8")
    broken = original.replace(
        "touch .sweetclaude/disabled",
        "touch .sweetclaude/disabled\nrm -f .sweetclaude/disabled",
    )
    assert broken != original, "the mutation did not apply — did skill-library/configure/off change?"
    (skills / "SKILL.md").write_text(broken, encoding="utf-8")

    with pytest.raises(PostconditionFailed):
        verify_capability("project.deactivate", project, skills_dir=tmp_path / "skills")


def test_a_missing_block_fails_loudly(project: Path, tmp_path: Path) -> None:
    """Selecting by content means a deleted block is an error, not a silent
    pass on whatever block happens to sit at that index."""
    skills = tmp_path / "skills" / "off"
    skills.mkdir(parents=True)
    original = (REPO_ROOT / "skill-library" / "configure" / "off" / "SKILL.md").read_text(encoding="utf-8")
    gutted = original.replace("touch .sweetclaude/disabled", "echo nothing")
    (skills / "SKILL.md").write_text(gutted, encoding="utf-8")

    with pytest.raises(BlockNotFound):
        verify_capability("project.deactivate", project, skills_dir=tmp_path / "skills")


# --- a project real enough for a skill block to run ----------------------

TEMPLATE = REPO_ROOT / "scripts" / "sweetclaude-yaml-template.py"


@pytest.fixture
def configured(tmp_path: Path) -> Path:
    """Onboarded project, deliberately missing every directory a check asserts.

    corpus/, artifacts/, .sweetclaude/research/, .sweetclaude/testing/ and
    .sweetclaude/failure/ are left absent on purpose: a path_written check
    against a directory the fixture already made would pass whether or not the
    block ran.
    """
    import subprocess
    import sys

    import yaml

    root = tmp_path / "configured"
    state = root / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    r = subprocess.run(
        [sys.executable, str(TEMPLATE), "--name", "fixture", "--type", "existing-code",
         "--version-stage", "GA", "--installed-version", "4.5.2",
         "--output", str(state / "sweetclaude.yaml")],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT))
    assert r.returncode == 0, r.stderr
    data = yaml.safe_load((state / "sweetclaude.yaml").read_text(encoding="utf-8"))
    data.setdefault("framework", {})["setup_complete"] = True
    (state / "sweetclaude.yaml").write_text(
        yaml.safe_dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")

    # several skills resolve their base from session-state, not the manifest
    (state / "session-state.yaml").write_text(yaml.safe_dump(
        {"paths": {f"{c}_base": f".sweetclaude/{c}"
                   for c in ("product", "design", "technical", "strategy")}},
        sort_keys=False), encoding="utf-8")

    for sub in ("backlog/done", "roadmap/epics/done", "roadmap/milestones",
                "roadmap/issues/done"):
        (root / ".sweetclaude" / "product" / sub).mkdir(parents=True, exist_ok=True)
    (root / ".sweetclaude" / "artifact-privacy.yaml").write_text(yaml.safe_dump({
        "schema_version": 1,
        "categories": {c: {"privacy": "private", "base_path": f".sweetclaude/{c}"}
                       for c in ("strategy", "product", "technical", "design")},
    }, sort_keys=False), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)],
                   capture_output=True, timeout=30)
    return root


# --- the two read-only claims that hold ---------------------------------

def test_corpus_status_does_not_mutate(configured: Path) -> None:
    result = verify_capability("corpus.status", configured)
    assert result.passed, result.detail
    assert result.blocks_run == 2, "both blocks must run, or the check is vacuous"


def test_init_writes_nothing_itself(configured: Path) -> None:
    """ISSUE-249 was init writing state v4 had abandoned. Its postcondition
    names that issue; nothing asserted it until now."""
    result = verify_capability("init.dispatch", configured)
    assert result.passed, result.detail
    assert result.blocks_run == 3


# --- the two corrected declarations -------------------------------------

def test_features_configure_writes_feature_status(configured: Path) -> None:
    """Declared read_only until ISSUE-299; it writes via os.replace."""
    result = verify_capability("features.configure", configured)
    assert result.passed, result.detail


def test_help_writes_the_skip_flag_when_asked(configured: Path) -> None:
    """The write is real, but only on the user's request — the reason its
    postcondition now says so instead of claiming no mutation at all."""
    import yaml

    result = verify_capability("session.help", configured)
    assert result.passed, result.detail
    state = yaml.safe_load(
        (configured / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text(encoding="utf-8"))
    assert state["skip_help_welcome"] is True


# --- every new check kind must be able to fail --------------------------

def _mutated_skill(tmp_path: Path, skill: str, old: str, new: str) -> Path:
    root = tmp_path / "mutated" / skill
    root.mkdir(parents=True)
    source = resolve_skill_markdown(skill)
    text = source.read_text(encoding="utf-8")
    assert old in text, f"mutation target {old!r} not in {source.relative_to(REPO_ROOT)}"
    (root / "SKILL.md").write_text(text.replace(old, new), encoding="utf-8")
    return tmp_path / "mutated"


def test_no_mutation_fails_when_a_block_starts_writing(
    configured: Path, tmp_path: Path
) -> None:
    skills = _mutated_skill(
        tmp_path, "corpus-status",
        "find corpus/raw/inbox/ -type f",
        "touch .sweetclaude/leaked\nfind corpus/raw/inbox/ -type f",
    )
    with pytest.raises(PostconditionFailed):
        verify_capability("corpus.status", configured, skills_dir=skills)


def test_content_changed_fails_when_the_write_is_removed(
    configured: Path, tmp_path: Path
) -> None:
    skills = _mutated_skill(
        tmp_path, "_features",
        "os.replace(tmp_name, path)",
        "pass  # write removed",
    )
    with pytest.raises(PostconditionFailed):
        verify_capability("features.configure", configured, skills_dir=skills)


def test_state_key_written_fails_when_the_key_changes(
    configured: Path, tmp_path: Path
) -> None:
    skills = _mutated_skill(
        tmp_path, "help",
        "d['skip_help_welcome'] = True",
        "d['skip_help_welcome'] = True\nd.pop('skip_help_welcome')",
    )
    with pytest.raises(PostconditionFailed):
        verify_capability("session.help", configured, skills_dir=skills)


# --- every specced capability, driven off the manifest -------------------

def _specced() -> list[str]:
    """Read the capabilities under test from the manifest, not a hardcoded
    list: a spec added without a test would otherwise go unexercised while the
    ledger counted it as tier-2."""
    import yaml

    manifest = yaml.safe_load(
        (REPO_ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"))
    return sorted(
        cid for cid, entry in manifest["capabilities"].items()
        if any(pc.get("verify") for pc in entry.get("postconditions", []))
    )


@pytest.mark.parametrize("capability", _specced())
def test_declared_postcondition_holds(capability: str, configured: Path) -> None:
    result = verify_capability(capability, configured)
    assert result.passed, result.detail


# A verification_commands entry naming a test file that does not exist runs
# nothing and reports nothing, while the ledger counts the capability as
# executably verified. Entries here are known-broken pointers, kept visible
# rather than deleted, following the allowlist convention in
# test_skill_contracts.py.
KNOWN_MISSING_VERIFICATION = {
    # Three of these went with EP-004's artifact-quality line when it was
    # parked on park/EP-004-ledger-and-quality; the pointers on main stayed
    # behind, so the ledger counts as executably verified a command that
    # cannot run here.
    "quality.artifact_lint": (
        "tests/test_artifact_quality.py exists only on "
        "park/EP-004-ledger-and-quality (4d27d96, ISSUE-271/272)."
    ),
    "quality.rubric_judge": (
        "tests/test_artifact_judge.py exists only on "
        "park/EP-004-ledger-and-quality (5ac5ea4, ISSUE-273)."
    ),
    "update.framework_sync": (
        "tests/test_update_orchestrator.py has never existed on any branch "
        "(git log --all is empty for it). The correct pointer is "
        "undetermined, so it is recorded rather than guessed."
    ),
}


def _named_test_files() -> dict[str, list[str]]:
    import yaml

    manifest = yaml.safe_load(
        (REPO_ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for cid, entry in manifest["capabilities"].items():
        named = [
            tok for cmd in (entry.get("verification_commands") or [])
            for tok in cmd.split() if tok.startswith("tests/")
        ]
        if named:
            out[cid] = named
    return out


def test_every_named_verification_file_exists() -> None:
    """A pointer to a file that is not there is not verification."""
    broken = {
        cid: [f for f in files if not (REPO_ROOT / f).is_file()]
        for cid, files in _named_test_files().items()
    }
    broken = {c: f for c, f in broken.items() if f}
    unexpected = {c: f for c, f in broken.items() if c not in KNOWN_MISSING_VERIFICATION}
    assert not unexpected, (
        "verification_commands name test files that do not exist:\n  "
        + "\n  ".join(f"{c}: {', '.join(f)}" for c, f in sorted(unexpected.items()))
    )


def test_the_known_missing_allowlist_has_no_stale_entries() -> None:
    """When a broken pointer is fixed, its allowlist entry must go with it, or
    the allowlist starts hiding regressions instead of recording them."""
    named = _named_test_files()
    stale = [
        cid for cid in KNOWN_MISSING_VERIFICATION
        if cid not in named
        or all((REPO_ROOT / f).is_file() for f in named[cid])
    ]
    assert not stale, f"allowlist entries no longer needed: {stale}"


def test_substituted_evidence_is_tracked_separately() -> None:
    """Harness-supplied values are weaker evidence than a block that ran
    unaided. They are allowed, but must never be indistinguishable."""
    import yaml

    manifest = yaml.safe_load(
        (REPO_ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"))
    subbed = []
    for cid, entry in manifest["capabilities"].items():
        for pc in entry.get("postconditions", []):
            v = pc.get("verify") or {}
            if v.get("substitutions"):
                assert v.get("evidence") == "substituted", (
                    f"{cid} substitutes without declaring evidence: substituted")
                subbed.append(cid)
    assert subbed, "expected at least one substituted spec"


def test_path_absent_fails_when_the_removal_is_removed(
    configured: Path, tmp_path: Path
) -> None:
    """purge's whole point is that .sweetclaude/ is gone afterwards."""
    skills = _mutated_skill(
        tmp_path, "purge",
        "rm -rf .sweetclaude/",
        "rm -rf .sweetclaude/nothing-here",
    )
    with pytest.raises(PostconditionFailed):
        verify_capability("purge.remove_all", configured, skills_dir=skills)


def test_artifact_written_fails_when_the_create_call_is_gutted(
    configured: Path, tmp_path: Path
) -> None:
    skills = _mutated_skill(
        tmp_path, "project-goals",
        "sc_artifact_create milestone '{",
        "true sc_artifact_create milestone '{",
    )
    with pytest.raises(PostconditionFailed):
        verify_capability("project.goals", configured, skills_dir=skills)


def test_the_fixture_guard_refuses_the_working_repository() -> None:
    """purge's block is `rm -rf .sweetclaude/`. Nothing may point it here."""
    from postcondition_verify import UnsafeFixture

    with pytest.raises(UnsafeFixture):
        verify_capability("purge.remove_all", REPO_ROOT)
    with pytest.raises(UnsafeFixture):
        verify_capability("purge.remove_all", REPO_ROOT / "tests")


# --- tier-3: what cannot be executed must say so, and why ---------------

def _manifest() -> dict:
    import yaml

    return yaml.safe_load(
        (REPO_ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"))


def test_every_behavioral_capability_records_why_it_is_not_executable() -> None:
    """ISSUE-299 requires what cannot be run to be listed with the reason
    rather than quietly counted. A tier-3 capability with neither an
    executable spec nor a recorded reason is exactly that quiet count."""
    silent = []
    for cid, entry in _manifest()["capabilities"].items():
        if entry.get("verification_tier") != "tier-3-behavioral":
            continue
        for pc in entry.get("postconditions", []):
            if not pc.get("verify") and not pc.get("not_executable"):
                silent.append(f"{cid}.{pc['id']}")
    assert not silent, (
        "tier-3 postconditions with no recorded reason:\n  " + "\n  ".join(sorted(silent)))


def test_no_postcondition_is_both_executable_and_not() -> None:
    both = [
        f"{cid}.{pc['id']}"
        for cid, entry in _manifest()["capabilities"].items()
        for pc in entry.get("postconditions", [])
        if pc.get("verify") and pc.get("not_executable")
    ]
    assert not both, f"postconditions claiming both routes: {both}"


def test_not_executable_reasons_are_substantive() -> None:
    """A reason of 'n/a' would satisfy the letter of the rule and defeat it."""
    thin = []
    for cid, entry in _manifest()["capabilities"].items():
        for pc in entry.get("postconditions", []):
            ne = pc.get("not_executable")
            if not ne:
                continue
            reason = (ne.get("reason") or "").strip()
            if len(reason) < 40:
                thin.append(f"{cid}.{pc['id']}: {reason!r}")
            # no-instrument: nothing scores this postcondition today. The
            # behavioural rubrics judge interaction conduct, not whether a
            # skill produced a work item, so naming a judge route here would
            # promise an instrument that does not exist.
            # none: not verifiable by anything (a production observation).
            # parked: the implementation is on another branch.
            assert ne.get("route") in {"no-instrument", "none", "parked"}, (
                f"{cid}.{pc['id']} declares an unknown route {ne.get('route')!r}")
    assert not thin, "not_executable reasons too thin to be useful:\n  " + "\n  ".join(thin)


def test_a_capability_with_no_executable_route_is_never_reported_working() -> None:
    """The ledger must not certify a capability nothing executes. This is the
    over-claim ISSUE-299 exists to remove: 21 of these read `works`."""
    import capability_ledger as led

    rows = {r["capability"]: r for r in led.build_ledger()["rows"]}
    offenders = [
        cid for cid, entry in _manifest()["capabilities"].items()
        if entry.get("verification_tier") == "tier-3-behavioral"
        and rows[cid]["status"] == "works"
    ]
    assert not offenders, f"tier-3 capabilities reported as working: {offenders}"


def test_evidence_grades_are_from_a_known_set() -> None:
    """Three grades, weakest last: a block that ran unaided, a block that ran
    on harness-supplied values, and a block read rather than run. A new grade
    must be added deliberately, not by typo."""
    known = {"unaided", "substituted", "static"}
    offenders = []
    for cid, entry in _manifest()["capabilities"].items():
        for pc in entry.get("postconditions", []):
            v = pc.get("verify") or {}
            if not v:
                continue
            grade = v.get("evidence", "unaided")
            if grade not in known:
                offenders.append(f"{cid}.{pc['id']}: {grade!r}")
    assert not offenders, f"unknown evidence grades: {offenders}"


def test_a_no_instrument_capability_does_not_claim_to_be_scored() -> None:
    """The relabel has to reach the published table, or it is cosmetic.

    Reporting "scored only against a live model" for a capability no rubric
    covers restates the over-claim ISSUE-299 removes, one level down: the
    status is honest while the note promises an instrument that does not
    exist. The rows that DO have rubrics must keep saying so.
    """
    import capability_ledger as led

    manifest = _manifest()["capabilities"]
    rows = {r["capability"]: r for r in led.build_ledger()["rows"]}

    no_instrument = {
        cid for cid, entry in manifest.items()
        if any((pc.get("not_executable") or {}).get("route") == "no-instrument"
               for pc in entry.get("postconditions", []))
    }
    assert len(no_instrument) >= 20, f"expected the re-tiered set, got {len(no_instrument)}"

    for cid in sorted(no_instrument):
        notes = " ".join(rows[cid]["reasons"]).lower()
        if rows[cid]["status"] != "not-mechanically-verifiable":
            continue  # a real defect (broken/compromised) reports that instead
        assert "no instrument" in notes, (
            f"{cid} is routed no-instrument but its ledger note reads {notes!r}")
        assert "scored only against a live model" not in notes, (
            f"{cid} promises live-model scoring but no rubric covers it")

    # the interaction-model rules genuinely are scored by the judge
    judged = [r for k, r in rows.items() if k.startswith("interaction-model.")]
    assert judged, "no interaction-model rows in the ledger"
    for row in judged:
        assert "behavioral_judge" in " ".join(row["reasons"]), (
            "interaction-model rules must keep naming the instrument that scores them")


# --- the derived-cache exclusion must not become an escape hatch ---------

def test_ignore_cannot_cover_a_source_of_truth_path() -> None:
    """`ignore` exists so a derived, gitignored cache does not fail a
    read-only claim. If it could name .sweetclaude/state or a product base,
    it would be a general way to make any no_mutation check pass, which is
    worse than having no check."""
    from postcondition_verify import PostconditionError, validate_ignore

    for allowed in (".sweetclaude/cache", ".sweetclaude/cache/", "artifacts/build"):
        assert validate_ignore([allowed], "t")

    for refused in (".", "/", "*", "**", "./", ".sweetclaude/state",
                    ".sweetclaude/product", ".sweetclaude/product/backlog",
                    "./.sweetclaude/work", ".sweetclaude/design",
                    ".sweetclaude/technical", ".sweetclaude/strategy"):
        with pytest.raises(PostconditionError):
            validate_ignore([refused], "t")


def test_no_declared_ignore_list_hides_a_source_path() -> None:
    """Every ignore list in the manifest, checked against the same guard."""
    from postcondition_verify import validate_ignore

    for cid, entry in _manifest()["capabilities"].items():
        for pc in entry.get("postconditions", []):
            ignore = (pc.get("verify") or {}).get("ignore")
            if ignore:
                validate_ignore(ignore, cid)  # raises if it covers a source path


def test_the_cache_exclusion_still_catches_a_real_write(
    configured: Path, tmp_path: Path
) -> None:
    """Ignoring roadmap.db must not ignore anything else."""
    skills = _mutated_skill(
        tmp_path, "dashboard",
        "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --rebuild",
        "mkdir -p .sweetclaude/state && touch .sweetclaude/state/leaked.yaml\n"
        "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --rebuild",
    )
    with pytest.raises(PostconditionFailed):
        verify_capability("report.dashboard", configured, skills_dir=skills)


def test_roadmap_analysis_priority_write_back_fails_when_removed(
    configured: Path, tmp_path: Path
) -> None:
    """The write is the point of RICE scoring; losing it must fail."""
    skills = _mutated_skill(
        tmp_path, "product-roadmap-analysis",
        "sc_artifact_write <MS-NNN>",
        "true sc_artifact_write <MS-NNN>",
    )
    with pytest.raises(PostconditionFailed):
        verify_capability("product.roadmap_analysis", configured, skills_dir=skills)


def test_the_seed_does_not_leak_into_other_capabilities(configured: Path) -> None:
    """A seeded MS-001 in the shared fixture would satisfy project.goals'
    artifact_written glob without its block doing anything, so the seed must
    be written by the spec that needs it and nowhere else."""
    milestones = configured / ".sweetclaude" / "product" / "roadmap" / "milestones"
    assert not list(milestones.glob("MS-*.md")), (
        "the fixture must not pre-seed a milestone; project.goals asserts one appears")
    verify_capability("project.goals", configured)
