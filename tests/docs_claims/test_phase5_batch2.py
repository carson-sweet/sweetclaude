"""Phase 5 docs-claims batch 2: corpus, behavioral contracts, work-item artifacts, platform dependencies, evidence and contracts, large story, skills reference. Each test is named for its remediation-ledger row id."""
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "user-guide"

DOCS = [
    "corpus-system",
    "behavioral-contracts",
    "work-item-artifacts",
    "platform-dependencies",
    "evidence-and-contracts",
    "large-story-workflow",
    "skills-reference",
]

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-⛿✅✨❌❎❓-❕❗➕-➗⭐⭕️]"
)


def doc(name):
    return (GUIDE / f"{name}.md").read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def section(text, heading_pattern, level=None):
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
    found = sorted(set(EMOJI.findall(doc(name))))
    assert not found, f"{name}: emoji characters {[hex(ord(c)) for c in found]}"


def test_R_133_design_section_has_no_accessibility_example():
    design = section(doc("skills-reference"), r"^Design library")
    assert "accessib" not in design.lower()


def test_R_134_configure_section_lists_no_regression_checks():
    configure = section(doc("skills-reference"), r"^Configure library")
    assert "regression" not in configure.lower()


def test_R_217_contract_edits_are_blocked_not_prompted():
    text = flat(doc("large-story-workflow"))
    assert "approval prompt" not in text
    assert "only you can answer" not in text
    define = text[text.index("**DEFINE**"):text.index("**DESIGN**")]
    assert re.search(r"\bblocked\b|\bdenied\b|\bdenies\b", define, re.I)
    assert re.search(r"re-?freez", define, re.I)
    assert re.search(r"\binit\b", define, re.I)


def test_R_219_protected_paths_are_exactly_the_controller_set():
    text = flat(doc("large-story-workflow"))
    assert "`.sweetclaude/state/` and `.sweetclaude/reports/`" not in text
    for token in ("state/workflows/", "state/phase.yaml", "reports/", "contracts/"):
        assert token in text, token


def test_R_220_stop_guard_blocks_once_then_records_pause():
    text = flat(doc("large-story-workflow"))
    assert "blocks the session from ending while the workflow is non-terminal" not in text
    guard = text[text.index("**The stop guard hook**"):]
    guard = guard[:900]
    assert re.search(r"intentional pause", guard, re.I)
    assert re.search(r"second stop", guard, re.I)
    assert re.search(r"re-?arm|reminder", guard, re.I)
    assert re.search(r"progress", guard, re.I)


def test_R_221_workflow_state_path_is_primary_and_pointers_are_legacy():
    text = flat(doc("large-story-workflow"))
    assert ".sweetclaude/state/workflows/{workflow_id}.yaml" in text
    for legacy in ("large-story.yaml", "small-story.yaml"):
        i = text.index(legacy)
        window = text[max(0, i - 300): i + 400]
        assert re.search(r"legacy", window, re.I), legacy
    assert not re.search(r"large-story\.yaml`?\s*\(or", text)


def test_R_222_backfill_script_is_run_from_the_plugin_root():
    text = doc("work-item-artifacts")
    script = "scripts/backfill_work_item_artifacts.py"
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backfill_work_item_artifacts.py" --project-dir .' in text
    for m in re.finditer(re.escape(script), text):
        assert text[: m.start()].endswith("${CLAUDE_PLUGIN_ROOT}/"), f"bare script path at offset {m.start()}"
    for flag in ("--dry-run", "--item", "--json"):
        assert flag in text, flag


def test_R_224_feature_status_includes_not_offered():
    text = doc("work-item-artifacts")
    assert "not_offered" in text
    for status in ("active", "declined"):
        assert status in text


def test_R_225_contracts_subdirectory_holds_success_criteria_contracts():
    text = doc("work-item-artifacts")
    line = next(l for l in text.splitlines() if re.match(r"^[├└]── contracts/", l))
    assert "API" not in line
    assert re.search(r"success[- ]criteria", line, re.I)


def test_R_266_init_contract_lists_three_refusal_conditions():
    text = flat(doc("evidence-and-contracts"))
    assert "refuses to overwrite while an active large-story workflow exists" not in text
    start = text.index("`init-contract` refuses")
    window = text[start: start + 900]
    assert re.search(r"different story|another story|other story", window, re.I)
    assert re.search(r"backlog", window, re.I)
    assert "--force" in window


def test_R_267_verify_blocked_when_no_file_changes_recorded():
    text = flat(doc("evidence-and-contracts"))
    assert not re.search(r"blocked if `evidence\.jsonl` is empty", text)
    i = text.index("--allow-no-file-changes")
    window = text[max(0, i - 600): i]
    assert re.search(r"file change|file-path|file path|file_path", window, re.I)


def test_R_268_model_upgrade_scoring_uses_validated_contracts_and_pass_fail_na():
    text = doc("behavioral-contracts")
    sec = section(text, r"How to Add Results for a New Model Version")
    assert "PARTIAL" not in sec
    assert "n/a" in sec
    assert re.search(r"\bpass\b", sec, re.I) and re.search(r"\bfail\b", sec, re.I)
    flat_sec = flat(sec)
    assert re.search(r"not judgeable", flat_sec, re.I)
    for n in ("06", "07", "08", "15"):
        assert n in flat_sec, n


def test_R_269_needs_no_context_table_matches_rubrics():
    rubrics = yaml.safe_load((REPO / "config" / "behavioral-rubrics.yaml").read_text(encoding="utf-8"))
    contracts = rubrics.get("rubrics", rubrics)
    expected = sorted(
        k.split("-")[1] for k, v in contracts.items()
        if isinstance(v, dict) and k.startswith("CONTRACT-") and v.get("needs_context") == "none"
    )
    assert "16" in expected
    sec = section(doc("behavioral-contracts"), r"What the harness now refuses to judge")
    row = next(l for l in sec.splitlines() if re.match(r"^\|\s*nothing\s*\|", l))
    listed = sorted(re.findall(r"\b(\d{2})\b", row.split("|")[2]))
    assert listed == expected


def test_R_270_three_of_five_improvement_triggers_have_contracts():
    text = flat(doc("behavioral-contracts"))
    assert "Only the first has a contract" not in text
    assert "is not covered by anything" not in text
    m = re.search(r"three of the five", text, re.I)
    assert m, "no statement that three of the five triggers have contracts"
    window = text[m.start(): m.start() + 500]
    for n in ("11", "12", "15"):
        assert n in window, n


def test_R_271_quick_reference_has_a_row_per_contract_heading():
    headings = set(re.findall(
        r"^###\s+(CONTRACT-\d+):", (REPO / "config" / "behavioral-contracts.md").read_text(encoding="utf-8"), re.M))
    sec = section(doc("behavioral-contracts"), r"Contract Descriptions")
    rows = re.findall(r"^\|\s*(CONTRACT-\d+)\s*\|", sec, re.M)
    assert "CONTRACT-16" in headings
    assert sorted(rows) == sorted(headings)


def test_R_280_corpus_steps_are_gated_with_override_phrase_not_unskippable():
    text = flat(doc("corpus-system"))
    assert not re.search(r"cannot skip", text, re.I)
    assert "enforced by a state machine" not in text
    assert "override phrase" in text


def test_R_281_set_up_rag_indexes_all_supported_types_by_default():
    sec = section(doc("corpus-system"), r"^Set Up RAG")
    flat_sec = flat(sec)
    assert "Indexes your canonical documents" not in flat_sec
    assert re.search(r"by default", flat_sec, re.I)
    assert re.search(r"canonical[^.]*\b(only|option|choose|chosen|select)", flat_sec, re.I)


def test_R_282_reindex_scopes_are_canonical_raw_all():
    sec = flat(section(doc("corpus-system"), r"^Reindex"))
    assert "one collection, several, or everything" not in sec
    for scope in ("Canonical", "Raw", "All"):
        assert scope in sec, scope


def test_R_283_menu_routes_one_selection_to_one_sub_skill():
    text = flat(doc("corpus-system"))
    assert not re.search(r"pick one or more", text, re.I)
    assert "sub-skill" in text
    assert "Update RAG" in text


def test_R_284_mcp_local_rag_is_an_npm_mcp_server_run_via_npx():
    text = flat(doc("platform-dependencies"))
    assert "one external plugin" not in text
    assert "npx" in text
    assert re.search(r"MCP server", text)
    dep2 = section(doc("platform-dependencies"), r"Dependency 2")
    assert not re.search(r"mcp-local-rag[^.]*\bplugin\b", dep2, re.I)


def test_R_285_hard_and_optional_dependencies_are_listed():
    text = flat(doc("platform-dependencies"))
    for token in ("python3", "PyYAML", "jq", "git", "codex", "openai"):
        assert token in text, token
    i = text.index("codex")
    assert re.search(r"optional", text[max(0, i - 300): i + 300], re.I)


def test_R_286_document_corpus_arguments_match_the_skill():
    text = doc("platform-dependencies")
    skill = (REPO / "skill-library" / "utils" / "document-corpus" / "SKILL.md").read_text(encoding="utf-8")
    assert "rag-setup" in text and "rag-reindex" in text
    for arg in re.findall(r"document-corpus\s+`?([a-z][a-z-]*)", text):
        assert f"`{arg}`" in skill, arg
