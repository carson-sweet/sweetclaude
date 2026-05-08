# Quick Start

You have SweetClaude installed. Here is how to use it.

---

## Your First Session

**New to SweetClaude? Start here:**

```
/sweetclaude:help
```

Conversational onboarding — explains what SweetClaude is, walks you through the four operating modes, and helps you decide where to start. Takes about 5 minutes. Teaches itself through conversation so you don't have to read docs first.

**Ready to work? Use this:**

```
/sweetclaude:go
```

Your daily driver. Detects where you are and routes automatically. Empty folder → setup. Active project → picks up where you left off. Pass plain-English arguments: `/sweetclaude:go I need to fix a bug in auth`.

**Suspend or remove SweetClaude:**

```
/sweetclaude:off    # suspend — preserves all artifacts, reactivate with /sweetclaude:go
/sweetclaude:purge  # delete all artifacts — warns and requires typed confirmation first
```

---

## Common Starting Points

### "I have an idea for a product but have not started building anything"

Run `/sweetclaude:go` in an empty folder. SweetClaude will:

> **First time?** Run `/sweetclaude:help` before `/sweetclaude:go` — it'll explain what to expect and help you choose the right operating mode.

1. Set up the project (git, directory structure, CLAUDE.md)
2. Run a short mode-assessment interview (5 questions) to configure enforcement — Flow, Kanban, Shape Up, or Agile
3. Ask what you want to build
4. Run product discovery — problem framing, personas, optional competitive landscape
5. Hand off to the product definition pipeline (brief, PRD, architecture, implementation)

### "I have a codebase and want to start using SweetClaude"

Run `/sweetclaude:go` in your project folder. SweetClaude will:
1. Detect the existing project
2. Create a safety snapshot branch before touching anything
3. Scan your code, tests, docs, and issues
4. Run a short mode-assessment interview to configure enforcement for your workflow
5. Interview you about current state and biggest concerns
6. Determine where the project sits in its lifecycle
7. Offer to address your immediate concerns first

### "I need to build a specific feature"

Run `/sweetclaude:go` and describe what you need. SweetClaude classifies the work and routes to the right starting point.

### "I have a GitHub issue to implement"

Run `/sweetclaude:go` and mention the issue number or paste the title. SweetClaude reads the issue, proposes a plan, implements with TDD, verifies, updates docs, and opens a PR.

### "Production is broken"

```
/sweetclaude:something-broke
```

Classifies severity, decides fix vs. rollback, and routes to the hotfix workflow: DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM. Skips ceremony, keeps discipline.

### "I have a pile of messy strategy files"

Tell SweetClaude "I have a pile of documents I need to organize." Four-step corpus pipeline: consolidate → triage → reconcile → promote. Originals are never deleted.

---

## Terminal Tips

**Copying commands to your clipboard:**

After SweetClaude outputs a command you want to run, use `/copy` to copy the last response to your clipboard. For a persistent shortcut, add this rule to your project's `CLAUDE.md`:

```
When I say "copy that", pipe the command to my system clipboard: pbcopy (macOS), xclip -selection clipboard (Linux), or clip (Windows).
```

Then you can say "copy that" after any command output.

**Fenced code blocks render in Claude Code's terminal** — commands wrapped in ` ``` ` blocks are easier to select cleanly than inline backtick code. SweetClaude uses this consistently for runnable commands.

---

## What to Read Next

- End-to-end scenario walkthroughs → [Walkthroughs](walkthroughs.md)
- Full command reference → [Skills Reference](skills-reference.md)
- How SweetClaude's architecture works → [How It Works](how-it-works.md)
- Honest answers to common questions → [FAQ](faq.md)
