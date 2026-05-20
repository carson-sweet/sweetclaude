---
id: CHORE-012
type: chore
title: "--force decision-log on non-implement phases"
status: new
priority: later
effort: s
epic: EP-010
tags: [self-hosting, sync, audit]
origin: STORY-300 adversarial-caucus
created: 2026-05-18
updated: 2026-05-18
---

# --force decision-log on non-implement phases

`--force` during a non-implement phase writes no audit entry because the decision-log condition gates on `$PHASE_LOWER = "implement"`. Once STORY-302 adds the test gate (which `--force` does NOT bypass), `--force` becomes meaningful only for the phase gate, so this is low-risk. But if future gates are added that `--force` does bypass, the missing audit trail becomes a gap. Either document that `--force` only logs during IMPLEMENT, or expand logging to all `--force` invocations.

## Origin

STORY-300 adversarial caucus finding.
