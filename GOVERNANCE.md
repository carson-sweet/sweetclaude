# Governance

**Version:** 1.0
**Date:** 2026-05-01

SweetClaude is currently maintained by one person. This document describes how the project makes decisions now, and how that structure should evolve as contributors join.

---

## Current State (Single Maintainer)

**Maintainer:** Carson Sweet ([@carson-sweet](https://github.com/carson-sweet))

Decision authority in the current state:
- Architecture and design decisions: maintainer
- Merge authority: maintainer
- Release decisions: maintainer
- Roadmap prioritization: maintainer, with input from Issues and Discussions

This is honest, not ideal. Single-maintainer projects have a known failure mode. The active co-maintainer search ([issue #7](https://github.com/carson-sweet/sweetclaude/issues/7)) is the path to the structure described in the next section.

---

## Target State (With Co-Maintainer)

When a co-maintainer joins, governance transitions to:

**Merge authority:**
- Either maintainer may merge pull requests in their area of expertise
- Changes to the hook system, migration registry, orchestration layer, and `config/` require review by both maintainers before merging
- Documentation and isolated skill changes (product/design skills) may be merged by either maintainer unilaterally

**Roadmap decisions:**
- Discussed in GitHub Discussions or Issues before implementation begins
- Either maintainer may block a roadmap item with a written rationale
- Unresolved disagreements: the maintainer who has owned the affected area longer makes the call, documented in the decision log

**New maintainer onboarding:**
- Co-maintainers are identified from active contributors
- The onboarding path: isolated skill contribution → core skill contribution → co-maintainer
- Co-maintainer status requires demonstrated understanding of the full framework (hook system, migration registry, phase pipeline) and is granted explicitly, not assumed from contribution history

---

## Contribution Decision Process

**Small changes** (docs, isolated skills, bug fixes): open a PR. No prior issue required.

**Significant changes** (new work type, new workflow shape, changes to `config/workflow-templates.yaml`, hook changes): open an issue first. Describe the change and motivation. Wait for maintainer acknowledgment before investing implementation time. This is to protect contributors from building something that won't be merged.

**Breaking changes** (schema migrations, hook API changes, install.sh changes): require explicit maintainer sign-off before implementation begins. Post in Discussions or open a design issue.

---

## Release Process

SweetClaude uses semantic versioning. Version bumps are made by hand — there is no automatic version bump on commit. Releases are tagged on main. There is no separate release branch. The release steps, including the files to bump and the checks to run before tagging, are in [CONTRIBUTING.md](CONTRIBUTING.md#cutting-a-release).

The version badge in `README.md` is static. Update its version number and release link as part of the version bump.

---

## What Is Not Governance

This document does not cover:
- Code style enforcement (there is none)
- Commit message enforcement beyond the conventional commit format
- Response time SLAs (the maintainer is one person; response times vary)

For community expectations, see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
