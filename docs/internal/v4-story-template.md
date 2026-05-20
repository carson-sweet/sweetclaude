# v4 Story Templates

**Version:** 2.0
**Date:** 2026-05-12
**See also:** `v4-story-schema.md` (canonical schema), `v4-sprint-template.md`

This file shows the canonical body shape for each story type. Frontmatter is identical across types; only the body sections differ.

---

## Frontmatter (all types)

```yaml
---
id: <TYPE>-NNN
type: <story | bug | debt | chore>
title: <Title>
status: new
priority: soon
effort: m
epic: null
milestone: null
sprint: null
tags: []
origin: manual
created: YYYY-MM-DD
updated: YYYY-MM-DD
closed_date: null
---
```

---

## story

```markdown
## Description

As a [who], I want [what] so that [why].

## Acceptance Criteria

- [ ] <criterion>

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```

---

## bug

```markdown
## Description

[What is broken and the impact]

## Steps to Reproduce

1. ...

## Expected / Actual

**Expected:** ...

**Actual:** ...

## Acceptance Criteria

- [ ] Bug no longer reproducible via above steps

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```

---

## debt

```markdown
## Description

[What the debt is]

## Why This Is Debt

[How it accumulated, what problem it causes now]

## Risk If Not Addressed

[What gets worse if this isn't fixed]

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```

---

## chore

```markdown
## Description

[What needs to be done]

## Definition of Done

- [ ] Item 1
- [ ] Item 2

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```
