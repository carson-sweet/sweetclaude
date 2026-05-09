---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Guided milestone planning workshop."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Milestone Planning

A guided workshop for defining milestones that mean something. Not a form. Not a timeline exercise. An interactive session that forces outcome-framing, surfaces risks, and produces milestone definitions you can actually evaluate against.

**Ask one question at a time. No batching.**

---

## Step 0: Read context

```bash
# Read existing milestones if any
product_base=$(cat .sweetclaude/state/session-state.yaml 2>/dev/null | python3 -c "
import yaml,sys
d=yaml.safe_load(sys.stdin) or {}
print(d.get('paths',{}).get('product_base','.sweetclaude/product'))
" 2>/dev/null || echo ".sweetclaude/product")

echo "PRODUCT_BASE=$product_base"

# Existing milestones
ls ${product_base}/milestones/MS-*.md 2>/dev/null | head -10
if ls ${product_base}/milestones/MS-*.md 2>/dev/null | head -1 | grep -q .; then
  grep -h "\*\*Status:\*\*\|\*\*Outcome:\*\*\|^# " ${product_base}/milestones/MS-*.md 2>/dev/null | head -20
fi

# Next MS number
ls ${product_base}/milestones/MS-*.md 2>/dev/null | grep -oE 'MS-[0-9]+' | sort -t- -k2 -n | tail -1
```

Note `product_base` for use in Step 5.

If existing milestones are found: "I see you already have milestones defined — {summary of existing ones}. We'll plan new ones and slot them into the sequence."

---

## Step 1: Orientation

Ask these two questions one at a time. Wait for each answer before asking the next.

**Question 1:**
> "What's the current state of the product? One sentence is fine."

**Question 2:**
> "What would need to be true — in terms of user behavior or business outcomes — for you to feel like this product has genuinely moved forward?"

Save the answer to Question 2 as the **ORIENTATION FRAME**. Internally evaluate it:

- **OUTCOME_ORIENTED**: answer contains behavioral or metric language ("users can do X", "Y% do Z", "we stop having to do [manual thing]", "customers pay for it")
- **OUTPUT_ORIENTED**: answer describes delivery or features ("we launch X", "we finish Y", "we release Z")

This orientation affects whether the 2a challenge fires later. Do not tell the user which category they fell into.

If the answer to Question 2 is very vague or abstract, ask one follow-up:
> "Can you give me a concrete example — a specific thing you'd observe or measure that would tell you you'd made that progress?"

---

## Step 2: How many milestones?

Ask:
> "How many milestones do you want to define today — one milestone in depth, or a sequence?"

Accept: "one", "a few", "three", a number, or any clear variant. Proceed milestone by milestone. Complete all questions for one milestone before starting the next.

---

## Step 2 (per milestone): Define each milestone

Work through these questions one at a time for each milestone.

### 2a: The outcome

> "What state of the world are you trying to reach with this milestone?"

Evaluate the answer:

**If outcome-framed** (describes a behavior change, metric, or state that doesn't just mean "we shipped something"): acknowledge and continue.
> "Got it — you're aiming to [restate the outcome in their words]. Let's make that specific."

**If output-framed** (AND orientation was OUTPUT_ORIENTED or this answer is clearly output-framed regardless): apply the challenge once.
> "That tells me what you're building — useful context. What changes on the other side of that? What does a user do differently, or what metric moves, once [X] ships?"

- If the second attempt is outcome-framed: continue normally.
- If the second attempt is still output-framed: accept it, note internally as NEEDS_OUTCOME_WORK, continue. Do not challenge a third time.

**If orientation was OUTCOME_ORIENTED and this answer is consistent with that frame**: skip the challenge entirely. The user knows what they're doing.

### 2b: Success criteria

> "How will you know this milestone is reached? Be specific enough to defend it in a room of skeptics."

After the answer, apply the falsifiability test:
> "Describe a scenario where you've done all the work but this milestone is *not* met."

- If the user can describe such a scenario: criteria are specific enough. "Good — that test means the criteria actually have teeth."
- If the user says they can't think of one: "That usually means the criteria need tightening — if you can't imagine being proved wrong, the definition isn't specific enough yet. What would you need to see to be convinced you missed it?"
- Accept the revised answer. Do not loop more than once.

### 2c: Bets and risks

> "What are the 3–5 biggest bets or assumptions this milestone depends on? Things that need to be true for this to work, but that you haven't fully validated yet."

If the user draws a blank, offer a prompt:
> "Think about: user behavior assumptions, technical unknowns, market conditions, team capability, or dependencies on things outside your control."

Record the bets. These go into the milestone file.

### 2d: Prerequisites

> "What needs to exist before you can reach this milestone? Think hard prerequisites — things where the milestone literally cannot be achieved without them."

Accept "nothing" or "none" — not every milestone has hard prerequisites.

### 2e: Gate or checkpoint?

> "Is this milestone a **gate** or a **checkpoint**?
> — Gate: downstream work waits until this is done (example: auth system gate means nothing else ships without login)
> — Checkpoint: parallel work can continue while this is in progress (example: docs can be written in parallel with feature development)"

Accept "both" or "it depends" — record it with a note rather than forcing binary.

### 2f: Confidence

> "Gut level — how confident are you that this is the right bet right now? High, medium, low, or not sure."

If low or not sure:
> "What would need to be true for you to feel confident this is the right milestone to pursue?"

Record confidence level and any conditions.

---

## Early reward: preview after milestone 1

After completing questions 2a–2f for the **first milestone only**, show a draft of what the milestone file will look like:

```
Here's what this looks like as a milestone record:

───────────────────────────────
MS-{N}: {milestone name (derived from outcome)}
───────────────────────────────
Outcome:   {outcome statement from 2a}
Status:    Planned

Success criteria:
  · {criterion from 2b}
  (falsifiability: {scenario where not met})

Bets:
  · {bet 1 from 2c}
  · {bet 2 from 2c}
  ...

Prerequisites: {from 2d or "none"}
Type: {Gate | Checkpoint | Gate / Checkpoint (conditional)}
Confidence: {High | Medium | Low | Not sure}
  {conditions if low/not sure}
───────────────────────────────

Does this format work for you before we define the rest?
```

Wait for confirmation before continuing to the next milestone. If the user wants adjustments to the format or field names, note them and apply for all subsequent milestones.

---

## Step 3: Consistency check

After all milestones are defined, surface the orientation frame from Step 1:

> "You said that real progress looks like: **{ORIENTATION_FRAME}**.
>
> Looking at the milestones we defined:
> {list milestone names and one-line outcomes}
>
> Which of these does the most direct work toward that outcome? And is there anything that needs to be true — that none of these milestones directly address?"

If the user identifies a gap: offer to define an additional milestone or note it as an open question in the output.

If any milestone was flagged NEEDS_OUTCOME_WORK: revisit it now.
> "Earlier, {milestone name} was framed in delivery terms. Now that we have the full picture — what's the underlying outcome it's pointing at? Want to tighten the definition?"

Accept "leave it as is" — do not force a rewrite.

---

## Step 4: Sequence review

Show the full milestone sequence:

```
Planned sequence:
  MS-{N}: {outcome summary} [{Gate | Checkpoint}] [{confidence}]
  MS-{N+1}: ...
  ...
```

For each gate milestone:
> "What specifically is blocked while {gate milestone} is in progress? Is there anything that could proceed in parallel?"

Then apply these checks — as questions, not verdicts:

**Possible merger candidates** (if >5 milestones):
> "You have {N} milestones. Worth asking: could any two of these be merged without losing information? Which ones are most likely to change as you learn more?"

**Low-confidence milestones:**
> "{milestone} was marked low-confidence. Is this one to pursue now, defer, or investigate before committing?"

**Retrospective milestone signal** (if any milestone uses past-tense framing or describes a state that already exists):
> "{milestone} sounds like it might already be true. Is this a current-state marker, or a future milestone?"

**Circular dependencies** (if detected):
> "{A} depends on {B} and {B} depends on {A} — worth resolving before we write these up."

Present each flag one at a time. Wait for the user's response before moving to the next. Accept "leave it" for any flag.

**Sequence assignment:**
After all flags are addressed, show the agreed-upon order and propose sequence numbers:
> "Based on our sequence discussion, I'll assign these sequence numbers:
>   1 — {milestone name}
>   2 — {milestone name}
>   ...
> Confirm, or tell me how to adjust."

Wait for confirmation. Apply any adjustments. Sequence numbers go into each milestone's `**Sequence:**` field in Step 5 output.

---

## Step 5: Output

Determine the next MS number:

```bash
product_base=$(cat .sweetclaude/state/session-state.yaml 2>/dev/null | python3 -c "
import yaml,sys
d=yaml.safe_load(sys.stdin) or {}
print(d.get('paths',{}).get('product_base','.sweetclaude/product'))
" 2>/dev/null || echo ".sweetclaude/product")

last=$(ls ${product_base}/milestones/MS-*.md 2>/dev/null | grep -oE 'MS-[0-9]+' | sort -t- -k2 -n | tail -1 | grep -oE '[0-9]+')
echo "LAST_MS=${last:-0}"
mkdir -p ${product_base}/milestones
```

For each milestone, derive a slug from the outcome statement (lowercase, hyphens, max 6 words).

Show each file before writing:

```
I'll write these milestone files:

{product_base}/milestones/MS-{N}-{slug}.md
{product_base}/milestones/MS-{N+1}-{slug}.md
...

Write them?
```

On confirmation, write each file:

```markdown
# MS-{N}: {milestone name}

**Status:** Planned
**Sequence:** {N}
**Type:** {Gate | Checkpoint | Gate / Checkpoint (conditional)}
**Confidence:** {High | Medium | Low | Not sure}
**Created:** {today}

## Outcome

{outcome statement}

## Success criteria

{criterion}

**Falsifiability:** {scenario where work is done but milestone is not met}

## Bets

{numbered list of bets and assumptions}

## Prerequisites

{list or "None"}

## Notes

{any conditions on confidence, open questions, or flags from sequence review}
```

Write atomically (temp file → rename).

---

## Step 6: Hand off to tracking

After files are written:

> "Milestone files written. Handing off to sweetclaude:product-milestones to add tracking."

Invoke `sweetclaude:product-milestones` via the Skill tool, passing the new milestone IDs so they are added to the milestone index and tracking state.

If `sweetclaude:product-milestones` is not set up for this project, offer:
> "It looks like milestone tracking isn't set up yet. Run `/sweetclaude:product-milestones` to initialize it and pull in these milestone files."

---

## Rules

- Ask one question at a time. Never batch 2a–2f into a single message.
- The output-framing challenge fires only when warranted. Read the orientation frame and the current answer before deciding.
- The falsifiability test fires for every milestone — it is not optional.
- All Step 4 flags are questions. None are verdicts. Never say "you have too many milestones."
- Show the draft preview after milestone 1. Never skip it.
- The consistency check (Step 3) is mandatory. It is the primary defense against a set of individually well-formed milestones that don't trace to the stated outcome.
- Do not push for phase advancement. The user decides when milestone planning is done.
