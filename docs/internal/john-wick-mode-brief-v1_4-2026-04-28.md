# Feature Brief: John Wick Mode for SweetClaude

**Version:** 1.4
**Author:** Carson Sweet
**Status:** Draft
**Last revised:** 2026-04-28
**License:** Distributed under the SweetClaude license (PolyForm Shield 1.0.0). Please do not forward without permission.



## What It Is

John Wick mode is a SweetClaude feature that orchestrates SweetClaude's development skills autonomously. Rather than requiring the user to invoke each skill manually and shepherd work through the pipeline phase by phase, John Wick runs the sequence end-to-end — driving product definition, design, test authorship, implementation, review, and pull request with minimal human involvement.

It is appropriate for well-scoped features where discovery is complete and the user wants to hand off execution rather than co-pilot it. The tradeoff is deliberate: less real-time collaboration in exchange for autonomous forward momentum.

Human pause points are explicit, pre-defined, and rare. Between them, the mode works without asking for guidance or checking in mid-step. It runs until it hits a gate, pauses cleanly, and resumes the moment it receives approval.

The pipeline spans multiple sessions by design. State is persisted after every step. If a session ends mid-run for any reason, the mode saves cleanly and picks up exactly where it left off.



## What It Is Not

- A replacement for human judgment. The pause points exist because certain decisions — approving requirements, approving design changes, triaging significant failures — require a human call.
- A tool for half-configured projects. If required discovery artifacts are absent, the mode does not start.
- Suitable for large or poorly-bounded work. If scope analysis indicates the feature is too large to reason about autonomously, the mode surfaces a warning and can refuse to proceed without explicit user override.
- Aware of other concurrent pipeline runs. Each feature runs its own isolated pipeline.



## Prerequisites

Before the pipeline starts, the mode validates that required discovery artifacts are present — user personas with tasks and success criteria, constraints analysis — and collects explicit user acknowledgment of autonomous mode. Missing prerequisites halt with a specific, actionable message.



## The Pipeline

The pipeline moves through six phases, each producing artifacts that carry forward into the next and building a traceable chain from requirements to pull request.

**Define.** Discovery artifacts are synthesized into a complete product requirements document without prompting the user for additional input. An automated review pass runs before the PRD is presented for approval. Only contested findings require active user decision; uncontested ones are applied automatically.

**Plan.** User stories are generated from the approved PRD, reviewed, and then converted into formal acceptance tests. These tests represent the behavioral contract for the feature before any implementation exists.

**Design.** An architecture document and technical specification are generated from the approved PRD and stories. A service contract analysis examines what the service promises to consumers, what it requires from providers, and where those assumptions are fragile. Compliance context flows through this phase automatically. After an automated review, contested design findings are presented to the user; approved changes cascade through downstream artifacts before anything is locked.

**Implement Prep.** Acceptance tests are implemented by an agent with no knowledge of the planned implementation, then reviewed for coverage gaps. The full suite is confirmed to be failing before any implementation begins. Test files are then locked — no subsequent pipeline step may modify them. Changes after this point require explicit user authorization.

**Implement.** The mode works through the story list sequentially, implementing each on its own branch and running the test suite after each. If a failure is not immediately resolvable or indicates a significant problem, the mode pauses and presents the situation to the user. All branches merge to the feature branch; main is not touched until the final pull request.

**Verify.** The full test suite runs on the completed feature branch. Code and security review runs. Documentation is updated to reflect the final implementation. A pull request is prepared and presented to the user for approval before anything is submitted.



## Compliance Awareness

Early in setup, the mode collects compliance context: what data categories the service handles, where users are located, and what kind of users they are. This is collected once and flows automatically through architecture decisions, contract analysis, and a final compliance review — the user never re-specifies requirements at each step.



## Scope Guardrails

If scope analysis indicates the feature exceeds reasonable bounds for autonomous execution, the mode surfaces a warning and recommends decomposing before continuing. Past a hard limit, it refuses to proceed without explicit user override. Autonomous pipelines compound scope problems: a feature too large to reason about clearly is too large to build autonomously.



## Drift Detection

Optional lightweight consistency checks can run at phase transitions. Each asks a single question: does this phase's output still match what came before? Before tests are locked, a significant finding can trigger a return to the appropriate approval gate. After tests are locked, findings escalate to the user only — the check-in cannot modify any locked artifact.



*This document describes the functional behavior of John Wick mode. It does not describe implementation architecture or internal mechanics.*
