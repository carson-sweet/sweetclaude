# State and Memory

**Version:** 2.0
**Date:** 2026-05-03

SweetClaude persists project context across sessions in `.sweetclaude/`. Commit this directory to git. It is project-critical data, not cache. Decision history, assumptions, scope changes, and progress live here — and they need to travel with the repo.

This page is reference. For why state is structured the way it is, read [How It Works](how-it-works.md).

---

## Directory Layout

```
.sweetclaude/
├── state/
│   ├── sweetclaude.yaml        ← Unified state: phase, work item, features, framework health
│   ├── project.yaml            ← Language, framework, test runner, build commands
│   ├── active-plan.txt         ← Pointer to the current plan file + sprint/milestone context
│   ├── decision-log.md         ← Architecture and design decisions with rationale
│   ├── assumption-register.md  ← Assumptions worth checking later
│   ├── improvement-register.md ← Feedback and learnings from each phase
│   ├── scope-changes.md        ← Scope additions and removals with justification
│   └── backups/                ← Pre-migration state snapshots (created by /sweetclaude:update)
├── plans/                      ← Claude Code plan files (.sweetclaude/plans is set as plansDirectory)
│   └── archive/                ← Plans archived at ship time, organized by milestone/sprint
├── traceability/               ← Story → requirement → test → code traceability maps
└── disabled                    ← (optional) Presence disables SweetClaude for this project
```

Skills create additional state files as they run — `state/discovery.yaml`, `state/personas.yaml`, `state/brief.yaml`, etc. Treat the schema as extensible.

---

## sweetclaude.yaml

The unified state file. Everything the framework needs to know about the project lives here — version stage, active work, feature activation, framework health.

```yaml
schema_version: 1
project:
  name: my-project
  type: existing-code
  version_stage: BETA
  safety_snapshot: pre-sweetclaude

session:
  deference_level: collaborative
  default_action: null

work:
  last_item_id: WI-013
  active:
    id: WI-014
    type: net-new-feature
    workflow: [DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
    phase: IMPLEMENT
    title: "OAuth login flow"
    started: 2026-04-29T14:00:00+00:00
    entry_category: mid-project-planned

features:
  product_milestones:
    status: active
    offered_at: 2026-04-15T10:00:00+00:00
    decided_at: 2026-04-15T10:05:00+00:00
    defer_until: null
  product_backlog:
    status: not_offered
    offered_at: null
    decided_at: null
    defer_until: null
  # ... other features

framework:
  installed_version: 3.44.4
  setup_complete: true
  hook_last_ran: 2026-05-03T14:00:00+00:00
  consistency:
    last_checked: 2026-05-03T14:00:00+00:00
    status: ok
    drift: []
    check_error: null
  update:
    available: null
    last_checked: 2026-05-03T14:00:00+00:00
    declined: false
    check_error: null
```

| Field | What it is |
|---|---|
| `project.version_stage` | Where the major version is in its release lifecycle. Slow-moving. PROTOTYPE → ALPHA → BETA → GA → SCALED → MAINTAINED. Controls progressive disclosure. You declare; the system never advances. |
| `session.deference_level` | `collaborative`, `guided`, or `autonomous`. Changeable mid-session. |
| `project.type` | `cold-start` or `existing-code`. Set at activation. |
| `project.safety_snapshot` | The git branch created during onboarding (`pre-sweetclaude`). Your insurance. |
| `work.last_item_id` | Monotonic counter. Persists across work item completions so IDs do not repeat. |
| `work.active` | The work in flight right now. Fast-moving. Type, workflow, phase, title, start date, entry category. |
| `features.*` | Per-feature activation state. `not_configured` → `active` or `declined`. Configured at setup and reviewable via fix-sweetclaude or update. |
| `framework.consistency` | Last drift-check result. Updated by the health hook. |
| `framework.update` | Whether a newer version is available. Updated by the health hook. |

**Migration from v2.x:** If your project has `phase.yaml` and `skills.yaml`, run `/sweetclaude` and the orchestrator will detect the old format and route to the migration flow automatically. The migration is non-destructive — originals are archived before any changes.

---

## project.yaml

Language and toolchain metadata. Read by skills that need to invoke build, test, or format commands.

```yaml
project:
  name: my-project
  language: typescript
  framework: nextjs
  package_manager: npm
  test_runner: jest
  test_command: npm test
  formatter: prettier
  format_command: npm run format
  build_command: npm run build
  install_command: npm install
  src_dir: src/
  test_dir: __tests__/
  notes: |
    Any project-specific quirks worth recording.
```

If a field is unknown, set it to `none`. Skills check before invoking commands.

---

## decision-log.md

Every significant architecture, design, or product decision recorded here. Written by `/sweetclaude:design-manage-decisions` but any skill can write to it. Query it with: "Why did we choose X?"

Format per entry:

```markdown
## DEC-007 — Chose PostgreSQL over DynamoDB

**Date:** 2026-04-22
**Status:** Accepted
**Phase:** DESIGN
**Work Item:** WI-008

**Context:** Need a primary data store for user accounts and feedback threads.
The team is comfortable with relational databases but the deployment target
(AWS) makes DynamoDB convenient.

**Decision:** PostgreSQL on RDS.

**Alternatives Considered:**
- DynamoDB — rejected because feedback threads have nested comments that benefit
  from joins; modeling that in DynamoDB requires either denormalization or
  multiple round-trips, both worse than a single SQL query.
- SQLite — rejected because we will need write concurrency.

**Rationale:** Joins matter for the access patterns. Operational familiarity
with Postgres is high. RDS handles backups and replication. The convenience
of DynamoDB does not outweigh the modeling cost for this access pattern.

**Consequences:**
- Need to provision RDS in IaC.
- Migrations managed via Flyway.
- Cost ceiling slightly higher than DynamoDB for low traffic; acceptable.
```

The format above is a template, not a strict schema. The point is that future-you (or a teammate) can read the entry and understand both *what* was decided and *why* — including what was rejected and why it was rejected.

---

## assumption-register.md

Assumptions recorded during discovery and design that carry risk if wrong. Each entry includes:

- The assumption itself
- What would happen if it is wrong
- What would validate or invalidate it

Example:

```markdown
## ASM-003 — Customers will accept Slack-based notifications

**Date recorded:** 2026-04-15
**Phase:** DISCOVER

**Assumption:** Target customers (freelance designers and their clients)
will accept Slack as the primary notification channel.

**Risk if wrong:** If clients are not on Slack, the entire notification
system needs an email path. ~2 weeks of work.

**Validation:** Five customer interviews. If any client refuses to install
Slack, the assumption is invalidated.

**Status:** Open. Validation scheduled in next discovery cycle.
```

SweetClaude writes to this automatically during structured interviews when it detects assumption-shaped statements.

---

## improvement-register.md

Feedback and learnings from each session. Populated at mandatory triggers:

- Before every phase transition: "Anything about how this phase went that I should do differently?"
- After code review findings are addressed
- After misalignments or visible frustration
- After smooth stretches or compliments

Read at session start. If there are entries, SweetClaude acknowledges: "I have N learnings from previous sessions — still apply?"

This is the mechanism for the framework to actually improve session over session. The first session you run, the file might be empty. By the tenth session, it should contain calibrated feedback that prevents the framework from making the same mistakes twice.

---

## scope-changes.md

Tracks additions and removals from scope. Every change is logged with who decided it, why, and what work items are affected. Prevents scope from silently growing without traceability.

Example entry:

```markdown
## SC-002 — Added: SAML SSO

**Date:** 2026-04-28
**Decided by:** Carson
**Reason:** Customer interview revealed three of five target customers
require SAML for procurement. Without it, the deal is dead.
**Affected work items:** WI-014 (OAuth login flow) gets a sibling work item
WI-015 for SAML.
**Original scope reference:** Brief section 4 (Authentication) explicitly
listed OAuth as the only auth method.
```

When sprint planning runs, it surfaces scope changes since the last sprint to keep the plan honest.

---

## Traceability

The `traceability/` directory contains maps connecting:

- User stories → product requirements (PRD epics and FRs)
- Requirements → test specs (Gherkin features)
- Tests → implementation files

Written progressively as the pipeline advances — `product-user-stories` writes the story-to-requirement map, `product-user-tdd-tests` adds the test mapping, the implementer agent updates the implementation column.

Used by code review and PR pre-check to verify coverage. A story with no test, or a test with no implementation, surfaces as a gap.

---

## Disabling SweetClaude

To disable for a project without uninstalling:

```bash
touch .sweetclaude/disabled
```

Running `/sweetclaude` removes the file and reactivates. The session-start health check fires automatically only when `disabled` does not exist.

To uninstall globally:

```bash
~/.claude/sweetclaude-uninstall.sh
```

(The installer wrote this script during install. It restores your pre-install `~/.claude/` configuration from the backup.)

---

## What Survives a Session Crash

Claude Code sessions die. Context windows fill. Networks drop. SweetClaude is designed to survive this.

What survives:
- Everything in `.sweetclaude/state/`
- Everything in `.sweetclaude/traceability/`
- Anything skills wrote to disk during the session — discovery output, briefs, PRDs, code, tests
- Git commits that happened (the git-checkpoint hook commits at phase transitions)

What does not survive:
- In-flight conversation context
- Drafts that were in progress but not committed
- Anything you typed but did not act on

If a session dies mid-discovery interview, you do not lose the answers you already gave (those are in state files). You lose the next question. Run `/sweetclaude` and it re-orients from state and resumes from the next step.

---

## Why Commit `.sweetclaude/`

Because the state is part of your project history. Three reasons:

**Traceability.** When someone asks "why does this codebase use PostgreSQL instead of DynamoDB?", the answer lives in `decision-log.md`. If `.sweetclaude/` is gitignored, that history is gone.

**Onboarding.** A new contributor cloning the repo gets the same context you have. They can read the assumptions, the decisions, the scope history. Without that, they have to re-derive everything.

**Recovery.** If your machine dies, your state is in the repo. You clone, you have everything. If state is local-only, you lose the project's institutional memory along with the laptop.

Treat `.sweetclaude/` like `docs/` — it is part of the project. Commit it.

---

## What to Read Next

- The two-dimension state model and why it works that way → [How It Works](how-it-works.md)
- Phase exit criteria that drive what gets written to state → [Phases and Workflows](phases-and-workflows.md)
- The skills that read and write state → [Skills Reference](skills-reference.md)
