---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Technical specification — every decision a developer needs before writing the first line of code."
category: technical
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Design Tech Spec

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.technical.base_path`. This is the base directory for all technical artifacts.

3. Construct full paths as `{base_path}/{filename}`, e.g. `{base_path}/architecture.md`, `{base_path}/tech-spec-v1.md`.

4. Write artifacts to those paths.

Define every technical decision a developer needs before committing code against user stories. This is the bridge between architecture decisions and day-one development.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/architecture.yaml` — required for architecture style and compliance requirements. If missing:
> "The tech spec builds on architectural decisions. I recommend running `design-architecture` first. Want to do that now, or continue without it?"
Accept if user declines. Log degraded. Note any compliance requirements from architecture state — treat them as hard requirements throughout.

Read `.sweetclaude/state/discovery.yaml` for project type and intent (informs cost/complexity recommendations).

## Interview and Decision Process

For each topic below: describe the decision to be made, ask what the user knows or prefers, offer a recommendation, record the decision. Always factor in:
- User's situation (solo founder, small team, larger team — ask if not known from prior state)
- Cost constraints (ask: "Are you bootstrapping or do you have runway for infrastructure costs?")
- Compliance requirements from architecture state (treat as non-negotiable)

### Repo Structure

"Will this be a monorepo (all code in one repository) or separate repos per service/component?"

Recommendation guidance:
- Monolith or small team → monorepo (simpler tooling, easier cross-cutting changes)
- Many services with separate teams → polyrepo (clear ownership, independent deploys)
- Bootstrapping → monorepo (lower tooling cost)

Also decide: branching strategy (trunk-based, gitflow, or other) and PR workflow.

### Source Control Platform

"GitHub, GitLab, Bitbucket, or self-hosted?"

Recommendation guidance: GitHub for most projects (ecosystem, Actions, Copilot integration). GitLab if self-hosting or compliance requires it.

### Local Development Environment

"How will developers run the app locally?"
- Native (install dependencies directly)
- Docker Compose (containerized local stack)
- Dev containers (VS Code devcontainer or similar)
- Nix or similar reproducible environment

Recommendation: Docker Compose for most projects with external dependencies (database, cache). Native for simple apps or CLIs.

Also: what toolchain is needed (package manager, build tools, linters)?

### Environments

"What environments do you need?"

Minimum viable: local dev + production.
Recommended: local dev + staging + production.
Full: local dev + CI + staging + production (+ feature environments if needed).

For each environment: how does it differ from production (data, scale, access), and how do you promote between them?

### CI/CD

"What CI/CD platform?" (GitHub Actions, GitLab CI, CircleCI, other)

For each environment, define the pipeline:
- **On every PR:** {lint, typecheck, unit tests, security scan, build check}
- **On merge to main:** {build, deploy to staging, integration tests}
- **Production gate:** {manual approval | automated smoke tests | canary | all three}
- **Rollback plan:** {how to roll back a bad deploy in under 5 minutes}

### Hosting Provider

"Where will this run in production?"

Ask about:
- Compute: serverless (Lambda, Cloud Run, Vercel), containers (ECS, Cloud Run, Fly.io), VMs (EC2, GCE), PaaS (Railway, Render, Heroku)
- Database hosting: managed (RDS, PlanetScale, Neon, Supabase) vs. self-managed
- Storage: S3-compatible, Cloudflare R2, or provider-native
- CDN/edge: Cloudflare, Fastly, provider CDN

Factor in cost constraints. Bootstrapping → Fly.io, Railway, or Render for compute; Neon or Supabase for database. Funded → AWS/GCP/Azure with managed services.

If compliance requirements exist: confirm that chosen provider meets those requirements (e.g., HIPAA BAA, SOC 2 certification, data residency).

### Auth

"How will you handle authentication and authorization?"

Options:
- Managed auth service (Auth0, Clerk, Supabase Auth, Cognito) — faster, more expensive at scale
- Self-hosted auth library (NextAuth, Lucia, Passport) — more control, more to maintain
- OAuth only (for developer tools) — simpler if users already have GitHub/Google accounts

Authorization: role-based (RBAC), attribute-based (ABAC), or simple permissions?

If PII/PHI is involved: auth must support audit logging and session management — flag these as requirements.

### Monitoring and Observability

"What will you monitor?"

Define:
- **Uptime monitoring:** Which endpoints? What SLA? (e.g., Uptime Robot, Better Uptime)
- **Application monitoring / APM:** Error tracking and performance (Sentry, Datadog, New Relic, or provider-native)
- **Logging:** Structured JSON logging. Log levels (error, warn, info, debug). Retention period. Destination (CloudWatch, Datadog, Logtail, self-hosted).
- **Alerts:** Who gets paged? At what threshold? (e.g., error rate > 1% for 5 minutes, p99 latency > 2s)
- **Dashboards:** What does on-call watch? (key metrics: request rate, error rate, latency, queue depth)

Bootstrapping: Sentry (free tier) + Uptime Robot + provider logs is sufficient to start.

### Scaling

"What's your expected load profile at launch and at meaningful scale?"

Define:
- Expected concurrent users at launch
- What triggers horizontal scaling (more instances) vs. vertical scaling (bigger instance)
- Known bottlenecks (database, external API rate limits, file processing, etc.)
- Any stateful components that complicate horizontal scaling (sessions, file uploads)

For bootstrapped projects: don't over-engineer. Define the scaling story so you know where the ceiling is, not to build for it now.

## Tech Spec Document

Write the tech spec with all decisions documented. Standard sections:
- Repo and source control
- Local development setup (step-by-step for a new developer)
- Environments
- CI/CD pipeline (include the pipeline config skeleton if using GitHub Actions or similar)
- Hosting architecture diagram (ASCII)
- Auth design
- Monitoring and observability setup
- Scaling strategy
- Compliance requirements (labeled HARD REQUIREMENTS if applicable)

When the tech spec is reviewed and approved to final:
> "The architecture document, ADRs, tech spec, and user stories are now complete. This set is ready for development handoff."

## Document Production System

File naming: `{base_path}/{project-name}-tech-spec-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: standard schema.

## Exit

Write `.sweetclaude/state/tech-spec.yaml`:

```yaml
repo_structure: monorepo | polyrepo
source_control: github | gitlab | bitbucket | other
environments: []
cicd_platform: {}
hosting_provider: {}
auth_approach: {}
monitoring_tools: []
scaling_notes: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-tech-spec (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets}
**Compliance requirements applied:** {list or none}
**Open questions:** {bullets}
```
