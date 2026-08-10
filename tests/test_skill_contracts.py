"""Tier-1 structural contracts across the whole skill corpus (EP-004).

Skills are instructions, not programs, so their behavior cannot be unit
tested. Their structure can. Every defect that opened EP-004 lived here:
ISSUE-249 (a skill writing a state file v4 abandoned), ISSUE-250 (guards
keyed on a file onboarding never creates), ISSUE-251 (canonical source
inverted), ISSUE-252 (routing targets that do not resolve).

This suite is corpus-wide on purpose. The per-domain issues (ISSUE-257
through ISSUE-264) carry the capability-manifest entries; the contracts
themselves are shared, because a rule that applies to product skills but not
design skills is not a rule.

Companion suites, kept separate because each pins a specific defect class:
  test_preflight_guard_state_file.py  — guards accept the v4 state file
  test_canonical_state_reads.py       — canonical reads, no unguarded opens
  test_slash_form_targets.py          — slash form only for invocable skills
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents"

SKILL_NAMES = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())
AGENT_NAMES = sorted(p.stem for p in AGENTS_DIR.glob("*.md"))

SKILL_MDS = sorted(SKILLS_DIR.glob("*/SKILL.md"))

REF = re.compile(r"(?<![/\w])sweetclaude:([a-z0-9_/-]+)")

# References that name a nonexistent skill on purpose.
#
#   routing-tables.md rows annotated *(Plan 3)* or *(fallback ...)* are
#   placeholders for skills that were designed but never built. The annotation
#   is what makes them honest; the test requires it.
#   doctor.py states outright that sweetclaude:adopt does not exist.
#   benchmark.sh embeds grep alternations, not references.
INTENTIONAL_MISSING = {
    ("skills/find-skill/routing-tables.md", "concept-framing"),
    ("skills/find-skill/routing-tables.md", "security-planning"),
    ("skills/find-skill/routing-tables.md", "release-planning"),
    ("skills/find-skill/routing-tables.md", "onboarding-flow-design"),
    ("skills/find-skill/routing-tables.md", "external-integration"),
    ("skills/find-skill/routing-tables.md", "break-glass-notes"),
    ("scripts/doctor.py", "adopt"),
    ("scripts/benchmark.sh", "something"),
    ("scripts/benchmark.sh", "testing"),
}


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) > 2 else ""


# --- frontmatter ---------------------------------------------------------

@pytest.mark.parametrize("skill_md", SKILL_MDS, ids=lambda p: p.parent.name)
def test_skill_has_frontmatter(skill_md: Path) -> None:
    assert _frontmatter(skill_md.read_text(encoding="utf-8")), (
        f"{skill_md.parent.name} has no YAML frontmatter"
    )


@pytest.mark.parametrize("skill_md", SKILL_MDS, ids=lambda p: p.parent.name)
def test_skill_declares_a_description(skill_md: Path) -> None:
    """The description is what routing and the skill picker match on."""
    fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
    assert re.search(r"^description:\s*\S", fm, re.M), (
        f"{skill_md.parent.name} has no description"
    )


@pytest.mark.parametrize("skill_md", SKILL_MDS, ids=lambda p: p.parent.name)
def test_skill_declares_its_licence(skill_md: Path) -> None:
    """AGPL project: an unlicensed file is a compliance gap, and nothing else
    in the repo or CI checks this."""
    fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
    assert re.search(r"^spdx-license:\s*\S", fm, re.M), (
        f"{skill_md.parent.name} declares no spdx-license"
    )


@pytest.mark.parametrize("skill_md", SKILL_MDS, ids=lambda p: p.parent.name)
def test_user_invocable_is_a_bare_boolean_when_present(skill_md: Path) -> None:
    fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
    m = re.search(r"^user-invocable:\s*(\S+)\s*$", fm, re.M)
    if m:
        assert m.group(1) in {"true", "false"}, (
            f"{skill_md.parent.name} has user-invocable: {m.group(1)!r}; "
            "anything other than true/false is read as invocable"
        )


# --- reference resolution ------------------------------------------------

def _all_reference_sites() -> list[tuple[str, str, int]]:
    sites = []
    for root in ("skills", "hooks", "scripts"):
        base = REPO_ROOT / root
        for p in base.rglob("*"):
            if p.suffix not in {".md", ".sh", ".py"}:
                continue
            rel = p.relative_to(REPO_ROOT).as_posix()
            for lineno, line in enumerate(
                p.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                for name in REF.findall(line):
                    sites.append((rel, name, lineno))
    return sites


def test_every_skill_reference_resolves() -> None:
    """A reference to a skill that does not exist is a dead end for whoever
    follows it. ISSUE-252 found six such targets."""
    bad = [
        (rel, name, lineno)
        for rel, name, lineno in _all_reference_sites()
        if name not in SKILL_NAMES and (rel, name) not in INTENTIONAL_MISSING
    ]
    rendered = "\n".join(f"  {rel}:{n} -> sweetclaude:{name}" for rel, name, n in bad)
    assert not bad, (
        f"{len(bad)} reference(s) name a skill that does not exist:\n{rendered}\n"
        "If a reference is a deliberate placeholder, annotate it and add it to "
        "INTENTIONAL_MISSING."
    )


def test_no_skill_reference_uses_the_path_form() -> None:
    """`sweetclaude:product/backlog` is an older naming scheme; the skill is
    `sweetclaude:product-backlog`. The path form resolves to nothing."""
    bad = [(rel, name, n) for rel, name, n in _all_reference_sites() if "/" in name]
    rendered = "\n".join(f"  {rel}:{n} -> sweetclaude:{name}" for rel, name, n in bad)
    assert not bad, f"path-form skill references:\n{rendered}"


def test_agents_are_not_referenced_as_skills() -> None:
    """qa-caucus-service and friends live in agents/ and are spawned as
    subagent types. Prefixing them with sweetclaude: implies a skill that
    cannot be invoked."""
    bad = [
        (rel, name, n) for rel, name, n in _all_reference_sites()
        if name in AGENT_NAMES and name not in SKILL_NAMES
    ]
    rendered = "\n".join(f"  {rel}:{n} -> sweetclaude:{name}" for rel, name, n in bad)
    assert not bad, (
        f"agent names referenced as skills:\n{rendered}\n"
        "Reference agents by bare name, not with the sweetclaude: prefix."
    )


def test_intentional_missing_entries_are_annotated() -> None:
    """A placeholder is only honest if it says so. This keeps the allowlist
    from becoming a place to hide real dead references."""
    unannotated = []
    for rel, name in sorted(INTENTIONAL_MISSING):
        path = REPO_ROOT / rel
        if not path.exists():
            unannotated.append((rel, name, "file missing"))
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if f"sweetclaude:{name}" not in line:
                continue
            # Annotation may sit on an adjacent line — a wrapped comment, or a
            # table row whose note follows the reference.
            window = "\n".join(lines[max(0, i - 2):i + 3])
            annotated = any(
                marker in window
                for marker in ("Plan 3", "fallback", "planned",
                               "There is NO", "run_prompt")
            )
            if not annotated:
                unannotated.append((rel, name, line.strip()[:80]))
            break
    assert not unannotated, (
        "allowlisted references must be visibly marked as placeholders:\n"
        + "\n".join(f"  {r}: {n} -> {why}" for r, n, why in unannotated)
    )


def test_allowlist_has_no_stale_entries() -> None:
    """If a placeholder skill gets built, its allowlist entry must go."""
    stale = [(rel, name) for rel, name in INTENTIONAL_MISSING if name in SKILL_NAMES]
    assert not stale, (
        f"these skills now exist and must leave INTENTIONAL_MISSING: {stale}"
    )


# --- artifact privacy ----------------------------------------------------

# Skills that consume the manifest to place artifacts. `base_path` is the
# usage signal: master only describes the manifest, and setup writes it, so
# neither is a consumer.
MANIFEST_WRITERS = {"setup"}
PRODUCT_WRITERS = [
    p for p in SKILL_MDS
    if "base_path" in p.read_text(encoding="utf-8")
    and p.parent.name not in MANIFEST_WRITERS
]


def test_some_skills_consume_the_privacy_manifest() -> None:
    """Guard the guard — if base_path is renamed, this suite goes quiet."""
    assert len(PRODUCT_WRITERS) >= 10


@pytest.mark.parametrize("skill_md", PRODUCT_WRITERS, ids=lambda p: p.parent.name)
def test_privacy_aware_skills_read_the_manifest_they_resolve_against(
    skill_md: Path,
) -> None:
    """A skill that uses base_path without naming the manifest is reading it
    from somewhere unstated, or assuming a default."""
    text = skill_md.read_text(encoding="utf-8")
    assert "artifact-privacy" in text, (
        f"{skill_md.parent.name} resolves base_path but never names "
        "artifact-privacy.yaml as its source"
    )


@pytest.mark.parametrize("skill_md", PRODUCT_WRITERS, ids=lambda p: p.parent.name)
def test_privacy_aware_skills_handle_a_missing_manifest(skill_md: Path) -> None:
    """A configured project can still be missing the manifest. The skill must
    either say what happens, or guard the read programmatically — falling
    through to an unset base_path writes artifacts to the wrong place.
    """
    text = skill_md.read_text(encoding="utf-8")
    documented = re.search(r"(?i)(if absent|if missing|not found|does not exist)", text)
    guarded = re.search(r"(\.exists\(\)|or \{\}|2>/dev/null|\|\| echo)", text)
    assert documented or guarded, (
        f"{skill_md.parent.name} resolves base_path but neither documents nor "
        "guards the manifest being absent"
    )


# --- invocation policy (ISSUE-287) ---------------------------------------
#
# hooks/new-skill-lint.sh was a pre-commit gate meant to stop a skill claiming
# ambient invocation. It grepped `skills/*/skill.md`; every skill is `SKILL.md`,
# so it never matched and never ran once. It also required
# `disable-model-invocation: true`, a key no skill in the corpus sets.
#
# These replace it, in CI where they run for everyone rather than per-clone and
# where --no-verify cannot skip them.

@pytest.mark.parametrize("skill_md", SKILL_MDS, ids=lambda p: p.parent.name)
def test_user_invocable_is_declared(skill_md: Path) -> None:
    """Whether a skill is user-facing or internal should be stated, not left to
    a default. Four skills had never declared it."""
    fm = _frontmatter(skill_md.read_text(encoding="utf-8"))

    assert re.search(r"^user-invocable:\s*(true|false)\s*$", fm, re.M), (
        f"{skill_md.parent.name} does not declare user-invocable")


# Phrasings that assert a skill activates without the user asking. Negated
# forms are excluded deliberately: report-failure's description ends "Never
# auto-invoke", which is the policy being honoured, and a pattern that flagged
# it would have to be weakened until it caught nothing.
_SELF_INVOKING = re.compile(
    r"(?<!never )(?<!not )(?<!don't )(?<!do not )"
    r"(auto-invoke[sd]?\b"
    r"|automatically (?:invoke|trigger|activate|run|fire)"
    r"|(?:invoked|triggered|activated|run|fired) automatically"
    r"|triggers? (?:on|when)\b"
    r"|fires? when\b"
    r"|use (?:this )?proactively)",
    re.I)


def _description(text: str) -> str:
    fm = _frontmatter(text)
    m = re.search(r"^description:\s*(.+?)(?=\n[a-z-]+:|\Z)", fm, re.S | re.M)
    return " ".join(m.group(1).split()) if m else ""


@pytest.mark.parametrize("skill_md", SKILL_MDS, ids=lambda p: p.parent.name)
def test_no_description_advertises_self_invocation(skill_md: Path) -> None:
    """The actual failure mode: a description saying a skill triggers on some
    condition gets it invoked in the wrong context, unasked."""
    description = _description(skill_md.read_text(encoding="utf-8"))
    match = _SELF_INVOKING.search(description)

    assert not match, (
        f"{skill_md.parent.name} description claims self-invocation "
        f"({match.group(0)!r}). Skills are invoked explicitly; describe what "
        f"it does, not when it fires.")


def test_the_pattern_catches_what_it_is_for() -> None:
    """A pattern that matches nothing would pass the whole corpus and mean
    nothing. These are the phrasings that caused the problem."""
    for bad in ("Triggers on any commit to main.",
                "This skill is invoked automatically at session start.",
                "Automatically runs when a test fails.",
                "Use proactively whenever the user edits a config file.",
                "Will auto-invoke on phase transitions."):
        assert _SELF_INVOKING.search(bad), bad


def test_the_pattern_leaves_the_negated_forms_alone() -> None:
    """report-failure says "Never auto-invoke" — the policy being stated, not
    broken. project-epics says "Redirects automatically", which describes where
    it sends you, not when it starts."""
    for fine in ("Invoke ONLY when the user explicitly asks. Never auto-invoke.",
                 "DEPRECATED — use /sweetclaude:epics instead. Redirects automatically.",
                 "Build a new feature end-to-end.",
                 "Run the full test suite and report failures."):
        assert not _SELF_INVOKING.search(fine), fine


def test_the_retired_hook_is_gone() -> None:
    """Leaving a dead pre-commit gate in place is worse than having none: it
    reads as a control that has never once executed."""
    assert not (REPO_ROOT / "hooks" / "new-skill-lint.sh").exists()
