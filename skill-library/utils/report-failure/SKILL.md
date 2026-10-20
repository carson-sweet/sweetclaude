---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Write one structured failure report and root cause analysis to .sweetclaude/failure/. Invoke ONLY when the user explicitly asks to record/report a failure, mistake, or incident. Never auto-invoke."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Report Failure

Produce ONE failure report + root cause analysis for a single mistake or incident,
written to `.sweetclaude/failure/FR-NNN-<slug>.md`.

This skill runs only when the user explicitly asks for it. It does not trigger on
its own and does not run as part of any other workflow.

---

## Step 1: Prepare the directory and ignore rule

```bash
DIR=".sweetclaude/failure"
mkdir -p "$DIR"
# Add a gitignore rule only if the path is not already ignored.
if ! git check-ignore -q "$DIR" 2>/dev/null; then
  printf '\n# Local-only failure reports\n.sweetclaude/failure/\n' >> .gitignore
  echo "ADDED_GITIGNORE_RULE"
else
  echo "ALREADY_IGNORED"
fi
```

If the project is not a git repo, `git check-ignore` errors out and the rule is
appended — acceptable. Do not stage or commit `.gitignore` automatically.

## Step 2: Assign the next FR id

```bash
DIR=".sweetclaude/failure"
NEXT=$(ls "$DIR" 2>/dev/null | grep -oE 'FR-[0-9]+' | sort -t- -k2 -n | tail -1 \
  | grep -oE '[0-9]+' | sed 's/^0*//')
NEXT=$(( ${NEXT:-0} + 1 ))
printf 'FR-%03d\n' "$NEXT"
```

Use the printed id (e.g. `FR-007`) for the report. The slug is a short
kebab-case summary of the failure (e.g. `release-tag-missing`).

## Step 3: Gather the facts

Collect the information the template needs. If the failure happened in this
session, reconstruct it from the conversation and the repo. Otherwise interview
the user. Do not guess — every claim must be verifiable.

Required, with concrete specifics:

- **Approximate incident datetime, with time.** Anchor it on real evidence: the
  commit that introduced or corrected the problem (`git log --format='%h %cI %s'`),
  a memory file's birth time (`stat -f '%SB' -t '%Y-%m-%dT%H:%M:%S%z' <file>`), or
  a state-file/artifact timestamp. Never write "unknown" — approximate from
  available timestamps and state the basis.
- **Technical mechanism that failed.** The exact file, function, command,
  skill-description line, config key, or code path. Quote the offending
  text/code. Not "I failed to follow the rule" — the actual mechanism.
- **What I did wrong.** The decision or action, plainly.
- **Technical mechanism of the correction.** Every artifact used to fix it, with
  identifiers: corrective commit SHAs with ISO-8601 timestamps and what each
  diff changed; any memory file created (full path, birth datetime, and the
  verbatim operative line); any code/hook/test/config/rule change. If the fix
  was purely behavioral with no artifact, say that explicitly.
- **Evidence.** SHAs/tags/paths/CHANGELOG lines verified to exist, or an explicit
  statement that no repo trace exists and the report rests on memory/timestamps.
- **5-whys root cause.**
- **Impact** and **Severity** (Low/Medium/High) and **Confidence** (High/Medium/Low).

Verify every SHA before citing it: `git show -s --format='%h %cI %s' <sha>`.
Do not invent commits or IDs.

## Step 4: Write the report

Write `.sweetclaude/failure/FR-NNN-<slug>.md` using this exact template:

```markdown
# FR-NNN — <short title>

**Date of report:** <YYYY-MM-DD>
**Source:** <"Direct observation, this session" OR a memory file + its birth datetime OR other>
**Originating session:** <session id, or "not recorded">
**Approx. incident datetime:** <datetime WITH time> — <one clause stating the basis>
**Severity:** <Low | Medium | High>
**Status:** <Observed directly | Reconstructed from memory + repo archaeology (best-effort)>

## The rule
<the standing rule this failure violated, 1-2 sentences>

## Technical mechanism that failed
<exact file/function/command/skill-line/config/code path; quote offending text>

## What I did wrong
<the decision or action>

## Technical mechanism of the correction
<corrective commit SHAs + ISO timestamps and what changed; memory file path +
birth datetime + verbatim operative line; code/hook/test/config/rule changes.
If purely behavioral, say so.>

## Evidence found in repo
<SHAs with ISO timestamps, tags, paths, CHANGELOG lines — or an explicit
"No direct repo evidence; anchored on <timestamp source>.">

## Root cause analysis (5 whys)
1. ...
2. ...
3. ...
4. ...
5. Root cause: ...

## Impact
<what it cost: trust, wasted work, public artifact damage, etc.>

## Confidence
<High | Medium | Low> — <one line on corroboration>
```

Style: plain declarative sentences. Name actual files/IDs/commits. No metaphors,
no dramatic words ("brick", "catastrophic"), no time estimates.

## Step 5: Confirm

Report the path written and the FR id. Do not commit or push — the report is
local-only. If `.gitignore` was modified in Step 1, mention it so the user can
review the change. Stop. Do not offer follow-on actions.
