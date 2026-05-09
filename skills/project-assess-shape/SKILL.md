---
user-invocable: true
description: "Interview user and recommend a SweetClaude project mode (Flow, Kanban, Shape Up, or Agile)"
version: 1.0.0
---

# project-assess-shape

Recommend a project mode by interviewing the user. Called automatically from `/sweetclaude:setup` at init and available on demand.

## MODE CHECK

If `mode` is already set in sweetclaude.yaml and this is not an explicit user invocation:
> "Project mode is already set to `{mode}`. Run `/sweetclaude:project-mode shift <mode>` to change it."
Stop.

Proceed if mode is unset or user explicitly invoked this skill.

## Questions (one at a time, wait for each answer)

**Q1:** Are you building this alone, with a small team, or as part of a larger organization?
- Alone / just me
- Small team (2–5 people or AI agents)
- Larger organization (5+ people)

**Q2:** Do you prefer fixed time cycles ("we ship every 6 weeks") or continuous delivery as work is ready?
- Fixed cycles
- Continuously / when ready

**Q3:** How much project management structure do you want?
- 1: None — I just want to build
- 2: Light — capture what I'm building as I go
- 3: Medium — issues, milestones, some structure
- 4: Full — sprints, epics, velocity tracking

**Q4:** Does your project handle regulated data (health, financial, payment) or need compliance standards like GDPR, HIPAA, or SOC 2?
- Yes
- No / not yet
- Not sure

**Q5:** Have you used Shape Up, Scrum, or Kanban before? What felt right?
- Shape Up / appetite-based cycles
- Scrum / sprint cadence
- Kanban / continuous flow
- None / not sure

## Recommendation Logic

Evaluate in order:

1. Q4=Yes (regulated data) → **Agile** (note: Agile + Enterprise available later for full compliance pipeline)
2. Q2=Fixed cycles AND Q5=Shape Up → **Shape Up**
3. Q1=Larger org OR Q3=4 OR Q5=Scrum → **Agile**
4. Q2=Continuous AND Q3 ≤ 2 → **Kanban**
5. Default → **Flow**

## Recommendation Output

> "Based on your answers, I recommend **{Mode}** mode.
>
> {One paragraph explaining what this mode means in practice and why it fits their answers.}
>
> Does this fit? (yes / no / tell me more)"

**If yes:** write `mode: {mode_key}` to `.sweetclaude/state/sweetclaude.yaml`, then run:
```bash
bash $HOME/dev/sweetclaude/scripts/generate-effective-gates.sh
```
Confirm: "Mode set to **{mode}**. Effective gates compiled."

**If no:** ask what they want instead, offer alternatives, confirm before writing.

**If tell me more:** explain the mode in depth — artifacts, enforcement, alternatives.

## Mode Keys

| Display Name | sweetclaude.yaml key |
|---|---|
| Flow | `flow` |
| Kanban | `kanban` |
| Shape Up | `shape_up` |
| Agile | `agile` |

## Skip

If user runs `/project-assess-shape skip`: set `mode: flow`, run generate-effective-gates, confirm without asking questions.
