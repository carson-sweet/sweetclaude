---
name: sweetclaude:status
description: "Orient to the current project. Shows what phase you're in, what's been done, what's pending, and what the logical next step is. Use when starting a session, returning after a break, or asking 'where are we?'"
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Status

Show where the project stands: what is done, what is open, what comes next.

## Process

### Step 1: Schema check (inline)

Read `.sweetclaude/state/phase.yaml`. Check `schema_version`:
- If absent or `1`: warn the user and stop — "Your `phase.yaml` is on schema v1. Run `/sweetclaude:update` to upgrade." Do not proceed to Step 2.
- If `2`: proceed.

### Step 2: Gather data (background)

Spawn a background agent using the Agent tool with **no subagent_type** (this creates a fork — its tool calls are invisible to the main conversation). Pass this exact prompt:

---
Read the following files and run the following commands from the current working directory. Return ONLY structured data — no prose, no explanations.

**Reads:**
1. `.sweetclaude/state/phase.yaml` — full contents
2. `.sweetclaude/state/improvement-register.md` — does it exist and have entries beyond the header row?
3. `.sweetclaude/state/project-sop.md` — full contents if it exists (return "none" if absent)

**Commands:**
4. `git log --oneline -7`
5. `git status --short`
6. `cat ~/.claude/plugins/installed_plugins.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); plugins=d.get('plugins',{}); e=[entry for k,v in plugins.items() if 'sweetclaude' in k.lower() for entry in v]; print(e[0].get('version','?') if e else '?')" 2>/dev/null`
7. `cat ~/dev/sweetclaude/package.json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null`
8. `cat .rag-index/.index-manifest.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); files=d.get('files',{}); print(len(files)); print(max((v.get('mtime','') for v in files.values()), default='never'))" 2>/dev/null`
9. `find corpus/canonical/ -type f 2>/dev/null | wc -l`
10. `ls .rag-index/lancedb/ 2>/dev/null | wc -l` — detect lancedb data even without a manifest
11. `cat .mcp.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); servers=d.get('mcpServers',{}); rags=[(k,v.get('env',{}).get('BASE_DIR','?')) for k,v in servers.items() if 'rag' in k.lower() or 'rag' in str(v.get('env',{})).lower()]; print('\n'.join(f'{k}|{b}' for k,b in rags) if rags else 'none')" 2>/dev/null`
12. `find docs/milestones/ -name "MS-*.md" 2>/dev/null` — for each file found, read it and extract: id, title, Status: field, count of `[x]` checked vs `[ ]` unchecked criteria checkboxes.
13. `find ~/.claude/skills/ -maxdepth 1 -iname "bmad*" -o -maxdepth 1 -iname "bmad" 2>/dev/null | head -5` — for BMAD detection
14. `cat ~/.claude/plugins/installed_plugins.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); plugins=d.get('plugins',{}); bmad=[k for k in plugins.keys() if 'bmad' in k.lower()]; print('\n'.join(bmad) if bmad else 'none')" 2>/dev/null`

**Return this exact structure:**
```
SC_INSTALLED: {version from command 6}
SC_LATEST: {version from command 7}
GIT_LOG:
  {output of command 4, one line per commit}
GIT_DIRTY: {yes if command 5 has output, no if empty}
RAG_FILES: {count from command 8, line 1}
RAG_LAST: {date from command 8, line 2}
LANCEDB_EXISTS: {yes if command 10 > 0, no otherwise}
RAG_MCPS: {output of command 11 — "name|base_dir" pairs or "none"}
CANONICAL_DOCS: {count from command 9}
HAS_IMPROVEMENTS: {yes/no}
SOP: {full contents of project-sop.md from read 3, or "none"}
MILESTONES:
  {id} | {title} | {Status value} | {met}/{total}
  ...
BMAD_SKILLS: {combined output of commands 13 and 14 — paths and plugin names found, or "none"}
PHASE_YAML:
  {full yaml contents from read 1}
```

**Important:** RAG is "active" if RAG_FILES > 0 OR LANCEDB_EXISTS is yes. Do not report RAG as inactive just because the manifest is missing — lancedb data without a manifest means the index was built outside SweetClaude.
---

Wait for the background agent to complete. Use its returned data block for Step 3.

### Step 3: Present status

Using the data returned by the background agent, render the appropriate template.

If `active_work_item.type`, `.phase`, and `.workflow` are all non-null:

Compute:
- **step_N** = 1-based position of `active_work_item.phase` in `active_work_item.workflow`
- **step_M** = total phases in workflow
- **Workflow line** = phases joined by ` → `, current phase wrapped in `*asterisks*`

```
SweetClaude ACTIVE — {project name}
════════════════════════════════════

Version stage:  {version_stage}
Work item:      [{active_work_item.id}] {active_work_item.title} [{active_work_item.type}]
Phase:          {active_work_item.phase}  (step {step_N} of {step_M})
Workflow:       {workflow line}
Deference:      {deference_level}

Done:
  - {completed artifact or milestone, from git log and milestone data}
  - ...

In progress:
  - {artifact or task currently open}
  - ...

Active milestones:
  - {MS-XXX  Title        met/total criteria}
  (omit section if no active milestones)

Next:
  → {logical next step based on phase and exit criteria}

Recent activity:
  {last 3-5 commits from GIT_LOG}

Framework:
  SweetClaude:  v{SC_INSTALLED}{" → v{SC_LATEST} available — run /sweetclaude:update" if SC_INSTALLED != SC_LATEST else " (up to date)"}
  Doc Corpus RAG:   {if RAG_FILES > 0: "{CANONICAL_DOCS} canonical docs · last indexed {RAG_LAST} · {RAG_FILES} files indexed · run /sweetclaude:document-corpus to update" elif LANCEDB_EXISTS: "{CANONICAL_DOCS} canonical docs · indexed (no manifest) · run /sweetclaude:document-corpus to rebuild manifest" elif CANONICAL_DOCS > 0: "{CANONICAL_DOCS} canonical docs · not indexed · run /sweetclaude:document-corpus to set up" else "not configured — run /sweetclaude:document-corpus to set up"}
  {if RAG_MCPS != "none" and SOP == "none": "⚠ RAG MCPs detected in .mcp.json but no project SOP — run /sweetclaude:on to register them"}
```

If `active_work_item` is absent or all fields are null:

```
SweetClaude ACTIVE — {project name}
════════════════════════════════════

Version stage:  {version_stage}
Work item:      (none)
Deference:      {deference_level}

Recent activity:
  {last 3-5 commits from GIT_LOG}

Framework:
  SweetClaude:  v{SC_INSTALLED}{" → v{SC_LATEST} available — run /sweetclaude:update" if SC_INSTALLED != SC_LATEST else " (up to date)"}
  Doc Corpus RAG:   {if RAG_FILES > 0: "{CANONICAL_DOCS} canonical docs · last indexed {RAG_LAST} · {RAG_FILES} files indexed · run /sweetclaude:document-corpus to update" elif LANCEDB_EXISTS: "{CANONICAL_DOCS} canonical docs · indexed (no manifest) · run /sweetclaude:document-corpus to rebuild manifest" elif CANONICAL_DOCS > 0: "{CANONICAL_DOCS} canonical docs · not indexed · run /sweetclaude:document-corpus to set up" else "not configured — run /sweetclaude:document-corpus to set up"}
  {if RAG_MCPS != "none" and SOP == "none": "⚠ RAG MCPs detected in .mcp.json but no project SOP — run /sweetclaude:on to register them"}
```

**BMAD notice (append after template if BMAD_SKILLS is not "none"):**

```
---
Notice: BMAD skills detected ({BMAD_SKILLS}). BMAD is no longer needed — SweetClaude has all orchestration built in. Remove them to reduce confusion? (yes to remove, no to keep)
```

If the user says yes: remove the detected BMAD directories/plugins using `rm -rf` on the detected paths. Confirm what was removed.
If the user says no: acknowledge and continue. Do not ask again this session.

### Step 4: Suggest action

If no active work item: suggest running `/sweetclaude:go` to pick up the next item.

If an active work item exists, propose one concrete next action in plain language. Tailor it using `active_work_item.entry_category`:
- **cold-start** or **mid-project-planned**: describe the next artifact or milestone to produce
- **mid-project-reactive**: lead with urgency — describe what needs to be resolved first
- **absent or unrecognized**: default to cold-start behavior

> "Next: {plain-language description}. Run `/sweetclaude:go` to continue."

Do not name internal skills in the output. `/sweetclaude:go` is the only command the user needs.
Do not start doing the work. Orient and suggest. The user decides what to do.

### Step 5: Doc corpus offer

**If RAG is fully active** (RAG_FILES > 0), append after the action suggestion:
> "Doc corpus is active ({CANONICAL_DOCS} docs, last indexed {RAG_LAST}). Want me to check if it's up to date? (`/sweetclaude:document-corpus`)"

**If lancedb exists but no manifest** (LANCEDB_EXISTS yes, RAG_FILES = 0), append:
> "A RAG index exists but has no manifest — SweetClaude can't track its state. Want me to rebuild the manifest? (`/sweetclaude:document-corpus`)"

**If RAG MCPs exist but no project SOP** (RAG_MCPS not "none", SOP = "none"), append:
> "I see RAG MCPs configured in `.mcp.json` that I don't have records for. Want me to register them in the project SOP so I know how to use them? (`/sweetclaude:on`)"

Do not run anything automatically — offer only.
