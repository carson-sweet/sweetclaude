---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Entry point for onboarding a project to SweetClaude — reads current state and hands off to the skill that owns the work."
---



# SweetClaude Init

Dispatcher. Init creates no files and writes no state. It reads the project's
current state and hands off to the skill that owns onboarding, migration, or
repair.

Onboarding itself belongs to `sweetclaude:library-load setup`, which detects project shape,
writes `.sweetclaude/state/sweetclaude.yaml`, and runs v4 storage setup.

---

## Step 0: Disabled check

```bash
ls .sweetclaude/disabled 2>/dev/null && echo "DISABLED" || echo "ENABLED"
```

If `DISABLED`, say:

> "SweetClaude is disabled for this project (`.sweetclaude/disabled` exists). Remove it to proceed."

Stop.

---

## Step 1: Framework-functional gate

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.sh" 2>/dev/null)"
echo "SC_PLUGIN_OK=${SC_PLUGIN_OK:-false}"
echo "SC_PLUGIN_REASON=${SC_PLUGIN_REASON}"
```

If `SC_PLUGIN_OK` is not `true`, the install itself is not healthy and no
onboarding decision can be trusted. Print `SC_PLUGIN_REASON` if set, then:

> "The SweetClaude install isn't healthy, so I can't safely onboard this project yet. Run `/sweetclaude:configure doctor` — it scans the install and repairs what it can."

Stop. Do not invoke setup, migration, or any project-mutating skill from this path.

---

## Step 2: State detection

```bash
python3 - << 'PY'
import pathlib, yaml

state = pathlib.Path('.sweetclaude/state')
sc = state / 'sweetclaude.yaml'
legacy = [p for p in (state / 'phase.yaml', state / 'skills.yaml') if p.exists()]

if not sc.exists():
    print('STATE=legacy' if legacy else 'STATE=none')
    if legacy:
        print('LEGACY_FILES=' + ','.join(p.name for p in legacy))
    raise SystemExit

try:
    d = yaml.safe_load(sc.read_text()) or {}
except Exception as exc:
    print('STATE=damaged')
    print(f'REASON=sweetclaude.yaml does not parse: {exc}')
    raise SystemExit

if not isinstance(d, dict):
    print('STATE=damaged')
    print('REASON=sweetclaude.yaml is not a mapping')
    raise SystemExit

schema = d.get('schema_version')
if schema not in (1, 2):
    print('STATE=damaged')
    print(f'REASON=unknown schema_version: {schema!r}')
    raise SystemExit

if (d.get('framework') or {}).get('setup_complete') is True:
    print('STATE=configured')
    print('NAME=' + str((d.get('project') or {}).get('name') or ''))
else:
    print('STATE=partial')
PY
```

---

## Step 3: Route

Route on `STATE`. Every branch either delegates to the owning skill or stops
with a concrete next command. Init never falls through to doing the work itself.

**`STATE=none`** — no SweetClaude state. This is the onboarding path.

Invoke `sweetclaude:library-load setup` via the Skill tool. Setup detects project shape
(new / existing codebase / messy-inherited), asks its own questions, writes
`sweetclaude.yaml`, runs v4 storage setup, and hands off to `sweetclaude:library-load _features`.

Stop after setup returns. Do not add anything on top of it.

**`STATE=legacy`** — v3 state files (`LEGACY_FILES`) with no `sweetclaude.yaml`.

Say:

> "This project has v3 state files ({LEGACY_FILES}) and no `sweetclaude.yaml`. That needs migration, not re-onboarding."

Invoke `sweetclaude:library-load _migrate` via the Skill tool. Stop.

**`STATE=partial`** — `sweetclaude.yaml` parses but `framework.setup_complete`
is not `true`. A previous onboarding did not finish.

Say:

> "Found a partial setup — `sweetclaude.yaml` exists but onboarding never completed. Resuming it."

Invoke `sweetclaude:library-load setup` via the Skill tool. Stop.

**`STATE=damaged`** — `sweetclaude.yaml` is present but unusable. Print `REASON`, then:

> "`.sweetclaude/state/sweetclaude.yaml` is present but unusable — {REASON}. This is a repair, not an initialization. Run `/sweetclaude:configure doctor`; it archives what it changes and can roll back."

Stop. Do not overwrite the file.

**`STATE=configured`** — healthy state, setup already complete.

Say:

> "{NAME} is already configured for SweetClaude — nothing to initialize. Run `/sweetclaude:go` to pick up work, or `/sweetclaude:status` to see where things stand."

Stop.

---

## Rules

- Init creates no directories, no state files, and no CLAUDE.md. Every one of
  those belongs to `sweetclaude:library-load setup`.
- Init never overwrites, repairs, or migrates state. Damaged state routes to
  `sweetclaude:library-load doctor`; v3 state routes to `sweetclaude:library-load _migrate`.
- `sweetclaude:library-load setup` is not user-invocable — always reach it through the Skill
  tool, never by telling the user to type `/sweetclaude:configure setup`.
- Init never runs product discovery. That belongs to
  `sweetclaude:library-load product-discovery`, reached through `/sweetclaude:go`.
- Ask no questions of your own. Setup owns the onboarding interview.
