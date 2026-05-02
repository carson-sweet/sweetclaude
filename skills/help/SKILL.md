---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:help
description: Interactive help assistant. Teaches the user how to work with SweetClaude through prompting, not commands. Ask what they want to accomplish and show them how.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Help

SweetClaude works through conversation, not commands. This skill helps users understand that model.

---

## Step 1: Set the frame

Tell the user:

> "SweetClaude works through conversation. You describe what you want, and I figure out the right process — you don't need to know the commands.
>
> What are you trying to do, or what do you want to know how to do?"

Wait for their response.

---

## Step 2: Route their question

### If they describe a task or goal

Map it to what SweetClaude would do. Show them how to ask for it naturally, not what command to run.

Examples:

| They say | Show them this |
|---|---|
| "I want to start a new project" | "Just say 'I want to build X' — SweetClaude will detect context and walk you through setup." |
| "I need to fix a bug" | "Describe the bug: 'users can't log in when X happens.' SweetClaude will open a bug-fix workflow, starting with root cause." |
| "I want to review my code" | "Say 'review my code' or 'I'm ready for code review.' SweetClaude will run a structured code and security review." |
| "I want to write a PRD" | "Say 'let's write the PRD' or 'I'm ready to define the product.' SweetClaude will open the product definition workflow." |
| "I want to refactor this" | "Say 'I want to clean up X' or 'this code is messy.' SweetClaude will lock existing behavior with tests before touching anything." |
| "I want to ship" | "Say 'I think this is ready to ship' — SweetClaude will check the verify phase gates and walk you through the handoff." |
| "What's next?" | "Say 'what's next' or just run `/sweetclaude:go` — SweetClaude reads your project state and tells you." |

Give a concrete example matching their specific task. Do not list all possible tasks — respond to what they actually asked.

---

### If they ask how SweetClaude works

Explain the model in plain terms:

> "SweetClaude tracks where your project is in its lifecycle and enforces a process — discover → define → design → build → verify → ship. Each step has exit criteria. When you say you're done with something, SweetClaude checks the criteria before moving on.
>
> You don't need to think about phases or commands. Just describe what you want to work on, and SweetClaude figures out where you are and what needs to happen next."

Then ask: "What are you working on right now?"

---

### If they ask what commands exist

Redirect gently:

> "The commands are mostly for getting started: `/sweetclaude:on` to set up a project, `/sweetclaude:go` to pick up where you left off, `/sweetclaude:status` to see where things stand. Everything else you do through conversation — just describe what you want.
>
> What are you trying to accomplish?"

---

### If they're confused or frustrated

Acknowledge it. Ask one specific question:

> "Let me help. What were you trying to do when things got confusing?"

Listen, then give a direct answer to that specific thing. Do not re-explain the whole system.

---

### If they ask about a specific topic (TDD, code review, product brief, etc.)

Explain how that works in SweetClaude's terms, with an example of how to invoke it through conversation. Do not show a command — show a prompt.

---

## Step 3: Stay in the conversation

After answering, offer to keep going:

> "Does that help? Want to try it, or is there something else you want to know?"

If they want to try something, hand off to the right skill or tell them what to say to get started.

This is a conversation, not a reference page. Stay with the user until they have what they need.
