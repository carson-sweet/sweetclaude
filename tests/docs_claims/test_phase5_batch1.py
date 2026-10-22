"""Phase 5 docs-claims batch 1: doctor, migration-and-recovery, v4-migration, install, upgrading-to-5, capability-ledger, capability-ledger-table."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "user-guide"

ROUTE_STATUSES = {
    "recovery-available",
    "supported-migration-available",
    "compatibility-mode",
    "graduation-available",
    "graduation-blocked",
    "migration-blocked",
    "manual-review",
    "no-maintenance-action",
}

STYLE_DOCS = [
    "doctor.md",
    "migration-and-recovery.md",
    "v4-migration.md",
    "install.md",
    "upgrading-to-5.md",
    "capability-ledger.md",
    "capability-ledger-table.md",
]

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⭐⭕⌚⌛⏩-⏺️‍]"
)


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def guide(name):
    return read(f"docs/user-guide/{name}")


def flat(text):
    return re.sub(r"\s+", " ", text)


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", flat(text))


def window(text, anchor, after=800, before=0):
    i = text.find(anchor)
    assert i >= 0, f"anchor not found: {anchor!r}"
    return text[max(0, i - before): i + len(anchor) + after]


def table_row(text, first_cell):
    for line in text.splitlines():
        if line.startswith("|") and line.split("|")[1].strip().strip("`") == first_cell:
            return line
    return None


def route_table_statuses(text):
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("|") and "route" in line.split("|")[1].lower():
            found = set()
            for row in lines[idx + 2:]:
                if not row.startswith("|"):
                    break
                m = re.match(r"\|\s*`([a-z-]+)`", row)
                if m:
                    found.add(m.group(1))
            return found
    return None


def section(text, heading_pattern):
    lines = text.splitlines()
    start = None
    level = 0
    for i, line in enumerate(lines):
        if re.match(r"#{1,6}\s", line) and re.search(heading_pattern, line, re.I):
            start = i
            level = len(line) - len(line.lstrip("#"))
            break
    assert start is not None, f"heading not found: {heading_pattern}"
    out = []
    for line in lines[start + 1:]:
        m = re.match(r"(#{1,6})\s", line)
        if m and len(m.group(1)) <= level:
            break
        out.append(line)
    return "\n".join(out)


def skill_description(rel):
    for line in read(rel).splitlines():
        if line.startswith("description:"):
            return line
    raise AssertionError(f"no description in {rel}")


@pytest.mark.parametrize("name", STYLE_DOCS)
def test_style_no_emoji(name):
    assert EMOJI.search(guide(name)) is None


@pytest.mark.parametrize("name", [n for n in STYLE_DOCS if n != "capability-ledger-table.md"])
def test_style_version_and_date_lines_near_top(name):
    head = "\n".join(guide(name).splitlines()[:12])
    assert re.search(r"^\*\*Version:\*\*\s*\S+", head, re.M)
    assert re.search(r"^\*\*Date:\*\*\s*\d{4}-\d{2}-\d{2}", head, re.M)


def test_R_018_beta_switch_does_not_claim_update_migrates_project_data():
    for rel in ("docs/user-guide/install.md", "skill-library/configure/update/SKILL.md"):
        text = read(rel)
        assert "migrates normally" not in flat(text), rel
        after = window(text, "marketplace remove sweetclaude-beta", after=900)
        assert "/sweetclaude:configure doctor" in after, rel


def test_R_019_firecrawl_names_plan_category_forms():
    text = guide("install.md")
    assert "/sweetclaude:plan product-research" in text
    assert "/sweetclaude:plan product-competition" in text
    stripped = text.replace("/sweetclaude:plan product-research", "").replace(
        "/sweetclaude:plan product-competition", ""
    )
    assert "sweetclaude:product-research" not in stripped
    assert "sweetclaude:product-competition" not in stripped


def test_R_020_local_rag_uses_per_project_config_not_global_binary():
    text = guide("install.md")
    assert '"command": "mcp-local-rag"' not in text
    points_to_setup = "/sweetclaude:utils corpus-rag-setup" in text
    shows_config = all(
        token in text
        for token in ('"command": "npx"', '"-y", "mcp-local-rag"', '"DB_PATH": "./.rag-index/lancedb"')
    )
    assert points_to_setup or shows_config


def test_R_021_reindex_uses_corpus_rag_reindex():
    text = guide("install.md")
    assert "/sweetclaude:utils corpus-rag-reindex" in text
    assert "document-corpus reindex" not in text


INTERNAL_IN_4X = [
    "john-wick-checkin", "large-story", "orchestrator", "small-story", "_features",
    "_health", "_migrate", "claude-config-audit", "setup", "next-steps",
]


@pytest.mark.parametrize("name", INTERNAL_IN_4X)
def test_R_024_internal_4x_names_omitted_or_marked(name):
    row = table_row(guide("upgrading-to-5.md"), name)
    assert row is None or "(internal in 4.x)" in row


def test_R_025_retired_in_5_0_note_names_behavioral_regression_commands():
    text = guide("upgrading-to-5.md")
    assert "Retired in 5.0" in text
    after = window(text, "Retired in 5.0", after=700)
    assert "sweetclaude-behavioral-regression" in after
    assert re.search(r"(?<!sweetclaude-)behavioral-regression", after)


REDIRECT_SKILLS = ["claude-config-audit", "fix-sweetclaude", "hook-repair", "migrate-diagnose"]


def test_R_026_redirects_name_configure_doctor_not_library_load():
    upgrading = guide("upgrading-to-5.md")
    index = read("skill-library/configure/INDEX.md")
    assert "library-load" not in upgrading
    for name in REDIRECT_SKILLS:
        desc = skill_description(f"skill-library/configure/{name}/SKILL.md")
        assert "library-load" not in desc, name
        assert "/sweetclaude:configure doctor" in desc, name
        irow = table_row(index, name)
        assert irow is not None
        assert "library-load" not in irow, name
        assert "/sweetclaude:configure doctor" in irow, name
        urow = table_row(upgrading, name)
        if urow is not None:
            assert "/sweetclaude:configure doctor" in urow, name


def test_R_027_project_epics_rows_point_to_plan_epics():
    for rel in ("docs/user-guide/upgrading-to-5.md", "skill-library/build/INDEX.md"):
        row = table_row(read(rel), "project-epics")
        assert row is not None, rel
        assert "use /sweetclaude:plan epics instead" in row, rel
        assert "use /sweetclaude:plan instead" not in row, rel


def test_R_198_rollback_states_reversible_skipped_and_safety_branch_fallback():
    text = flat(guide("doctor.md"))
    assert "fully reversed" not in text
    assert "skipped" in text
    assert "reversible" in text
    near_skipped = window(text, "skipped", after=500, before=500)
    assert "safety branch" in near_skipped.lower()


def test_R_199_doctor_route_table_lists_exactly_emitted_statuses():
    text = guide("doctor.md")
    assert "no-migration-recommended" not in text
    assert route_table_statuses(text) == ROUTE_STATUSES


def test_R_200_doctor_offers_to_run_recovery_or_migration_itself():
    text = guide("doctor.md")
    assert "handed off to `/sweetclaude:configure migrate`" not in flat(text)
    routes = section(text, r"routes")
    for line in routes.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            assert not re.fullmatch(r"`/sweetclaude:configure (recover|migrate)`", cells[-1]), line
    assert re.search(r"\boffers?\b[^.]{0,80}\b(run|start)\b", flat(text), re.I)


def test_R_201_doctor_lists_accepted_report_only_resolution_kind():
    resolved = section(guide("doctor.md"), r"how findings get resolved")
    assert re.search(r"accepted|report-only", resolved, re.I)


def test_R_202_doctor_remembered_proceed_skips_menu_and_interactive_restores():
    text = flat(guide("doctor.md"))
    assert "--interactive" in text
    assert "after you approve the batch" not in text
    near = window(text, "--interactive", after=300, before=300)
    assert "proceed" in near


def test_R_203_migration_doc_uses_plugin_root_paths():
    text = guide("migration-and-recovery.md")
    assert "~/.claude/scripts/sweetclaude" not in text
    assert re.search(
        r'python3 "?\$\{CLAUDE_PLUGIN_ROOT\}/scripts/doctor\.py"? maintenance-route --project-dir \.', text
    )
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/migrate/migrate-v3-to-v4.py" in text


def test_R_204_safe_order_switches_to_5x_before_configure_update():
    text = guide("migration-and-recovery.md")
    order = section(text, r"safe order")
    assert "upgrading-to-5.md" in order
    for cmd in (
        "/plugin marketplace update sweetclaude-stable",
        "/plugin update sweetclaude@sweetclaude-stable",
        "/plugin marketplace add carson-sweet/sweetclaude@main",
        "/plugin install sweetclaude@sweetclaude-stable",
        "/plugin marketplace remove sweetclaude-beta",
    ):
        assert cmd in order, cmd
    assert "/sweetclaude:configure update" in order
    assert order.lower().index("restart") < order.index("/sweetclaude:configure update")


def test_R_205_migration_route_table_lists_exactly_emitted_statuses():
    text = guide("migration-and-recovery.md")
    assert "no-migration-recommended" not in text
    assert route_table_statuses(text) == ROUTE_STATUSES


def test_R_206_supported_migration_covers_typed_legacy_layout():
    text = guide("migration-and-recovery.md")
    row = table_row(text, "supported-migration-available")
    assert row is not None
    assert re.search(r"typed", row, re.I)
    assert "BL-" in row
    assert "migrate_taxonomy" in text


def test_R_208_typed_layouts_route_to_taxonomy_migrator_and_duplicates_to_doctor():
    text = flat(guide("migration-and-recovery.md"))
    assert "Blocked projects route to recovery" not in text
    assert "migrate_taxonomy" in text
    m = re.search(r"duplicate[- ]ids", text, re.I)
    assert m, "duplicate IDs blocker not described"
    assert "doctor" in text[max(0, m.start() - 300): m.end() + 300].lower()


def test_R_209_typed_layout_migrator_exists_and_is_named():
    text = flat(guide("migration-and-recovery.md"))
    assert "Until a layout-specific migrator exists" not in text
    assert "migrate_taxonomy.py" in text


def test_R_210_accepted_legacy_state_has_three_outcomes():
    body = flat(section(guide("migration-and-recovery.md"), r"legacy"))
    assert "does not show a migration prompt" not in body
    assert "graduat" in body.lower()
    assert "compatibility" in body.lower()
    assert "migration prompt" in body.lower()


def test_R_211_v4_guide_is_framed_for_moving_to_5x():
    text = flat(guide("v4-migration.md"))
    assert "stable 3.x" not in text
    assert "5.x" in text
    assert re.search(r"retired", text, re.I)
    assert "sweetclaude-legacy" in text


def test_R_212_v4_guide_gives_switch_commands_and_no_bare_plugin_update():
    text = guide("v4-migration.md")
    assert re.search(r"/plugin update(?!\s+sweetclaude@)", text) is None
    for cmd in (
        "/plugin marketplace add carson-sweet/sweetclaude@main",
        "/plugin install sweetclaude@sweetclaude-stable",
        "/plugin marketplace remove sweetclaude-beta",
    ):
        assert cmd in text, cmd
    assert "upgrading-to-5.md" in text


def test_R_213_v4_guide_gates_configure_commands_on_5x_install_and_restart():
    text = guide("v4-migration.md")
    gating = [
        s for s in sentences(text)
        if "configure" in s.lower()
        and re.search(r"\b(only|until|unknown|not exist|do not exist)\b", s, re.I)
        and re.search(r"5\.(x|0)", s)
        and "restart" in s.lower()
    ]
    assert gating, "no sentence says configure commands need 5.x installed and a restart"


def test_R_214_v4_route_table_lists_exactly_emitted_statuses():
    text = guide("v4-migration.md")
    assert "no-migration-recommended" not in text
    assert route_table_statuses(text) == ROUTE_STATUSES


def test_R_215_v4_typed_layouts_route_to_taxonomy_migrator_and_duplicates_to_doctor():
    text = flat(guide("v4-migration.md"))
    assert "route to recovery instead" not in text
    assert re.search(r"taxonomy", text, re.I)
    m = re.search(r"duplicate[- ](work-item )?ids", text, re.I)
    assert m, "duplicate IDs not described"
    assert "doctor" in text[max(0, m.start() - 300): m.end() + 300].lower()


def test_R_272_ledger_ci_runs_on_prs_to_main_without_behavioral_rows():
    text = guide("capability-ledger.md")
    assert "on every pull request" not in flat(text)
    assert re.search(r"pull requests?[^.]{0,40}\bmain\b", flat(text))
    assert any(
        "CI" in s and re.search(r"--no-behavioral|without behavioral|no behavioral", s)
        for s in sentences(text)
    )


def test_R_273_broken_causes_match_classifier():
    text = guide("capability-ledger.md")
    assert not re.search(r"no entrypoint", text)
    near = window(text, "delegate_skill", after=700, before=700)
    assert "verification_commands" in near
    assert "rollback" in near.lower()


def test_R_274_compromised_means_unhandled_unsupported_states_not_any():
    row = table_row(guide("capability-ledger.md"), "compromised")
    assert row is not None
    assert "unsupported" in row
    assert "handling" in row.lower()


def test_R_275_broken_is_defined_by_declaration_checks_not_failed_verification():
    text = guide("capability-ledger.md")
    assert "verification fails" not in flat(text)
    row = table_row(text, "broken")
    assert row is not None
    assert "declar" in row.lower()


def test_R_276_unverifiable_rows_scored_only_when_a_rubric_covers_them():
    row = table_row(guide("capability-ledger.md"), "not-mechanically-verifiable")
    assert row is not None
    assert "behavioral_judge.py" in row
    assert "rubric" in row.lower()


def test_R_277_tier3_rows_keep_broken_or_compromised_and_contracts_only_on_interaction_rows():
    text = guide("capability-ledger.md")
    assert "always reported" not in flat(text)
    assert "interaction-model" in text
    keeps = [
        s for s in sentences(text)
        if re.search(r"tier[- ]3", s, re.I) and re.search(r"broken|compromised", s)
    ]
    assert keeps, "no sentence says Tier 3 rows keep a broken or compromised status"


def test_R_278_adding_capability_lists_validator_required_fields():
    body = section(guide("capability-ledger.md"), r"adding a capability")
    for field in ("title", "supports_project_shapes", "mutates_project", "requires_approval", "mutation_class"):
        assert field in body, field
    assert "broken" in body
    assert "At minimum it needs `title`, `verification_commands`" not in flat(body)


def test_R_279_capability_ledger_table_is_generated_output():
    res = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "capability_ledger.py"), "--no-behavioral", "--format", "markdown"],
        capture_output=True, cwd=REPO,
    )
    assert res.returncode == 0, res.stderr.decode()
    committed = (GUIDE / "capability-ledger-table.md").read_bytes()
    assert committed == res.stdout
