from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def _normalized(path: str) -> str:
    return " ".join(_read(path).split())


def test_shared_process_controls_contract_exists():
    text = _read("skills/process-controls.md")

    for phrase in (
        "Required Ledger",
        "Default Limits",
        "Hard Stops",
        "Resume Requirements",
        "one three-reviewer caucus per budget window",
        "second blocking caucus failure",
        "no background implementer or reviewer dispatch while a process stop is active",
    ):
        assert phrase in text


def test_code_tdd_and_feature_require_process_control_ledger():
    for path in ("skills/code-tdd/SKILL.md", "skills/code-feature/SKILL.md", "skills/code-issue/SKILL.md"):
        text = _read(path)
        assert "skills/process-controls.md" in text
        assert ".sweetclaude/state/process-control-ledger.yaml" in text
        assert "stop disposition" in text


def test_john_wick_autonomous_caucus_steps_require_process_controls():
    for path in (
        "skills/john-wick/SKILL.md",
        "skills/john-wick/phase-1-define.md",
        "skills/john-wick/phase-2-plan.md",
        "skills/john-wick/phase-3-design.md",
        "skills/john-wick/phase-4-implement-prep.md",
        "skills/john-wick/phase-5-implement.md",
        "skills/john-wick/phase-6-verify.md",
    ):
        text = _read(path)
        assert "process-controls.md" in text
        assert "process_control" in text


def test_john_wick_state_schema_contains_process_control_state():
    text = _read("skills/john-wick/state-schema.md")

    for phrase in (
        "process_control:",
        "budget_approved",
        "max_caucus_rounds_per_step",
        "max_reviewer_agents_per_budget",
        "max_blocking_caucus_failures_per_step",
        "active_stop_disposition",
        "human_resume_approved",
    ):
        assert phrase in text


def test_shared_process_controls_define_success_criteria_contract():
    text = _read("skills/process-controls.md")
    normalized = _normalized("skills/process-controls.md")

    for phrase in (
        "success_criteria_contract",
        "success_criteria_contract_hash",
        "criterion_ids",
        "success-criteria-ledger.json",
        "scripts/success_criteria_contracts.py validate-contract",
        "scripts/success_criteria_contracts.py validate-ledger",
        "scripts/success_criteria_contracts.py validate-workflow --stage define-exit",
        "scripts/success_criteria_contracts.py validate-workflow --stage completion",
        "success_criteria_contract_valid",
        "success_criteria_completion_valid",
        "success_criteria_ledger_valid",
        "status.py set-terminal --status done",
        "--allow-missing-evidence",
        "all_success_criteria_passed == true",
    ):
        assert phrase in text
    assert "No review, caucus, verification, release, or completion step may add completion criteria" in normalized


def test_large_story_4x_canonical_entrypoint_is_large_story_skill():
    process_controls = _read("skills/process-controls.md")
    large_story = _read("skills/large-story/SKILL.md")
    john_wick = _read("skills/john-wick/SKILL.md")
    skills_reference = _read("docs/user-guide/4.x-beta/skills-reference.md")
    route = _read("skills/_route/SKILL.md")

    assert "The production 4.x entrypoint for a complete large/high-rigor story workflow is" in process_controls
    assert "`/sweetclaude:large-story`" in process_controls
    assert "`/sweetclaude:large-story`" in large_story
    assert "user-invocable: true" in large_story
    assert "Canonical 4.x entrypoint for complete large/high-rigor story workflows" in skills_reference
    assert "| **Large Story** | `/sweetclaude:large-story` |" in skills_reference
    assert "`large-story`" in route
    assert "`sweetclaude:large-story`" in route

    for forbidden in ("john-wick", "John Wick", "sweetclaude:john-wick"):
        assert forbidden not in large_story

    for path in ("skills/code-tdd/SKILL.md", "skills/code-feature/SKILL.md", "skills/code-issue/SKILL.md"):
        text = _read(path).lower()
        assert "canonical 4.x entrypoint" not in text
        assert "end-to-end large-story entrypoint" not in text

    assert "canonical SweetClaude 4.x production entrypoint" not in john_wick
    assert "end-to-end large-story entrypoint" not in john_wick


def test_large_story_entrypoint_requires_contract_before_downstream_work():
    process_controls = _normalized("skills/process-controls.md")
    large_story = _normalized("skills/large-story/SKILL.md")

    for phrase in (
        "During Define, create and freeze `success_criteria_contract`",
        "Run `validate-workflow --stage define-exit` before Plan, Design, Implementation Prep, Implementation, Verify, review, release, or caucus completion evaluation",
        "At completion, write `success-criteria-ledger.json` and run `validate-workflow --stage completion` before any `done` transition",
    ):
        assert phrase in process_controls

    for phrase in (
        "Create or locate a frozen `success_criteria_contract`",
        "Run `python3 scripts/success_criteria_contracts.py validate-workflow --stage define-exit`",
        "If validation fails, stop. Do not continue downstream",
        "No review, caucus, verification, release, or completion step may add completion criteria",
    ):
        assert phrase in large_story


def test_large_story_state_schema_contains_contract_surface():
    text = _read("skills/large-story/state-schema.md")

    for phrase in (
        "requires_success_criteria_contract: true",
        "success_criteria_contract_path: string | null",
        "success_criteria_contract_hash: string | null",
        "criterion_ids:",
        "success_criteria_ledger_path: string | null",
        ".sweetclaude/state/large-story.yaml",
        ".sweetclaude/state/workflows/{workflow_id}.yaml",
    ):
        assert phrase in text


def test_entry_skills_require_success_criteria_contract_for_large_work():
    for path in ("skills/code-tdd/SKILL.md", "skills/code-feature/SKILL.md", "skills/code-issue/SKILL.md"):
        text = _read(path)
        normalized = _normalized(path)
        assert "success_criteria_contract" in text
        assert "success_criteria_contract_hash" in text
        assert "criterion_ids" in text
        assert "success-criteria-ledger.json" in text
        assert "all_success_criteria_passed == true" in text
        assert "No review, caucus, verification, release, or completion step may add completion criteria" in normalized


def test_john_wick_phases_preserve_success_criteria_contract():
    for path in (
        "skills/john-wick/SKILL.md",
        "skills/john-wick/phase-1-define.md",
        "skills/john-wick/phase-2-plan.md",
        "skills/john-wick/phase-3-design.md",
        "skills/john-wick/phase-4-implement-prep.md",
        "skills/john-wick/phase-5-implement.md",
        "skills/john-wick/phase-6-verify.md",
    ):
        text = _read(path)
        assert "success_criteria_contract_hash" in text
        assert "criterion_ids" in text

    for path in (
        "skills/john-wick/SKILL.md",
        "skills/john-wick/phase-5-implement.md",
        "skills/john-wick/phase-6-verify.md",
    ):
        text = _read(path)
        assert "success-criteria-ledger.json" in text
        assert "all_success_criteria_passed == true" in text


def test_john_wick_state_schema_contains_success_criteria_state():
    text = _read("skills/john-wick/state-schema.md")

    for phrase in (
        "success_criteria_contract:",
        "success_criteria_contract_hash",
        "criterion_ids",
        "criteria_amendment_requests",
        "success_criteria_ledger:",
        "evaluated_contract_hash",
        "all_success_criteria_passed",
        "missing_or_failed_criterion_ids",
    ):
        assert phrase in text
