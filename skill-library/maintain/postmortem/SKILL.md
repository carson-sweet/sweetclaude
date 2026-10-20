---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Post-mortem authoring — timeline, root cause analysis, contributing factors, and action items."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Post-Mortem

Structured post-mortem authoring for incidents, hotfixes, and rollbacks. Produces a document and backlog items.

**Phase:** POST-MORTEM (follow-on from SHIP on hotfix, rollback, or something-broke work types).

---

## Step 1: Identify the originating incident

Check for a linked incident or hotfix work item. Look for decision-log entries that spawned this post-mortem:

```bash
grep -i 'POST-MORTEM required' .sweetclaude/state/decision-log.md 2>/dev/null | tail -5
```

```bash
git log --oneline -10 2>/dev/null
```

Ask the user:

> "Which incident or hotfix is this post-mortem for? I found these recent references:
> {decision-log entries if any}
>
> What was the incident? (One sentence — e.g. 'boot dead-zone caused by missing gate check after v4.3.2 deploy')"

If the user provides an existing work item ID (e.g. ISSUE-NNN), read it:

```bash
find .sweetclaude/product/backlog -name "${WORK_ITEM_ID}*" 2>/dev/null | head -1
```

Record: `INCIDENT_SUMMARY`, `INCIDENT_SEVERITY` (if known), `ORIGINATING_ITEM` (if linked).

---

## Step 2: Timeline of events

Walk through the timeline with the user. Present a template and ask them to fill or confirm:

> "Let's build the timeline. For each event, I need: **when** it happened and **what** happened. Walk me through from first signal to resolution."

Prompt specifically for:
1. **First signal** — when was the problem first noticed, by whom, how
2. **Investigation** — what was tried, what was ruled out
3. **Root cause identified** — when, how
4. **Fix applied** — what was done, when deployed
5. **Resolution confirmed** — when was it verified working

Build a markdown timeline table:

```markdown
| Time | Event |
|---|---|
| {time} | {event} |
```

Do not invent timeline entries. If the user is vague on timing, record approximate times and note them as approximate.

---

## Step 3: Root cause analysis (5 Whys)

Guide the user through the 5 Whys:

> "Now the root cause analysis. We'll use the 5 Whys — each answer becomes the next question. The goal is to get past the symptom to the systemic cause."

Start with:
> "**Why 1:** Why did {INCIDENT_SUMMARY} happen?"

After each answer, formulate the next "Why" from their response. Continue until:
- 5 levels deep, OR
- The user reaches a systemic/process-level cause before 5

Record each level:

```markdown
1. **Why did {X}?** — {answer}
2. **Why did {answer}?** — {answer}
...
```

After the chain completes, state the root cause:
> "**Root cause:** {the deepest why answer — the systemic issue}"

---

## Step 4: Contributing factors

Ask:

> "Beyond the root cause, what else contributed? Common categories:
> - **Process gaps** — missing tests, skipped reviews, no runbook
> - **Tooling gaps** — no monitoring, no alerts, no automated checks
> - **Knowledge gaps** — undocumented behavior, tribal knowledge
> - **Environmental factors** — time pressure, concurrent changes, unfamiliar code
>
> What contributed here?"

Record each factor with its category. If the user identifies none beyond the root cause, that's valid — record "No additional contributing factors identified."

---

## Step 5: Action items

For each contributing factor and the root cause, ask:

> "What changes would prevent this from happening again?"

For each action item, capture:
- **What** — the specific change
- **Type** — prevention (stops it happening) or detection (catches it faster)
- **Priority** — now, high, medium, low

If the fix applied during the incident was a workaround rather than a real fix, explicitly prompt:

> "The incident fix was applied under time pressure. Is it a permanent fix or a workaround that needs a proper follow-up?"

If workaround: add a tech-debt action item for the proper fix.

---

## Step 6: Write the post-mortem document

Determine the output location:

```bash
ls docs/postmortems/ 2>/dev/null && echo "DIR_EXISTS" || echo "NO_DIR"
```

If `DIR_EXISTS`: write to `docs/postmortems/{date}-{slug}.md`.
If `NO_DIR`: write to `docs/postmortems/{date}-{slug}.md` (create the directory).

Document format:

```markdown
# Post-Mortem: {INCIDENT_SUMMARY}

**Date:** {today}
**Severity:** {INCIDENT_SEVERITY or 'Not classified'}
**Originating item:** {ORIGINATING_ITEM or 'N/A'}
**Author:** {git user.name}

## Timeline

{timeline table from Step 2}

## Root Cause Analysis (5 Whys)

{5 whys chain from Step 3}

**Root cause:** {root cause statement}

## Contributing Factors

{factors from Step 4, bulleted with category}

## Action Items

| # | Action | Type | Priority |
|---|---|---|---|
{action items from Step 5}

## Lessons Learned

{one-paragraph synthesis: what this incident taught us about the system, the process, or both}
```

Present the draft to the user before writing:

> "Here's the post-mortem document. Review it — I'll write it after you confirm."

---

## Step 7: Create backlog items for action items

For each action item with priority `now` or `high`, create a backlog issue:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --query next-id --prefix ISSUE
```

Write each issue to `.sweetclaude/product/backlog/ISSUE-NNN-{slug}.md`:

```yaml
id: ISSUE-{NNN}
title: "{action item title}"
type: {bug-fix if prevention, enhancement if detection, tech-debt if workaround follow-up}
priority: {action item priority}
status: new
created: {today}
labels:
- post-mortem
- {originating item ID if known}
```

Body: link back to the post-mortem document.

Rebuild cache after creating items:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --rebuild
```

For `medium` and `low` priority items: list them in the post-mortem document but do not create backlog issues. Note: "Lower-priority items are documented in the post-mortem and can be promoted to the backlog when ready."

---

## Step 8: Update decision log and close

Append to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | POST-MORTEM complete for {INCIDENT_SUMMARY} | Document: {path}. {N} action items created. Root cause: {one-line root cause} | N/A |
```

Add a learning to the improvement register if the root cause or contributing factors revealed a systemic gap:

```bash
cat .sweetclaude/state/improvement-register.md 2>/dev/null | tail -1
```

If a systemic learning emerged, append:

```markdown
| {next #} | {today} | correction | {one-line learning from this incident} |
```

Report:

> "Post-mortem complete.
> - Document: {path}
> - Action items created: {list of ISSUE-NNN IDs, or 'none'}
> - Root cause: {one-line}
>
> The incident record is closed."

---

## Rules

- **Every section is required.** A post-mortem without a root cause analysis or without action items is incomplete.
- **No blame language.** Post-mortems document systemic causes, not individual mistakes. If the user uses blame language, reframe: "Let's capture that as a process gap — what systemic change would prevent it?"
- **The user owns the narrative.** Do not invent timeline events, root causes, or contributing factors. Ask, record, synthesize.
- **Action items must be concrete.** "Be more careful" is not an action item. "Add a pre-deploy smoke test for X" is.
- **Workaround detection is mandatory.** Always ask whether the incident fix was permanent or a workaround. If workaround, the tech-debt follow-up item is required, not optional.
- **Present the document before writing.** The user reviews the draft. Do not write to disk until confirmed.
