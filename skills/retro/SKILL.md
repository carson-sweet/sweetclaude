---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Review and maintain the improvement register."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or .sweetclaude/state/phase.yaml does not exist, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Retro

Review the improvement register. Surface what's still load-bearing. Retire what isn't. Write a summary.

---

## Step 1: Read the register

```bash
cat .sweetclaude/state/improvement-register.jsonl 2>/dev/null || \
cat .sweetclaude/state/improvement-register.md 2>/dev/null || \
echo "REGISTER_EMPTY"
```

If `REGISTER_EMPTY` or the register has no entries beyond a header row:

> "Improvement register is empty — nothing to review. Add a learning with `/sweetclaude:go` after completing a phase, or note one now: what should I do differently next session?"

If they provide one, append it to `improvement-register.md` and write the checkpoint summary (Step 4). Stop.

---

## Step 2: Parse and group entries

**If JSONL format** (`improvement-register.jsonl` exists):

Parse each line as a JSON object. Compute effective weight:
```
weeks_elapsed = (today - entry.date).days / 7
if entry.decay_exempt:
    effective_weight = entry.weight
else:
    effective_weight = entry.weight * (0.95 ** weeks_elapsed)
```

Group by type: `correction`, `confirmation`, `preference`, `pattern`.
Sort by effective_weight descending within each group.
Take top 5 overall by effective_weight.

**If Markdown format** (`improvement-register.md` exists):

Parse table rows (skip header and separator). Each row: `| # | Date | Type | Learning |`.
Take the last 5 entries (most recent = most relevant without weights).

---

## Step 3: Confirmation pass

Present entries one at a time in this format:

```
Learning {N} of {total_shown} — {type}
Added: {date}
"{entry text}"

Still applies? (y) keep  (n) retire  (u) update  (s) skip remaining
```

Wait for user response after each entry before showing the next.

**On `y`:** Keep as-is. Note confirmed.
**On `n`:** Mark retired. For JSONL: set `weight: 0` and add `retired: true`. For Markdown: note for removal.
**On `u`:** Ask "Updated text?" — replace entry text with user's response.
**On `s`:** Stop the confirmation pass, proceed to Step 4 with current results.

After all entries shown, or on `s`: summarize what happened:

```
Reviewed {N} entries:  {N_confirmed} confirmed · {N_retired} retired · {N_updated} updated
```

If any entries were retired or updated, write the changes back to the register file.

**For Markdown format — retiring entries:** Remove the retired rows from the table. Append them to `.sweetclaude/state/improvement-register-archive.md` (create if absent) with a `Retired: {date}` note.

---

## Step 4: Write checkpoint summary

Append to `.sweetclaude/state/checkpoint.md`:

```
---
Retro — {date}
Reviewed {N} entries. Confirmed: {N}. Retired: {N}. Updated: {N}.
Top learning in force: {text of highest-weight/most-recent confirmed entry, one line}.
Next: Continue with active work item, or run /sweetclaude:go.
---
```

If `checkpoint.md` doesn't exist, create it with just this entry.

---

## Step 5: Close

Report:

> "Retro complete. Register has {remaining_count} active entries.
> {If any retired: "Retired {N} stale entries."}
> {If register was empty or nearly empty: "Register is lean — good signal."}
> Checkpoint updated."

Do not suggest running any other skill. The user decides what's next.

---

## Rules

- Never delete entries — only retire them (move to archive or set weight: 0).
- One entry at a time in the confirmation pass — never batch.
- If the user corrects you during the retro (adds context, changes a learning), add that as a new entry before closing.
- If `improvement_register_count` from session state is 0 but the file exists with content, parse it anyway — the count may be stale.
