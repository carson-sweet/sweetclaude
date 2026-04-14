---
name: product/research
description: "Conduct market or technical research on a specific question. Returns findings with evidence and sources. Wraps bmad:research."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Research

Research: $ARGUMENTS

## SweetClaude Context

- Answer every research question with evidence and sources
- Identify research gaps explicitly — flag unanswered questions as open items
- Save output to `brainstorm/` or `strategy/` in `.sweetclaude/` depending on topic
- Use RAG index if available for project-specific context

## Execute

Invoke `bmad:research` and follow its workflow.
