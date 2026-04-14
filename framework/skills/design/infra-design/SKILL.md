---
name: sweetclaude-design-infra-design
description: "Design infrastructure: deployment targets, environments, CI/CD pipeline, monitoring, and scaling strategy."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Infrastructure Design

Design infrastructure for: $ARGUMENTS

## Process

### 1. Deployment targets

- Where does this run? (AWS, GCP, Cloudflare, Vercel, bare metal, local)
- What services/resources are needed? (compute, database, storage, CDN, DNS)
- What are the cost constraints?

### 2. Environments

- Which environments? (dev, staging, production minimum)
- How do they differ? (scale, data, access, feature flags)
- How do you promote between them?

### 3. CI/CD pipeline

- What runs on every PR? (lint, typecheck, test, security scan)
- What runs on merge to main? (build, deploy to staging)
- What gates production? (approval, staging validation, canary)
- What's the rollback plan?

### 4. Monitoring and observability

- What do you monitor? (uptime, latency, error rate, queue depth)
- What alerts? (who gets paged, at what threshold)
- What do you log? (structured logging, log levels, retention)

### 5. Scaling

- What's the expected load?
- What scales horizontally vs vertically?
- Where are the bottlenecks?

### 6. Save

Save to `specs/infra-design.md`. Record key decisions via `design/manage-decisions`.
