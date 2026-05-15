---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Craft external messaging — how you describe the product, the problem, and the value to different audiences."
category: strategy
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:product-market-messaging" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Market Messaging

Craft external messaging for: $ARGUMENTS

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.strategy.base_path`. This is the base directory for all strategy artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/strategy`, competitive analysis goes to `.sweetclaude/strategy/competitive-analysis/`).

4. Write artifacts to those paths.

## Context

Read `{base_path}/concept.md`, `{base_path}/pain-thesis.md`, `{base_path}/ideal-customer-profile.md`, `{base_path}/positioning-statement.md`, and `{base_path}/competitive-analysis.md` if they exist. Messaging builds on all of these.

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

Save to `{base_path}/market-messaging/market-messaging.md`. Each audience section is a standalone reference for writing landing pages, pitch decks, emails, or social content.
