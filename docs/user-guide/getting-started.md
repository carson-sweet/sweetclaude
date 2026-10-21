# Getting Started

**Version:** 1.2
**Date:** 2026-10-21

This page takes you from "I have not installed anything" to "I have a feature scaffolded, tested, and committed." Reading time is fifteen minutes. Doing it takes about an hour because the interactive parts depend on you typing things.

---

## Prerequisites

You need Claude Code, Git, and the GitHub CLI installed. If you want corpus management and semantic search, also install Node.js — but you can skip it for now.

| Tool | Check | Install |
|---|---|---|
| Claude Code | `claude --version` | [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| GitHub CLI | `gh --version` | `brew install gh` |
| Node.js _(optional)_ | `node --version` | [nodejs.org](https://nodejs.org/) |

If `gh` is not authenticated yet, run `gh auth login` once.

---

## Install

Inside Claude Code, install the stable channel:

```text
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
```

Restart Claude Code after install. See [Installing SweetClaude](install.md) for update instructions. After install, every Claude Code session in any project folder has nine commands available: `go`, `plan`, `design`, `build`, `maintain`, `configure`, `utils`, `status` and `help`. Workflows are run as `/sweetclaude:<category> <workflow>`, for example `/sweetclaude:configure doctor`, or by describing what you want after `/sweetclaude:go`.

---

## Your First Session: The Three Patterns

There are three ways a session starts. Pick the one that matches you.

### Pattern A — A new idea

You have a folder. The folder is empty. You have a vague concept and no code.

```bash
cd ~/projects/freelance-feedback-tool
claude
```

Then in Claude Code:

```
/sweetclaude:go
```

SweetClaude detects the empty folder and routes to setup. It asks for the project name, a one-sentence description, where issues should live (local or GitHub) and which working mode fits, then creates `.sweetclaude/` and adds a SweetClaude section to `CLAUDE.md`. The deference level starts at **Collaborative**, so you see every step on your first run.

Then it asks you to describe the idea.

What you should expect: SweetClaude will not just take your description and start building. It will challenge the framing. You might see something like:

> You said "feedback tool for freelance designers." Before I draft anything, I want to challenge that. The friction in client feedback exists across roles — agencies, in-house teams, indie product designers all face it. What makes you confident the freelance segment specifically? Or is "freelance designers" a stand-in for a broader pattern?

This is the [Discover phase](how-it-works.md) doing its job. The best concepts survive scrutiny. Push back if you have a real reason. Adjust if you do not.

After you settle the framing, SweetClaude offers product discovery at three depths — quick intent (L1), problem and success (L2), or full pain thesis (L3). Pick the depth appropriate to what you are building. A weekend hobby tool is L1. A B2B product you intend to sell is L3.

### Pattern B — An existing codebase

You have a project. There is code. You want SweetClaude to start helping but not break anything.

```bash
cd ~/work/my-existing-project
claude
```

```
/sweetclaude:go
```

SweetClaude detects the existing codebase and routes to setup. It works in this order:

1. **Safety snapshot.** Creates a `pre-sweetclaude` git branch from your current state. If you ever want to undo everything SweetClaude added to your repo, that branch is your insurance. SweetClaude will not proceed without this.
2. **Project scan.** Reads the codebase (read-only). Detects languages, frameworks, test runners, doc files, open issues. Reports what it found.
3. **Setup questions.** Asks, one at a time, the project name, the stage (early prototype, active development, approaching launch or in production), where issues should live (local or GitHub, the issue tracker) and which working mode fits. The stage sets the project's version stage.
4. **Assessment.** If the codebase looks disorganized (many TODO comments, inconsistent naming or no tests), SweetClaude runs an assess, diagnose, plan and scaffold flow and shows you the scaffolding plan before touching anything.
5. **Handoff.** Setup creates `.sweetclaude/`, adds a SweetClaude section to your `CLAUDE.md` without overwriting existing content, and hands off to the feature library so you can pick the next piece of work.

### Pattern C — Resuming work

You set SweetClaude up yesterday. You are coming back today.

```
/sweetclaude:go
```

That is it. SweetClaude reads `sweetclaude.yaml`, sees what work item is active, checks the phase exit criteria, and proposes what to work on next, or tells you what is missing. It waits for your go-ahead before acting.

---

## Deference Levels

Setup stores a deference level in `sweetclaude.yaml`, and the default is **Collaborative**. SweetClaude does not ask again at the start of each session. There are three levels:

**Collaborative.** Stops after every sub-step. Best for your first project, for unfamiliar phases, or when you want to learn the rhythm. Slow but instructive.

**Guided.** Executes within a phase autonomously, stops at major decisions and at phase boundaries. Best for daily work once you know what is happening.

**Autonomous.** Executes freely within phases. Stops only at phase gates. Best for implementation when the architecture is locked and you trust the process. Phase gates still pause it — autonomous does not mean unsupervised.

You can change the level mid-session by saying "Switch to guided" or "go autonomous." Respect is immediate.

The level is stored in `sweetclaude.yaml`. SweetClaude reads it next session and acts accordingly.

---

## What You Will Have After Your First Session

If you started a new project and ran through Discovery to Define:

```
your-project/
├── .sweetclaude/
│   ├── state/
│   │   ├── sweetclaude.yaml        ← unified state: phase, work item, features, framework
│   │   ├── discovery.yaml          ← product discovery output: who this is for, why it matters
│   │   ├── decision-log.md         ← any decisions you made with rationale
│   │   ├── assumption-register.md  ← assumptions worth checking later
│   │   └── improvement-register.md ← anything you told SweetClaude to do differently
│   ├── product/                    ← milestones, backlog and stories
│   ├── plans/                      ← plans written during planning sessions
│   └── traceability/
├── .claude/settings.json           ← points plansDirectory at .sweetclaude/plans
└── CLAUDE.md                       ← teaches future sessions about this project
```

If you adopted an existing codebase:

```
your-project/
├── .sweetclaude/                   ← (same files as above, mostly empty until you run more skills)
└── (your existing project untouched)
```

Plus the `pre-sweetclaude` git branch sitting there as your safety net.

`.sweetclaude/state/project.yaml` (language, framework, build commands) is optional. Setup does not create it; the auto-test-runner reads it if you add one.

Commit `.sweetclaude/` to git, except the guardian flag and recovery snapshots (setup gitignores `.sweetclaude/state/recovery-runs/`), which are derived and local. The rest is project context, not cache. You want decision history and assumptions to travel with the code.

---

## Five Useful Things to Try

These cost nothing and surface capabilities that are not obvious from the command list.

**1. "Explain the full SweetClaude process end-to-end."** Claude reads the master skill and walks through every phase, every work type, and which skills fit where. Better than reading docs.

**2. "Show me everything SweetClaude can do."** Walks through every domain — strategy, product, design, code, operations — explaining the capability, not just naming the command.

**3. "What kinds of problems can I hand to SweetClaude?"** Surfaces the less obvious uses: meeting prep, competitive analysis, pain thesis development, research paper drafting, document organization. Most users do not realize SweetClaude does any of these.

**4. `/sweetclaude:help`** All commands grouped by category, one line each. Faster than the full reference.

**5. `/sweetclaude:go`** Then describe what you want to do in plain English. SweetClaude classifies the work, picks the right starting skill, and runs it.

---

## When Something Goes Wrong

**Skill blocked you for missing prerequisites.** The skill is honoring a phase gate. You can usually bypass with "I've addressed this informally — proceed." That logs the override and continues. Hard gates cannot be soft-bypassed; for those, see the [phase-gates.md](phases-and-workflows.md) reference. (Not currently enforced: this is not checked by code yet; Claude applies it as an instruction.)

**Skill seems stuck in an interview loop.** Tell SweetClaude "go autonomous and finish the draft." It will conduct the rest of the interview internally and produce a draft for review.

**You want to undo everything SweetClaude added.** If you are on an existing repo, check out the `pre-sweetclaude` branch. If you are mid-session and want to reset state without losing the project, run `/sweetclaude:configure purge` (it asks for typed confirmation before deleting `.sweetclaude/`).

**Status fired automatically and you did not want it.** Touch `.sweetclaude/disabled` in the project root. The session-start check will not fire until you run `/sweetclaude:go` again.

**Want to keep SweetClaude updated.** Update the Claude Code plugin package first (`/plugin update sweetclaude@sweetclaude-stable`), restart Claude Code, then run `/sweetclaude:configure update` to sync framework files. Project repair and migration route through `/sweetclaude:configure doctor`.

---

## What to Read Next

You have a working install and have done a session. The next thing to read depends on what you want to know:

- Want to understand *why* the framework is shaped this way? → [How It Works](how-it-works.md)
- Want to see specific scenarios end-to-end? → [Walkthroughs](walkthroughs.md)
- Want to see what a specific skill does? → [Skills Reference](skills-reference.md)
- Wondering whether SweetClaude is right for you at all? → [FAQ](faq.md)
