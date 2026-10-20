"""Slash-form references must name user-invocable skills (ISSUE-252).

Rule R2 from docs/internal/2026-06-06-onboarding-redesign-and-cleanup-plan.md:
`/sweetclaude:<name>` is reserved for skills whose frontmatter says
user-invocable: true. Internal skills are reached through routing and are
named without the slash, or shown as _(internal)_ in the user guide.

Telling a user to type a command that is marked internal is a dead end.
The allowlist below covers the one legitimate case: naming an internal
skill in order to say "do not call this yourself".
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
SEARCH_ROOTS = ["skills", "skill-library", "hooks", "scripts", "docs/user-guide"]

# Capture the whole token so templated refs (/sweetclaude:corpus-{step}) and
# angle-bracket placeholders (/sweetclaude:<skill-name>) can be recognized and
# skipped rather than silently truncated to a bogus skill name.
SLASH_REF = re.compile(r"/sweetclaude:([^\s`'\"),.;]+)")
PLACEHOLDER = re.compile(r"[{<]")
FRONTMATTER_UI = re.compile(r"^user-invocable:\s*(\S+)\s*$", re.MULTILINE)

ALLOWLIST: set[tuple[str, str]] = set()


def _skill_invocability() -> dict[str, bool]:
    out = {}
    for skill_md in sorted((REPO_ROOT / "skills").glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        head = text.split("---", 2)
        fm = head[1] if len(head) > 2 else ""
        m = FRONTMATTER_UI.search(fm)
        # Absent frontmatter key means invocable — only an explicit false is internal.
        out[skill_md.parent.name] = False if (m and m.group(1) == "false") else True
    return out


def _files() -> list[Path]:
    files = []
    for root in SEARCH_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in {".md", ".sh", ".py", ".json"}:
                files.append(p)
    return sorted(files)


INVOCABLE = _skill_invocability()


def _violations() -> list[tuple[str, str, int, str]]:
    bad = []
    for path in _files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith("skills/") and rel.split("/")[1] in INVOCABLE:
            owner = rel.split("/")[1]
        else:
            owner = None
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for token in SLASH_REF.findall(line):
                if PLACEHOLDER.search(token):
                    continue
                name = token.rstrip("-_")
                if name == owner:
                    continue
                if (rel, name) in ALLOWLIST:
                    continue
                if name not in INVOCABLE:
                    bad.append((rel, name, lineno, "names a skill that does not exist"))
                elif not INVOCABLE[name]:
                    bad.append((rel, name, lineno, "names a user-invocable: false skill"))
    return bad


def test_no_slash_refs_to_internal_or_missing_skills() -> None:
    bad = _violations()
    rendered = "\n".join(f"  {p}:{n} -> /sweetclaude:{s} ({why})" for p, s, n, why in bad)
    assert not bad, (
        "Slash-form references must name existing, user-invocable skills "
        f"(rule R2). {len(bad)} violation(s):\n{rendered}"
    )
