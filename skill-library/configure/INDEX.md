# Configure Library Index

This index is read only after Tier 1 selected this category. Choose one workflow; do not load every workflow body.

| Workflow | Trigger / outcome |
|---|---|
| `_features` | Feature configuration — shows all optional SweetClaude features with descriptions and current status, lets the user enable or disable them. |
| `_health` | Consistency scan and version check. |
| `_migrate` | Migration orchestrator. Wraps the runner with snapshot, recovery menus, and end-of-session report. |
| `claude-config-audit` | Redirects to /sweetclaude:configure doctor. Config compatibility checks are now part of the doctor system. |
| `doctor` | Diagnostic scan, repair, and rollback. Checks 8 categories (state integrity, hooks, storage, migration, config, files, onboarding, environment), fixes what it safely can, and can restore (roll back / undo / revert) the files a previous doctor run changed. |
| `feature-setup` | Deploy local repo to installed locations and rebuild the project cache. |
| `fix-sweetclaude` | Redirects to /sweetclaude:configure doctor. This skill has been absorbed into the doctor diagnostic system. |
| `guardian-off` | Disable the Protocol Guardian for the current session |
| `guardian-on` | Enable the Protocol Guardian — enforces skill invocations, TDD discipline, and artifact saves for the current session |
| `hibernate` | Use when hibernating or unhibernating a project managed by SweetClaude. |
| `hook-repair` | Redirects to /sweetclaude:configure doctor. Hook diagnostics are now part of the doctor system. |
| `init` | Entry point for onboarding a project to SweetClaude — reads current state and hands off to the skill that owns the work. |
| `migrate` | Migrate legacy work items to unified ISSUE-NNN format. Supports flat BL-NNN layouts and typed legacy backlog layouts (stories/, bugs/, debt/). |
| `migrate-diagnose` | Redirects to /sweetclaude:configure doctor. File diagnostics are now part of the doctor system. |
| `off` | Deactivate SweetClaude for the current project. |
| `project-assess-shape` | Interview user and recommend a SweetClaude project mode (Flow, Kanban, Shape Up, or Agile) |
| `project-mode` | Assess and shift project modes. |
| `purge` | Delete all SweetClaude artifacts from the current project. |
| `recover` | Recover or unblock SweetClaude projects left in bad update, migration, doctor, or repair states. |
| `retro` | Review and maintain the improvement register. |
| `setup` | Consolidated onboarding skill. |
| `update` | Update SweetClaude to the latest version from GitHub. |
| `usage` | Toggle and view local usage tracking. |
| `work-item-artifacts` | Co-locate all artifacts per story, epic, and milestone into .sweetclaude/work/<ID>/. Manages onboarding, backfill, and per-item directory creation. |
