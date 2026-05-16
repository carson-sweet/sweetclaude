---
id: CHORE-009
type: chore
title: Include version number in "SweetClaude is active" bootup message
status: done
priority: sooner
effort: xs
epic: EP-039
milestone: null
sprint: null
tags: [bootstrap, ux, version, status]
origin: manual
created: 2026-05-14
updated: 2026-05-15
closed_date: 2026-05-15
---

## Description

The session-start status message currently says "SweetClaude is active" (or equivalent) without showing the installed version. Users have no way to confirm which version is running without checking `sweetclaude.yaml` manually.

## Definition of Done

- [x] Bootstrap status surface (Step 8 of `bootstrap` skill) includes the installed version alongside the project name and version stage
- [x] Format: `SweetClaude {installed_version} · {project name} · {version_stage}` (or equivalent compact form)
- [x] Version is read from `framework.installed_version` in `sweetclaude.yaml` — not hardcoded

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
