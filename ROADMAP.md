# Roadmap

SweetClaude is in active development. This roadmap reflects current direction, not a commitment. Things move; priorities shift.

---

## Now

Work that is actively in progress or nearly complete.

- **OSS launch readiness** — Community surface, documentation gaps, README restructuring, behavioral contract status tracking. Most of Phase 1 and Phase 2 complete. See [oss-launch-readiness plan](docs/plans/oss-launch-readiness-2026-05-01.md) for the full breakdown.
- **Demo terminal recording** — A 90-second recording showing `/sweetclaude:on` through a first product brief skeleton. Pending.
- **Co-maintainer search** — Actively looking. See [issue #7](https://github.com/carson-sweet/sweetclaude/issues/7).

---

## Next

Committed work that hasn't started yet.

- **Behavioral regression CI** — Automate the 15-contract behavioral test suite against a CI trigger tied to model version tags. Turns the manual process into published, model-version-tagged compliance reports. Significant engineering; the most differentiating capability on the roadmap.
- **Deploy bucket** — SweetClaude covers everything up to SHIP but has no skills for deployment workflows. This is the largest functional gap. Likely covers: infrastructure-as-code review, environment promotion, rollback procedures, post-deploy smoke tests.
- **Standalone `init` and `adopt` skills** — Currently `/sweetclaude:on` handles both new and existing projects. Separating them into `init` (cold start) and `adopt` (existing codebase) would make the entry paths clearer and easier to maintain independently.

---

## Later

On the backlog but not actively planned.

- **Full README reorganization** — README (pitch only) + INSTALL.md + QUICKSTART.md. The current README is good enough; the structural reorganization is a polish pass for when there's a second maintainer to coordinate it.
- **Security planning skill** — A dedicated skill for the security planning work type. Currently handled through `product-discovery` compliance context and `code-review`. A standalone skill would make the ASSESS → DEFINE → SHIP workflow more explicit.
- **Infrastructure change skill** — Dedicated workflow for the infrastructure change work type. High-blast-radius work that currently relies on the abbreviated pipeline.
- **Mockup pipeline** — A design-to-implementation pipeline for UI-first projects: wireframes → component specs → component implementation.
- **Formal governance** — Contributor rights, merge authority, maintainer onboarding process. Meaningful once there's a second maintainer.

---

## What This Is Not

This roadmap is not a release calendar. SweetClaude does not generate timelines. The items above are direction, not schedule. Each moves from Later → Next → Now when conditions are right.

If you want to work on anything in Next or Later, open an issue or comment on an existing one. Co-maintainer and contributor work on roadmap items is welcome.
