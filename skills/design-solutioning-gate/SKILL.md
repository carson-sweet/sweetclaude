---
spdx-license: AGPL-3.0-or-later
description: "Validate the proposed solution before implementation. Checks architecture decisions, identifies risks, confirms design addresses requirements."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Solutioning Gate

Validate the proposed solution for: $ARGUMENTS

## SweetClaude Context

- Check architecture and tech spec against PRD requirements
- Find risks and gaps before implementation starts
- Record gate results in decision log
- This is a quality gate. Challenge the design.

## Execute

1. **Review architecture and tech spec** against PRD requirements
2. **Identify risks and gaps** in the design before implementation starts
3. **Challenge assumptions** about feasibility, scalability, and compliance
4. **Document gate results** in the decision log with pass/fail and rationale
