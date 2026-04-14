---
name: product/product-brief
description: "Walk through an 11-section product brief. One section at a time with probing follow-ups. Wraps bmad:product-brief with SweetClaude context and preflight."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Product Brief

Walk through an 11-section product brief for: $ARGUMENTS

## SweetClaude Context

Before invoking BMAD, set expectations:
- One section at a time — never batch multiple sections
- Probe vague answers with follow-ups before moving to the next section
- The interview is a discovery conversation, not a form to fill
- After generating the document, run the BMAD validation checklist
- Save the output to `specs/product-brief.md` in `.sweetclaude/`

## Execute

Invoke `bmad:product-brief` and follow its workflow. Apply the depth rules from the SweetClaude interaction model throughout.
