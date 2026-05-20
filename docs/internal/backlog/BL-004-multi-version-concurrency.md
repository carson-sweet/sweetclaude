---
id: BL-004
title: Multi-version concurrency in version_stage tracking
priority: P3
status: backlog
created: 2026-04-29
---

## Summary

Support tracking multiple concurrent major versions, each with their own `version_stage`, within a single project.

## Context

The version_stage model (PROTOTYPE → ALPHA → BETA → GA → SCALED → MAINTAINED) applies per major version, not per product. A product may eventually have v1 at MAINTAINED while v2 is in ALPHA — both in flight simultaneously.

Currently `phase.yaml` assumes one active version at a time (flat `version_stage` field). This is the right call for the solo-dev / small-team target user, who will almost never run parallel versions. By the time a team has this problem, they likely have a larger team and different tooling.

## Design intent (build to the concept)

The field is named `version_stage` (not `product_stage`) so the semantic is correct now. Future extension: replace the flat field with a `versions:` list where each entry carries its own `version_stage`. No structural breaking change required.

## Deferred until

SweetClaude targets teams large enough to maintain parallel major versions — likely v3+.
