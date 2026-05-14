---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Audit and repair SweetClaude's own configuration for this project."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Fix Config

Audit this project's SweetClaude setup. Fix what is broken.

**This skill changes SweetClaude configuration, not project code. Every change is proposed before applied.**

---

## Step 0: Check for YAML parse failure

If called because `sweetclaude.yaml` failed to parse (the `/sweetclaude` orchestrator routes here on parse error), run:

```bash
python3 -c "
import yaml
try:
    yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml'))
    print('YAML_OK')
except yaml.YAMLError as e:
    print(f'YAML_ERROR: {e}')
except FileNotFoundError:
    print('YAML_MISSING')
" 2>/dev/null
```

If `YAML_ERROR`, show the problematic area:
```bash
python3 -c "
import yaml
try:
    yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml'))
except yaml.YAMLError as e:
    if hasattr(e, 'problem_mark'):
        m = e.problem_mark
        lines = open('.sweetclaude/state/sweetclaude.yaml').readlines()
        start = max(0, m.line - 2)
        end = min(len(lines), m.line + 3)
        for i, l in enumerate(lines[start:end], start+1):
            marker = ' <<<' if i == m.line+1 else ''
            print(f'{i:3}: {l.rstrip()}{marker}')
    else:
        print(str(e))
" 2>/dev/null
```

> "Your \`sweetclaude.yaml\` has a syntax error at the line marked above. Most common cause: a manual edit introduced bad indentation or a special character."

Options for the user:
1. **Fix it for me** → attempt auto-repair: run `sweetclaude:_migrate` (will rebuild from archived files if present)
2. **Show me the file** → `cat .sweetclaude/state/sweetclaude.yaml`
3. **Restore from archive** → copy archive back and re-migrate:
   ```bash
   cp .sweetclaude/state/archive/phase.yaml.bak .sweetclaude/state/phase.yaml 2>/dev/null || true
   cp .sweetclaude/state/archive/skills.yaml.bak .sweetclaude/state/skills.yaml 2>/dev/null || true
   rm -f .sweetclaude/state/sweetclaude.yaml
   ```
   Then invoke `sweetclaude:_migrate`.

If `YAML_OK`, proceed to the existing steps below (the YAML is fine — the issue is something else).
If `YAML_MISSING`, say: "Looks like the config file is missing entirely. Let me set things up." Then invoke `sweetclaude:setup`.

---

## Step 1: Check .sweetclaude/ state exists

If neither `.sweetclaude/state/phase.yaml` nor `.sweetclaude/state/sweetclaude.yaml` exists:
> "SweetClaude is not set up for this project. Ask me to set it up."

Stop. Do not proceed.

---

## Step 2: Audit phase state vs reality

If `.sweetclaude/state/phase.yaml` does not exist (project is on the new `sweetclaude.yaml` schema), skip this step entirely.

Read `.sweetclaude/state/phase.yaml`. Then assess the actual project state:

1. Check git log — how many commits? How recent? What kind of work?
2. Check for implementation artifacts — source code, tests, builds
3. Check for product artifacts — PRD, product brief, specs, stories
4. Check for design artifacts — architecture docs, tech specs, ADRs
5. Check for strategy artifacts — concept, pain thesis, competitive analysis

Compare what the phase says vs what actually exists:

| phase.yaml says | Project actually has | Assessment |
|---|---|---|
| DISCOVER | Substantial code, tests, deployed | Phase is stale — should be IMPLEMENT or later |
| DISCOVER | PRD and architecture but no code | Phase should be PLAN or DESIGN |
| IMPLEMENT | Only a concept doc | Phase is ahead of reality |

If phase does not match reality, propose the correction:
> "phase.yaml says {current}. The project is actually in {recommended} based on: {evidence}. Update?"

---

## Step 3: Audit CLAUDE.md

Read the project's CLAUDE.md. Check:

1. **Repo structure section** — does it list directories that actually exist? Does it omit directories that do exist?
   - `ls` key directories and compare against what CLAUDE.md claims
   - Flag: directories listed but missing, directories that exist but are not listed

2. **Build/test/lint commands** — are they accurate?
   - Check package.json scripts, Makefile, pyproject.toml against what CLAUDE.md says
   - Try running the test command to see if it works

3. **SweetClaude section** — is it present and correct?
   - Should reference `.sweetclaude/state/sweetclaude.yaml` (the unified state file post-v3.18).
   - Should have the pre-flight / auto-fire invocation instruction (see 3a below).
   - Should NOT reference a "working repo".

   **3a. Auto-fire instruction patch** (relocated from the deleted `update/project-migration.md` Step 8c).

   Check whether the `## SweetClaude` section contains the text `invoke \`sweetclaude:status\` automatically at session start`. If missing, find the line that reads `Read .sweetclaude/state/sweetclaude.yaml` (or `Read .sweetclaude/state/phase.yaml` on pre-3.18 projects) and replace with:

   ```
   - Read `.sweetclaude/state/sweetclaude.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist. If `.sweetclaude/state/sweetclaude.yaml` exists and `.sweetclaude/disabled` does not exist, invoke `sweetclaude:status` automatically at session start.
   ```

   Propose the patch via AskUserQuestion; apply only on user approval. Report whether the patch was applied or already up to date.

4. **Project description** — is it still accurate?

For each issue found, propose a specific fix:
> "CLAUDE.md says {wrong thing}. Actual: {right thing}. Fix?"

---

## Step 4: Audit file locations

Use paths from pre-loaded session state: `paths.product_base`, `paths.strategy_base`, `paths.technical_base`, `paths.design_base`. If session state is unavailable, fall back to `.sweetclaude/product`, `.sweetclaude/strategy`, `.sweetclaude/technical`, `.sweetclaude/design`.

Check that artifacts are where SweetClaude expects them:

| Expected Location | Check |
|---|---|
| `.sweetclaude/state/` | phase.yaml, project.yaml, skills.yaml, decision-log, assumption-register, improvement-register, scope-changes |
| `docs/` or `{technical_base}/` | product-brief, prd, architecture, tech-spec, data-model, api-design, workflows (if they exist anywhere in the project) |
| `{product_base}/stories/` | user stories and .feature files (if they exist) |
| `{product_base}/backlog/` | BACKLOG-INDEX.md and item detail files (if product-parking-lot has been used) |
| `{product_base}/milestones/` | milestone detail files (if product-milestones has been used) |
| `{product_base}/sprints/` | sprint files (if product-sprint-plan has been used) |
| `{strategy_base}/` | concept, pain-thesis, ICP, competitive, etc. |
| `.sweetclaude/traceability/` | requirements-map, ripple-map |

If artifacts exist but in the wrong location (e.g., specs at `.sweetclaude/specs/` instead of `docs/`):

Use AskUserQuestion with these options:
- "Move it" — relocate {artifact} from {actual location} to {expected location}
- "Symlink it" — create a link at {expected location} pointing to {actual location}
- "Leave it" — update SweetClaude's reference to look at {actual location}

Do not assume. The user may have good reasons for the current location.

---

## Step 4b: Audit session-state.yaml

Check that the session-state file is present and valid:

| Check | Pass | Fail action |
|---|---|---|
| `session-state.yaml` exists | ✓ | "session-state.yaml missing — regenerate?" (run `hooks/generate-session-state.sh`) |
| ETHOS block present in session-state | ✓ | "ETHOS block missing from session-state.yaml — regenerate?" |
| `schema_version: 2` in phase.yaml | ✓ | "phase.yaml is schema v1 — migrate?" (already handled in Step 2 but confirm here) |
| `generate-session-state.sh` hook wired in settings.json or settings.local.json | ✓ | "Session state hook missing — add it?" |

To check session-state existence and ETHOS block:
```bash
[ -f .sweetclaude/state/session-state.yaml ] && echo "SESSION_STATE_EXISTS" || echo "SESSION_STATE_MISSING"
grep -q "ethos:" .sweetclaude/state/session-state.yaml 2>/dev/null && echo "ETHOS_PRESENT" || echo "ETHOS_MISSING"
python3 -c "
import json, os
settings_files = [
    os.path.expanduser('~/.claude/settings.json'),
    os.path.join(os.getcwd(), '.claude/settings.local.json')
]
found = False
for f in settings_files:
    try:
        d = json.load(open(f))
        all_cmds = ' '.join(
            h.get('command','')
            for ev in d.get('hooks',{}).values()
            for entry in ev
            for h in entry.get('hooks',[])
        )
        if 'generate-session-state' in all_cmds:
            found = True
            break
    except:
        pass
print('SESSION_HOOK_WIRED' if found else 'SESSION_HOOK_MISSING')
" 2>/dev/null
```

Propose a fix for each issue. Do not auto-apply.

---

## Step 5: Audit skills.yaml and onboarding state

**5a: Resolve base_path**

Read `.sweetclaude/artifact-privacy.yaml` → `categories.product.base_path`. If absent, use `.sweetclaude/artifacts/product` as fallback.

**5b: Bootstrap skills.yaml if needed**

Read `.sweetclaude/state/skills.yaml` if it exists.

For each data-owning skill, check whether it is present in `skills.yaml`. Use the following signals to infer state for any missing entry:

| Skill | Artifact signal (file exists → was in use) |
|---|---|
| `product-milestones` | `{product_base}/milestones/MILESTONES-INDEX.md` |
| `product-parking-lot` | `{product_base}/backlog/BACKLOG-INDEX.md` |
| `product-sprint-plan` | any file under `{product_base}/sprints/` |
| `user-personas` | `.sweetclaude/state/personas.yaml` |
| `product-user-stories` | any `US-*.md` under `{product_base}/stories/` |
| `document-corpus` | `.sweetclaude/state/corpus-pipeline.yaml` |
| `deploy-ship` | `.sweetclaude/state/deploy-config.yaml` |
| `retro` | any `RETRO-*.md` under `{product_base}/retros/` |
| `something-broke` | any `INC-*.md` under `{product_base}/incidents/` |
| `adopt` | *(no inference — write `enabled: false` if absent)* |

If `skills.yaml` is missing entirely: propose creating it (schema v2) with entries inferred from the above.
If entries are missing from an existing `skills.yaml`: propose adding them with the inferred state.

If `skills.yaml` exists with `schema_version: 1`: do **not** re-implement the migration here. Invoke the registry-driven migration runner (BL-065 refactor):

```bash
RUNNER=~/.claude/scripts/sweetclaude/migrations/runner.py
if [ -f "$RUNNER" ]; then
  python3 "$RUNNER" --project-dir . --file skills.yaml
else
  echo "Migration runner not found at $RUNNER. Run /sweetclaude:update to install the framework."
fi
```

The runner's registered handler (`scripts/migrations/skills_yaml_v1_to_v2.py`) is the single source of truth for the v1→v2 mapping. Same algorithm that previously lived inline here.

After the runner finishes, re-read `skills.yaml` and proceed to the bootstrap-of-missing-entries logic below.

> "skills.yaml is missing / has gaps. Based on artifacts on disk: backlog=active, milestones=uninitialized, … Write the missing entries?"

On user approval: write the missing entries using atomic write (temp file → rename). Use v2 schema:
- Data file exists → `status: active`, `last_changed_at: {today}`, `last_changed_by: migrated`
- Data file missing → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
Do not remove or modify entries that are already present and consistent.

**5c: Flag remaining mismatches**

After bootstrap, re-read `skills.yaml` and check for inconsistencies:

| Situation | Flag |
|---|---|
| `status: active` but no artifacts on disk | "Skill marked active but no artifacts found — partial deletion or failed onboard. Re-run onboard?" |
| `status: uninitialized` or `status: paused` but artifacts clearly exist on disk | "Artifacts found but skill not active — skills.yaml may be stale. Mark active?" |
| `status: paused` — data intact | No flag needed. Paused is an intentional state. |

Propose a fix for each mismatch. Do not auto-apply.

**5d: Offer onboarding for unenabled skills**

After resolving all mismatches, check `skills.yaml` for any skill with `enabled: false`.

If any exist, ask:
> "These skills are not yet set up for this project: {list}. Would you like to onboard any of them now? Enter keywords (e.g. 'milestones backlog') or 'none' to skip."

| Keyword | Skill |
|---|---|
| `milestones` | `product-milestones` |
| `backlog` | `product-parking-lot` |
| `sprint` | `product-sprint-plan` |
| `personas` | `user-personas` |
| `stories` | `product-user-stories` |
| `corpus` | `document-corpus` |
| `deploy` | `deploy-ship` |
| `retro` | `retro` |
| `incidents` | `something-broke` |
| `adopt` | `adopt` |

For each skill the user enables, invoke it with argument `onboard`. Complete each onboard before starting the next.

**5e: Artifact safety check for deprecated or deleted skills**

Read `skills.yaml`. For any skill with `status: deprecated` or any skill directory present in the installed location but absent from the source (detected via diff), scan artifact paths for live content that would be orphaned.

Use `base_path` from session-state (`paths.product_base`) or fall back to `.sweetclaude/artifacts/product`.

| Skill | Artifact path |
|---|---|
| `product-milestones` | `{base_path}/milestones/MILESTONES-INDEX.md` |
| `product-parking-lot` or `product-backlog` | `{base_path}/backlog/BACKLOG-INDEX.md` |
| `product-sprint-plan` | `{base_path}/sprints/` (any files) |
| `user-personas` | `.sweetclaude/state/personas.yaml` |
| `product-user-stories` | `{base_path}/stories/US-*.md` (any files) |
| `document-corpus` | `.sweetclaude/state/corpus-pipeline.yaml` |

If live content is found for a deprecated/deleted skill:

```
⚠ Skill marked deprecated but has live artifact content:
  {skill-name}: {artifact path} — {N} items found

  This content will become orphaned if the skill is removed.
  Inspect before deleting. Run /{skill-name} to review the content.
```

Propose no automatic action — surface only. User decides what to do with the content before any deletion proceeds.

---

## Step 6: Audit registers

Check if SweetClaude's tracking registers have content:
- `.sweetclaude/state/decision-log.md` — any entries?
- `.sweetclaude/state/assumption-register.md` — any entries?
- `.sweetclaude/state/improvement-register.md` — any entries?
- `.sweetclaude/state/scope-changes.md` — any entries?

If all are empty on a project with substantial history:
> "All SweetClaude registers are empty. The project has {N} commits and existing docs. Populate them from git history and existing docs? This gives SweetClaude context about past decisions."

If user says yes, scan git log and existing docs for:
- Decisions: architecture choices, technology selections, scope changes visible in commits
- Assumptions: things implied by the current implementation
- Scope: features that were added or removed based on commit history

Populate as draft entries marked `[retroactive]` for user review.

---

## Step 7: Audit hook registrations

Read the hooks manifest. Resolve path: `${CLAUDE_PLUGIN_ROOT}/hooks/hooks-manifest.json` if `CLAUDE_PLUGIN_ROOT` is set, otherwise the legacy install location at `$HOME/.claude/hooks/sweetclaude/hooks-manifest.json`.

Determine the current project version:
- If `.sweetclaude/state/sweetclaude.yaml` exists: v2
- If `.sweetclaude/state/phase.yaml` exists: v1
- Otherwise: unknown

**7a: Reconcile SweetClaude hook entries in settings.json**

After v3.68.2 the three preflight hooks (session-preflight, drift-gate, master-preflight) are plugin-native — Claude Code loads them from `hooks/hooks.json` automatically. The maintenance script's job is to keep `~/.claude/settings.json` clean of broken `${CLAUDE_PLUGIN_ROOT}` literals and stale plugin-version paths left over from earlier versions.

The script lives at `~/.claude/scripts/sweetclaude/maintenance/ensure-global-hooks.py` after a `sweetclaude:update` has run. Plugin-marketplace installs that have never run update only have it under the plugin cache — try both.

```bash
SCRIPT=~/.claude/scripts/sweetclaude/maintenance/ensure-global-hooks.py
if [ ! -f "$SCRIPT" ]; then
  SCRIPT=$(find ~/.claude/plugins/cache/sweetclaude -type f -name 'ensure-global-hooks.py' 2>/dev/null | head -1)
fi
if [ -z "$SCRIPT" ] || [ ! -f "$SCRIPT" ]; then
  echo "warning: ensure-global-hooks.py not found; skipping hook reconciliation" >&2
elif ! python3 "$SCRIPT"; then
  echo "warning: hook reconciliation failed — see error above" >&2
fi
```

Surface the script's output to the user. If it printed `cleaned:` lines (broken or stale entries removed), follow up with:
> "Cleaned up stale entries in ~/.claude/settings.json. **Restart Claude Code for these changes to take effect** — settings.json is read at session start. The hooks themselves are registered via the plugin's hooks.json and continue working."

If it printed `ok: hooks already up to date`, no further action needed.

**7b: Check project hooks (v2 only)**

Skip entirely for v1 projects — per-project hook registration is a v2 concept.

Filter manifest for entries where `required=true` and `scope="project"`. Verify each file is referenced in `.claude/settings.local.json` in the current project directory.

```bash
python3 -c "
import json, os
_sc_root = os.environ.get('CLAUDE_PLUGIN_ROOT','')
manifest_path = (os.path.join(_sc_root, 'hooks', 'hooks-manifest.json') if _sc_root
                 else os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'sweetclaude', 'hooks-manifest.json'))
manifest = json.load(open(manifest_path))
project_settings_path = os.path.join(os.getcwd(), '.claude/settings.local.json')
try:
    settings = json.load(open(project_settings_path))
except:
    settings = {}
all_cmds = ' '.join(
    h.get('command', '')
    for event_hooks in settings.get('hooks', {}).values()
    for entry in event_hooks
    for h in entry.get('hooks', [])
)
missing = [h for h in manifest['hooks']
           if h.get('required') and h.get('scope') == 'project' and h.get('event') and h['file'] not in all_cmds]
print('\n'.join(f\"{h['file']} ({h['event']})\" for h in missing) if missing else 'OK')
" 2>/dev/null
```

If any required project hooks are missing:
> "These required project hooks are not registered in .claude/settings.local.json: {list}. Add them?"

If user says yes, add the missing entries to `.claude/settings.local.json` under `hooks.{event}`. Create the file if it does not exist. Write atomically (temp file → rename). Do not remove or modify existing entries.

```bash
python3 - << 'PY'
import json, os, tempfile
project_settings_path = os.path.join(os.getcwd(), '.claude/settings.local.json')
_sc_root = os.environ.get('CLAUDE_PLUGIN_ROOT','')
manifest_path = (os.path.join(_sc_root, 'hooks', 'hooks-manifest.json') if _sc_root
                 else os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'sweetclaude', 'hooks-manifest.json'))

os.makedirs(os.path.dirname(project_settings_path), exist_ok=True)
try:
    with open(project_settings_path) as f:
        settings = json.load(f)
except:
    settings = {}
with open(manifest_path) as f:
    manifest = json.load(f)

all_cmds = ' '.join(
    h.get('command', '')
    for event_hooks in settings.get('hooks', {}).values()
    for entry in event_hooks
    for h in entry.get('hooks', [])
)

hooks_section = settings.setdefault('hooks', {})
for h in manifest['hooks']:
    if not h.get('required') or h.get('scope') != 'project' or not h.get('event') or h['file'] in all_cmds:
        continue
    event = h['event']
    cmd = h.get('command_path') or os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'sweetclaude', h['file'])
    entry = {'hooks': [{'type': 'command', 'command': cmd}]}
    matcher = h.get('matcher', '')
    if matcher and matcher != 'startup':
        entry['matcher'] = matcher
    hooks_section.setdefault(event, []).append(entry)

with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(project_settings_path),
                                  suffix='.tmp', delete=False) as tmp:
    json.dump(settings, tmp, indent=2)
    tmp_name = tmp.name
os.replace(tmp_name, project_settings_path)
print('OK')
PY
```

> "Project hooks registered in .claude/settings.local.json. New event-time hooks (SessionStart) require a new session to take effect; PreToolUse / PostToolUse / UserPromptSubmit hooks become active on next event in this session."

**7c: Strip stale hook registrations**

Hooks present in `settings.json` or `.claude/settings.local.json` that no longer appear in `hooks-manifest.json` are STALE — typically because the hook was removed in a framework version bump (e.g., `version-bump.sh` was removed in v3.66.0 but its registration lingers in old projects).

Scan both files for hook commands matching SweetClaude paths (`hooks/sweetclaude/` or `${CLAUDE_PLUGIN_ROOT}/hooks/`). For each, extract the hook script's basename and check whether `hooks-manifest.json` lists it as a `file` entry. If not present in the manifest → stale.

```bash
python3 - << 'PY'
import json, os, tempfile, re
_sc_root = os.environ.get('CLAUDE_PLUGIN_ROOT','')
manifest_path = (os.path.join(_sc_root, 'hooks', 'hooks-manifest.json') if _sc_root
                 else os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'sweetclaude', 'hooks-manifest.json'))
try:
    manifest = json.load(open(manifest_path))
except:
    print('MANIFEST_MISSING')
    raise SystemExit

known_files = {h.get('file') for h in manifest.get('hooks', [])}

def find_stale(settings_path):
    try:
        d = json.load(open(settings_path))
    except:
        return []
    stale = []
    for event, entries in (d.get('hooks') or {}).items():
        for entry in entries:
            for h in entry.get('hooks', []):
                cmd = h.get('command', '') or ''
                if 'hooks/sweetclaude/' not in cmd and '${CLAUDE_PLUGIN_ROOT}/hooks/' not in cmd:
                    continue
                base = cmd.rsplit('/', 1)[-1]
                if base and base not in known_files:
                    stale.append((event, base, cmd))
    return stale

for sp in [os.path.expanduser('~/.claude/settings.json'),
           os.path.join(os.getcwd(), '.claude/settings.local.json')]:
    if not os.path.exists(sp):
        continue
    s = find_stale(sp)
    for event, base, cmd in s:
        print(f"STALE|{sp}|{event}|{base}")
PY
```

For each STALE entry: propose removal via AskUserQuestion (one entry at a time, or batched per settings file). On user approval, rewrite the settings file with the stale entries removed (atomic temp+rename).

```bash
python3 - << 'PY'
import json, os, tempfile, sys
# Args: settings_path event base (one stale entry to remove)
settings_path, event, base = sys.argv[1:4]
with open(settings_path) as f:
    d = json.load(f)
new_entries = []
for entry in (d.get('hooks') or {}).get(event, []):
    kept_hooks = [h for h in entry.get('hooks', []) if not h.get('command','').rsplit('/',1)[-1] == base]
    if kept_hooks:
        entry['hooks'] = kept_hooks
        new_entries.append(entry)
if new_entries:
    d['hooks'][event] = new_entries
else:
    d['hooks'].pop(event, None)
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(settings_path), suffix='.tmp', delete=False) as tmp:
    json.dump(d, tmp, indent=2)
    tmp_name = tmp.name
os.replace(tmp_name, settings_path)
print('OK')
PY
```

If `hooks-manifest.json` does not exist:
> "hooks-manifest.json is missing from the hooks directory. This file should have been installed with SweetClaude. Run `install.sh` from the SweetClaude repo to restore it."

**7d: Reconcile `framework.installed_version` with reality**

`sweetclaude.yaml`'s `framework.installed_version` is written once during the `_migrate` consolidation and is not auto-updated thereafter. The authoritative source for the actually-installed plugin version is `~/.claude/plugins/installed_plugins.json`. If the two differ, the state file is stale.

```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml, json, os, tempfile
sc_path = sys.argv[1]
with open(sc_path) as f:
    d = yaml.safe_load(f) or {}
fw = d.get('framework', {})
recorded = fw.get('installed_version')
try:
    p = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [v for k, v in (p.get('plugins') or {}).items() if 'sweetclaude' in k.lower()]
    actual = entries[0][0].get('version') if entries and entries[0] else None
except Exception:
    actual = None
if actual and actual != recorded:
    print(f'VERSION_DRIFT|recorded={recorded}|actual={actual}')
    d.setdefault('framework', {})['installed_version'] = actual
    with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(sc_path), suffix='.tmp', delete=False) as tmp:
        yaml.safe_dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
        tmp_name = tmp.name
    os.replace(tmp_name, sc_path)
    print('UPDATED')
else:
    print('OK')
PY
```

If output starts with `VERSION_DRIFT`, report:
> "framework.installed_version was {recorded} but installed_plugins.json says {actual}. Updated sweetclaude.yaml to match reality."

If `OK`, silent.

---

## Step 8: Check for untracked SweetClaude files

Run `git status` on the project. Check if `.sweetclaude/` and `strategy/` have untracked or uncommitted files:

> "These SweetClaude files are not tracked in git: {list}. Commit them?"

---

## Step 9: Claude config audit

Invoke `sweetclaude:claude-config-audit` via the Skill tool. This scans CLAUDE.md, settings.json, and `~/.claude/rules/` for instructions that conflict with SweetClaude.

If `.sweetclaude/state/known-conflicts.md` already exists and has entries, note how many were previously logged so the report can show whether any new conflicts were found.

---

## Step 10: Report

Present a summary:

```
SweetClaude Config Audit — {project}
═════════════════════════════════════

Phase state:      {✓ correct | ⚠ stale → recommended fix}
Session state:    {✓ present and valid | ⚠ {N} issues}
CLAUDE.md:        {✓ accurate | ⚠ {N} issues found}
File locations:   {✓ correct | ⚠ {N} misplaced artifacts}
Skills / onboard: {✓ in sync | ⚠ {N} mismatches}
Registers:        {✓ populated | ⚠ empty on active project}
Hooks:            {✓ all registered | ⚠ {N} missing | hooks-manifest.json missing}
Git tracking:     {✓ clean | ⚠ {N} untracked files}
Config conflicts: {✓ none | ⚠ {N} known (see .sweetclaude/state/known-conflicts.md)}

→ Proposed fixes: {N}
```

List each proposed fix. Wait for user to approve individually or as a batch.

---

## Step 11: Feature configuration review

After all proposed fixes are resolved, check whether a feature review is warranted:

```bash
python3 - << 'PY'
import yaml

try:
    d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
except:
    d = {}

features = d.get('features', {})
keys = ['product_milestones', 'product_backlog', 'product_personas',
        'product_stories', 'document_corpus', 'usage_tracking', 'behavioral_regression']

enabled = sum(1 for k in keys
              if isinstance(features.get(k), dict) and features[k].get('status') == 'active')
unconfigured = sum(1 for k in keys
                   if not isinstance(features.get(k), dict)
                   or features[k].get('status') not in ('active', 'declined'))

# usage_tracking: check actual metrics config
try:
    mc = yaml.safe_load(open('.sweetclaude/metrics/config.yaml'))
    if mc.get('enabled', False) and features.get('usage_tracking', {}).get('status') != 'active':
        enabled += 1
        unconfigured = max(0, unconfigured - 1)
except:
    pass

print(f"ENABLED:{enabled}")
print(f"TOTAL:{len(keys)}")
print(f"UNCONFIGURED:{unconfigured}")
PY
```

If `UNCONFIGURED` > 0 or `ENABLED` < `TOTAL`:

Use **AskUserQuestion** (single-select):
> "This project has {ENABLED} of {TOTAL} features enabled. Want to review the feature setup?"
- **Yes** → invoke `sweetclaude:_features`
- **No** → stop

---

## Step 12: Configure plan directory

Ensure the plan directory exists and `plansDirectory` points to it in both project settings files. Run silently — no proposal needed.

```bash
mkdir -p .sweetclaude/plans
python3 - << 'PY'
import json, os, tempfile
os.makedirs('.claude', exist_ok=True)
for path in ['.claude/settings.json', '.claude/settings.local.json']:
    try:
        d = json.load(open(path))
    except:
        d = {}
    if d.get('plansDirectory') != '.sweetclaude/plans':
        d['plansDirectory'] = '.sweetclaude/plans'
        with tempfile.NamedTemporaryFile('w', dir='.claude', suffix='.tmp', delete=False) as tmp:
            json.dump(d, tmp, indent=2)
            tmp_name = tmp.name
        os.replace(tmp_name, path)
PY
```

---

## Step 13: v4 storage lint repairs

Run the v4 lint rules from `sweetclaude:_health` Step 3 inline. For each finding, present the repair recipe below and wait for user confirmation before applying.

### Repair recipes

**`counter-drift:<type>` (stored counter < highest ID seen)**

Auto-repair: set counter to max(observed, current).

```python
import pathlib, yaml, re

BACKLOG_BASE = pathlib.Path('docs/product/backlog')
INDEX_PATH = BACKLOG_BASE / 'INDEX.md'
raw = INDEX_PATH.read_text(encoding='utf-8')
parts = raw.split('---', 2)
index_fm = yaml.safe_load(parts[1]) or {}
counters = index_fm.setdefault('counters', {})

TYPE_PREFIX = {'story': 'STORY', 'bug': 'BUG', 'debt': 'DEBT', 'chore': 'CHORE'}
TYPE_DIRS = {'story': 'stories', 'bug': 'bugs', 'debt': 'debt', 'chore': 'chores'}

for typ, dir_name in TYPE_DIRS.items():
    prefix = TYPE_PREFIX[typ]
    max_seen = 0
    for p in (BACKLOG_BASE / dir_name).rglob('*.md'):
        m = re.match(rf'^{prefix}-(\d+)-', p.name)
        if m:
            max_seen = max(max_seen, int(m.group(1)))
    counters[typ] = max(counters.get(typ, 0), max_seen)

import datetime
index_fm['updated'] = datetime.date.today().isoformat()
INDEX_PATH.write_text(
    f"---\n{yaml.safe_dump(index_fm, default_flow_style=False, sort_keys=False).rstrip()}\n---{parts[2]}",
    encoding='utf-8'
)
```

> "Counter drift repaired. Counters set to max(observed, stored) for each type."

---

**`done-status-mismatch:<filename> is in done/ but has status=<status>`**

File is in `done/` but has an active status. Proposal: move the file back to the active directory.

Require user confirmation before moving. Do NOT auto-apply.

```python
import shutil, pathlib

# path = the file in done/
# active_dir = path.parent.parent  (e.g. docs/product/backlog/stories/)
active_dir = path.parent.parent
new_path = active_dir / path.name
shutil.move(str(path), str(new_path))
```

---

**`done-status-mismatch:<filename> has status=done/abandoned but is not in done/`**

File has a terminal status but is in the active directory. Proposal: move the file to `done/`.

Require user confirmation before moving. Do NOT auto-apply.

```python
import shutil, pathlib, datetime

fm['closed_date'] = fm.get('closed_date') or datetime.date.today().isoformat()
# write updated fm, then move
done_dir = path.parent / 'done'
done_dir.mkdir(exist_ok=True)
shutil.move(str(path), str(done_dir / path.name))
```

---

**`v3-files-present:<N> BL-NNN files remain`**

No auto-fix. Proposal: run `/sweetclaude:migrate`.

> "v3 story files found. Run `/sweetclaude:migrate` to migrate them to v4 storage. Migration creates a safety backup."

Do not modify or delete v3 files.

---

**`cross-location-duplicate-id:<id>`**

No auto-fix. Report only.

> "ID {id} appears in both the backlog and roadmap. This is a data integrity issue — resolve it manually by renaming one of the files."

---

## Step 14: Continue to bootstrap (no session restart required)

When `session-preflight.sh` fires `emit_heal`, it instructs Claude NOT to invoke `sweetclaude:bootstrap` in this session. That instruction is meant to prevent bootstrap from running against a broken config. Once `fix-sweetclaude` has resolved the issues that triggered the heal (including any v4 storage lint repairs from Step 13), that instruction is stale.

After completing the repair sequence above:

1. Announce briefly: `"Configuration repaired. Continuing to bootstrap so drift detection and any pending state work can run in this session — no session restart required."`
2. Invoke `sweetclaude:bootstrap` via the Skill tool.

Bootstrap will run Steps 1–8 in this same session. Step 5b runs the v4 hard-stop check; Step 5c runs the registry-driven drift scan via the runner and presents the hard-demand prompt if drift is found. The user does NOT need to start a new Claude Code session for the new system to engage. The earlier "new session required" advice (Step 7b) applies only to hooks that fire on events ALREADY consumed earlier in this session (specifically `SessionStart`); UserPromptSubmit / PreToolUse / PostToolUse hooks that were added or removed by Step 7b/7c will pick up on their next event in this session without restart.

Override the prior heal-context instruction: explicitly state that bootstrap is being invoked deliberately as a post-fix continuation.

---

## Rules

- **Propose, do not apply.** Every change needs user approval.
- **Do not move project files without asking.** The user may have reasons for current locations.
- **Retroactive register entries are drafts.** Mark them `[retroactive]` so the user knows they were not captured in real-time.
- **Do not judge the project.** This skill fixes SweetClaude configuration, not project quality.
- **v4 repairs apply only to `docs/product/backlog/`.** Never touch `.sweetclaude/product/backlog/`.
