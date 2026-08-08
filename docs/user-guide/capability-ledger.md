# Capability Ledger

**Version:** 1.0
**Date:** 2026-08-08

The capability ledger answers one question: **which parts of SweetClaude are
known to work, which are compromised, and which are broken.**

It is generated, not written by hand. `scripts/capability_ledger.py` reads
`config/capability-manifest.yaml`, the coverage report, and the behavioral
contract map, and emits a row for every declared capability.

```bash
python3 scripts/capability_ledger.py --format markdown
python3 scripts/capability_ledger.py --coverage coverage.json --out ledger.md
```

CI runs it on every pull request and uploads the result as a build artifact.

---

## The rule that makes it useful

**A capability with no verification path is reported as `broken`, never
omitted.** An omitted capability is indistinguishable from a working one, so
leaving something out of the table would quietly turn "we never checked" into
"it works".

That means a `broken` row does not always mean the feature is faulty. It can
also mean the capability is under-declared — no `verification_commands`, no
resolvable `delegate_skill`, no entrypoint. The Notes column says which.

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `works` | Declared, verified, nothing outstanding. |
| `compromised` | Verified, but a documented limitation applies — unsupported states, rollback limitations, or entrypoint coverage below the bar. |
| `broken` | A verification fails, or the capability has no verification path at all. |
| `not-mechanically-verifiable` | Tier 3. Scored only by running `/sweetclaude:behavioral-regression` against a live model. |

---

## Verification tiers

Coverage means different things for different surfaces, and only two of the
three are mechanical.

| Tier | What it covers | Can CI decide it? |
|---|---|---|
| `tier-1-structural` | Contracts over the skill corpus — guards name the right state file, references resolve, frontmatter is valid. | Yes |
| `tier-2-executable` | Line coverage over Python entrypoints. | Yes |
| `tier-3-behavioral` | Whether the model follows an instruction. | No — needs a live model |

Tier 3 rows are always reported as `not-mechanically-verifiable` and carry
their contract ids. Reporting them as passing from CI would be a claim the
ledger cannot support.

---

## Adding a capability

Add an entry to `config/capability-manifest.yaml`. At minimum it needs
`title`, `verification_commands`, and either a `delegate_skill` or a
`command_entrypoint`. If it sets `mutates_project: true` it must also declare
working `rollback_support` — `tests/test_capability_manifest.py` enforces that,
and the ledger reports a violation as `broken`.

Capabilities that are known-broken or partially working should be declared as
such rather than left out. The ledger records reality.
