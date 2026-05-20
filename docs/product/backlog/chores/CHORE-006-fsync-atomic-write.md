---
id: CHORE-006
type: chore
title: Add fsync to ensure-global-hooks.py atomic write for crash safety
status: new
priority: later
effort: s
epic: null
milestone: null
sprint: null
tags: [hooks, maintenance, durability]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

`scripts/maintenance/ensure-global-hooks.py` `atomic_write_json()` uses `tempfile.NamedTemporaryFile` + `os.replace`. This is atomic at the rename level, but does not flush the file's data to disk before the rename. If the OS crashes between `os.replace` and the kernel's eventual fsync, the rename could be persisted while the data file content is lost or partial.

**Origin:** Identified by the Opus QA caucus during 3.68.2 review. Filed 2026-05-13 by Carson Sweet.

**Severity:** theoretical. The script runs in under a second; a power loss in that window is extraordinarily rare on a developer machine. Standard hygiene improvement for durability-conscious systems.

### Proposed fix

Before `os.replace`, flush the file and fsync:

```python
with tempfile.NamedTemporaryFile("w", dir=settings_dir, suffix=".tmp", delete=False) as tmp:
    tmp_name = tmp.name
    json.dump(data, tmp, indent=2)
    tmp.flush()
    os.fsync(tmp.fileno())
os.replace(tmp_name, path)
```

Optionally also fsync the containing directory after `os.replace` to ensure the rename is persisted.

## Acceptance Criteria

- [ ] `atomic_write_json` calls `tmp.flush()` and `os.fsync(tmp.fileno())` before `os.replace`
- [ ] All existing test cases pass unchanged
- [ ] No measurable performance regression on the script's normal runtime

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
