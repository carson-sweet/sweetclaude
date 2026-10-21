"""Phase 5 docs-claims batch 5: TDD, how it works, planning concepts, phases and workflows, hook development. Each test is named for its remediation-ledger row id."""
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "user-guide"

DOCS = ["tdd", "how-it-works", "planning-concepts", "phases-and-workflows", "hook-development"]

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-⛿✅✨❌❎❓-❕❗➕-➗⭐⭕️]"
)

DOCTOR_STATUSES = {
    "recovery-available",
    "supported-migration-available",
    "compatibility-mode",
    "no-maintenance-action",
    "manual-review",
    "graduation-available",
    "graduation-blocked",
    "migration-blocked",
}


def doc(name):
    return (GUIDE / f"{name}.md").read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", flat(text))


def section(text, heading_pattern):
    lines = text.splitlines()
    start = None
    depth = 0
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


def table_rows(text):
    rows = []
    for line in text.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|?\s*$", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def rows_containing(text, token):
    return [line for line in text.splitlines() if line.startswith("|") and token in line]


def yaml_block_with(text, key):
    for m in re.finditer(r"```ya?ml\n(.*?)```", text, re.S):
        if key in m.group(1):
            return m.group(1)
    raise AssertionError(f"no yaml block containing {key!r}")


def norm(text):
    return re.sub(r"\s+", " ", text.lower().replace("-", " "))


@pytest.mark.parametrize("name", DOCS)
def test_style_version_and_date_near_top(name):
    head = "\n".join(doc(name).splitlines()[:15])
    assert re.search(r"\*\*Version:\*\*\s+\S+", head), f"{name}: no **Version:** near top"
    assert re.search(r"\*\*Date:\*\*\s+\d{4}-\d{2}-\d{2}", head), f"{name}: no **Date:** near top"


@pytest.mark.parametrize("name", DOCS)
def test_style_no_emoji(name):
    assert not EMOJI.search(doc(name)), f"{name}: contains emoji"


def test_R_083_test_guardian_applies_only_once_code_tdd_marks_implementing():
    for name in ("how-it-works", "glossary"):
        text = doc(name)
        paras = [p for p in paragraphs(text) if re.search(r"test-guardian", p, re.I)]
        assert any(
            "code-tdd" in p and "tdd_phase" in p and "implementing" in p for p in paras
        ), f"{name}: no test-guardian passage naming code-tdd, tdd_phase and implementing"
    glossary_entry = [p for p in paragraphs(doc("glossary")) if p.startswith("**Test-guardian hook**")][0]
    assert not re.search(r"Active at TDD Levels 1.3", glossary_entry)


def test_R_084_test_guardian_row_names_the_real_override_path():
    row = rows_containing(section(doc("how-it-works"), r"Enforcement Tiers"), "test-guardian.sh")[0]
    assert "tool approval" not in row
    assert "tdd_phase.py release" in row
    assert "approval" in row


def test_R_085_auto_test_runner_row_has_no_approval_override():
    row = rows_containing(section(doc("how-it-works"), r"Enforcement Tiers"), "auto-test-runner.sh")[0]
    assert "approval" not in row.lower()
    assert "override" not in row.lower()


def test_R_086_guardian_on_lists_exactly_its_three_protections():
    tiers = section(doc("how-it-works"), r"Enforcement Tiers")
    para = [p for p in paragraphs(tiers) if "guardian-on" in p][0]
    low = para.lower()
    assert "skill skipping" in low
    assert "artifact skipping" in low
    assert "tdd bypass" in low
    for wrong in ("deference", "improvement register", "propose-not-ask", "language matching"):
        assert wrong not in low, f"guardian-on passage still mentions {wrong}"
    assert "upgrades it to deterministic" not in low


def test_R_087_tdd_isolation_row_is_instruction_guided():
    tiers = section(doc("how-it-works"), r"Enforcement Tiers")
    head, _, tail = tiers.partition("**Instruction-guided")
    assert tail, "Instruction-guided table not found"
    assert not [r for r in rows_containing(head, "context isolation")]
    assert [r for r in rows_containing(tail, "context isolation")]


def test_R_088_only_implementer_is_a_subagent_at_level_2():
    text = doc("how-it-works")
    assert "test writer and implementer are different agents" not in flat(text)
    sents = sentences(text)
    assert any(
        re.search(r"Level 2(?!\s*[-–]\s*3)", s) and "implementer" in s and "subagent" in s.lower()
        for s in sents
    ), "no sentence says the Level 2 implementer is a subagent"
    assert any(
        re.search(r"Level 3", s) and "test writer" in s and "subagent" in s.lower() for s in sents
    ), "no sentence says the Level 3 test writer is also a subagent"


def test_R_090_shape_up_row_names_the_blocked_skills():
    row = [r for r in rows_containing(doc("how-it-works"), "Shape Up") if "Level" in r][0]
    assert "project-sprints" in row
    assert "project-backlog" in row
    assert "backlog-triage" not in row


def test_R_097_stories_carry_epic_and_theme_fields():
    text = doc("how-it-works")
    para = [p for p in paragraphs(text) if "classification attributes" in p][0]
    assert "epic_id" not in para
    assert "theme_id" not in para
    assert "`epic`" in para
    assert "`theme`" in para


def test_R_102_hard_gate_table_lists_every_prerequisite():
    gates = yaml.safe_load((REPO / "config" / "workflow-templates.yaml").read_text())["hard_gate_policy"]["hard_gate_tasks"]
    sect = section(doc("phases-and-workflows"), r"Soft Gates and Hard Gates")
    for entry in gates:
        rows = norm("\n".join(rows_containing(sect, f"`{entry['task']}`")))
        assert rows, f"no hard-gate rows for {entry['task']}"
        for prereq in entry["prerequisites"]:
            assert norm(prereq) in rows, f"{entry['task']}: prerequisite {prereq} missing from hard-gate table"


def test_R_105_routing_is_category_selection_not_work_type_classification():
    for name in ("how-it-works", "phases-and-workflows"):
        text = flat(doc(name))
        assert "reads the shape from config" not in text
        assert "it classifies the work into one of" not in text
        assert "The work type determines the shape" not in text
        assert re.search(r"/sweetclaude:go[^.]*categor|categor[^.]*/sweetclaude:go", text), f"{name}: routing not described as category selection"


def test_R_107_course_correction_and_security_planning_sequences():
    text = doc("phases-and-workflows")
    for line in text.splitlines():
        if "course-correction" in line:
            assert "full-pipeline" not in line, line
        if "security-planning" in line:
            assert "full-pipeline" not in line, line
    for typ, seq in (("course-correction", "DISCOVER → DEFINE → TRIAGE → SHIP"), ("security-planning", "DISCOVER → DEFINE → SHIP")):
        for line in text.splitlines():
            if f"`{typ}`" in line and "→" in line and line.count("`") <= 4:
                assert seq in line


def test_R_108_tech_debt_sequence_has_scope_in_place_of_design():
    text = doc("phases-and-workflows")
    for line in text.splitlines():
        if "tech-debt" in line and not line.startswith("| **SCOPE**"):
            assert "abbreviated" not in line, line
    for line in text.splitlines():
        if "`tech-debt`" in line and "→" in line and line.count("`") <= 4:
            assert "DEFINE → SCOPE → IMPLEMENT → VERIFY → SHIP" in line


def test_R_109_migration_types_do_not_use_the_migration_shape():
    for name in ("how-it-works", "phases-and-workflows"):
        for line in doc(name).splitlines():
            if not line.startswith("|"):
                continue
            if re.search(r"api-deprecation|data-migration|dependency-upgrade|API deprecation", line):
                cells = [c.strip(" `") for c in line.strip().strip("|").split("|")]
                assert not any(c.startswith("migration") for c in cells), f"{name}: {line}"
    text = doc("phases-and-workflows")
    expected = {
        "api-deprecation": "ASSESS → DEFINE → IMPLEMENT → VERIFY → SHIP → CLEANUP",
        "dependency-upgrade": "ASSESS → IMPLEMENT → VERIFY → SHIP",
        "data-migration": "ASSESS → DESIGN → PLAN → IMPLEMENT → VERIFY → SHIP",
    }
    for typ, seq in expected.items():
        for line in text.splitlines():
            if f"`{typ}`" in line and "→" in line and line.count("`") <= 4:
                assert seq in line


@pytest.mark.parametrize("name", ["how-it-works", "phases-and-workflows"])
def test_R_110_example_state_uses_ids_and_fields_the_code_writes(name):
    block = yaml_block_with(doc(name), "active:")
    assert "WI-" not in block
    assert "ISSUE-" in block
    assert "workflow:" not in block
    assert "mid-project-planned" not in block
    assert re.search(r"entry_category:\s*(small-story|large-story)", block)


def test_R_111_last_item_id_is_the_most_recently_closed_item():
    text = flat(doc("phases-and-workflows"))
    assert "monotonic" not in text
    assert "IDs do not repeat" not in text
    assert re.search(r"last_item_id[^.]*most recently (closed|completed)", text)


def test_R_112_progressive_disclosure_is_retired():
    pages = list(GUIDE.glob("*.md")) + list((REPO / "skills").rglob("*.md"))
    offenders = [str(p.relative_to(REPO)) for p in pages if re.search(r"progressive[ -]disclosure", p.read_text(encoding="utf-8"), re.I)]
    assert not offenders, offenders
    for name in ("how-it-works", "phases-and-workflows", "glossary"):
        text = doc(name)
        assert not re.search(r"visible buckets", text, re.I), name
        assert not re.search(r"(does not|doesn't) see compliance", text, re.I), name
        assert "surfaced automatically" not in text, name
        assert "de-emphasized" not in text, name


def test_R_112_progressive_disclosure_config_block_is_removed():
    templates = yaml.safe_load((REPO / "config" / "workflow-templates.yaml").read_text())
    assert "progressive_disclosure" not in templates


def test_R_113_idea_is_the_onboarding_stage():
    how = [l for l in doc("how-it-works").splitlines() if l.startswith("**`version_stage`**")][0]
    assert "IDEA" in how
    assert "PRE-ALPHA" not in how
    glossary_entry = [p for p in paragraphs(doc("glossary")) if p.startswith("**Version stage**")][0]
    assert "IDEA" in glossary_entry
    assert "PRE-ALPHA" not in glossary_entry
    for stage in ("ALPHA", "BETA", "GA"):
        assert stage in how
        assert stage in glossary_entry


def test_R_114_no_4x_beta_framing_for_current_maintenance():
    text = doc("how-it-works")
    assert not re.search(r"^#+\s.*4\.x", text, re.M)
    assert not re.search(r"^4\.x\b", text, re.M)
    assert "Beta Operating Model" not in text


def test_R_115_doctor_route_table_lists_exactly_the_returnable_statuses():
    doctor_src = (REPO / "scripts" / "doctor.py").read_text(encoding="utf-8")
    for status in DOCTOR_STATUSES:
        assert f'"{status}"' in doctor_src
    assert '"no-migration-recommended"' not in doctor_src
    table_start = doc("how-it-works").index("| Route status |")
    table = doc("how-it-works")[table_start:].split("\n\n")[0]
    listed = {m.group(1) for row in table_rows(table)[1:] for m in [re.match(r"`([^`]+)`", row[0])] if m}
    assert listed == DOCTOR_STATUSES


def test_R_116_migrate_handles_flat_and_typed_legacy_layouts():
    text = doc("how-it-works")
    para = [p for p in paragraphs(text) if "stories/" in p][0]
    flat_para = flat(para)
    assert "route to recovery instead of blind migration" not in flat_para
    assert "until a layout-specific migrator exists" not in flat_para
    assert "/sweetclaude:configure migrate" in flat_para
    assert "BL-NNN" in flat_para
    assert "recovery" in flat_para.lower()


def test_R_119_only_real_subagent_patterns_are_named():
    text = flat(doc("how-it-works"))
    assert "John Wick escalation" not in text
    assert "privileged agent" not in text


def test_R_120_deference_change_is_not_claimed_to_persist():
    para = [p for p in paragraphs(doc("how-it-works")) if "switch to guided" in p][0]
    assert "sweetclaude.yaml" not in para
    assert "updates" not in para.lower()


def test_R_121_what_lives_where_shows_skill_library_and_scripts():
    text = doc("how-it-works")
    tree = re.search(r"```\n(SweetClaude plugin bundle/.*?)```", text, re.S).group(1)
    assert "skill-library/" in tree
    assert "scripts/" in tree
    skills_line = [l for l in tree.splitlines() if "skills/" in l and "skill-library" not in l][0]
    assert "all skills" not in skills_line
    assert "command" in skills_line.lower()
    assert "router" in skills_line.lower()


def test_R_122_project_yaml_describes_what_is_actually_read():
    text = doc("how-it-works")
    lines = [l for l in text.splitlines() if "project.yaml" in l]
    assert lines
    joined = flat(" ".join(lines))
    assert "Language, framework, commands" not in joined
    assert "test_command" in joined
    assert re.search(r"created|written|recorded", joined), "no statement of when project.yaml is created"


def test_R_123_corpus_ordering_is_instruction_guided():
    how = flat(doc("how-it-works"))
    assert "state machine" not in how
    assert "refuses out-of-order" not in how
    para = [p for p in paragraphs(doc("how-it-works")) if "corpus pipeline" in p][0]
    assert "instruction-guided" in para.lower()
    cheat = flat((GUIDE / "cheatsheet-existing-project.md").read_text(encoding="utf-8"))
    assert "The pipeline enforces ordering" not in cheat
    corpus = [p for p in paragraphs((GUIDE / "cheatsheet-existing-project.md").read_text(encoding="utf-8")) if "Select **Status**" in p][0]
    assert "instruction-guided" in corpus.lower()


CANONICAL_STATUSES = ["new", "ready", "active", "in-review", "blocked", "on-hold", "deferred", "done", "declined", "abandoned", "superseded"]
TERMINAL_STATUSES = ["done", "declined", "abandoned", "superseded"]


def test_R_125_all_eleven_statuses_and_four_terminal():
    text = doc("planning-concepts")
    bullet = [l for l in text.splitlines() if l.startswith("- A **status**")][0]
    for s in CANONICAL_STATUSES:
        assert s in bullet, f"status bullet missing {s}"
    ref = section(text, r"Status and Priority Reference")
    first_col = {r[0] for r in table_rows(ref.split("**Priority values**")[0])[1:]}
    assert first_col == set(CANONICAL_STATUSES)
    terminal = [s for s in sentences(ref) if "terminal" in s.lower()]
    assert terminal, "terminal statuses not described"
    assert all(t in " ".join(terminal) for t in TERMINAL_STATUSES)


def test_R_126_priority_values_match_the_cache_sort():
    text = doc("planning-concepts")
    bullet = [l for l in text.splitlines() if l.startswith("- A **priority**")][0]
    assert "next" not in bullet
    assert "now" in bullet
    ref = section(text, r"Status and Priority Reference")
    prio = ref.split("**Priority values**")[1]
    first_col = {r[0] for r in table_rows(prio)[1:]}
    assert "next" not in first_col
    assert "now" in first_col
    assert "P0" in flat(text) and "P3" in flat(text)


def test_R_127_triage_moves_file_and_epic_linking_is_separate():
    pc = doc("planning-concepts")
    gl = doc("glossary")
    assert "assigned to an epic" not in flat(pc)
    assert "moving it to an epic" not in flat(pc)
    for name, text in (("planning-concepts", pc), ("glossary", gl)):
        assert "roadmap/issues" in text, f"{name}: no mention of roadmap/issues"
    backlog_entry = [p for p in paragraphs(gl) if p.startswith("**Backlog**")][0]
    assert "roadmap/issues" in backlog_entry
    assert re.search(r"epic[^.]*milestone[^.]*separate|separate[^.]*epic|epic and milestone linking", flat(backlog_entry + pc), re.I)


def test_R_128_milestone_is_achieved_when_criteria_met_and_user_confirms():
    pc = doc("planning-concepts")
    gl = doc("glossary")
    milestone_pc = section(pc, r"^Milestone$")
    milestone_gl = [p for p in paragraphs(gl) if p.startswith("**Milestone**")][0]
    assert "all its stories" not in flat(milestone_pc)
    assert "all its epics" not in flat(milestone_gl)
    for text in (milestone_pc, milestone_gl):
        low = flat(text).lower()
        assert "achieved" in low
        assert "success criteria" in low
        assert "confirm" in low


def test_R_129_hierarchy_is_milestone_sprint_story():
    text = doc("planning-concepts")
    hierarchy = section(text, r"^The Hierarchy$")
    block = re.search(r"```\n(.*?)```", hierarchy, re.S).group(1)
    assert "Epic" not in block
    assert block.index("Milestone") < block.index("Sprint") < block.index("Story")
    flat_h = flat(hierarchy)
    assert "attached to either a milestone or an epic" not in flat_h
    assert "attribute" in flat_h.lower()
    assert "theme" in flat_h.lower()


@pytest.mark.parametrize("name", ["planning-concepts", "glossary"])
def test_R_130_epics_are_not_mode_dependent(name):
    text = flat(doc(name))
    assert "not surfaced" not in text
    assert "are not surfaced" not in text
    assert "surfaced by default" not in text
    assert "In all other modes, epics" not in text
    assert "do not appear in status views" not in text
    assert "appear in status views, Kanban boards" not in text


def test_R_131_agile_milestones_are_recommended_not_required():
    modes = section(doc("planning-concepts"), r"Choosing a Mode")
    row = [r for r in table_rows(modes) if r[0].replace("*", "") == "Milestones"][0]
    agile = row[-1]
    assert "required" not in agile.lower()
    assert "recommended" in agile.lower()


def test_R_132_no_kanban_board_column_claim():
    text = flat(doc("planning-concepts"))
    assert "statuses as columns" not in text
    assert "map directly to board columns" not in text
    assert "project-issues" in text


def test_R_252_tdd_hook_list_matches_registered_hooks():
    import json
    registered = json.loads((REPO / "hooks" / "hooks.json").read_text())["hooks"]["PreToolUse"]
    commands = " ".join(h["command"] for m in registered for h in m["hooks"])
    assert "tdd-prewrite-guardian.sh" in commands
    sect = section(doc("tdd"), r"Why Hooks")
    start = sect.index("The mechanism is")
    block = sect[start:].split("\n\n", 1)
    names = set(re.findall(r"^- \*\*([\w-]+)\*\*", block[1] if len(block) > 1 else "", re.M))
    assert names == {"test-guardian", "tdd-prewrite-guardian", "auto-test-runner"}
    assert not re.search(r"git-checkpoint[^.\n]*\bhook\b", sect)


def test_R_253_test_guardian_active_only_after_code_tdd_sets_implementing():
    text = doc("tdd")
    assert not re.search(r"OS[ -]level", text, re.I)
    paras = [p for p in paragraphs(text) if "test-guardian" in p]
    assert any("code-tdd" in p and "implementing" in p for p in paras)


def test_R_254_level_0_orders_fix_regression_test_confirm_commit():
    sect = section(doc("tdd"), r"^Level 0")
    flat_s = flat(sect)
    assert "before you fix the bug" not in flat_s
    assert "without the fix" in flat_s


def test_R_255_level_2_writes_tests_in_main_context():
    sect = section(doc("tdd"), r"^Level 2")
    flat_s = flat(sect)
    assert "main context" in flat_s
    assert "Test writer agent writes failing tests in an isolated context" not in flat_s
    assert "watch the test writer commit" not in flat_s
    level3 = flat(section(doc("tdd"), r"^Level 3"))
    assert "Test writer agent" in level3


def test_R_261_wip_limit_conditions_match_the_hook():
    text = flat(doc("hook-development"))
    clause = re.search(r"`wip-limit\.sh`\s*\((.*?)\),? and `preflight-guard", text).group(1)
    assert "recovery" not in clause.lower()
    assert "Kanban" in clause
    assert "limit" in clause.lower()
    assert "activat" in clause.lower()
    assert "IMPLEMENT" not in clause
