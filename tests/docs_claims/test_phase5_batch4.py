"""Phase 5 docs-claims batch 4: cheatsheets, walkthroughs, state and memory, beta rescue. Each test is named for its remediation-ledger row id."""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "user-guide"

DOCS = [
    "cheatsheet-new-project",
    "cheatsheet-existing-project",
    "walkthroughs",
    "state-and-memory",
    "beta-rescue",
]

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-⛿✅✨❌❎❓-❕❗➕-➗⭐⭕️]"
)


def doc(name):
    return (GUIDE / f"{name}.md").read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def section(text, heading_pattern):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        m = re.match(r"^(#+)\s+(.*)$", line)
        if m and re.search(heading_pattern, m.group(2), re.I):
            start = i
            depth = len(m.group(1))
            break
    assert start is not None, f"heading matching {heading_pattern!r} not found"
    out = [lines[start]]
    for line in lines[start + 1:]:
        m = re.match(r"^(#+)\s", line)
        if m and len(m.group(1)) <= depth:
            break
        out.append(line)
    return "\n".join(out)


@pytest.mark.parametrize("name", DOCS)
def test_style_version_and_date_near_top(name):
    head = "\n".join(doc(name).splitlines()[:15])
    assert re.search(r"^\*\*Version:\*\*\s+\S+", head, re.M), f"{name}: no **Version:** line near top"
    assert re.search(r"^\*\*Date:\*\*\s+\d{4}-\d{2}-\d{2}", head, re.M), f"{name}: no **Date:** line near top"


@pytest.mark.parametrize("name", DOCS)
def test_style_no_emoji(name):
    assert not EMOJI.search(doc(name)), f"{name}: contains emoji"


def test_R_137_cheatsheets_onboard_with_configure_init():
    for name in ("cheatsheet-new-project", "cheatsheet-existing-project"):
        assert "/sweetclaude:configure init" in doc(name), name
    assert "takes over from here" not in doc("cheatsheet-new-project")


def test_R_140_setup_does_not_claim_claude_md_for_every_project():
    new_step = section(doc("cheatsheet-new-project"), r"Step 1")
    assert "CLAUDE.md" not in new_step
    assert "Updates to CLAUDE.md if needed" not in doc("cheatsheet-existing-project")


def test_R_141_discovery_is_started_manually_after_feature_selection():
    text = flat(doc("cheatsheet-new-project"))
    assert "feature selection" in text
    assert text.index("feature selection") < text.index("/sweetclaude:plan product-discovery")
    assert not re.search(r"Step \d+: Concept Articulation", text)


def test_R_142_discovery_levels_use_l1_l2_l3_names():
    text = doc("cheatsheet-new-project")
    for token in ("L1", "L2", "L3"):
        assert token in text
    assert "11-section" not in text
    assert "Quick intent" not in text


def test_R_143_discovery_output_is_state_discovery_yaml():
    text = doc("cheatsheet-new-project")
    assert ".sweetclaude/state/discovery.yaml" in text
    assert "strategy/" not in text


def test_R_144_milestones_link_uses_issue_and_ms_ids():
    text = doc("cheatsheet-new-project")
    assert "product-milestones link ISSUE-NNN MS-NNN" in text
    assert "US-XXX" not in text


def test_R_145_cheatsheets_do_not_instruct_bump_version_script():
    for name in ("cheatsheet-new-project", "cheatsheet-existing-project"):
        assert "bump-version.sh" not in doc(name), name


def test_R_146_go_proposes_next_item_not_acts():
    text = flat(doc("cheatsheet-new-project"))
    assert "reads your phase state and acts" not in text
    assert re.search(r"reads (your )?(phase )?state and proposes", text)


def test_R_148_project_scan_describes_only_what_setup_runs():
    scan = section(doc("cheatsheet-existing-project"), r"Project Scan").lower()
    assert "test coverage" not in scan
    assert "open github issues" not in scan
    assert "strategy:" not in scan
    assert "git log" in scan or "readme" in scan


def test_R_149_existing_project_interview_lists_three_questions():
    interview = section(doc("cheatsheet-existing-project"), r"Interview").lower()
    assert "four questions" not in interview
    assert "three questions" in interview
    assert "project name" in interview
    assert "issue tracker" in interview


def test_R_150_stage_answer_sets_version_stage_without_pipeline_positioning():
    text = doc("cheatsheet-existing-project")
    assert "Pipeline Positioning" not in text
    assert "DISCOVER" not in text
    assert "version_stage" in text


def test_R_151_setup_does_not_create_a_decision_log():
    assert "decision log" not in doc("cheatsheet-existing-project").lower()


def test_R_152_setup_ends_by_offering_optional_features():
    text = doc("cheatsheet-existing-project")
    assert "suggests a specific first action" not in text
    assert "optional features" in text


def test_R_153_session_start_shows_short_status_line():
    text = doc("cheatsheet-existing-project")
    assert "Status fires automatically" not in text
    assert "status line" in text


def test_R_170_evidence_dir_is_release_gate_control_receipts():
    text = flat(doc("state-and-memory"))
    assert "and `state/evidence/` directories" not in text
    assert "scripts/control_receipts.py" in text
    assert re.search(r"state/evidence/.{0,200}release[- ]gate|release[- ]gate.{0,200}state/evidence/", text)


def test_R_171_yaml_example_uses_schema_2_and_null_declined():
    text = doc("state-and-memory")
    assert "schema_version: 2" in text
    assert "schema_version: 1" not in text
    assert "declined: null" in text
    assert "declined: false" not in text


def test_R_172_version_stage_starts_at_idea():
    row = next(l for l in doc("state-and-memory").splitlines() if l.startswith("| `project.version_stage`"))
    assert "IDEA" in row
    assert "PROTOTYPE" not in row
    assert re.search(r"setup writes `?IDEA`?", flat(row))


def test_R_173_version_stage_does_not_control_progressive_disclosure():
    assert "progressive disclosure" not in doc("state-and-memory").lower()


def test_R_174_project_type_values_are_new_and_existing_code():
    row = next(l for l in doc("state-and-memory").splitlines() if l.startswith("| `project.type`"))
    assert "cold-start" not in row
    assert "`new`" in row
    assert "`existing-code`" in row


def test_R_176_feature_status_starts_at_not_offered():
    row = next(l for l in doc("state-and-memory").splitlines() if l.startswith("| `features.*`"))
    assert "not_configured" not in row
    assert "not_offered" in row


def test_R_177_update_command_named_per_major_version():
    text = flat(doc("state-and-memory"))
    assert "/sweetclaude:update" in text
    assert "In 4.x, `/sweetclaude:configure update` reports drift" not in text
    assert "/sweetclaude:configure update" in text


def test_R_179_learnings_are_applied_silently():
    reg = flat(section(doc("state-and-memory"), r"improvement-register"))
    assert "still apply?" not in reg
    assert "silently" in reg


def test_R_181_traceability_writers_are_named_correctly():
    trace = section(doc("state-and-memory"), r"^Traceability")
    for writer in ("setup", "product-user-tdd-tests", "code-testing", "documents-update-docs", "mockup-graduate"):
        assert writer in trace, writer
    assert "product-user-stories" not in trace
    assert "implementer agent" not in trace


def test_R_183_global_uninstall_uses_plugin_command():
    text = doc("state-and-memory")
    assert "sweetclaude-uninstall.sh" not in text
    assert "/plugin uninstall sweetclaude@sweetclaude-stable" in text
    assert "/sweetclaude:configure purge" in text


def test_R_184_surviving_commits_come_from_skills_not_checkpoint_hook():
    text = doc("state-and-memory")
    assert "git-checkpoint" not in text
    assert re.search(r"commits? made by skills", text)
    assert "RED commit" in text


def test_R_185_product_dir_is_not_labelled_4x_only():
    line = next(l for l in doc("state-and-memory").splitlines() if l.startswith("├── product/"))
    assert "4.x" not in line
    assert "backlog" in line


def test_R_190_existing_codebase_interview_is_three_questions_with_assessment_path():
    sec = section(doc("walkthroughs"), r"^2\. ").lower()
    assert "four-question" not in sec
    assert "messy" not in sec
    assert "three" in sec
    assert "issue tracker" in sec
    assert "assessment" in sec


def test_R_191_hotfix_triage_questions_and_rollback_fallback():
    sec = flat(section(doc("walkthroughs"), r"^3\. ")).lower()
    for token in ("failure", "severity", "scope"):
        assert token in sec, token
    assert "temporary mitigation" not in sec
    assert "is rollback faster than patching" not in sec
    assert "if rollback is faster" not in sec
    assert "rollback-revert" in sec
    assert "does not resolve" in sec or "unresolved" in sec


def test_R_192_post_mortem_is_offered_now_or_later():
    pm = flat(section(doc("walkthroughs"), r"^POST-MORTEM$")).lower()
    assert "spawned automatically" not in pm
    assert "backlog item now" in pm
    assert "later" in pm


def test_R_193_post_mortem_reminds_about_tech_debt_followup():
    pm = flat(section(doc("walkthroughs"), r"^POST-MORTEM$")).lower()
    assert "creates a follow-on tech-debt work item" not in pm
    assert "reminds" in pm or "reminder" in pm
    assert "tech-debt" in pm


def test_R_194_rag_index_lives_in_dot_rag_index():
    text = doc("walkthroughs")
    assert ".rag-index/" in text
    assert "corpus/rag/" not in text


def test_R_195_code_feature_search_order_matches_skill():
    sec = section(doc("walkthroughs"), r"^6\. ")
    para = flat(sec.split("### Step 0")[0])
    assert ".sweetclaude/stories" not in para
    i_gherkin = para.index("Gherkin")
    i_product = para.index(".sweetclaude/product/")
    i_docs = para.index("docs/")
    assert i_gherkin < i_product < i_docs
    assert "features/" in para


def test_R_196_story_branch_step_matches_code_feature():
    step = flat(section(doc("walkthroughs"), r"Step 0")).lower()
    assert "us-042" not in step
    assert "issue-" in step
    assert "recommended" in step
    assert "main is untouched until you open a pr" not in step
    assert "merge" in step and "main" in step


def test_R_197_corpus_steps_check_previous_and_allow_risk_override():
    sec = flat(section(doc("walkthroughs"), r"^4\. "))
    assert "state machine refuses" not in sec
    assert "I accept the risk of corpus corruption" in sec


def test_R_216_beta_rescue_removes_bare_legacy_marketplace():
    lines = [l.strip() for l in doc("beta-rescue").splitlines()]
    assert "/plugin marketplace remove sweetclaude" in lines
