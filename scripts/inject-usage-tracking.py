#!/usr/bin/env python3
"""Inject skill_invoked recording into every skills/*/SKILL.md."""
import re
import pathlib
import sys

SKILLS_DIR = pathlib.Path(__file__).parent.parent / "skills"
MARKER = "record-event.sh"
RECORDING_TEMPLATE = (
    '\n!`bash ~/.claude/hooks/sweetclaude/record-event.sh'
    ' skill_invoked "sweetclaude:{name}" 2>/dev/null || true`\n'
)


def inject(filepath: pathlib.Path, skill_name: str) -> str:
    content = filepath.read_text()

    if MARKER in content:
        return "already_injected"

    match = re.match(r"^(---\n.*?---\n)", content, re.DOTALL)
    if not match:
        return "no_frontmatter"

    end = match.end()
    recording = RECORDING_TEMPLATE.format(name=skill_name)
    filepath.write_text(content[:end] + recording + content[end:])
    return "injected"


counts = {"injected": 0, "already_injected": 0, "no_frontmatter": 0}
for skill_dir in sorted(SKILLS_DIR.iterdir()):
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        continue
    skill_name = skill_dir.name
    result = inject(skill_file, skill_name)
    counts[result] += 1
    print(f"{result}: {skill_name}")

print(f"\nTotal: {counts}")
