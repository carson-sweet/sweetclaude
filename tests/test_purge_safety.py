"""Purge-safety regression lock (promoted from validation workstream V6).

Proves the guarantee: `sweetclaude:purge` removes ONLY .sweetclaude/ state; the
user's actual project code is never touched.

Two layers:
  A. Static contract on the purge SKILL.md — the assertions test_recovery_skill.py
     is MISSING. Mirrors the existing skill-text-assertion style in that file.
  B. Behavioral execution of the exact command the skill runs (`rm -rf .sweetclaude/`)
     against a synthetic project tree, asserting code-untouched.

Tier-4 (P2) routes users to sweetclaude:purge, so this guarantee is load-bearing.
"""

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PURGE_SKILL = REPO / "skill-library" / "configure" / "purge" / "SKILL.md"


# ---------------------------------------------------------------------------
# A. STATIC CONTRACT (the missing test_recovery_skill.py assertions)
# ---------------------------------------------------------------------------

def test_purge_skill_only_mutating_command_is_scoped_rm():
    skill = PURGE_SKILL.read_text(encoding="utf-8")
    # Extract every fenced bash block and collect its lines.
    blocks = re.findall(r"```bash\n(.*?)```", skill, re.DOTALL)
    cmd_lines = [
        ln.strip()
        for b in blocks
        for ln in b.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    # The one and only deletion command.
    assert "rm -rf .sweetclaude/" in cmd_lines
    # No deletion of anything broader than .sweetclaude/. The ONLY rm command
    # in any executable block must be exactly `rm -rf .sweetclaude/`.
    rm_cmds = [ln for ln in cmd_lines if ln.split()[0:1] == ["rm"]]
    assert rm_cmds == ["rm -rf .sweetclaude/"], f"unexpected rm command(s): {rm_cmds!r}"
    # No dangerous rm-target ever appears as a command (glob, parent, home, root).
    for bad in ["rm -rf .sweetclaude/*", "rm -rf ..", "rm -rf ~", "rm -rf /",
                "rm -rf .", "rm -rf *", "rm .sweetclaude"]:
        assert bad not in cmd_lines


def test_purge_skill_does_not_edit_project_config_files():
    skill = PURGE_SKILL.read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", skill, re.DOTALL)
    body = "\n".join(blocks)
    # No edits to user project files outside .sweetclaude/.
    for target in ["settings.json", "settings.local.json", "CLAUDE.md", ".gitignore", ".mcp.json"]:
        assert target not in body, f"purge touches {target}"
    # No in-place stream edits anywhere in the skill.
    for editor in ["sed -i", "tee ", "truncate", ">>", "> CLAUDE", "> settings"]:
        assert editor not in body


def test_purge_skill_git_ops_are_nondestructive_only():
    skill = PURGE_SKILL.read_text(encoding="utf-8")
    # The only git mutation is creating a backup branch (opt-in).
    git_lines = [ln for ln in skill.splitlines() if "git " in ln]
    for ln in git_lines:
        assert not any(
            d in ln for d in ["git reset --hard", "git clean", "git rm", "git push", "git checkout -- ", "git restore"]
        ), f"destructive git op: {ln!r}"
    assert "git checkout -b sweetclaude-backup-" in skill
    assert "git branch --show-current" in skill


def test_purge_skill_requires_typed_confirmation_and_backup_offer():
    skill = PURGE_SKILL.read_text(encoding="utf-8")
    assert "Type **I understand** to confirm deletion" in skill
    assert "create a backup branch" in skill
    assert "inside `.sweetclaude/`" in skill  # the preview is scoped to .sweetclaude


# ---------------------------------------------------------------------------
# B. BEHAVIORAL: run the exact purge command, assert code untouched
# ---------------------------------------------------------------------------

def _build_project(root: Path):
    """A synthetic project: real code + config alongside .sweetclaude/ state."""
    # Project code & config that MUST survive.
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')\n")
    (root / "README.md").write_text("# My Project\n")
    (root / "CLAUDE.md").write_text("# project rules\n")
    (root / ".gitignore").write_text(".sweetclaude/\n")
    (root / "package.json").write_text("{}\n")
    cc = root / ".claude"
    cc.mkdir()
    (cc / "settings.json").write_text("{}\n")
    # SweetClaude state that MUST be removed.
    sc = root / ".sweetclaude"
    (sc / "state").mkdir(parents=True)
    (sc / "state" / "sweetclaude.yaml").write_text("version_stage: ga\n")
    (sc / "product").mkdir()
    (sc / "product" / "brief.md").write_text("brief\n")


def _snapshot(root: Path, exclude_top):
    out = {}
    for p in sorted(root.rglob("*")):
        top = p.relative_to(root).parts[0]
        if top == exclude_top:
            continue
        if p.is_file():
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


def test_purge_command_removes_only_sweetclaude_and_leaves_code_intact(tmp_path):
    proj = tmp_path / "project"
    proj.mkdir()
    _build_project(proj)

    before = _snapshot(proj, exclude_top=".sweetclaude")
    assert (proj / ".sweetclaude").is_dir()

    # The EXACT command from purge SKILL.md Step 5, run with cwd = project root.
    subprocess.run(["rm", "-rf", ".sweetclaude/"], cwd=proj, check=True)

    # Guarantee 1: .sweetclaude is gone.
    assert not (proj / ".sweetclaude").exists()

    # Guarantee 2: every other file is byte-for-byte unchanged, none added/removed.
    after = _snapshot(proj, exclude_top=".sweetclaude")
    assert after == before, "project code/config was modified or deleted by purge"

    # Spot-check the high-value files explicitly.
    assert (proj / "src" / "main.py").read_text() == "print('hello')\n"
    assert (proj / "CLAUDE.md").exists()
    assert (proj / ".claude" / "settings.json").exists()
    assert (proj / ".gitignore").exists()


def test_purge_command_is_cwd_relative_noop_when_run_outside_a_sc_project(tmp_path):
    """Documents the ONE risk surface: `rm -rf .sweetclaude/` is cwd-relative.

    Run from the wrong directory it is a harmless no-op (nothing named
    .sweetclaude there). It can only ever delete a .sweetclaude/ in cwd — it
    cannot escape to a project's code. This is why Step 1's `ls .sweetclaude/`
    existence gate + Step 3's scoped preview are the safety net.
    """
    proj = tmp_path / "project"
    proj.mkdir()
    _build_project(proj)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "important.txt").write_text("keep me\n")

    # Run from a dir with no .sweetclaude — must not error-delete anything.
    subprocess.run(["rm", "-rf", ".sweetclaude/"], cwd=elsewhere, check=True)
    assert (elsewhere / "important.txt").exists()
    assert (proj / ".sweetclaude").is_dir()  # the real one is untouched from here
