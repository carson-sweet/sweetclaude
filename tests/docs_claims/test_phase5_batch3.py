"""Phase 5 docs-claims batch 3: hook development, README, getting started, faq, glossary, index, quickstart. Each test is named for its remediation-ledger row id."""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "user-guide"

STYLED = ["hook-development", "getting-started", "faq", "glossary", "index", "quickstart"]

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-⛿✅✨❌❎❓-❕❗➕-➗⭐⭕️]"
)

NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}


def doc(name):
    return (GUIDE / f"{name}.md").read_text(encoding="utf-8")


def readme():
    return (REPO / "README.md").read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


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


def first_code_block(text):
    m = re.search(r"```[^\n]*\n(.*?)```", text, re.S)
    assert m, "no fenced code block"
    return m.group(1)


def links(text):
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)


def pre_tool_use_hooks_matching(tool):
    data = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    names = []
    for group in data["hooks"]["PreToolUse"]:
        matcher = group.get("matcher", "")
        if re.fullmatch(matcher or ".*", tool):
            for h in group["hooks"]:
                names.append(Path(h["command"]).stem)
    return names


@pytest.mark.parametrize("name", STYLED)
def test_style_version_and_date_near_top(name):
    head = "\n".join(doc(name).splitlines()[:15])
    assert re.search(r"\*\*Version:\*\*\s+\S+", head), f"{name}: no **Version:** line near top"
    assert re.search(r"\*\*Date:\*\*\s+\d{4}-\d{2}-\d{2}", head), f"{name}: no **Date:** line near top"


@pytest.mark.parametrize("name", STYLED)
def test_style_no_emoji(name):
    found = sorted(set(EMOJI.findall(doc(name))))
    assert not found, f"{name}: emoji characters {[hex(ord(c)) for c in found]}"


def test_style_readme_no_emoji():
    found = sorted(set(EMOJI.findall(readme())))
    assert not found, f"README.md: emoji characters {[hex(ord(c)) for c in found]}"


def test_R_010_readme_install_blocks_restart_before_help():
    text = readme()
    for heading in (r"^TL;DR", r"^Quick Start"):
        block = first_code_block(section(text, heading))
        install = block.index("/plugin install sweetclaude@sweetclaude-stable")
        help_at = block.index("/sweetclaude:help")
        between = block[install:help_at]
        assert re.search(r"restart", between, re.I), f"{heading}: no restart step between install and help"


def test_R_011_readme_skills_reference_links_target_skills_reference():
    found = [
        (label, url)
        for label, url in links(readme())
        if re.search(r"skills reference|all skills by category", label, re.I)
    ]
    assert len(found) >= 3, found
    for label, url in found:
        assert url.endswith("skills-reference.md"), (label, url)


def test_R_012_readme_architecture_link_targets_how_it_works():
    found = [url for label, url in links(readme()) if re.search(r"architecture and design decisions", label, re.I)]
    assert found, "architecture link missing"
    assert all(u.endswith("how-it-works.md") for u in found), found


def test_R_014_readme_behavioral_contracts_counts():
    text = readme()
    bullet = next(l for l in text.splitlines() if l.lstrip("- ").startswith("**Behavioral contracts**"))
    low = bullet.lower()
    assert "scored against each claude model version" not in low
    assert "instruction-guided" in low
    assert re.search(r"\b16\b", bullet)
    assert re.search(r"\b6\b", bullet)
    assert re.search(r"\b4\b", bullet)
    assert "hook-enforced" in low
    assert "separate" in low


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "docs/README.md",
        "docs/user-guide/install.md",
        "skill-library/configure/update/SKILL.md",
    ],
)
def test_R_016_no_never_double_installed(path):
    text = flat((REPO / path).read_text(encoding="utf-8"))
    assert not re.search(r"never\s+double[- ]installed", text, re.I)


def test_R_017_readme_beta_switch_restarts_before_update():
    text = readme()
    start = text.index("**From the 4.x beta channel:**")
    end = text.index("**From 3.x:**")
    para = text[start:end]
    update_at = para.rindex("/sweetclaude:configure update")
    restart = re.search(r"restart", para[:update_at], re.I)
    assert restart, "beta switch paragraph has no restart before configure update"


def test_R_023_index_install_row_is_stable():
    row = next(l for l in doc("index").splitlines() if l.startswith("| [Install](install.md)"))
    assert "beta install" not in row.lower()
    assert "stable install" in row.lower()


def test_R_028_quickstart_says_5x():
    opening = "\n".join(doc("quickstart").splitlines()[:6])
    assert "SweetClaude 5.x" in opening
    assert "4.x" not in opening


def test_R_031_no_git_init_offer():
    gs = flat(doc("getting-started"))
    qs = flat(doc("quickstart"))
    for text in (gs, qs):
        assert not re.search(r"git init", text, re.I)
        assert not re.search(r"asks if you want a git repo", text, re.I)
        assert not re.search(r"\(git,", text)


def test_R_032_getting_started_has_no_strategy_folder():
    text = doc("getting-started")
    assert "strategy/" not in text
    assert "concept.md" not in text
    assert "personas/" not in text


def test_R_033_getting_started_has_no_deference_question():
    text = flat(doc("getting-started"))
    assert not re.search(r"asks (you )?how collaborative", text, re.I)
    assert not re.search(r"every session,? sweetclaude asks", text, re.I)
    assert re.search(r"default", section(doc("getting-started"), r"Deference"), re.I)
    assert "Collaborative" in section(doc("getting-started"), r"Deference")


def test_R_035_existing_codebase_questions_match_setup():
    gs_b = section(doc("getting-started"), r"Pattern B")
    for token in ("frustration", "messy", "What are you working on right now"):
        assert token not in gs_b, token
    low = gs_b.lower()
    assert "stage" in low
    assert "tracker" in low
    qs = flat(doc("quickstart")).lower()
    assert "biggest concerns" not in qs
    assert "frustration" not in qs


def test_R_036_getting_started_install_states_nine_commands():
    install = flat(section(doc("getting-started"), r"^Install$"))
    assert "/sweetclaude:<skill-name>" not in install
    assert re.search(r"\bnine\b", install, re.I)
    assert "/sweetclaude:<category> <workflow>" in install


def test_R_037_resume_proposes_and_waits():
    pc = flat(section(doc("getting-started"), r"Pattern C"))
    assert "It does not show a menu" not in pc
    assert "It just goes" not in pc
    assert re.search(r"propos", pc, re.I)
    assert re.search(r"wait|go-ahead", pc, re.I)


def test_R_038_project_yaml_not_claimed_as_setup_output():
    for name in ("getting-started", "faq"):
        for line in doc(name).splitlines():
            if "project.yaml" in line:
                assert re.search(r"optional", line, re.I), f"{name}: {line.strip()}"


def test_R_039_first_session_tree_lists_real_outputs():
    text = doc("getting-started")
    tree = section(text, r"What You Will Have After Your First Session")
    new_tree = tree.split("If you adopted an existing codebase")[0]
    assert "product/" in new_tree
    assert "plans" in new_tree
    assert "discovery.yaml" in new_tree
    assert "discovery.md" not in new_tree
    assert "concept.md" not in new_tree
    assert "project.yaml" not in new_tree


def test_R_040_faq_milestones_have_no_target_dates():
    text = flat(doc("faq"))
    assert not re.search(r"milestones have target dates", text, re.I)
    assert not re.search(r"target date", text, re.I)
    assert "Now/Next/Later" in text
    assert re.search(r"notes", text, re.I)


def test_R_041_faq_tdd_hooks_not_in_global_settings():
    row = next(l for l in doc("faq").splitlines() if l.startswith("| TDD hooks"))
    assert "settings.json" not in row
    assert "installer wires" not in row
    assert "hooks.json" in row


def test_R_042_faq_has_no_legacy_skills_path():
    text = doc("faq")
    assert "~/.claude/skills/sweetclaude" not in text
    row = next(l for l in text.splitlines() if l.startswith("| Specific skills"))
    assert "_features" in row


def test_R_043_faq_contribute_points_to_repo_skills():
    contribute = section(doc("faq"), r"want to contribute")
    assert "~/.claude/skills" not in contribute
    assert "skills/" in contribute
    assert "skill-library/" in contribute
    for key in ("spdx-license", "user-invocable", "description"):
        assert key in contribute, key
    assert "`name` and `description`" not in contribute


def test_R_044_faq_planned_matches_roadmap():
    planned = flat(section(doc("faq"), r"What's planned")).lower()
    assert "focus-group" not in planned
    assert "skill generator" not in planned
    assert "allowed-tools" not in planned
    assert "regression" in planned


def test_R_117_glossary_compatibility_mode_is_current():
    entry = section(doc("glossary"), r"^Compatibility Mode")
    assert "4.x beta" not in entry


def test_R_118_glossary_stable_channel_is_5x_main():
    text = doc("glossary")
    assert "Stable 3.x Channel" not in text
    assert "carson-sweet/sweetclaude@main" in text
    assert "5.x" in section(text, r"^Stable")
    for line in text.splitlines():
        if "stable-3.x" in line:
            assert "legacy" in line.lower(), line


def test_R_136_glossary_commit_excludes_derived_state():
    text = doc("glossary")
    m = re.search(r"\.sweetclaude/` directory\*\*\n(.*?)(?:\n\n|\Z)", text, re.S)
    assert m, "directory entry missing"
    entry = m.group(1)
    assert re.search(r"except", entry)
    assert "guardian" in entry.lower()
    assert re.search(r"snapshot|recovery", entry, re.I)


def test_R_136_cheatsheet_commit_excludes_derived_state():
    lines = [
        l for l in doc("cheatsheet-existing-project").splitlines()
        if re.search(r"ommit", l) and ".sweetclaude" in l
    ]
    assert lines
    for line in lines:
        assert "except" in line, line
        assert "guardian" in line.lower(), line
        assert re.search(r"snapshot|recovery", line, re.I), line


def test_R_256_hook_dev_symptom_is_hook_error():
    text = doc("hook-development")
    assert '{"ok": false}' not in text
    sym = flat(section(text, r"^Recovery"))
    assert re.search(r"exit(?:s|ing)? (?:with )?(?:status |code )?2", sym, re.I)
    assert "stderr" in sym


def test_R_257_hook_dev_repair_goes_through_doctor():
    text = doc("hook-development")
    assert "/sweetclaude:configure hook-repair" not in text
    assert "/sweetclaude:configure doctor" in text
    assert "hook_health" in text
    auto = flat(section(text, r"Automated repair"))
    assert "hooks.bak" not in auto
    assert re.search(r"plugin(?:'s)? hooks", auto, re.I)


def test_R_258_hook_dev_names_every_bash_pretooluse_hook():
    text = doc("hook-development")
    assert not re.search(r"never gated", text, re.I)
    names = pre_tool_use_hooks_matching("Bash")
    assert len(names) >= 5
    for name in names:
        assert name in text, name


def test_R_259_hook_dev_only_pretooluse_hooks_block_writes():
    text = doc("hook-development")
    for name in pre_tool_use_hooks_matching("Write"):
        assert name in text, name
    for para in re.split(r"\n\s*\n", text):
        if "auto-test-runner" in para:
            assert "PostToolUse" in para, para


def test_R_260_hook_dev_bash_hook_count_matches_hooks_json():
    text = flat(doc("hook-development"))
    count = len(pre_tool_use_hooks_matching("Bash"))
    word = NUMBER_WORDS[count]
    assert not re.search(r"\bThree other hooks\b", text)
    assert re.search(rf"\b(?:{word}|{count})\b(?: [\w-]+){{0,3}} hooks", text, re.I)


def test_R_262_hook_dev_preflight_flag_and_clear_conditions():
    text = doc("hook-development")
    assert "needs-preflight" in text
    for token in ("sweetclaude.yaml", "phase.yaml", ".sweetclaude-skip"):
        assert token in text, token


def test_R_263_hook_dev_uses_stable_cache_path_and_scopes_backup():
    text = doc("hook-development")
    assert "cache/sweetclaude/sweetclaude" not in text
    assert "cache/sweetclaude-stable/sweetclaude/<ver>/" in text
    assert "sync-to-installed.sh" in text


def test_R_264_hook_dev_emergency_command_resolves_outside_repo():
    sec = section(doc("hook-development"), r"From inside a deadlocked")
    cmds = [l for l in sec.splitlines() if "emergency-hook-restore.sh" in l and "bash" in l]
    assert cmds
    for cmd in cmds:
        assert not re.search(r"bash\s+scripts/", cmd), cmd
        assert re.search(r"bash\s+\S*/scripts/emergency-hook-restore\.sh", cmd), cmd


def test_R_265_hook_dev_plugin_id_is_stable_marketplace():
    text = doc("hook-development")
    assert "sweetclaude@sweetclaude-stable" in text
    assert not re.search(r"sweetclaude@sweetclaude(?![-\w])", text)
