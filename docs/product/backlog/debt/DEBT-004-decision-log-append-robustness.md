---
id: DEBT-004
type: debt
title: "Decision-log append robustness"
status: new
priority: later
effort: s
epic: EP-010
tags: [self-hosting, sync, code-quality]
origin: STORY-300 code-review
created: 2026-05-18
updated: 2026-05-18
---

# Decision-log append robustness

Check for trailing newline before appending a row to `decision-log.md` — if the file doesn't end with a newline, the new row merges with the last line. Also align decision-log entry text with the spec's prescriptive wording.

## Origin

STORY-300 code review nit N-2 and adversarial caucus finding (entry text diverges from spec).
