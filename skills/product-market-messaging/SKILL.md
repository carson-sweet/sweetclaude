---
spdx-license: AGPL-3.0-or-later
description: "Craft external messaging — how you describe the product, the problem, and the value to different audiences. Builds on positioning statement and ICP."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Market Messaging

Craft external messaging for: $ARGUMENTS

## Context

Read `strategy/concept.md`, `strategy/pain-thesis.md`, `strategy/ideal-customer-profile.md`, `strategy/positioning-statement.md`, and `strategy/competitive-analysis.md` if they exist. Messaging builds on all of these.

## Process

### 1. Audience mapping

Different audiences need different messages. Identify which apply:
- **Primary users** (the ICP)
- **Decision makers** (if different from users — buyers, managers, executives)
- **Technical evaluators** (if the product has a technical buy-in process)
- **Partners/investors** (if relevant)
- **Community** (if open-source or community-driven)

### 2. For each audience, produce:

**Elevator pitch** (30 seconds):
> {2-3 sentences. Problem → solution → why you.}

**Value proposition** (one paragraph):
> {What you do, for whom, what's different, what the outcome is.}

**Key messages** (3-5 bullet points):
> - {message 1 — addresses the primary pain}
> - {message 2 — addresses differentiation}
> - {message 3 — addresses credibility/trust}

**Proof points** for each message:
> - {evidence that backs the claim — data, testimonials, benchmarks, research}

### 3. Tone and voice

- What is the personality? (authoritative, approachable, technical, provocative)
- What words do you use? What words do you avoid?
- What is the reading level? (match the ICP)

### 4. Save

Save to `strategy/market-messaging.md`. Each audience section is a standalone reference for writing landing pages, pitch decks, emails, or social content.
