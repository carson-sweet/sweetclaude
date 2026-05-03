---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:help
user-invocable: true
description: Interactive help for SweetClaude. Explains free-language usage, walks through setup, shows available features, and explains project modes. Conversation flows from the user's question.
---

# SweetClaude Help

SweetClaude works through conversation. You don't need to know any commands.

## Step 1: Set the frame

Tell the user:

> "SweetClaude works through plain English — you describe what you want, and I figure out the right process. You don't need to know any skill names or commands.
>
> What would you like help with?"

Offer these options (conversationally based on context):

1. **Set up SweetClaude** — for a new project or an existing codebase
2. **See what's available** — browse the features: product planning, coding workflows, design, testing, and more
3. **Understand project modes** — Flow, Kanban, Shape Up, Agile
4. **Learn how to use SweetClaude** — examples of what to type
5. **Something else** — ask freely

## Step 2: Follow the user's choice

**"Set up SweetClaude":**
> "Just type `/sweetclaude` and I'll walk you through it — I'll detect whether this is a new project or an existing codebase and ask a couple of questions."

**"See what's available":**
Present a plain-language feature tour (grouped by area, no skill names):

*Building things*
- Plan a new feature from scratch (discovery → stories → code → ship)
- Fix a bug end-to-end with a proper diagnosis
- Review code before merging
- Deploy and run a smoke test

*Product work*
- Write a product brief or PRD
- Define your users (personas)
- Prioritize your backlog (RICE scoring, roadmap)
- Plan a sprint

*Design*
- Define your architecture
- Design an API
- Create wireframes and user flows

*Testing*
- Plan your test strategy
- Run a security review (STRIDE / OWASP)
- Accessibility audit (WCAG 2.1)

*Day-to-day*
- See where things stand (`/sweetclaude` with no text)
- Prepare for a meeting
- Export a session

**"Understand project modes":**
Explain each mode in 2 sentences:
- **Flow** — unstructured creative work, minimal process overhead
- **Kanban** — visual board, continuous flow, limit WIP
- **Shape Up** — fixed time, variable scope, 6-week cycles with appetite-based bets
- **Agile** — sprints, ceremonies, velocity tracking

> "To switch modes, just tell me: 'Switch to Kanban mode' or 'I want to use Shape Up.'"

**"Learn how to use SweetClaude":**
Show examples:
```
/sweetclaude                          → see where things stand
/sweetclaude build a login page       → start a new feature
/sweetclaude fix the auth bug         → diagnose and fix a bug
/sweetclaude review my PR             → code review
/sweetclaude something broke in prod  → incident response
/sweetclaude use code-review          → explicit skill routing
```

**"Something else":**
Answer the user's question directly and offer to continue exploring.

## Step 3: Continue the conversation

After answering, ask:
> "Anything else you'd like to know, or ready to dive in?"

If they're ready: "Just type `/sweetclaude` and tell me what you want to build."

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
