"""Enforcement markers in the user docs track what the code enforces.

Claims about rules still not enforced must say "Not currently enforced" in the
same paragraph, table row, or list item wherever the claim still appears
(UNENFORCED_CLAIMS below). Claims about rules enforced since 5.1 must not
carry the marker (ENFORCED_CLAIMS below). Enforced since 5.1: test
immutability, the TDD pre-write guard, the auto-test-runner, the WIP limit,
the phase-dwelling guard, the preflight guard, the Agile no-active-sprint
block, the TDD commit gate, the Kanban blocked-skill denial, the Shape Up
betting-table gate, the Shape Up ship/no-ship gate, phase exit criteria with
soft-gate escape and hard-gate risk-acceptance overrides (logged to the
decision log), the GA+ hard-gate matrix, and the solutioning-gate pass
record. Phrases match with emoji removed, so a rewrite that drops a warning
glyph still matches. The claim list comes from the 2026-10-20 docs audit
(group-B and group-D)."""
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MARKER = "Not currently enforced"

GUIDE = "docs/user-guide/"

UNENFORCED_CLAIMS = [
    ("README.md", "A betting table decides what gets the next cycle"),
    ("README.md", "hard gates at key decisions"),
    (GUIDE + "how-it-works.md", "Active sprint required to implement (hard block)"),
    (GUIDE + "how-it-works.md", "It still respects hard gates"),
    (GUIDE + "planning-concepts.md", "implementation is blocked unless there is an active sprint"),
    (GUIDE + "planning-concepts.md", "\"Hard block\" means SweetClaude will not let you proceed"),
    (GUIDE + "glossary.md", "Implementation is hard-blocked without an active sprint"),
    (GUIDE + "behavioral-contracts.md", "are enforced by shell hooks"),
    (GUIDE + "getting-started.md", "Hard gates (⚠️) cannot be soft-bypassed"),
    (GUIDE + "faq.md", "physically cannot — is bypass hard gates"),
    (GUIDE + "faq.md", "Hard gates (⚠️) require explicit risk acceptance with the override logged"),
]

ENFORCED_CLAIMS = [
    ("README.md", "SweetClaude enforces the WIP limit"),
    ("README.md", "implementation is blocked when no sprint is active"),
    ("README.md", "Test files are physically blocked from modification during implementation by hooks"),
    ("README.md", "TDD hooks physically block test file modification during implementation"),
    (GUIDE + "how-it-works.md", "WIP limit (default 3 in-progress issues, hard block)"),
    (GUIDE + "how-it-works.md", "`wip-limit.sh`, a PreToolUse hook, blocks tool calls in Kanban mode"),
    (GUIDE + "how-it-works.md", "**Test-guardian hook** (PreToolUse) blocks edits to test files"),
    (GUIDE + "how-it-works.md", "**Auto-test-runner hook** (PostToolUse) runs tests automatically"),
    (GUIDE + "how-it-works.md", "Hooks block this physically"),
    (GUIDE + "how-it-works.md", "Edits to test directories are blocked at the tool call level"),
    (GUIDE + "how-it-works.md", "Test suite runs automatically after source edits"),
    (GUIDE + "how-it-works.md", "Blocks tool calls that would create new in-progress work"),
    (GUIDE + "how-it-works.md", "betting table approval required before implementation"),
    (GUIDE + "how-it-works.md", "ship/no-ship gate at cycle end"),
    (GUIDE + "how-it-works.md", "`phase-dwelling-guard.sh` (Stop hook)"),
    (GUIDE + "how-it-works.md", "Protocol Guardian enforces it when active"),
    (GUIDE + "planning-concepts.md", "SweetClaude hard-enforces a maximum of three stories"),
    (GUIDE + "planning-concepts.md", "The WIP limit is not advisory"),
    (GUIDE + "planning-concepts.md", "| **WIP limit** | None | 3 active (hard block)"),
    (GUIDE + "planning-concepts.md", "implementation is blocked until the betting table approves the pitch"),
    (GUIDE + "planning-concepts.md", "| **Hard gate to implement**"),
    (GUIDE + "how-it-works.md", "A phase is done when its exit criteria are met"),
    (GUIDE + "how-it-works.md", "**Hard gates** (⚠️) cannot be soft-bypassed"),
    (GUIDE + "phases-and-workflows.md", "The framework will not advance you past a phase whose criteria are unmet"),
    (GUIDE + "phases-and-workflows.md", "The override is logged. SweetClaude continues."),
    (GUIDE + "phases-and-workflows.md", "**Hard gates** (⚠️) cannot be soft-bypassed"),
    (GUIDE + "phases-and-workflows.md", "Hard gate — human decision required. |"),
    (GUIDE + "phases-and-workflows.md", "VERIFY is a hard gate (security review mandatory)"),
    (GUIDE + "phases-and-workflows.md", "CUTOVER is a hard gate"),
    (GUIDE + "phases-and-workflows.md", "VERIFY is a hard gate — integrity checks"),
    (GUIDE + "phases-and-workflows.md", "Hard gate at DESIGN for GA+ projects"),
    (GUIDE + "phases-and-workflows.md", "triggers automatically when a hard-gate work type reaches DESIGN"),
    (GUIDE + "glossary.md", "SweetClaude will not advance to the next phase until the exit criteria"),
    (GUIDE + "glossary.md", "physically blocks edits to test files during the IMPLEMENT phase"),
    (GUIDE + "glossary.md", "Implementation is hard-blocked until the betting table is approved"),
    (GUIDE + "glossary.md", "A betting table approves pitches before implementation begins (hard gate)"),
    (GUIDE + "glossary.md", "runs the test suite automatically after every source file edit"),
    (GUIDE + "glossary.md", "A continuous-flow mode with a hard WIP limit of 3"),
    (GUIDE + "glossary.md", "test-guardian hook active"),
    (GUIDE + "tdd.md", "SweetClaude makes it physically impossible at higher levels"),
    (GUIDE + "tdd.md", "**test-guardian** (PreToolUse) blocks edits to test files"),
    (GUIDE + "tdd.md", "**auto-test-runner** (PostToolUse) runs tests automatically after every source edit"),
    (GUIDE + "tdd.md", "**tdd-commit-gate** (PreToolUse) denies a `git commit`"),
    (GUIDE + "tdd.md", "the workflow refuses to advance"),
    (GUIDE + "tdd.md", "Test-guardian hook activates"),
    (GUIDE + "tdd.md", "Auto-test-runner hook fires after every source edit"),
    (GUIDE + "tdd.md", "test-guardian blocks the edit at the OS level"),
    (GUIDE + "tdd.md", "auto-test-runner runs after every source edit; failure is immediate"),
    (GUIDE + "tdd.md", "The test-guardian hook blocks the edit"),
    (GUIDE + "hook-development.md", "`test-guardian.sh` and `auto-test-runner.sh`"),
    (GUIDE + "hook-development.md", "`wip-limit.sh` (blocks only in Kanban mode"),
    (GUIDE + "hook-development.md", "`preflight-guard.sh` (blocks until first valid invocation"),
    (GUIDE + "walkthroughs.md", "The test-guardian hook physically blocks any test file edits"),
    (GUIDE + "walkthroughs.md", "The auto-test-runner hook fires after every source edit"),
    (GUIDE + "walkthroughs.md", "Test-guardian and auto-test-runner hooks are still active"),
    (GUIDE + "walkthroughs.md", "The test-guardian hook prevents any change to test files"),
]
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def _blocks(text):
    blocks = []
    run = []

    def flush():
        if not run:
            return
        current = []
        for line in run:
            if line.lstrip().startswith("|"):
                if current:
                    blocks.append(" ".join(current))
                    current = []
                blocks.append(line.strip())
            elif LIST_ITEM.match(line):
                if current:
                    blocks.append(" ".join(current))
                current = [line.strip()]
            else:
                current.append(line.strip())
        if current:
            blocks.append(" ".join(current))
        run.clear()

    for line in text.splitlines():
        if line.strip():
            run.append(line)
        else:
            flush()
    flush()
    return blocks


def _norm(s):
    return re.sub(r"\s+", " ", s)


EMOJI = re.compile("[\u2600-\u27BF\U0001F000-\U0001FAFF\uFE0F]")


def _match_form(s):
    return _norm(EMOJI.sub("", s).replace("()", "")).strip()


def _hits(rel, phrase):
    text = (ROOT / rel).read_text(encoding="utf-8")
    needle = _match_form(phrase)
    return [b for b in _blocks(text) if needle in _match_form(b)]


@pytest.mark.parametrize(
    "rel,phrase",
    UNENFORCED_CLAIMS,
    ids=[f"{rel.rsplit('/', 1)[-1]}::{phrase[:48]}" for rel, phrase in UNENFORCED_CLAIMS],
)
def test_unenforced_claim_carries_not_currently_enforced_marker(rel, phrase):
    missing = [b for b in _hits(rel, phrase) if MARKER not in b]
    assert missing == [], (
        f"{rel}: claim {phrase!r} lacks the exact marker {MARKER!r} in its "
        f"paragraph, table row, or list item"
    )


@pytest.mark.parametrize(
    "rel,phrase",
    ENFORCED_CLAIMS,
    ids=[f"{rel.rsplit('/', 1)[-1]}::{phrase[:48]}" for rel, phrase in ENFORCED_CLAIMS],
)
def test_enforced_claim_has_no_not_currently_enforced_marker(rel, phrase):
    stale = [b for b in _hits(rel, phrase) if MARKER in b]
    assert stale == [], f"{rel}: {phrase!r} is enforced since 5.1 but still says {MARKER!r}"
