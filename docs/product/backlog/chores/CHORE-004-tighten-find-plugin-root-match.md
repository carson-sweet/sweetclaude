---
id: CHORE-004
type: chore
title: Tighten find_plugin_root() plugin_key match to startswith("sweetclaude@")
status: new
priority: later
effort: s
epic: null
milestone: null
sprint: null
tags: [hooks, maintenance, defensive]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

`scripts/maintenance/ensure-global-hooks.py` `find_plugin_root()` matches plugin keys via substring:

```python
if "sweetclaude" not in plugin_key.lower():
    continue
```

A fork or downstream plugin named `sweetclaude-extras@someone` would also match. Among matches, the script picks the most-recently-updated entry. If a user installed both the official plugin and a fork, the fork could be selected — possibly with a different `hooks-manifest.json` that causes the script to misclassify SweetClaude entries during cleanup.

**Origin:** Identified by the Opus QA caucus during 3.68.2 review. Filed 2026-05-13 by Carson Sweet.

**Severity:** theoretical. No known forks exist today. The risk only materializes if a fork ships its own manifest with the same hook basenames.

### Proposed fix

Replace the substring check with a prefix or equality check on the canonical plugin key:

```python
if not plugin_key.lower().startswith("sweetclaude@"):
    continue
```

Or use exact equality: `plugin_key.lower() == "sweetclaude@sweetclaude"`.

## Acceptance Criteria

- [ ] `find_plugin_root()` matches only the canonical SweetClaude plugin key, not forks or downstream plugins with "sweetclaude" in the name
- [ ] Existing test fixtures with `installed_plugins.json` containing `sweetclaude@sweetclaude` continue to work
- [ ] A test fixture with `sweetclaude-extras@user` alongside `sweetclaude@sweetclaude` returns the official plugin path

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
