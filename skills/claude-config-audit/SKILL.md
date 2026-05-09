---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Scan the CLAUDE.md hierarchy, settings.json, and ~/.claude/rules/ for instructions that conflict with SweetClaude."
---

# SweetClaude Claude Config Audit

Scan Claude Code configuration for instructions that conflict with SweetClaude. Detection is pattern-based — deterministic, auditable, no semantic drift.

**Every conflict is raised to the user. Nothing is changed without approval.**

---

## Step 0: Backup

Write a backup of the project CLAUDE.md before scanning anything:

```bash
if [ -f CLAUDE.md ]; then
  datetime=$(date '+%Y-%m-%d %H:%M:%S')
  {
    echo "# Backed up by SweetClaude — $datetime"
    echo "# Original: CLAUDE.md"
    echo "# This file is a safety copy created before claude-config-audit ran."
    echo "# It is not active configuration. Delete when no longer needed."
    echo ""
    cat CLAUDE.md
  } > _CLAUDE.md.bak.tmp && mv _CLAUDE.md.bak.tmp _CLAUDE.md.bak
  echo "BACKED_UP $datetime"
else
  echo "CLAUDE_MISSING"
fi

if [ -f ~/.claude/CLAUDE.md ]; then
  datetime=$(date '+%Y-%m-%d %H:%M:%S')
  {
    echo "# Backed up by SweetClaude — $datetime"
    echo "# Original: ~/.claude/CLAUDE.md"
    echo "# This file is a safety copy created before claude-config-audit ran."
    echo "# It is not active configuration. Delete when no longer needed."
    echo ""
    cat ~/.claude/CLAUDE.md
  } > ~/.claude/_CLAUDE.md.bak.tmp && mv ~/.claude/_CLAUDE.md.bak.tmp ~/.claude/_CLAUDE.md.bak
  echo "GLOBAL_BACKED_UP"
fi
```

Tell the user:
> "Backed up CLAUDE.md → _CLAUDE.md.bak. Proceeding with audit."

---

## Step 1: Collect sources

Read each source that exists:

```bash
echo "=== PROJECT CLAUDE.md ==="
[ -f CLAUDE.md ] && cat -n CLAUDE.md || echo "MISSING"

echo "=== GLOBAL CLAUDE.md ==="
[ -f ~/.claude/CLAUDE.md ] && cat -n ~/.claude/CLAUDE.md || echo "MISSING"

echo "=== PROJECT SETTINGS ==="
[ -f .claude/settings.json ] && cat .claude/settings.json || echo "MISSING"

echo "=== GLOBAL SETTINGS ==="
[ -f ~/.claude/settings.json ] && cat ~/.claude/settings.json || echo "MISSING"

echo "=== USER RULES (non-SweetClaude) ==="
ls ~/.claude/rules/ 2>/dev/null | grep -v '^sweetclaude$' | while read f; do
  if [ -f "$HOME/.claude/rules/$f" ]; then
    echo "--- $f ---"
    cat "$HOME/.claude/rules/$f"
  fi
done
```

For `@`-referenced files in CLAUDE.md: scan for lines matching `@path/to/file` and read each:

```bash
grep -oE '@[^ ]+' CLAUDE.md 2>/dev/null | while read ref; do
  path="${ref#@}"
  if [ -f "$path" ]; then
    echo "=== REFERENCED: $path ==="
    cat -n "$path"
  fi
done
```

If no sources found (no CLAUDE.md, no settings.json, no rules):
> "No Claude configuration files found to audit. Nothing to check."
Stop.

---

## Step 2: Detect conflicts

Scan the collected content for the following patterns. Track: source file, line number (or "settings key"), exact matched text, severity, which SweetClaude rule it conflicts with.

### FATAL — break SweetClaude functionality

**F1 — allowedTools excludes Agent, Bash, or Write**

In any `settings.json`, if `allowedTools` is present and any of `Agent`, `Bash`, or `Write` are absent from its value array:
- Conflicts with: skill spawning (Agent), hook execution (Bash), file generation (Write)
- Impact: SweetClaude skills and hooks will not function

**F2 — PostToolUse hook targets test/spec files (non-SweetClaude command)**

In any `settings.json`, a PostToolUse hook with a matcher containing `test` or `spec` and a command that does not contain `sweetclaude` or `${CLAUDE_PLUGIN_ROOT}`:
- Conflicts with: test-guardian hook
- Impact: test-guardian and the foreign hook both intercept test file writes

**F3 — PostToolUse hook runs test suite directly**

In any `settings.json`, a PostToolUse hook command containing any of: `npm test`, `pytest`, `cargo test`, `jest `, `vitest`, `go test`:
- Conflicts with: auto-test-runner hook
- Impact: test suite runs twice on every file write

**F4 — Skip-hooks instructions**

In any text file, patterns (case-insensitive): `--no-verify`, `skip hooks`, `bypass hooks`, `skipHooks`:
- Conflicts with: SweetClaude enforcement layer (test-guardian, artifact-guardian, phase-dwelling-guard)
- Impact: SweetClaude's behavioral enforcement cannot function if hooks are bypassed

### WARNING — degrade SweetClaude features

**W1 — Time-estimate phrases**

Patterns (case-insensitive, in text files): `estimate`, `how long will`, `days to complete`, `weeks to complete`, `sprint velocity`, `story points`:
- Conflicts with: interaction-model.md no-time-estimates rule
- Impact: Time-estimate questions will be answered rather than deflected

**W2 — Comment-everywhere instructions**

Patterns: `always add comments`, `comment every`, `document all methods`, `add docstrings`, `comment all functions`:
- Conflicts with: no-comments-by-default rule
- Impact: AI-generated code will have unnecessary comment noise

**W3 — Skip-tests instructions**

Patterns: `skip tests`, `tests optional`, `no TDD`, `don't write tests`, `tests are not required`:
- Conflicts with: TDD enforcement
- Impact: TDD discipline will not be enforced

**W4 — Skip-confirmation instructions**

Patterns: `proceed without asking`, `don't ask for approval`, `skip confirmation`:
- Conflicts with: deference levels and AskUserQuestion discipline
- Impact: User approval steps will be skipped

**W5 — Conflicting commit format**

Instructions specifying emoji prefixes in commit messages (e.g. `✨ add feature`, `🐛 fix bug`) or any format that conflicts with `type(scope): message` conventional commits:
- Conflicts with: conventional commits rule
- Impact: Commit messages will not follow conventional-commits format

### INFO — redundant (already covered by SweetClaude)

**I1 — Duplicate phase-dwelling rule**

Patterns: `never ask if ready to move`, `don't push for advancement`, `user decides when phase is done`:
- Already covered by: `~/.claude/rules/sweetclaude/interaction-model.md`

**I2 — Duplicate proposal-mode rule**

Patterns: `propose don't ask`, `give recommendation with reasoning`, `propose not ask`:
- Already covered by: interaction-model.md

---

## Step 3: Reconcile each conflict

Load existing known-conflicts.md:

```bash
cat .sweetclaude/state/known-conflicts.md 2>/dev/null && echo "---KNOWN_LOADED---" || echo "NO_KNOWN_CONFLICTS"
```

Process all conflicts in order: FATALs first, then WARNINGs, then INFOs.

For each conflict found that is **not already in known-conflicts.md** (match by source + exact text):

Present:
```
⚠ [{FATAL|WARNING|INFO}] Conflict detected
  Location: {file}:{line or "settings key"}
  Found:    "{exact matched text}"
  Conflicts with: {SweetClaude rule or feature}
  Impact:   {what breaks or degrades}
```

Use AskUserQuestion with these options:
- **Adopt SweetClaude's rule** — remove or disable the conflicting instruction (I'll make the edit)
- **Keep existing** — {specific feature} will not function correctly for this project (I'll log this)
- **Keep both** — log as known conflict, warn on `sweetclaude:status`

If user picks **Adopt SweetClaude's rule**: edit the source file to remove or comment out the line. Report what changed.

If user picks **Keep existing** or **Keep both**: append to `.sweetclaude/state/known-conflicts.md`. If the file does not exist, create it first:

```markdown
# Known Conflicts

Conflicts between existing Claude configuration and SweetClaude, accepted by the user.
Maintained by `sweetclaude:claude-config-audit`.
```

Entry format:
```markdown
## Known Conflict — {date}
**Source:** {file}:{line}
**Instruction:** "{text}"
**Conflicts with:** {SweetClaude feature}
**Decision:** {keep existing | keep both}
**Impact:** {what degrades}
```

After all FATAL conflicts are processed, if any were not adopted:
> "FATAL conflicts will prevent SweetClaude from functioning correctly. Resolve these before proceeding."

---

## Step 4: Report

```
Claude Config Audit — {project or current directory}
════════════════════════════════════════════════════

Sources scanned:    {N} files
Conflicts found:    {total} ({FATAL} fatal · {WARNING} warnings · {INFO} info)
Resolved (adopted): {N}
Known conflicts:    {N logged}

{If FATAL=0}:  ✓ No fatal conflicts — SweetClaude will function correctly.
{If FATAL>0}:  ⚠ {N} fatal conflict(s) unresolved — SweetClaude features will be impaired.
```

If known-conflicts.md has entries:
> "Known conflicts are logged in `.sweetclaude/state/known-conflicts.md`. `sweetclaude:status` will remind you these exist."

---

## Rules

- Pattern-based only. No semantic analysis. If it doesn't match a listed pattern, it is not a conflict.
- Never flag files inside `~/.claude/rules/sweetclaude/` — those are SweetClaude's own rules, not conflicts.
- Never auto-apply changes. Every edit requires user approval.
- Run Step 0 (backup) before reading any content, always.
- INFO findings are informational — no action required, but surfaced for awareness.
- If an entry already exists in known-conflicts.md (same source + same text), skip it — the user already decided.
