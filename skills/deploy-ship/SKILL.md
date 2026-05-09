---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "SHIP phase skill."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Deploy Ship

Guides the final push to production. Ensures no project ships without a checklist, rollback plan, or smoke test.

---

## Step 1: Verify VERIFY is complete

Read `active_work_item` from session state. If `phase` is not `SHIP`:
> "The active work item is in {phase}, not SHIP. Complete VERIFY first — all tests must be passing, code review done, and docs updated before shipping."
Stop.

Check VERIFY exit criteria by scanning recent context:
- All tests passing (confirm: `git log --oneline -3` for a recent test run commit, or ask)
- Code review complete (ask if not confirmed in session context)
- No critical findings open

If VERIFY clearly incomplete, surface what's missing. Do not soft-bypass.

---

## Step 2: Scan deployment configuration

```bash
# Deployment config files
ls Dockerfile docker-compose.yml fly.toml render.yaml railway.json \
   .replit Procfile app.yaml kubernetes/ helm/ netlify.toml vercel.json \
   .github/workflows/deploy*.yml .github/workflows/release*.yml 2>/dev/null

# Runtime detection
ls package.json pyproject.toml Cargo.toml go.mod pom.xml build.gradle Gemfile 2>/dev/null

# Existing run/build commands
cat package.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); s=d.get('scripts',{}); print({k:v for k,v in s.items() if k in ['start','build','preview','prod']})" 2>/dev/null || true
cat Procfile 2>/dev/null
cat fly.toml 2>/dev/null | grep -E "command|build|deploy" | head -10 || true

# Break-glass notes / runbook
ls docs/runbook.md RUNBOOK.md docs/RUNBOOK.md .sweetclaude/state/runbook.md 2>/dev/null
```

---

## Step 3: Confirm deployment target and commands

Based on the scan, present what was found. If no deployment config exists, ask:
> "No deployment configuration found. Where are you deploying?
> - **Static hosting** (Vercel, Netlify, GitHub Pages) — needs build command + output directory
> - **App platform** (Fly.io, Railway, Render) — needs start command + Dockerfile or Procfile
> - **VM / VPS** — needs start command, process manager (systemd, PM2)
> - **Container registry** — needs Dockerfile + build command
> - **Managed platform** (Heroku, App Engine) — needs Procfile or configuration file"

Wait for answer. Then confirm:
> "**Run command:** `{start command}`
> **Build command:** `{build command or N/A}`
> **Target:** {platform}
>
> Is this right, or does it need updating?"

Fix if wrong.

---

## Step 4: Pre-ship checklist

Work through each item explicitly. Record responses.

**The checklist (confirm each, one by one):**

1. **All acceptance criteria met** — does the shipped code satisfy everything in the work item's AC?
2. **All tests passing** — last test run green? (check git history or ask)
3. **No secrets in the diff** — scan the changes going out:
   ```bash
   git diff HEAD~5..HEAD -- . 2>/dev/null | grep -icE "(SECRET|API_KEY|PASSWORD|TOKEN|PRIVATE_KEY|CREDENTIALS)" || echo "0"
   ```
   Report the count only. If count > 0, stop and tell the user "N potential secret patterns found in the diff — review before shipping." Never output the matched lines.
4. **Changelog / release notes** — exists and current? (`ls CHANGELOG.md CHANGELOG.rst CHANGELOG.txt docs/changelog.md 2>/dev/null`)
5. **Rollback plan confirmed** — what is the rollback if this goes wrong? Get a one-line answer.
6. **Break-glass notes exist** (GA+ only) — runbook present? (from Step 2 scan)
7. **Monitoring active** — will you know within 5 minutes if this deploy breaks something?

If any item fails: stop and surface it. Do not proceed with a failed checklist item unless the user explicitly says "I've addressed this — continue."

Log the checklist result to `.sweetclaude/state/decision-log.md`:
```markdown
| {next #} | {today} | Pre-ship checklist for {work item id} | All items confirmed OR [list what was waived with reason] | N/A |
```

---

## Step 5: Execute or guide the deploy

If deployment is automated (CI/CD pipeline detected):
> "Your deployment will be triggered by pushing to `{branch}`. Is the branch ready to push?"

If manual deployment:
Present the commands the user needs to run. Do not run destructive deployment commands automatically — show them and ask for confirmation.

Tell the user: "Run your deploy now. I'll wait — come back when it's live or if something goes wrong."

Wait for the user to confirm deployment is done.

---

## Step 6: Smoke test

Once the user confirms deployment is complete, run through the smoke test:

> "Let's confirm the deploy is healthy. Walk me through:
> 1. Can you reach the live URL/endpoint?
> 2. Does the core workflow work? (describe what you tested)
> 3. Are there any errors in the logs?"

If the user reports issues: transition to `sweetclaude:something-broke`. Say:
> "Sounds like the deploy has a problem. Let's triage it. Run `/sweetclaude:something-broke`."

If smoke test passes, log result:
```markdown
| {next #} | {today} | Smoke test passed for {work item id} | {brief description of what was tested} | N/A |
```

---

## Step 7: Close out the work item

Update `.sweetclaude/state/phase.yaml`:
```yaml
active_work_item:
  id: ~
  type: ~
  workflow: []
  phase: ~
  title: ~
  started: ~
  entry_category: ~
```

And update `last_work_item_id` to the completed item's ID.

Archive the active plan file if one exists:

```bash
python3 - << 'PY'
import os, re, shutil
from datetime import datetime, timezone

POINTER = '.sweetclaude/state/active-plan.txt'
if not os.path.exists(POINTER):
    exit()

lines = dict(
    line.split(': ', 1) for line in open(POINTER).read().strip().splitlines()
    if ': ' in line
)
plan_file = lines.get('plan', '').strip()
if not plan_file or not os.path.exists(plan_file):
    os.remove(POINTER)
    exit()

# Slug from H1 heading
content = open(plan_file).read()
h1 = re.search(r'^# (.+)', content, re.MULTILINE)
slug = re.sub(r'[^a-z0-9]+', '-', (h1.group(1) if h1 else os.path.basename(plan_file)).lower()).strip('-')
date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

# Archive folder: milestone/sprint or misc
ms_raw = lines.get('milestone', '').strip()
sp_raw = lines.get('sprint', '').strip()
ms_slug = re.sub(r'[^a-z0-9]+', '-', ms_raw.lower()).strip('-') if ms_raw else ''
sp_slug = re.sub(r'[^a-z0-9]+', '-', sp_raw.lower()).strip('-') if sp_raw else ''

if ms_slug and sp_slug:
    folder = os.path.join('.sweetclaude/plans/archive', ms_slug, sp_slug)
elif ms_slug:
    folder = os.path.join('.sweetclaude/plans/archive', ms_slug)
elif sp_slug:
    folder = os.path.join('.sweetclaude/plans/archive', sp_slug)
else:
    folder = '.sweetclaude/plans/archive/misc'

os.makedirs(folder, exist_ok=True)
dest = os.path.join(folder, f'{date_str}-{slug}.md')
shutil.move(plan_file, dest)
os.remove(POINTER)
print(f'Archived plan → {dest}')
PY
```

Tell the user:

```
════════════════════════════════════
Shipped
════════════════════════════════════
```

> "Shipped. {work item id} — {title} — is live.
>
> **Rollback plan:** {what the user said in the checklist}
> **Keep an eye on:** {monitoring signal if mentioned}
>
> Run `/sweetclaude:status` to see the updated project state, or `/sweetclaude:go` to pick up the next item."

---

## Rules

- **Never skip the pre-ship checklist.** All 7 items must be confirmed or explicitly waived with a reason.
- **Rollback plan must be documented before deploy executes.** Not after.
- **Secrets check is non-negotiable.** If secrets are found in the diff, stop and surface it immediately.
- **Do not run the deploy command yourself.** Guide the user through it. Deployment is their action.
- **Smoke test is required.** A deploy without a smoke test is not a completed SHIP.
- **If smoke test fails, route to `sweetclaude:something-broke`** — do not try to debug in this skill.
