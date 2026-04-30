---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:product-discovery
description: Establish what is being built, for whom, and why — at the depth appropriate for the project type. Three depth levels from quick intent to full pain thesis.
---

# Product Discovery

Establish what is being built, for whom, and why. This skill conducts a structured interview at the depth you choose — from a quick orientation to a full pain thesis.

## Entry

Check for `.sweetclaude/` directory. If not found:
> "This project isn't configured for SweetClaude yet. Run `/sweetclaude:on` to set it up, then try again."
Stop.

Check for `.sweetclaude/log.md`. If not found, create it with the header `# SweetClaude Effort Log`.

## Depth Levels

Before starting, ask:
> "How deep do you want to go with discovery?
> - **L1 — Intent and boundaries:** Quick orientation — what you're building, for whom, and what's explicitly out of scope. Takes 2–3 questions.
> - **L2 — Problem and success:** Adds a concrete problem definition, audience refinement, success criteria, and a challenge of your framing. Good for significant internal tools.
> - **L3 — Full pain thesis:** Adds pain measurement, market context, accountability analysis, escalation chains, and a validation rubric. Appropriate for commercial products.
> Which level, or should I suggest based on what you tell me about the project?"

If the user asks for a suggestion: ask what they're building and their intent (L1 question), then recommend a level based on their answer. Commercial → recommend L3. Internal tool → recommend L2. Utility or hobby → recommend L1.

## L1 — Intent and Boundaries

Ask one question at a time. Do not combine questions.

1. "Describe what you're building in your own words."

2. If the target user is not apparent from their answer: "Who is this for?"

3. "What is this — commercial product, internal tool, simple utility, hobby project, or something else?"

4. "What is this explicitly NOT? Give me at least one thing that's out of scope."

After these questions, produce:

```
**What:** {one-sentence description}
**For:** {target user}
**Intent:** {commercial | internal | utility | hobby | other}
**Not in scope:** {at least one item}
```

Present this and ask if it's accurate. Adjust until confirmed.

If the user chose L1, go to [Exit]. Otherwise continue to L2.

## L2 — Problem and Success

Do not re-ask anything captured in L1.

5. "What specific problem does this solve? Give me a concrete scenario — a specific person in a specific situation, not an abstract pain."

6. "For the person in that scenario: what does success look like? What are they able to do or stop doing?"

7. **Challenge the framing.** Propose at least one of:
   - An alternative framing of the problem ("Another way to see this: [reframe]. Is the real problem upstream/downstream of what you described?")
   - A gap ("You said X, but what about Y — have you thought through that?")
   - A questionable assumption ("This assumes Z is true — is it?")
   Do not accept the first framing without scrutiny.

After discussion, produce an updated concept statement incorporating L2 additions. Present and confirm.

If the user chose L2, go to [Exit]. Otherwise continue to L3.

## L3 — Full Pain Thesis

Do not re-ask anything captured in L1 or L2. Ask one question at a time.

8. "What do people use today to deal with this problem?" (existing approaches/alternatives)

9. "Why does that fail — what specifically breaks or falls short?"

10. "Is this problem a must-have to solve (like medicine — budget already exists for this category) or a nice-to-have (like vitamins — discretionary spending)?"

11. "Who gets fired, fined, or blamed when this problem isn't solved?" (accountability owner)

12. "Why can't they fix it themselves?" (control gap)

13. "Walk me through what happens when this problem hits — from the first sign to the worst case." (escalation chain)

14. "Can this problem be measured in time lost or money spent? If so, roughly how much per instance?"

15. "Is there any market research, analyst coverage, or industry data on this problem — market size, problem descriptions, or published statistics you're aware of?"

16. Produce a **Validation Rubric** assessing the current state of evidence:

| Pain element | Status | Evidence |
|---|---|---|
| Pain exists | 🔴 Assumption / 🟡 Qualitative / 🟢 Quantified | {what you have} |
| Pain is owned | 🔴 / 🟡 / 🟢 | {what you have} |
| Budget exists | 🔴 / 🟡 / 🟢 | {what you have} |
| Existing solutions fail | 🔴 / 🟡 / 🟢 | {what you have} |

🔴 = intuition or assumption only. 🟡 = qualitative evidence (conversations, observed behavior). 🟢 = quantified (specific costs, specific buyer quotes, data).

Present the rubric and explain: "The goal before committing to a wedge is to move every critical element from Red to Yellow, and the top three from Yellow to Green."

17. "What is the narrowest, most painful slice of this problem that a buyer or user would want solved on its own — before seeing anything else?" (wedge)

Apply the **checkbook test**: "If you described only this capability in a meeting, would they write a check or sign up?" Discuss until the wedge is clear.

Produce the complete pain thesis. Present and confirm.

## Frustration and Skip Handling

If the user seems frustrated at any point, offer:
> "We can proceed with what we have so far, or come back to this section. Which would you prefer?"

Accept immediately. Log what was skipped.

## Compliance Context

After the user confirms the concept statement at their chosen depth level, and before writing state files, ask these three questions. One at a time.

**A. Data categories:**
> "What data will this service handle? Select all that apply:
> - **PII** — names, emails, addresses, government IDs
> - **Financial** — payment methods, transaction records, account balances
> - **Health / medical** — diagnoses, prescriptions, health records
> - **Behavioral / tracking** — usage logs, location data, clickstreams
> - **None of the above**"

**B. User geography:**
> "Where are your users? Select all that apply:
> - **United States**
> - **European Union or UK**
> - **Global or unknown**
> - **Other** (specify)"

**C. User type:**
> "Who are your users? Select all that apply:
> - **Consumers (B2C)**
> - **Enterprise / business users (B2B)**
> - **Minors or potentially mixed-age audience**
> - **Healthcare providers or patients**
> - **Financial services users**"

Derive applicable frameworks from answers:

| Condition | Framework |
|---|---|
| EU or UK geography AND any non-none data category | `gdpr` (required) |
| US geography AND health data | `hipaa` (required) |
| Financial data present | `pci_dss` (required) |
| Minors in user type | `coppa` (required) |

**Fallback:** If none of the above rows apply, use `gdpr_floor`. Never include `gdpr_floor` alongside `gdpr`, `hipaa`, `pci_dss`, or `coppa` — it is only used when no specific framework was triggered.

> If the user selects only "None of the above" for data categories, set `data_categories: []` and still apply `gdpr_floor` — baseline data handling obligations exist regardless of tracked data types.

**Note on "Global or unknown" geography:** A global product with PII or health data likely has EU users. Apply `gdpr_floor` and add a note in the `notes` field: "GDPR may apply if EU users are present — confirm before launch."

Write `.sweetclaude/state/compliance-context.yaml`:

```yaml
schema_version: 1
collected_at: {YYYY-MM-DDTHH:MM:SSZ}
data_categories:
  - {pii | financial | health | behavioral | none}
user_geography:
  - {us | eu_uk | global | other}
geography_notes: null    # free text for "Other" geography specification
user_type:
  - {b2c | b2b | minors | healthcare | financial}
derived_frameworks:
  - {gdpr | hipaa | pci_dss | coppa | gdpr_floor}
notes: null
```

## Exit

Write `.sweetclaude/state/discovery.yaml`:

```yaml
project_type: commercial | internal | utility | hobby | other
intent: {one-line}
problem_summary: {one-line, or "" if L1 only}
target_user_summary: {one-line}
depth_run: L1 | L2 | L3
not_scope:
  - {item}
pain_thesis_present: true | false
validation_rubric_run: true | false
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-discovery ({depth})

**Status:** completed
**Depth:** {L1 | L2 | L3}
**Produced:** none (state only)
**Skipped/shortcuts:** {what was skipped, or none}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
