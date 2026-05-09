---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "SweetClaude help and skill discovery."
---

# SweetClaude Help

Reference content lives in three sibling files:
- [phases-content.md](phases-content.md) — Options 1, 1a, 1b, 1c, 1d
- [modes-content.md](modes-content.md) — Options 2, 2b, 2c
- [workflows-content.md](workflows-content.md) — Options 3, 3a, 3b, 3c

When an option below says *"present the [section] from [file].md"*, read that file, find the matching `## Option X — ...` heading, and present its content verbatim.

## Step 1: Check the skip flag

Read `.sweetclaude/state/sweetclaude.yaml`. If `skip_help_welcome: true`, skip directly to Step 3 (skip path).

## Step 2: Welcome message and main menu

Tell the user:

> Welcome to SweetClaude's help skill. It's designed to provide support through natural conversation instead of dumping a wall of text at you. If you want a more typical user guide, there's one in the repo: https://github.com/carson-sweet/sweetclaude/blob/main/docs/user-guide/index.md
>
> **SweetClaude** is a software development partner built for the full project lifecycle — from the first idea through design, implementation, testing, and ship.
>
> It adapts to your working style. You can move fast with minimal structure (vibe-coding), or apply enterprise-class discipline with phase gates, formal specs, TDD pipelines, and QA caucuses — or land anywhere in between. The framework adjusts to the project, not the other way around.
>
> SweetClaude has also been used successfully for academic research, product marketing strategy, and other knowledge-intensive work, but software development is where it lives.

Then use AskUserQuestion with these four options:

1. **Project Phases** — how SweetClaude structures product development, from conceptual idea to go-live
2. **Operating Modes** — how SweetClaude supports incremental structure and discipline, from vibe-coding to enterprise-grade
3. **Workflows and Skills** — an inventory of the individual skills and how they compose into orchestrated workflows
4. **Tell me about your project** — start a conversation about how SweetClaude would approach your specific situation

The AskUserQuestion tool automatically provides an "Other" option — freeform questions go through Option 5.

After the menu, add this plain-text line:
> "To skip this intro in future sessions, just say `skip the welcome`."

## Step 3: Follow the user's choice

### Option 1 — Project Phases

Present the **Option 1** section from [phases-content.md](phases-content.md). Then use AskUserQuestion with:

- **Skill workflows per phase** → present **Option 1a** from `phases-content.md`
- **Project structure and deliverables** → present **Option 1b** from `phases-content.md`
- **Hello-world project** → present **Option 1c** from `phases-content.md`
- **Approaching an existing project** → present **Option 1d** from `phases-content.md`

### Option 2 — Operating Modes

Present the **Option 2** section from [modes-content.md](modes-content.md). Then use AskUserQuestion with:

- **Help me choose a level** → run Option 2a logic (interactive, defined below)
- **What actually changes at each level** → present **Option 2b** from `modes-content.md`
- **How to change levels mid-project** → present **Option 2c** from `modes-content.md`
- **Start a conversation about something else** → run Option 4 logic (defined below)

#### Option 2a — Help me choose a level (interactive)

Open with: "I'm going to ask you four quick questions, then I'll give you a recommendation."

Ask each question one at a time using AskUserQuestion:

**Q1** — plain text prompt: "What are you building?"

**Q2** — AskUserQuestion: *Where is it now?*
- Just an idea
- Exploring / early prototyping
- Prototype built
- Actively shipping

**Q3** — AskUserQuestion: *What kind of project?*
- Hobby / side project
- Internal company tool
- B2C product
- B2B product

**Q4** — AskUserQuestion: *Does the data or user base create compliance requirements?*
- No
- Possibly — not sure
- Yes (HIPAA, GDPR, SOC 2, PCI, etc.)

Synthesize all four answers into one of these modes:
- **Flow Mode** — conversational, minimal process, no gates
- **Kanban** — WIP-limited continuous flow, light TDD
- **Shape Up** — pitch-driven 6-week cycles, TDD Level 2, betting table gate
- **Agile** — sprint-based, TDD Level 2, structured iteration

Present the recommended level with a one-sentence rationale explaining why it fits their situation.

Then ask using AskUserQuestion: "Want to explore this further or give it a try?"
- Explore further
- Give it a try

**If "Give it a try":**
> "Great. Start a Claude Code session in your project folder. When Claude starts up, just run `/sweetclaude:go` — it'll detect where you are and route to the right starting point. If SweetClaude isn't set up yet, it'll walk you through init and mode selection. If it's already running, just describe what you want to work on and it takes it from there.
>
> You can always come back to `/sweetclaude:help` if you have questions along the way."

**If "Explore further":**
Use AskUserQuestion with:
- **Tell me more about [recommended mode]** — describe a concrete day-in-the-life session in that mode (specific to the recommended mode, not generic)
- **Compare it to the other modes** → present **Option 2b** from `modes-content.md`
- **How do I switch modes later?** → present **Option 2c** from `modes-content.md`
- **Something else** — ask anything

### Option 3 — Workflows and Skills

Present the **Option 3** section from [workflows-content.md](workflows-content.md). Then use AskUserQuestion with:

- **View all skills by phase** → present **Option 3a** from `workflows-content.md`
- **Explore workflow examples** → present **Option 3b** from `workflows-content.md`
- **How does testing work?** → present **Option 3c** from `workflows-content.md`
- **Ask something else** → run Option 5 (freeform)

After **3b**, follow up with AskUserQuestion:
- **Go deeper on one of these** — ask which workflow (feature build / production bug / new product kickoff), then walk through it step by step — what each skill does, what the user sees at each step, what artifacts come out
- **Show me more workflow examples** — offer two or three from adjacent areas — security review, corpus/RAG setup, Shape Up pitch-to-implementation cycle
- **I want to try one of these on my project** → run Option 4 logic
- **Something else** → run Option 5

### Option 4 — Tell me about your project

Open with: "Tell me about your project. I will probably have questions, then I'll share how I'd approach it with you."

The goal of this conversation is to arrive at three things:
1. The right operating mode — how much structure and discipline fits this project
2. Whether security or compliance work is needed — ask briefly about what data the app handles and who the users are (consumers, employees, regulated industries)
3. A concrete recommendation for how to start

Keep it conversational. Ask one question at a time. Cover:
- What are they building and where are they in the process
- Who are the users and what data does the app handle
- Are they working alone or with a team
- Is this exploratory or going to production

After a few exchanges, offer to look directly at the project to give a more grounded recommendation:

> "If you'd like, I can take a look at your project directly — read the codebase, git history, and any existing docs — and give you a more specific picture of how I'd approach it. I won't make any changes. No files touched, no commits, nothing written. Read-only, full stop."

If they agree, do a read-only survey (structure, stack, existing tests, README, recent commits) and return a concrete recommendation covering:

- **First: create a safety branch.** Before doing anything else, strongly recommend they create a snapshot branch (`git checkout -b pre-sweetclaude-snapshot`) so they have a clean rollback point if they ever want to undo everything SweetClaude has touched. Frame it as a seatbelt — takes 5 seconds, costs nothing, and means they can always get back to exactly where they are right now.
- **Suggested operating mode** — based on the conversation and what was observed in the project
- **First steps** — concrete next actions to get started with SweetClaude on this project
- **Security/compliance flags** — anything worth knowing based on the data and user types described

### Option 5 — Other (freeform)

The user typed their own question or request. Answer directly and conversationally.

### "skip the welcome" (any time)

Set `skip_help_welcome: true` in `.sweetclaude/state/sweetclaude.yaml`:

```bash
python3 - << 'PY'
import yaml, tempfile, os
path = '.sweetclaude/state/sweetclaude.yaml'
try:
    with open(path) as f:
        d = yaml.safe_load(f) or {}
except FileNotFoundError:
    d = {}
d['skip_help_welcome'] = True
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
print("Done.")
PY
```

Confirm it's set, then say: "Done — I'll skip the intro next time. Tell me what you need and let's see how I can help."

## Step 3 (skip path): Conversation-only entry

If `skip_help_welcome` was true, say:

> "Tell me what you need and let's see how I can help."

Then answer directly and conversationally.

## After any answer

Continue the conversation naturally. Don't ask "anything else?" — just stay available. The user will redirect if they want to explore something different.

## Learnings visibility

If the user asks "what have you learned about me?" or "show my preferences":

```bash
python3 - << 'PY'
import yaml
try:
    d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml'))
    learnings = d.get('learnings', [])
    if learnings:
        print("Here's what I've learned from our sessions:\n")
        for i, l in enumerate(learnings, 1):
            print(f"{i}. {l}")
    else:
        print("No learnings recorded yet.")
except:
    print("Can't read learnings right now.")
PY
```

Offer: "Want to remove any of these? Just tell me which number."

If they specify one, remove it:

```bash
python3 - .sweetclaude/state/sweetclaude.yaml INDEX << 'PY'
import sys, yaml, tempfile, os
path, idx = sys.argv[1], int(sys.argv[2]) - 1
with open(path) as f: d = yaml.safe_load(f)
learnings = d.get('learnings', [])
if 0 <= idx < len(learnings):
    removed = learnings.pop(idx)
    with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
        yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
        tmp_name = tmp.name
    os.replace(tmp_name, path)
    print(f"Removed: {removed}")
else:
    print("Index out of range.")
PY
```
