#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Light SKILL.md prompt validation. For every skill that mentions
# AskUserQuestion, check that the surrounding text plausibly defines at
# least 2 options. Catches obvious authoring errors (orphaned
# AskUserQuestion references, single-option "menus" that should be plain
# prose, missing options blocks).
#
# This is a heuristic check, not a strict schema validator. The skill files
# are markdown read by an LLM — they don't have a formal schema. The check
# greps for AskUserQuestion mentions and verifies an "Options:" block (or
# equivalent numbered/bulleted list) follows within ~25 lines.
#
# Known false-positive sources (acceptable noise, not bugs):
#   - AskUserQuestion mentioned in commentary/explanation, not as an actual
#     prompt instruction. These can be excluded by adding the word "tool"
#     or "interaction-model" nearby (rough heuristic).

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

echo "=== SKILL.md AskUserQuestion prompt sanity check ==="

# For each SKILL.md mentioning AskUserQuestion, run the heuristic.
python3 - "$REPO_ROOT/skills" <<'PY'
import pathlib, re, sys

skills_root = pathlib.Path(sys.argv[1])
total_skills = 0
total_mentions = 0
warnings = []

# Patterns that look like option listings. We accept any of:
#   - Bulleted at line start (with optional blockquote ">" prefix)
#   - Numbered (1. or 1))
#   - Markdown table rows containing **bold** labels (typical "Option" column)
OPTION_LINE_RE = re.compile(
    r'^\s*(?:>\s*)?(?:[-*]\s+|\d+[.)]\s+).{2,}'
    r'|^\s*\|\s*\*\*[^|]+\*\*\s*\|'
    r'|^\s+\[\w[\w \-]*\]\s+\S',
    re.MULTILINE
)

# Lines that strongly indicate this is a real prompt instruction (vs commentary)
PROMPT_INDICATORS = re.compile(
    r'present\s+(?:via\s+)?\*?\*?AskUserQuestion|'
    r'\*?\*?AskUserQuestion\*?\*?\s+with|'
    r'use\s+AskUserQuestion|'
    r'invoke\s+AskUserQuestion|'
    r'call\s+AskUserQuestion',
    re.IGNORECASE
)

for skill_md in sorted(skills_root.rglob('SKILL.md')):
    text = skill_md.read_text(encoding='utf-8')
    if 'AskUserQuestion' not in text:
        continue
    total_skills += 1
    lines = text.split('\n')

    # Find every line mentioning AskUserQuestion
    for i, line in enumerate(lines):
        if 'AskUserQuestion' not in line:
            continue
        # Skip commentary-only mentions
        is_prompt = PROMPT_INDICATORS.search(line)
        if not is_prompt:
            # Check 2 lines back/forward for prompt indicators (multi-line prose)
            window = '\n'.join(lines[max(0, i-2):i+3])
            if not PROMPT_INDICATORS.search(window):
                continue

        total_mentions += 1

        # Look forward AND backward — the AskUserQuestion mention may
        # reference a menu defined earlier ("Present via AskUserQuestion.").
        forward = '\n'.join(lines[i:i+25])
        backward = '\n'.join(lines[max(0, i-15):i])
        option_lines = OPTION_LINE_RE.findall(forward) + OPTION_LINE_RE.findall(backward)
        # Filter: keep only ones that look like menu options (short label)
        plausible_options = [
            ln for ln in option_lines
            if len(ln.strip()) < 200 and not ln.strip().startswith('---')
        ]

        if len(plausible_options) < 2:
            rel = skill_md.relative_to(skills_root.parent)
            warnings.append(
                f"{rel}:{i+1}: AskUserQuestion mentioned but <2 plausible options in next 25 lines (found {len(plausible_options)})"
            )

print(f"Scanned {total_skills} SKILL.md files mentioning AskUserQuestion")
print(f"Found {total_mentions} prompt-instruction mentions")
print(f"Warnings: {len(warnings)}")
for w in warnings:
    print(f"  {w}")

# Informational test — surface warnings but always exit 0. The heuristic
# cannot catch every legitimate option-listing format (dynamic-options
# prose, deeply-nested formats). Real orphan-AskUserQuestion bugs would
# typically appear as warnings with no options found in either direction,
# but the maintainer needs to eyeball the warnings to know which are bugs
# vs. accepted false positives.
sys.exit(0)
PY

EXIT_CODE=$?

if [ "$EXIT_CODE" = "0" ]; then
    pass "scan completed (warnings above are informational; eyeball them when refactoring skill prompts)"
else
    fail "scan exited unexpectedly with code $EXIT_CODE"
fi

echo ""
if [ "$FAILED" -gt 0 ]; then
    echo "=== FAILED: $FAILED check(s) ==="
    exit 1
else
    echo "=== ALL PASSED ==="
    exit 0
fi
