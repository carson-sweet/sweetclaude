---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:status
description: "Orient to the current project. Shows what phase you're in, what's been done, what's pending, and what the logical next step is. Use when starting a session, returning after a break, or asking 'where are we?'"
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Status

Show where the project stands. Reads state files directly — no background agent.

## Step 1: Schema check

Read `.sweetclaude/state/phase.yaml`. Check `schema_version`:
- If absent or `1`: warn — "Your `phase.yaml` is on schema v1. Run `/sweetclaude:update` to upgrade." Stop.
- If `2`: proceed.

## Step 2: Read state directly

Run all of these inline — do NOT spawn a background agent:

```bash
# Git context
git log --oneline -5
git status --short

# Checkpoint (last session handoff)
tail -25 .sweetclaude/state/checkpoint.md 2>/dev/null || echo "NO_CHECKPOINT"

# Scratch directory (continuation files)
ls scratch/ 2>/dev/null | grep -iE "checkpoint|continue|resume|handoff" | head -5

# RAG state (lightweight — existence check only)
ls .rag-index/lancedb/ 2>/dev/null | wc -l
find corpus/canonical/ -type f 2>/dev/null | wc -l

# Roadmap (milestones) — path from artifact privacy manifest
product_base=$(python3 -c "import yaml; d=yaml.safe_load(open('.sweetclaude/artifact-privacy.yaml')); print(d['categories']['product']['base_path'])" 2>/dev/null || echo "MANIFEST_MISSING")
if [ "$product_base" != "MANIFEST_MISSING" ]; then
  ls ${product_base}/milestones/MS-*.md 2>/dev/null | head -10
  grep -rh "\*\*Status:\*\*" ${product_base}/milestones/ 2>/dev/null | head -10
else
  echo "ARTIFACT_PRIVACY_NOT_CONFIGURED"
fi

# Versions
python3 -c "import json; d=json.load(open('$HOME/.claude/plugins/installed_plugins.json')); e=[v[0] for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower() and v]; print(e[0].get('version','?') if e else '?')" 2>/dev/null
python3 -c "import json; print(json.load(open('$HOME/dev/sweetclaude/package.json')).get('version','?'))" 2>/dev/null
```

Also read:
- `.sweetclaude/state/improvement-register.md` — does it exist and have entries beyond the header?
- `.sweetclaude/state/project-sop.md` — exists? (yes/no only — do not read full contents)

**Skills state check (read-only — do not write):**

```bash
cat .sweetclaude/state/skills.yaml 2>/dev/null || echo "SKILLS_YAML_MISSING"
```

If `SKILLS_YAML_MISSING` or `schema_version` is absent: set `SKILLS_STATUS = "not initialized — run /sweetclaude:fix-sweetclaude"`.

If `schema_version: 1`: set `SKILLS_STATUS = "schema v1 — run /sweetclaude:update to migrate"`.

If `schema_version: 2`: for each skill with `status: active`, check whether its artifact exists:

```bash
product_base=$(python3 -c "import yaml; d=yaml.safe_load(open('.sweetclaude/artifact-privacy.yaml')); print(d['categories']['product']['base_path'])" 2>/dev/null || echo ".sweetclaude/artifacts/product")
ls ${product_base}/milestones/MILESTONES-INDEX.md 2>/dev/null || echo "milestones_MISSING"
ls ${product_base}/backlog/BACKLOG-INDEX.md 2>/dev/null || echo "backlog_MISSING"
ls .sweetclaude/state/personas.yaml 2>/dev/null || echo "personas_MISSING"
find ${product_base}/stories/ -name "US-*.md" 2>/dev/null | head -1 || echo "stories_MISSING"
ls .sweetclaude/state/corpus-pipeline.yaml 2>/dev/null || echo "corpus_MISSING"
```

Collect each skill marked `active` where the corresponding artifact is `*_MISSING`. Store as `SKILLS_WARNINGS` list. If none: `SKILLS_WARNINGS = []`.

## Step 3: Present status

Use the data from Step 2. No other reads or commands.

Compute:
- **step_N / step_M** = 1-based position of active phase in workflow / total phases
- **Workflow line** = phases joined by ` → `, current phase wrapped in `*asterisks*`
- **SC_UPDATE** = if installed version ≠ latest version, append `→ v{latest} available — run /sweetclaude:update`
- **RAG_STATUS** = if lancedb count > 0: `{canonical_count} canonical docs · indexed` / else if canonical_count > 0: `{canonical_count} canonical docs · not indexed` / else: `not configured`
- **CHECKPOINT** = if checkpoint.md has content, show the `Next:` line from the last entry. If scratch files found, list them.
- **MILESTONES** = if `product_base` is `MANIFEST_MISSING`: show `not configured (run /sweetclaude:on)`. Otherwise: from the Status grep output: for each `active` milestone, show its filename slug and `active`. If none are active but milestone files exist, show `none active`. If no MS-*.md files exist, show `none`.
- **SKILLS_LINE** = if `SKILLS_STATUS` is set: show it. If `SKILLS_WARNINGS` is non-empty: show `⚠ {N} skill(s) marked active but missing artifacts: {list} — run /sweetclaude:fix-sweetclaude`. If both empty: omit the line entirely.

**If active work item exists:**

```
SweetClaude ACTIVE — {project name}
════════════════════════════════════

Version stage:  {version_stage}
Work item:      [{id}] {title} [{type}]
Phase:          {phase}  (step {N} of {M})
Workflow:       {workflow line}
Deference:      {deference_level}

Active milestones:
  {MILESTONES}

Last checkpoint:
  {Next: line from checkpoint.md, or "none — run a skill to create one"}

Scratch checkpoints:
  {list of matching scratch files, or "none"}

Recent activity:
  {last 5 commits}

Framework:
  SweetClaude:    v{installed} {SC_UPDATE}
  Doc Corpus RAG: {RAG_STATUS}
  {SKILLS_LINE — omit line if empty}
```

**If no active work item:**

```
SweetClaude ACTIVE — {project name}
════════════════════════════════════

Version stage:  {version_stage}
Work item:      (none)
Deference:      {deference_level}

Active milestones:
  {MILESTONES}

Last checkpoint:
  {Next: line from checkpoint.md, or "none"}

Scratch checkpoints:
  {list of matching scratch files, or "none"}

Recent activity:
  {last 5 commits}

Framework:
  SweetClaude:    v{installed} {SC_UPDATE}
  Doc Corpus RAG: {RAG_STATUS}
  {SKILLS_LINE — omit line if empty}
```

## Step 4: Suggest action

If no active work item: "Run `/sweetclaude:go` to pick up the next item."

If active work item: one concrete sentence on what to do next, derived from the checkpoint or phase. End with "Run `/sweetclaude:go` to continue."

## Step 5: Improvement register

If improvement register has entries, append:
> "I have {N} learnings from previous sessions. Run `/sweetclaude:go` and I'll apply them."

Do not list them here — keep status fast.
