# SweetClaude User Guide

**Version:** 1.0
**Date:** 2026-05-01

Most AI coding tools start at implementation. SweetClaude starts at the idea.

That distinction shapes everything else. SweetClaude is a Claude Code plugin for the full lifecycle of building software — articulating what you are building and why, defining who it is for, designing the architecture, writing tests before code, reviewing what gets shipped, and keeping the resulting documents organized so you can find them six months later. It works with any language because the workflow discipline is the product, not the boilerplate.

This guide is the long form. The README on the front page sells the idea; these pages explain how it actually fits together when you sit down to use it.

---

## Where to Begin

If you are new and want a working install, read [Getting Started](getting-started.md). It walks you through your first session with sample interactions so you know what to expect when SweetClaude pushes back on your concept or asks you to challenge an assumption.

If you have it installed and want to understand the design decisions — why phases instead of a single linear flow, why TDD is enforced by hooks instead of asked-for in prompts, why SweetClaude refuses to estimate timelines — read [How It Works](how-it-works.md).

If you have a specific situation ("I have a messy pile of strategy docs," "I need to ship a hotfix," "I am adopting an existing codebase"), jump to [Walkthroughs](walkthroughs.md). Each scenario is end-to-end with the commands and what comes back.

If you are looking up a specific skill or phase, the [Skills Reference](skills-reference.md), [Phases and Workflows](phases-and-workflows.md), [TDD Levels](tdd.md), and [State and Memory](state-and-memory.md) pages are the lookups.

If you are deciding whether SweetClaude is the right tool for what you are doing, the [FAQ](faq.md) is honest about when it is and is not.

---

## What Is in This Guide

| Page | What it is |
|---|---|
| [Getting Started](getting-started.md) | A tutorial. Install through your first feature. Includes sample interactions so you can recognize the rhythm. |
| [How It Works](how-it-works.md) | The mental model. Why two-dimensional state, why phase dwelling, why deference levels, what survives a crash. |
| [Walkthroughs](walkthroughs.md) | Six concrete scenarios end-to-end. New product from a napkin sketch, hotfix, doc pile, course correction, existing repo, building one feature with full TDD. |
| [Phases and Workflows](phases-and-workflows.md) | Reference for the 7 phases, 6 workflow shapes, 19 work types, hard and soft gates, progressive disclosure by version stage. |
| [Skills Reference](skills-reference.md) | All 52 skills with invocation, purpose, and common combinations. |
| [TDD Levels](tdd.md) | The four enforcement levels and the design choice underneath them. Why hooks, not prompts. |
| [State and Memory](state-and-memory.md) | What lives in `.sweetclaude/`, how it survives sessions, what to commit. |
| [Corpus and RAG](corpus-system.md) | Document pipeline (consolidate → triage → reconcile → promote) and local semantic search. |
| [FAQ](faq.md) | Honest answers. When SweetClaude is the right tool. When it is not. |

---

## A Note on Voice

Throughout these pages you will see SweetClaude take positions. It thinks unbounded autonomous coding agents are bad ideas without phase gates. It thinks tests and implementations should be written by separate contexts so neither can rationalize away the other. It refuses to give time estimates because AI-assisted development does not run on calendar time.

This is by design. SweetClaude is opinionated software with a workflow that came from one person building things and finding out which steps could be skipped without consequences and which ones could not. The opinions are documented here so you can take them, leave them, or argue with them — but you will not have to guess what they are.

---

## Quick Reference

```
/sweetclaude:on          Activate on any project — new or existing
/sweetclaude:go          Pick up where you left off
/sweetclaude:find-skill  Describe what you want to do
/sweetclaude:status      Where am I in the pipeline
/sweetclaude:help        All commands organized by category
```

The other 47 skills are documented in the [Skills Reference](skills-reference.md). Most of them are invoked automatically by `/sweetclaude:go` based on your project state. You rarely need to memorize commands.
