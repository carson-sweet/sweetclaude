# sweetclaude:skill-generator — Design Document
Version: 1.0 — 2026-05-02
Status: DESIGN COMPLETE — implementation deferred to MS-005

## Summary

`sweetclaude:skill-generator` converts a workflow description into a complete behavioral-contract SKILL.md. The gap it fills: Skill Seekers (the closest prior art) extracts documentation → SKILL.md prose, but does not produce behavioral contracts with phase gates, deference levels, and routing table entries. This skill generates behavioral contracts from first principles.

---

## Design Questions — Decisions

### Q1: Input format

**Decision: Free-text description with structured interview.**

The generator accepts a free-text description ("I want a skill that guides database schema migrations") and conducts a focused 4-question interview to clarify:

1. **What phase(s) does this skill span?** (DISCOVER / DEFINE / DESIGN / PLAN / IMPLEMENT / VERIFY / SHIP — or pick "it's a utility that spans all phases")
2. **Which work type does it most closely map to?** (net-new-feature / enhancement / bug-fix / tech-debt / other — or "it doesn't fit any of these")
3. **What are the entry criteria?** (What must be true before this skill can run? e.g., "product brief exists", "tests are written", "no active work item")
4. **What are the exit criteria?** (What artifact or state constitutes "done" for this skill?)

This is the minimum viable specification. The generator infers everything else from these 4 answers.

**Why not structured YAML?** Friction at entry point. Most users have a workflow description in their head, not a YAML schema. The interview structures it.

**Why not Gherkin?** Gherkin is output of `code-tdd`, not input to skill-generator. The generator may produce Gherkin-formatted acceptance criteria as part of the output, but it does not require them as input.

---

### Q2: Output validation

**Decision: Human review with structured checklist.**

Stage 5 presents the complete generated SKILL.md to the user with a checklist:

```
Before writing this skill, review:
[ ] The shell preprocessing block reads all the state it needs
[ ] Every step has a clear entry condition and output
[ ] Deference level guidance matches the skill's interactive/autonomous nature
[ ] Exit criteria are measurable (true/false evaluable)
[ ] The routing table entry correctly describes when to invoke this skill
[ ] The skill does not duplicate an existing skill's core responsibility
```

No automated validation in MS-004/MS-005. Human review is sufficient.

**Why not a self-validation subagent?** The generated SKILL.md is prose + markdown. A subagent could check structural completeness (all required sections present) but not behavioral correctness (does this phase gate make sense?). Human review catches correctness; a structural check catches format errors. Structural check can be added as a simple regex/grep in a later version.

---

### Q3: Phase gate generation

**Decision: Template from work type, specialize for the skill.**

All SweetClaude work types have defined phase gates in `phase-gates.md`. The generator uses these as templates:

1. **Map the skill to the closest work type** (from Q1/Q2 interview)
2. **Extract the phases the skill spans** from the work type's gate set
3. **Keep only the gates that apply** — a skill spanning only DEFINE and IMPLEMENT does not need SHIP gates
4. **Specialize the gate text** to the skill's specific artifacts and criteria

For skills that don't map to any work type ("it's a utility"):
- Default template: DEFINE → IMPLEMENT → VERIFY → SHIP with generic gates
- User customizes the gate text in the review pass

**The insight:** Phase gates are essentially "what artifact proves this phase is done?" For any new skill, the generator asks: "What file, state change, or observable behavior proves each phase is complete?" and formats the answer as exit criteria.

---

### Q4: Agent vs. skill

**Decision: Top-level skill. Internal subagents as needed.**

`sweetclaude:skill-generator` is a skill — user-invoked via `/sweetclaude:skill-generator`. It interacts with the user directly, conducts the interview, presents the output, and writes files.

**Internal subagents may be used for:**
- Parallel generation of the SKILL.md sections (description, steps, rules, shell block) if they can be generated independently
- A "duplicate check" subagent that scans existing skills for overlap before Stage 4

**Not a pure subagent because:** The interview (Q1–Q4) requires back-and-forth with the user. A subagent spawned from another skill cannot conduct this interview — it receives its instructions in one shot.

**The skill spawns no persistent agents.** All work happens within the session.

#### Duplicate Check Subagent Specification (from BL-010)

Before Stage 4 (SKILL.md generation), the duplicate check subagent must perform **all four checks** and return a structured finding. Failing to run these checks is how ~18/38 spec proposals in the syncog inventory batch ended up duplicating existing skills.

**Check 1 — Full skill body scan (not just frontmatter).**
Read the complete text of every existing SweetClaude skill in the same domain bucket (`code-*`, `product-*`, `design-*`, `document-*`, etc.), not just their frontmatter or directory names. Mode routing is invisible from titles alone.

**Check 2 — Verb/mode grep inside skill bodies.**
Before declaring "no skill exists for X," grep `skills/*/SKILL.md` for the primary verb or mode name. Example: to check whether a `corpus-triage` skill is needed, grep for `triage` in skill bodies — do not rely on `ls skills/ | grep triage`.

```bash
grep -rn "triage\|{mode-verb}" skills/*/SKILL.md
```

**Check 3 — Flag `$ARGUMENTS` mode-routing lines.**
These patterns indicate a multi-mode consolidated skill. Any skill with these patterns already handles modes that would otherwise look like separate skills:
- `If $ARGUMENTS was passed`
- `route directly`
- `skip the menu and route`
- `$ARGUMENTS` routing

If any existing skill contains these patterns for the proposed skill's domain, it is likely already handled.

**Check 4 — Read the first 30 lines of each existing skill in the bucket.**
Several skills (`code-testing`, `code-review`, `document-corpus`) open with a numbered menu of internal modes. Reading just the opening section of each skill in the domain bucket catches most consolidations without reading the full file.

**Subagent output format:**
```
DUPLICATE CHECK RESULTS
───────────────────────
Proposed skill: {name}
Domain bucket: {code|product|design|document|framework}

Existing skills scanned: {list}
Modes found in existing skills matching proposed scope: {list or "none"}
$ARGUMENTS routing patterns found: {list or "none"}
Verdict: DUPLICATE (already handled by {skill} Mode: {mode}) | PARTIAL OVERLAP ({what overlaps}) | CLEAR GAP (no existing skill covers this)
Confidence: HIGH | MEDIUM | LOW
Notes: {any ambiguity or edge cases}
```

If verdict is DUPLICATE or PARTIAL OVERLAP, surface to the user before Stage 4 and ask whether to continue, adjust scope, or abandon.

---

### Q5: Integration with /sweetclaude:go routing table

**Decision: Generator produces a routing table proposal; user confirms and adds it manually.**

The generator outputs, as part of Stage 5, a proposed routing table entry:

```markdown
Add to sweetclaude:go routing table:
| {work type} | {phase} | {trigger condition} | sweetclaude:{skill-name} |
```

And a proposed `find-skill` routing entry:

```markdown
Add to sweetclaude:find-skill routing section:
Route to sweetclaude:{skill-name} when users say: "{trigger phrases}"
```

**Why manual?** Routing table entries require human judgment — the generator can propose, but the user decides if the trigger condition is correct. Automatic injection risks routing collisions with existing skills.

**Registration checklist output:** The generator also produces a one-page registration checklist:
- [ ] `skills/{skill-name}/SKILL.md` written
- [ ] Entry added to `~/.claude/plugins/sweetclaude@sweetclaude/skills/{skill-name}/SKILL.md`
- [ ] Routing table entry added to `skills/go/SKILL.md`
- [ ] Find-skill entry added to `skills/find-skill/SKILL.md`
- [ ] Skill registered in `.sweetclaude/state/skills.yaml` under the project using it (if project-specific)

---

## Stage-by-Stage Flow

```
Input: workflow description (free text)
  ↓
Stage 1: Intent extraction
  — What does this skill do in one sentence?
  — What is the user's trigger (why would they invoke this)?
  — What is the first thing the skill does?
  — What is the last artifact or state it produces?

  ↓
Stage 2: Work type mapping + interview
  — Interview: 4 questions (phase(s), work type, entry criteria, exit criteria)
  — Map to closest work type in workflow-templates.yaml

  ↓
Stage 3: Duplicate check (subagent)
  — Full body scan of existing skills in the same domain bucket
  — Grep for primary verb/modes within skill bodies
  — Flag any $ARGUMENTS mode-routing lines
  — Read first 30 lines of each skill in bucket for mode menus
  — Return structured verdict: DUPLICATE | PARTIAL OVERLAP | CLEAR GAP
  — If DUPLICATE or PARTIAL OVERLAP: surface to user before continuing

  ↓
Stage 4: Template adaptation
  — Pull phase gate template for the work type
  — Filter to phases the skill spans
  — Specialize gate text to this skill's artifacts
  — Generate deference level guidance (collaborative if interactive, guided/autonomous if largely automated)

  ↓
Stage 5: SKILL.md generation
  — Frontmatter (spdx-license, name, description)
  — Shell preprocessing block (session state + any skill-specific state reads)
  — One section per phase step the skill executes
  — Rules section (invariants — things the skill must never do)
  — Exit section (state files written, log appended)

  ↓
Stage 6: Review pass
  — Present complete SKILL.md to user
  — Checklist (6 items, listed above)
  — User approves or requests changes
  — Iterate until approved

  ↓
Output:
  — SKILL.md written to skills/{skill-name}/SKILL.md
  — Routing table proposal (copy-paste ready)
  — Find-skill routing proposal (copy-paste ready)
  — Registration checklist
```

---

## SKILL.md Required Sections

A generated SKILL.md must contain:

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:{skill-name}
description: "{one sentence — used in find-skill routing}"
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# {Skill Title}

{One paragraph: what this skill does and when to use it.}

---

## Step 1: {Entry guard / context read}
{shell block + prose}

## Step 2: ...

## Rules
- {Invariants — what this skill must never do}
```

The shell preprocessing block must read `session-state.yaml` (for deference level, active work item, paths). Additional reads depend on the skill's domain.

---

## Worked Example: sweetclaude:content-calendar

**Input description:** "I want a skill that helps me plan a content calendar for a blog or newsletter. Given a topic and audience, it produces a 4-week editorial calendar with topics, formats, and publication dates."

### Stage 1: Intent extraction

- **What it does:** Plans a 4-week editorial calendar from topic + audience input
- **Trigger:** User wants to plan blog/newsletter content
- **First action:** Read existing strategy context (discovery.yaml, product brief if present)
- **Last artifact:** `strategy/content-calendar-{yyyymmdd}.md` + optional `.sweetclaude/state/content-calendar.yaml`

### Stage 2: Work type mapping

- Closest work type: **net-new-feature** (producing a new artifact) or **enhancement** (if refining an existing calendar)
- Phases spanned: DEFINE (scope the calendar), IMPLEMENT (generate content), VERIFY (user review)
- Interview answers:
  1. Phases: DEFINE + IMPLEMENT + VERIFY
  2. Work type: net-new-feature
  3. Entry: project has a discovery.yaml or user can describe the topic and target audience
  4. Exit: `strategy/content-calendar-{yyyymmdd}.md` exists and user has approved it

### Stage 3: Template adaptation

From net-new-feature DEFINE/IMPLEMENT/VERIFY gates:
- **DEFINE exit:** Scope locked — topic area, audience, 4-week horizon, content format mix, publication frequency
- **IMPLEMENT exit:** All 4 weeks populated — topic, format (blog/video/newsletter/thread), publication date, headline draft
- **VERIFY exit:** User has reviewed and approved the calendar

### Stage 4: Generated SKILL.md

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:content-calendar
description: "Plan a 4-week editorial calendar for a blog or newsletter. Given topic area and audience, produces topics, formats, and publication dates."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Content Calendar

Four-week editorial planning. Input: topic area and audience. Output: calendar with topics, formats, and publication dates.

---

## Step 1: Read context

cat .sweetclaude/state/discovery.yaml 2>/dev/null || echo "DISCOVERY_MISSING"
ls strategy/content-calendar*.md 2>/dev/null | head -3

If an existing calendar exists: ask whether to extend it or create a new one.

## Step 2: Scope the calendar (DEFINE)

Ask:
1. "What is the topic area? (e.g., 'developer tools', 'personal finance', 'AI news')"
2. "Who is your audience? (one sentence — their role, knowledge level, what they want)"
3. "What formats do you publish? (blog posts, video scripts, newsletters, social threads — pick the mix)"
4. "How often do you publish? (daily, 3x/week, weekly)"

Wait for answers before proceeding.

**DEFINE exit:** Topic, audience, format mix, and frequency confirmed.

## Step 3: Generate the calendar (IMPLEMENT)

Produce a 4-week calendar:

| Week | Date | Topic | Format | Headline draft |
|---|---|---|---|---|
| 1 | {date} | {topic} | {format} | {draft headline} |
...

Each topic should:
- Be specific enough to write (not "AI tools" — "How to evaluate AI coding assistants in 30 minutes")
- Alternate formats per the user's mix
- Build a loose narrative arc across the 4 weeks (awareness → depth → application → next step)

**IMPLEMENT exit:** All 4 weeks populated.

## Step 4: Review and approve (VERIFY)

Present the full calendar. Ask:
> "Does this calendar look right? Anything to adjust — topics, dates, formats, or the headline direction?"

Iterate until approved.

**VERIFY exit:** User approves the calendar.

## Step 5: Write output

Write the calendar to `strategy/content-calendar-{yyyymmdd}.md`.

## Rules

- Never skip the scope questions — publishing frequency and format mix determine the calendar structure.
- Never produce "generic" topics — every topic must be specific enough to write.
- The 4-week arc should build toward something, not be a random topic list.
```

### Stage 5: Routing proposals

**sweetclaude:go routing entry:**
```
| any | any | No content calendar for current quarter | sweetclaude:content-calendar |
```
(This is an optional skill — only add to routing if you use it regularly.)

**sweetclaude:find-skill routing entry:**
```
Route to sweetclaude:content-calendar when users say:
"content calendar", "editorial calendar", "plan blog posts", "newsletter schedule",
"what should I write about next month", "content planning"
```

---

## Implementation Decision

**Defer to MS-005.** The design is complete. Implementation requires:
- Building the interview flow (4 questions + clarification loops)
- Phase gate template library (one template per work type × phase set)
- SKILL.md structural generation (frontmatter, shell block, step sections, rules)
- Worked example validation (5 more worked examples needed before implementation to pressure-test the design)

Estimated scope: medium. Not trivial, but not a blocker for MS-004. Prioritize in MS-005 after deploy bucket and mockup pipeline are in use and producing feedback.

---

## Open Questions (carry forward to MS-005)

1. **Template library completeness:** The worked example used net-new-feature. Need worked examples for tech-debt, bug-fix, and "utility" (no work type match) before implementing the template adapter.
2. **Routing collision detection:** How does the generator know if a proposed routing entry conflicts with an existing entry in `find-skill`? A simple substring search may be enough.
3. **Multi-phase skills:** Some skills (like `sweetclaude:adopt`) span unusual phase sequences. The generator needs to handle non-standard phase sequences gracefully.
4. **Skill update story:** When a generated skill needs to be updated, how does the user re-run the generator against the existing SKILL.md? Add a `--update {existing-skill-path}` mode in MS-005.
