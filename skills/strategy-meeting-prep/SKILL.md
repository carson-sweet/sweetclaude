---
name: strategy-meeting-prep
description: "Prepare for a specific meeting. Pulls relevant context from strategy corpus, drafts agenda, talking points with confidence levels, key asks, anticipated questions, and leave-behinds."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Meeting Prep

Prepare for meeting: $ARGUMENTS

## Input

Ask the user:
1. **Who** — who are you meeting with? Check `strategy/meeting-prep/` for existing stakeholder profiles.
2. **When** — when is the meeting?
3. **Purpose** — what's the goal? What outcome do you want?

## Process

### 1. Gather context

- Search the strategy corpus (RAG if available, otherwise read `strategy/` files) for content relevant to this meeting's topic and stakeholder.
- If `strategy/narrative-arc/` exists, check: what claims are strong enough to present vs. still soft?
- Read stakeholder profile if one exists.

### 2. Draft deliverables

**Agenda** with objectives:
```
1. {topic} — {objective for this topic} ({time allocation})
2. {topic} — {objective}
...
```

**Talking points** per topic:
- {point} — confidence: {high/medium/low based on evidence strength}
- {point} — confidence: {level}

**Key asks / desired outcomes:**
- {what you want from this meeting}

**Anticipated questions with prepared responses:**
- Q: {likely question}
  A: {prepared response with evidence}

**Leave-behinds** (if applicable):
- {one-pager, summary, or reference document to leave with the stakeholder}

### 3. Present for review

Present all deliverables. The user edits and approves before the meeting.

### 4. Post-meeting debrief

After the meeting, ask:
- What happened? What was decided?
- Any surprises?
- What follow-up is needed?

Save debrief to `strategy/meeting-prep/{stakeholder}-{date}-debrief.md`.
Update stakeholder profile with new context.

### Stakeholder profiles

Maintained in `strategy/meeting-prep/`:

```
strategy/meeting-prep/{name}.md
```

Each contains: role, relationship context, meeting history, what they care about, communication style notes. Updated after each debrief.
