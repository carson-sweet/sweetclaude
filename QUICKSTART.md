# Quick Start

You have SweetClaude installed. Here is how to use it.

---

## Your First Session

**Activate SweetClaude for a project (new or existing):**

```
/sweetclaude:on
```

Detects whether the folder is empty or already has a project. For new projects: walks through setup, product discovery, user personas, and hands off to the pipeline. For existing projects: creates a safety snapshot, scans the codebase, interviews you about current state, and positions you in the right phase.

**Pick up where you left off:**

```
/sweetclaude:go
```

Reads your project state, checks phase gate exit criteria, and routes to the right skill. No menu — it tells you what needs to happen and does it.

**Check project status:**

```
/sweetclaude:status
```

Shows version stage, active work item, phase progress, SweetClaude version, and RAG corpus state. Fires automatically at session start for active projects.

**Suspend or remove SweetClaude:**

```
/sweetclaude:off    # suspend — preserves all artifacts, reactivate with /sweetclaude:on
/sweetclaude:purge  # delete all artifacts — warns and requires typed confirmation first
```

**Get help:**

```
/sweetclaude:help
```

Conversational assistant. Describe what you want to do and it shows you how.

---

## Common Starting Points

### "I have an idea for a product but have not started building anything"

Run `/sweetclaude:on` in an empty folder. SweetClaude will:
1. Set up the project (git, directory structure, CLAUDE.md)
2. Ask what you want to build
3. Run product discovery — problem framing, personas, optional competitive landscape
4. Hand off to the product definition pipeline (brief, PRD, architecture, implementation)

### "I have a codebase and want to start using SweetClaude"

Run `/sweetclaude:on` in your project folder. SweetClaude will:
1. Detect the existing project
2. Create a safety snapshot branch before touching anything
3. Scan your code, tests, docs, and issues
4. Interview you about current state and biggest concerns
5. Determine where the project sits in its lifecycle
6. Offer to address your immediate concerns first

### "I need to build a specific feature"

Run `/sweetclaude:go` and describe what you need. SweetClaude classifies the work and routes to the right starting point.

### "I have a GitHub issue to implement"

Run `/sweetclaude:go` and mention the issue number or paste the title. SweetClaude reads the issue, proposes a plan, implements with TDD, verifies, updates docs, and opens a PR.

### "Production is broken"

```
/sweetclaude:find-skill production is down
```

Routes to the hotfix workflow: DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM. Skips ceremony, keeps discipline.

### "I have a pile of messy strategy files"

Tell SweetClaude "I have a pile of documents I need to organize." Four-step corpus pipeline: consolidate → triage → reconcile → promote. Originals are never deleted.

---

## What to Read Next

- End-to-end scenario walkthroughs → [Walkthroughs](docs/user-guide/walkthroughs.md)
- Full command reference → [COMMANDS.md](COMMANDS.md)
- How SweetClaude's architecture works → [How It Works](docs/user-guide/how-it-works.md)
- Honest answers to common questions → [FAQ](docs/user-guide/faq.md)
