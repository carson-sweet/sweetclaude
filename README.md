# superclaude

Claude Code environment configuration: playbooks, skills, audit artifacts, and reference docs for a Superpowers + BMAD setup.

## Structure

```
audit/       Environment audit reports
playbooks/   Step-by-step setup prompts (global and per-project)
skills/      Portable skill files (session-export, RAG index)
docs/        Reference guides (Claude Code optimization, TDD)
```

## Usage

- **Setting up a new machine:** Run the global setup playbook in a fresh Claude Code session.
- **Setting up a new project:** Run the project setup playbook from inside the repo.
- **Skills:** Copy into `~/.claude/skills/` or `.claude/skills/` as needed.

## Context

This repo captures decisions and artifacts from an April 2026 effort to clean up and rationalize a Claude Code environment that had accumulated overlapping tooling (Superpowers, Don Cheli SDD, custom skills). The outcome: keep Superpowers + BMAD, remove Don Cheli, lean global CLAUDE.md, and structured per-project harnesses.
