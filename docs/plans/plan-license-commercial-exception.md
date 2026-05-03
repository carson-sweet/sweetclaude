# Plan: AGPL Commercial Use Exception
**Status:** planned
**Date:** 2026-05-03
**Priority:** strategic — compliance pipeline and AGPL are in direct contradiction

---

## Problem

The compliance pipeline (SOC 2, HIPAA, GDPR control tracking, evidence collection) is SweetClaude's strongest enterprise differentiator. Regulated enterprises — health tech, fintech, legal tech — are exactly the organizations that need it most. AGPL prohibits them from using it without open-sourcing all internal modifications and customizations. Legal teams at regulated enterprises refuse AGPL categorically.

This is not a theoretical concern. It is a direct feature/license contradiction that blocks the highest-value segment.

---

## Options Considered

| Option | Pros | Cons |
|---|---|---|
| **A. AGPL + private internal use exception** | Minimal change. Preserves copyleft for SaaS/hosted use. No new infrastructure needed. | Requires contributor CLA. Slightly unusual but well-precedented (GCC runtime exception, FOSS exception). |
| **B. Dual license (AGPL + commercial)** | Clean commercial story. Generates revenue. | Requires CLA, payment infrastructure, separate commercial terms, more legal surface area. |
| **C. Apache 2.0 or MIT** | Maximum adoption, zero friction. | Loses all copyleft protection. Anyone can offer SweetClaude as a hosted service without giving anything back. |
| **D. No change** | No effort. | The compliance features are unusable by the segment that needs them most. |

---

## Recommendation: Option A — AGPL + Private Internal Use Exception

**Why:** The spirit of the AGPL copyleft is to prevent companies from taking the code, wrapping it in a service, and offering it commercially without contributing back. A regulated enterprise using SweetClaude internally to build their own product is not that scenario. They're the user, not a distributor. An explicit exception for "private internal use without distribution" aligns the license with its intent while removing enterprise friction.

**Precedent:** MySQL FOSS exception, GCC runtime exception, MongoDB's original SSPL to AGPL transition. AGPL + linking/use exception is well understood by enterprise legal teams.

---

## What the Exception Covers

> **Private Internal Use Exception**
>
> Notwithstanding the terms of the GNU Affero General Public License, you may use, modify, and run SweetClaude for your organization's internal operations without the obligation to make your modifications available under the AGPL, provided that:
>
> 1. You do not distribute SweetClaude or any modified version to third parties.
> 2. You do not offer SweetClaude or any modified version as a service to third parties.
> 3. You do not sublicense or resell SweetClaude.
>
> For clarity: internal use means use by employees and contractors of a single organization for that organization's own work. Using SweetClaude to build a product you sell to customers is internal use. Reselling SweetClaude or offering it as a hosted AI tool to your own customers is not.

---

## What It Does NOT Cover

- Offering SweetClaude (or a fork) as a hosted service to third parties → full AGPL applies
- Bundling SweetClaude into a commercial product sold to others → full AGPL applies or requires a commercial license

---

## Implementation Steps

### Step 1: Contributor License Agreement (CLA)

Before adding an exception, all substantive contributors must grant rights to allow licensing under terms beyond AGPL. Without a CLA, copyright is fragmented across contributors and exceptions cannot be granted unilaterally.

Action: Set up a CLA via `cla-assistant.io` (free for open source). Add a CLA check to the PR process. Reach out to any past contributors for retroactive CLA signature.

Files to create:
- `.github/CLA.md` — CLA text
- `.github/workflows/cla.yml` — CLA bot workflow

### Step 2: Exception document

Create `LICENSE-EXCEPTION.md` in repo root:

```markdown
# SweetClaude Private Internal Use Exception

Version 1.0, 2026-05-03

[exception text as drafted above]

This exception is granted by the copyright holders of SweetClaude.
It supplements but does not modify the GNU Affero General Public License
under which SweetClaude is licensed.
```

### Step 3: Update LICENSE and README

In `LICENSE`: add a pointer at the top — "See LICENSE-EXCEPTION.md for a private internal use exception."

In `README.md` Dependencies table: update the SweetClaude license line to `AGPL-3.0 with private internal use exception`.

In `README.md` add a short Licensing section:

```markdown
## Licensing

SweetClaude is AGPL-3.0. A **private internal use exception** permits organizations to use
and modify SweetClaude for their own internal work without the AGPL copyleft obligation,
provided they do not distribute or resell it. See [LICENSE-EXCEPTION.md](LICENSE-EXCEPTION.md)
for the full terms.

For hosted or redistributed use, the full AGPL applies.
```

### Step 4: Update SPDX identifiers in skill files

SPDX doesn't have a standard identifier for AGPL + custom exception. Options:
- Leave `spdx-license: AGPL-3.0-or-later` as is (acceptable — exception is additive)
- Change to `spdx-license: AGPL-3.0-or-later WITH SweetClaude-exception-1.0`

Recommendation: leave as `AGPL-3.0-or-later` with a comment in CONTRIBUTING.md noting the exception. SPDX custom identifiers require registry submission; not worth the overhead for v1.

---

## Sequencing

1. Draft CLA text and get legal review (even informal)
2. Set up CLA bot
3. Contact prior contributors for retroactive signature
4. Once CLA infrastructure is in place: add `LICENSE-EXCEPTION.md`
5. Update `LICENSE`, `README.md`
6. Announce in GitHub Discussions with clear explanation of what changed and why

## Not In This Plan

- Commercial licensing tier (Option B) — deferred. Can be layered on top of this later if revenue model emerges.
- SPDX custom exception identifier — deferred.

## Risk

The exception is a grant by the copyright holder. If future contributions are made without a CLA and those contributors retain copyright, the exception cannot cover their contributions without their consent. The CLA step is non-optional.
