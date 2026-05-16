# BL-020 Spike: OpenClaw

**Date:** 2026-05-05  
**Source:** https://github.com/openclaw (247K stars, ClawHub registry)  
**Status:** DONE

---

## What OpenClaw Actually Is

OpenClaw is not a Claude Code workflow framework. It is a self-hosted personal AI assistant that runs on your own devices and connects to messaging channels you already use — WhatsApp, Telegram, Discord, iMessage, Signal, and others. Its core value proposition is ambient, always-on automation: email drafting, calendar management, cross-app workflow triggers. It supports any LLM (Claude, GPT-4o, Gemini, Llama) and has a community skill registry (ClawHub) with 13,700+ skills. It is not a coding agent, has no codebase awareness, and has no native understanding of test suites, PRs, or development workflows.

This is relevant context for the BL-048 positioning brief: "OpenClaw" as a name competes for mindshare in the Claude Code ecosystem, but the product is entirely different.

---

## Architecture

OpenClaw uses a local-first Gateway that manages sessions, channels, tools, and agent routing. Extensions integrate through a manifest-first control plane with declared metadata. Skills are SKILL.md files — the same format Claude Code adopted — loaded from a six-level precedence stack (workspace > project > personal > bundled) and injected as compact XML into the system prompt at session start. Hooks are event-triggered handlers attached to 15+ Gateway events (session start/stop, message:received, command:new, etc.).

The hooks model is the key architectural divergence from SweetClaude. OpenClaw hooks are notification handlers — they write messages back to the user. SweetClaude hooks are enforcement mechanisms — they block prohibited actions (test-guardian) and run verification automatically (auto-test-runner). Same noun, different semantics.

---

## Overlap and Divergence with SweetClaude

**Structural overlap:**
- Both use SKILL.md as the instruction unit
- Both support hook-style event handlers
- Both support workspace-level skill overrides

**Where they diverge:**
- SweetClaude: phase gates with exit criteria (DISCOVER → SHIP), enforced by runtime state
- SweetClaude: TDD enforcement via blocking hooks, not advisory reminders
- SweetClaude: QA Caucus (parallel isolated subagents reviewing from 3 angles) — no equivalent in OpenClaw
- SweetClaude: deference levels (collaborative/guided/autonomous) — no equivalent
- SweetClaude: project modes with compiled effective-gates.yaml — no equivalent
- OpenClaw: ambient cross-channel messaging orchestration — absent from SweetClaude entirely

The closest OpenClaw has to SweetClaude's discipline is a community-authored `solo-build` skill on ClawHub that implements a red-green-refactor cycle. It is a community SKILL.md, not a runtime primitive. OpenClaw has no hook-based TDD enforcement at the framework level.

---

## Community Signals

OpenClaw has 247K GitHub stars and 13,700+ ClawHub community skills — far larger than SweetClaude in raw numbers. The community signal worth noting: at least six separate community repos exist that wrap Claude Code as an OpenClaw plugin (headless session manager, containerized execution, OAuth bridge, async job manager). Developers want OpenClaw's ambient orchestration layer sitting above Claude Code's coding capability. This is the interop surface worth watching.

One quality-signal issue: the February 2026 ClawHavoc incident revealed 341 malicious skills in ClawHub, prompting a community moderation layer. The scale of OpenClaw's skill registry introduces supply-chain risk that SweetClaude's curated, hand-authored skill model avoids by design.

---

## Skills 2.0 / SKILL.md Compatibility

OpenClaw has fully adopted the SKILL.md format. The same SKILL.md works in Claude Code, OpenClaw, and Codex CLI without modification. When spawning a Claude Code session, OpenClaw materializes a "temporary Claude Code plugin snapshot" — meaning SweetClaude's skills, as SKILL.md files, are technically injectable into an OpenClaw-orchestrated Claude Code session today without extra integration work.

This is the one practical bridge worth preserving: SweetClaude's SKILL.md-compatible format ensures it remains injectable from ambient orchestration environments without extra integration work. No action required — just maintain the format.

---

## Answers to Spike Questions

**1. Core value proposition:** Ambient AI assistant across messaging channels. Not a developer workflow tool.

**2. Architecture:** SKILL.md skills, event hooks (notification-style, not enforcement-style), local Gateway, ClawHub registry.

**3. Overlap/divergence:** Shared SKILL.md format is the only meaningful overlap. Phase gates, TDD enforcement, caucus review, deference model — none present in OpenClaw.

**4. Community demand signals:** Strong demand for OpenClaw-above-Claude-Code layering (6+ community integration repos). The coding workflow gap in OpenClaw is a real user need that SweetClaude fills from a different entry point.

**5. Skills 2.0 adoption:** Full SKILL.md compatibility. Practical interop surface exists today.

**6. Competitive threat or reference:** Neither. Different layer. Layered complementarity is the correct framing.

---

## Recommendation: Monitor SKILL.md Compatibility — No Action Required

OpenClaw is not a competitive threat. It does not address phase gates, TDD enforcement, or multi-agent code review — SweetClaude's three structural differentiators from the GStack analysis (BL-016) remain intact.

The one thing worth maintaining is SKILL.md format compatibility. If OpenClaw becomes the dominant ambient orchestration shell above Claude Code sessions, SweetClaude's SKILL.md-compatible skills will be injectable from that environment without integration work. This costs nothing to preserve — it is the current state.

No new backlog items required. BL-048 (competitive positioning brief) should note that OpenClaw occupies a different layer entirely and is not a peer comparison point.
