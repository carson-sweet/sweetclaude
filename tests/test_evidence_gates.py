from pathlib import Path


ROOT = Path(__file__).parents[1]


def _skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_code_verify_writes_completion_evidence_receipts():
    skill = _skill("code-verify")

    assert "evidence.py write" in skill
    assert "--receipt-type completion" in skill
    assert "--subject-id {WORK_ITEM_ID}" in skill
    assert "--evidence-receipt {receipt}" in skill


def test_code_verify_runs_the_command_rather_than_asserting_its_result():
    """This replaced an assertion that the skill said "do not write a passing
    receipt" for a failed command (ISSUE-283).

    That instruction was the defect. It asked the model to be honest about a
    run instead of having the script perform the run, so a receipt reading
    `status: pass, command: "npm test"` could be written by a project with no
    test script — which is how this was found. `--run` executes the command and
    records the exit code, so there is nothing left to be honest about.
    """
    skill = _skill("code-verify")

    write_block = skill[skill.index("evidence.py write"):]
    write_block = write_block[:write_block.index("```")]
    assert "--run" in write_block


def test_project_issue_close_requires_evidence_receipt_for_done():
    skill = _skill("project-issues")

    close_idx = skill.index("## Close")
    close_section = skill[close_idx:skill.index("## Decline")]
    assert "require a valid completion evidence receipt" in close_section
    assert "evidence.py validate" in close_section
    assert "--evidence-receipt {receipt_path}" in close_section


def test_backlog_triage_done_requires_evidence_receipt():
    skill = _skill("project-backlog-triage")

    done_idx = skill.index("On `done`")
    done_section = skill[done_idx:skill.index("### 6. Split flow")]
    assert "Require a valid completion evidence receipt" in done_section
    assert "evidence.py validate" in done_section
    assert "--evidence-receipt \"{receipt_path}\"" in done_section


def test_go_closeout_requires_evidence_receipt_before_done():
    skill = _skill("go")

    assert "Step C5" in skill
    c5 = skill[skill.index("**Step C5"):skill.index("**Step C6")]
    assert "Require a fresh completion evidence receipt" in c5
    assert "evidence.py validate" in c5
    assert "--evidence-receipt \"{receipt_path}\"" in c5


def test_epic_completion_requires_evidence_receipt_before_done():
    skill = _skill("epics")

    complete = skill[skill.index("## Operation: Complete"):]
    assert "Require a fresh completion evidence receipt" in complete
    assert "evidence.py validate" in complete
    assert "--evidence-receipt \"{receipt_path}\"" in complete


def test_github_sync_creates_external_close_receipt_before_local_done():
    skill = _skill("project-gh-sync-issues")

    assert "evidence.py'), 'write'" in skill
    assert "'--receipt-type', 'external-close'" in skill
    assert "'--evidence-receipt', receipt" in skill


def test_deploy_ship_writes_ship_evidence_receipt_after_smoke_test():
    skill = _skill("deploy-ship")

    assert "evidence.py write" in skill
    assert "--receipt-type ship" in skill
    assert "--check smoke-test" in skill
