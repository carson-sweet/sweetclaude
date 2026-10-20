# Step 7: Surface capabilities (capability-surface.md)

**IMPORTANT:** `/sweetclaude:configure update` may use only the read-only "What's new"
section below. Project skill-state migration, bootstrap, and onboarding are
disabled from update in beta 4.x stabilization because they mutate project
state without the maintenance safety contract.

## 7a: What's new in this update

Compare the installed hooks and config files (before sync) against the new version. Identify:

1. **New hooks** — files in `$SOURCE_DIR/hooks/` that did not exist in the previously installed hooks directory (`${CLAUDE_PLUGIN_ROOT}/hooks/`)
2. **New skills** — skill directories in `$SOURCE_DIR/skills/` that did not exist in the previously installed `{installPath}/skills/`
3. **New config templates** — files in `$SOURCE_DIR/config/templates/` that are new

For each new item, check whether it requires per-project opt-in. Read the hook or skill to determine what config is needed.

If new items exist, present:
```
New in this update:
  → {skill-name}: {one-line description}
    Available as: /sweetclaude:{skill-name}
    Enable: {opt-in steps if required, else omit}
```

If nothing is new, show: "No new skills or hooks in this update."

**Skill state check and bootstrap (disabled from update):**

Do not run this section from `/sweetclaude:configure update`. It is retained as historical
reference until the logic is moved behind a dedicated doctor/setup capability
with diagnosis, plan, snapshot, approval, verification, and rollback/fail-closed
behavior.

Historical reference only: the old implementation ran this only if
`.sweetclaude/` existed in the current project directory. Do not execute these
commands from update.

Read `.sweetclaude/state/skills.yaml` if it exists.

**Step 1 — schema migration:** If `skills.yaml` exists with `schema_version: 1`, invoke the registry-driven migration runner (ISSUE-066 refactor):

```bash
RUNNER=${CLAUDE_PLUGIN_ROOT}/scripts/migrations/runner.py
if [ -f "$RUNNER" ]; then
  python3 "$RUNNER" --project-dir . --file skills.yaml
  echo "Migrated skills.yaml to schema v2."
else
  echo "Migration runner not found at $RUNNER. Run /sweetclaude:configure update."
fi
```

The registered handler `scripts/migrations/skills_yaml_v1_to_v2.py` owns the v1→v2 mapping. Same algorithm that previously lived inline here.

**Step 2 — fill missing entries:** For `base_path`: read `.sweetclaude/artifact-privacy.yaml` → `categories.product.base_path`. If absent, use `.sweetclaude/artifacts/product`.

For each of the six data-owning skills not already in `skills.yaml`, infer state from data files:

| Skill | Data file that indicates it was in use |
|---|---|
| `product-milestones` | any `MS-*.md` under `{base_path}/milestones/` |
| `product-parking-lot` | any item files under `{base_path}/backlog/` |
| `product-sprint-plan` | *(no inference — always `uninitialized` if absent)* |
| `user-personas` | `.sweetclaude/state/personas.yaml` |
| `product-user-stories` | any `US-*.md` under `{base_path}/stories/` |
| `document-corpus` | `.sweetclaude/state/corpus-pipeline.yaml` |

For each missing entry: data file exists → `status: active`, `last_changed_by: migrated`. Does not exist → `status: uninitialized`. Write atomically (temp file → rename). Do not remove existing entries.

**Skill onboarding prompt:**

After bootstrap, read `skills.yaml`. Build a list of all six data-owning skills where `status: uninitialized`. This list drives the onboarding prompt.

If the list is empty, skip the prompt and continue to 7b.

If non-empty, ask:

> "These skills aren't set up for this project yet. Which would you like to set up now?
>
>   {list only the skills with status: uninitialized, one per line with keyword and description}
>
> Enter keywords (e.g. "milestones backlog"), or "none" to skip."

| Keyword | Skill | What it does |
|---------|-------|--------------|
| `milestones` | `product-milestones` | Roadmap targets like "Exit Stealth" or "MVP Shipped" |
| `backlog` | `product-parking-lot` | Deferred work items with context |
| `sprint` | `product-sprint-plan` | Select stories from backlog into a sprint |
| `personas` | `user-personas` | Define who your users are and what they need |
| `stories` | `product-user-stories` | Write user stories for defined personas |
| `corpus` | `document-corpus` | Import and index your project documents |

For each skill the user enables, invoke it with argument `onboard`. Complete each onboard flow before starting the next. If the user says "none", continue.

After the onboarding prompt (or immediately if no uninitialized skills), add:

```
You don't need to learn the skill list — SweetClaude routes you automatically.
Just describe what you want to do and /sweetclaude:go will handle the rest.
Type /sweetclaude:help to see all available skills at any time.
```

Do not print the full skill catalog. Do not continue to any further step.
