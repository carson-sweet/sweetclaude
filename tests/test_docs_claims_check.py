"""Interface: scripts/docs_claims_check.py [--root DIR] [--json] [paths...]
Exit 0 when all claims resolve, 1 when any fail. --json prints a list of
{path, line, kind, claim, reason} with kind in slash, script, flag, path, link."""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CHECKER = REPO / "scripts" / "docs_claims_check.py"

TOY_SCRIPT = textwrap.dedent('''
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--known", help="a known flag")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("run", help="run it")
    p.parse_args()
''')


@pytest.fixture
def root(tmp_path):
    (tmp_path / "skills" / "status").mkdir(parents=True)
    (tmp_path / "skills" / "status" / "SKILL.md").write_text("# status\n")
    (tmp_path / "skill-library" / "build" / "ship").mkdir(parents=True)
    (tmp_path / "skill-library" / "build" / "ship" / "SKILL.md").write_text("# ship\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "toy.py").write_text(TOY_SCRIPT)
    (tmp_path / "docs" / "user-guide").mkdir(parents=True)
    (tmp_path / "docs" / "user-guide" / "other.md").write_text("# other\n")
    (tmp_path / "README.md").write_text("# readme\n")
    return tmp_path


def run(root, *extra, as_json=True):
    cmd = [sys.executable, str(CHECKER), "--root", str(root)]
    if as_json:
        cmd.append("--json")
    cmd += list(extra)
    return subprocess.run(cmd, capture_output=True, text=True)


def check(root, text, name="README.md"):
    (root / name).write_text(text)
    res = run(root, name)
    assert res.returncode in (0, 1), res.stderr
    return res, json.loads(res.stdout)


def kinds(findings):
    return [f["kind"] for f in findings]


class TestSlashReferences:
    def test_tier1_command_resolves(self, root):
        res, f = check(root, "Run /sweetclaude:status now.\n")
        assert res.returncode == 0 and f == []

    def test_tier1_command_missing(self, root):
        res, f = check(root, "Run /sweetclaude:nonesuch now.\n")
        assert res.returncode == 1
        assert len(f) == 1 and f[0]["kind"] == "slash"
        assert "/sweetclaude:nonesuch" in f[0]["claim"]
        assert f[0]["reason"]

    def test_category_workflow_resolves(self, root):
        res, f = check(root, "Use `/sweetclaude:build ship` to release.\n")
        assert res.returncode == 0 and f == []

    def test_category_workflow_missing(self, root):
        res, f = check(root, "Use `/sweetclaude:build vanish` to release.\n")
        assert res.returncode == 1
        assert kinds(f) == ["slash"]

    def test_unknown_category_workflow_missing(self, root):
        res, f = check(root, "Use /sweetclaude:nocat ship here.\n")
        assert res.returncode == 1
        assert kinds(f) == ["slash"]

    def test_builtin_commands_ignored(self, root):
        res, f = check(root, "Try /plugin, /hooks, /help and /config.\n")
        assert res.returncode == 0 and f == []

    def test_slash_in_fenced_block_checked(self, root):
        res, f = check(root, "```\n/sweetclaude:ghost\n```\n")
        assert res.returncode == 1
        assert kinds(f) == ["slash"] and f[0]["line"] == 2


class TestScriptCommands:
    def test_existing_script_passes(self, root):
        res, f = check(root, "```\npython3 scripts/toy.py\n```\n")
        assert res.returncode == 0 and f == []

    def test_missing_script_fails(self, root):
        res, f = check(root, "Run `python3 scripts/gone.py`.\n")
        assert res.returncode == 1
        assert kinds(f) == ["script"]
        assert "scripts/gone.py" in f[0]["claim"]

    def test_plugin_root_prefix_resolves_against_repo_root(self, root):
        res, f = check(root, "`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/toy.py`\n")
        assert res.returncode == 0 and f == []

    def test_plugin_root_prefix_missing_script(self, root):
        res, f = check(root, "`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gone.py`\n")
        assert res.returncode == 1
        assert kinds(f) == ["script"]

    def test_known_flag_passes(self, root):
        res, f = check(root, "`python3 scripts/toy.py --known x`\n")
        assert res.returncode == 0 and f == []

    def test_unknown_flag_fails(self, root):
        res, f = check(root, "`python3 scripts/toy.py --bogus`\n")
        assert res.returncode == 1
        assert kinds(f) == ["flag"]
        assert "--bogus" in f[0]["claim"]

    def test_known_subcommand_passes(self, root):
        res, f = check(root, "`python3 scripts/toy.py run`\n")
        assert res.returncode == 0 and f == []

    def test_unknown_subcommand_fails(self, root):
        res, f = check(root, "`python3 scripts/toy.py explode`\n")
        assert res.returncode == 1
        assert kinds(f) == ["flag"]
        assert "explode" in f[0]["claim"]

    def test_missing_script_does_not_also_report_flags(self, root):
        res, f = check(root, "`python3 scripts/gone.py --known`\n")
        assert kinds(f) == ["script"]

    def test_flag_in_fenced_block_checked(self, root):
        res, f = check(root, "text\n```bash\npython3 scripts/toy.py --bogus\n```\n")
        assert kinds(f) == ["flag"] and f[0]["line"] == 3


class TestRepoPaths:
    def test_existing_path_passes(self, root):
        res, f = check(root, "See `docs/user-guide/other.md` and `skills/status/SKILL.md`.\n")
        assert res.returncode == 0 and f == []

    def test_missing_path_fails(self, root):
        res, f = check(root, "See `docs/user-guide/missing.md`.\n")
        assert res.returncode == 1
        assert kinds(f) == ["path"]
        assert f[0]["claim"] == "docs/user-guide/missing.md"

    def test_missing_skill_path_fails(self, root):
        res, f = check(root, "Defined in `skills/ghost/SKILL.md`.\n")
        assert kinds(f) == ["path"]

    def test_runtime_sweetclaude_paths_ignored(self, root):
        res, f = check(root, "State lives in `.sweetclaude/state/sweetclaude.yaml` and `.sweetclaude/plans/x.md`.\n")
        assert res.returncode == 0 and f == []


class TestRelativeLinks:
    def test_existing_link_passes(self, root):
        res, f = check(root, "[other](docs/user-guide/other.md)\n")
        assert res.returncode == 0 and f == []

    def test_link_with_anchor_resolves_file(self, root):
        res, f = check(root, "[other](docs/user-guide/other.md#section)\n")
        assert res.returncode == 0 and f == []

    def test_missing_link_fails(self, root):
        res, f = check(root, "[nope](docs/user-guide/nope.md)\n")
        assert res.returncode == 1
        assert kinds(f) == ["link"]
        assert "docs/user-guide/nope.md" in f[0]["claim"]

    def test_link_resolves_relative_to_containing_file(self, root):
        res, f = check(root, "[o](other.md) [r](../../README.md)\n", name="docs/user-guide/guide.md")
        assert res.returncode == 0 and f == []

    def test_relative_link_wrong_base_fails(self, root):
        res, f = check(root, "[o](docs/user-guide/other.md)\n", name="docs/user-guide/guide.md")
        assert kinds(f) == ["link"]

    def test_external_and_anchor_links_ignored(self, root):
        res, f = check(root, "[a](https://example.com/x) [b](#top) [c](mailto:a@b.co)\n")
        assert res.returncode == 0 and f == []


class TestReporting:
    def test_line_numbers_one_based(self, root):
        text = "ok\n\nfine\nRun /sweetclaude:ghost\n\n[x](nope.md)\n"
        res, f = check(root, text)
        by_kind = {x["kind"]: x["line"] for x in f}
        assert by_kind == {"slash": 4, "link": 6}

    def test_json_shape(self, root):
        res, f = check(root, "/sweetclaude:ghost\n")
        assert isinstance(f, list) and len(f) == 1
        assert set(f[0]) == {"path", "line", "kind", "claim", "reason"}
        assert f[0]["path"] == "README.md"
        assert f[0]["line"] == 1
        assert f[0]["kind"] in {"slash", "script", "flag", "path", "link"}

    def test_json_empty_list_when_clean(self, root):
        res = run(root, "README.md")
        assert res.returncode == 0
        assert json.loads(res.stdout) == []

    def test_multiple_findings_all_reported(self, root):
        res, f = check(root, "/sweetclaude:a1\n/sweetclaude:a2\n`python3 scripts/gone.py`\n")
        assert sorted(kinds(f)) == ["script", "slash", "slash"]

    def test_human_output_without_json_mentions_failure(self, root):
        (root / "README.md").write_text("/sweetclaude:ghost\n")
        res = run(root, "README.md", as_json=False)
        assert res.returncode == 1
        assert "README.md:1" in res.stdout + res.stderr

    def test_human_output_clean_exit_zero(self, root):
        res = run(root, "README.md", as_json=False)
        assert res.returncode == 0


class TestDefaultScope:
    def test_default_scans_readme_and_user_guide_recursively(self, root):
        (root / "README.md").write_text("/sweetclaude:bad1\n")
        (root / "docs" / "user-guide" / "sub").mkdir()
        (root / "docs" / "user-guide" / "sub" / "deep.md").write_text("ok\n/sweetclaude:bad2\n")
        res = run(root)
        f = json.loads(res.stdout)
        assert res.returncode == 1
        assert {(x["path"], x["line"]) for x in f} == {
            ("README.md", 1),
            ("docs/user-guide/sub/deep.md", 2),
        }

    def test_default_scope_excludes_other_docs(self, root):
        (root / "docs" / "design").mkdir()
        (root / "docs" / "design" / "x.md").write_text("/sweetclaude:bad\n")
        res = run(root)
        assert res.returncode == 0 and json.loads(res.stdout) == []

    def test_explicit_paths_limit_scan(self, root):
        (root / "README.md").write_text("/sweetclaude:bad\n")
        (root / "docs" / "user-guide" / "ok.md").write_text("fine\n")
        res = run(root, "docs/user-guide/ok.md")
        assert res.returncode == 0 and json.loads(res.stdout) == []


class TestIgnoreMarker:
    def test_same_line_marker_suppresses_slash(self, root):
        res, f = check(root, "Formerly /sweetclaude:doctor. <!-- docs-claims: ignore slash:/sweetclaude:doctor -->\n")
        assert res.returncode == 0 and f == []

    def test_previous_line_marker_suppresses_slash(self, root):
        res, f = check(root, "<!-- docs-claims: ignore slash:/sweetclaude:doctor -->\nFormerly /sweetclaude:doctor.\n")
        assert res.returncode == 0 and f == []

    def test_marker_two_lines_above_does_not_suppress(self, root):
        res, f = check(root, "<!-- docs-claims: ignore slash:/sweetclaude:doctor -->\n\nFormerly /sweetclaude:doctor.\n")
        assert res.returncode == 1
        assert sorted(kinds(f)) == ["marker", "slash"]

    def test_marker_suppresses_path(self, root):
        res, f = check(root, "Your project has `docs/internal/` here. <!-- docs-claims: ignore path:docs/internal/ -->\n")
        assert res.returncode == 0 and f == []

    def test_marker_suppresses_only_named_claim(self, root):
        res, f = check(
            root,
            "Use /sweetclaude:doctor and /sweetclaude:nonesuch. <!-- docs-claims: ignore slash:/sweetclaude:doctor -->\n",
        )
        assert res.returncode == 1
        assert kinds(f) == ["slash"]
        assert "/sweetclaude:nonesuch" in f[0]["claim"]

    def test_marker_for_other_kind_does_not_suppress(self, root):
        res, f = check(root, "Formerly /sweetclaude:doctor. <!-- docs-claims: ignore path:/sweetclaude:doctor -->\n")
        assert res.returncode == 1
        assert sorted(kinds(f)) == ["marker", "slash"]

    def test_stale_marker_reported(self, root):
        res, f = check(root, "Nothing wrong here. <!-- docs-claims: ignore slash:/sweetclaude:doctor -->\n")
        assert res.returncode == 1
        assert kinds(f) == ["marker"]
        assert f[0]["line"] == 1
        assert "/sweetclaude:doctor" in f[0]["claim"]
        assert f[0]["reason"]

    def test_marker_above_naming_claim_on_other_line_is_stale(self, root):
        res, f = check(root, "<!-- docs-claims: ignore slash:/sweetclaude:doctor -->\nPlain text.\n")
        assert res.returncode == 1
        assert kinds(f) == ["marker"]

    def test_marker_suppresses_flag(self, root):
        res, f = check(root, "`python3 scripts/toy.py --bogus` <!-- docs-claims: ignore flag:--bogus -->\n")
        assert res.returncode == 0 and f == []

    def test_marker_suppresses_link(self, root):
        res, f = check(root, "[x](docs/user-guide/gone.md) <!-- docs-claims: ignore link:docs/user-guide/gone.md -->\n")
        assert res.returncode == 0 and f == []

    def test_marker_suppresses_script(self, root):
        res, f = check(root, "`python3 scripts/gone.py` <!-- docs-claims: ignore script:scripts/gone.py -->\n")
        assert res.returncode == 0 and f == []
