#!/usr/bin/env python3
"""
Idempotent: adds `disable-model-invocation: true` to specified skills,
sets `user-invocable: false` on internal skills.

Reads the explicit list below — does NOT touch any other skill.
"""
import os
import re
import sys

# Group B — user-invocable: true (80 skills after corpus split)
EXPLICIT_ONLY = [
    "code-debt", "code-review", "code-testing", "code-verify",
    "corpus-consolidate", "corpus-promote", "corpus-rag-reindex",
    "corpus-rag-setup", "corpus-reconcile", "corpus-status", "corpus-triage",
    "deploy-ship",
    "design-api-design", "design-architecture", "design-change-impact-analysis",
    "design-data-model", "design-manage-decisions", "design-tech-spec",
    "design-user-flows", "design-ux", "design-ux-review", "design-wireframes",
    "document-corpus", "documents-academic-research", "documents-narrative-arc",
    "epic-design", "fix-sweetclaude", "hibernate", "init", "john-wick",
    "misc-meeting-prep", "mockup-extract", "mockup-graduate", "mockup-sandbox",
    "off", "product-brief", "product-competition", "product-discovery",
    "product-manage-scope", "product-market-messaging",
    "product-milestone-planning", "product-milestones", "product-parking-lot",
    "product-positioning-statement", "product-prd", "product-research",
    "product-roadmap", "product-roadmap-analysis", "product-sprint-plan",
    "product-terminology", "product-user-focus-group", "product-user-stories",
    "product-user-tdd-tests", "project-assess-shape", "project-backlog",
    "project-backlog-triage", "project-epics", "project-gh-import-issues",
    "project-gh-sync-issues", "project-goals", "project-issues",
    "project-mode", "project-scope", "project-sprints", "project-themes",
    "purge", "recap", "retro", "session-export", "something-broke",
    "testing-accessibility", "testing-compliance", "testing-performance",
    "testing-plan", "testing-security", "testing-session", "ultraplan",
    "update", "usage", "user-personas",
]

# Group C — user-invocable: false (9 skills)
INTERNAL_ALSO_NOT_INVOCABLE = [
    "claude-config-audit", "code-tdd",
    "design-solutioning-gate", "documents-update-docs", "guardian-off",
    "guardian-on", "john-wick-checkin", "next-steps", "setup",
]

# Skills that must NOT be edited
AMBIENT_CORE = {
    "bootstrap", "code-feature", "code-issue", "find-skill", "go", "help",
    "master", "status", "_health", "_migrate", "_offer", "_route",
}

REPO_SKILLS_DIR = "/Users/carsonsweet/dev/sweetclaude/skills"


def edit(path: str, set_user_invocable_false: bool) -> str:
    """Returns 'ok', 'already', or 'error: ...' """
    content = open(path).read()

    fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not fm_match:
        return f"error: no frontmatter in {path}"
    fm = fm_match.group(1)

    if re.search(r'^disable-model-invocation:\s*true\s*$', fm, re.MULTILINE):
        return "already"

    if re.search(r'^user-invocable:', fm, re.MULTILINE):
        new_fm = re.sub(
            r'^(user-invocable:.*)$',
            r'\1\ndisable-model-invocation: true',
            fm, count=1, flags=re.MULTILINE,
        )
    else:
        ui_value = "false" if set_user_invocable_false else "true"
        new_fm = re.sub(
            r'^(description:)',
            f'user-invocable: {ui_value}\ndisable-model-invocation: true\n\\1',
            fm, count=1, flags=re.MULTILINE,
        )

    if set_user_invocable_false:
        new_fm = re.sub(
            r'^user-invocable:\s*true\s*$',
            'user-invocable: false',
            new_fm, flags=re.MULTILINE,
        )

    new_content = content.replace(fm, new_fm, 1)
    if new_content == content:
        return f"error: edit produced no change for {path}"

    with open(path, 'w') as f:
        f.write(new_content)
    return "ok"


def main() -> int:
    targets = [(name, False) for name in EXPLICIT_ONLY]
    targets += [(name, True) for name in INTERNAL_ALSO_NOT_INVOCABLE]

    bad = [n for n, _ in targets if n in AMBIENT_CORE]
    if bad:
        print(f"FATAL: target list overlaps ambient core: {bad}")
        return 1

    missing = [n for n, _ in targets
               if not os.path.exists(f"{REPO_SKILLS_DIR}/{n}/skill.md")]
    if missing:
        print(f"FATAL: missing skill.md for: {missing}")
        return 1

    ok = already = errors = 0
    for name, force_invocable_false in targets:
        path = f"{REPO_SKILLS_DIR}/{name}/skill.md"
        result = edit(path, force_invocable_false)
        if result == "ok":
            ok += 1
        elif result == "already":
            already += 1
        else:
            print(result)
            errors += 1

    print(f"\nEdited: {ok}  Already had disable: {already}  Errors: {errors}")
    print(f"Total targets: {len(targets)}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
