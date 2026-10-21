# Capability Ledger

**Version:** 1.1
**Date:** 2026-10-21

The capability ledger answers one question: **which parts of SweetClaude are known to work, which are compromised, and which are broken.**

It is generated, not written by hand. `scripts/capability_ledger.py` reads `config/capability-manifest.yaml`, the coverage report, and the behavioral contract map, and emits a row for every declared capability.

```bash
python3 scripts/capability_ledger.py --format markdown
python3 scripts/capability_ledger.py --coverage coverage.json --out ledger.md
```

CI runs the ledger on pull requests to `main`, with `--no-behavioral` so the interaction-model rows are left out, and uploads the result as a build artifact. The committed snapshot in `capability-ledger-table.md` is the output of `python3 scripts/capability_ledger.py --no-behavioral --format markdown`, without coverage, so it is the same every time it is generated.

---

## The rule that makes it useful

**A capability that fails a declaration check is reported as `broken`, never omitted.** An omitted capability is indistinguishable from a working one, so leaving something out of the table would quietly turn "we never checked" into "it works".

That means a `broken` row does not always mean the feature is faulty. It means the manifest entry fails one of these checks, and the Notes column says which:

- A declared `delegate_skill` does not resolve to a skill.
- A declared entrypoint or executable script does not exist on disk.
- No `verification_commands` are declared.
- The capability sets `mutates_project: true` but declares no working rollback.

The ledger never runs the `verification_commands`. It checks that they are declared.

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `works` | Declared, passes the declaration checks, nothing outstanding. |
| `compromised` | Passes the declaration checks, but a documented limitation applies: an unsupported state with no defined handling (a behavior other than `block`, `diagnose_only` or `escalate`), rollback limitations, or entrypoint coverage below the bar. Unsupported states with defined handling do not downgrade a row. |
| `broken` | Fails a declaration check: an unresolved `delegate_skill`, a missing entrypoint script, no `verification_commands`, or a mutating capability without working rollback. |
| `not-mechanically-verifiable` | Tier 3 row that would otherwise be `works`. `scripts/behavioral_judge.py` scores it only when a rubric covers it; where no rubric covers the postcondition, nothing scores it today and the Notes column says so. |

---

## Verification tiers

Coverage means different things for different surfaces, and only two of the three are mechanical.

| Tier | What it covers | Can CI decide it? |
|---|---|---|
| `tier-1-structural` | Contracts over the skill corpus: guards name the right state file, references resolve, frontmatter is valid. | Yes |
| `tier-2-executable` | Line coverage over Python entrypoints. | Yes |
| `tier-3-behavioral` | Whether the model follows an instruction. | No, needs a live model |

Tier 3 rows that would otherwise be `works` are reported as `not-mechanically-verifiable`. A Tier 3 row that is `broken` or `compromised` keeps that status, because a genuine defect still shows. Contract ids appear only on the `interaction-model` rows, which are included unless `--no-behavioral` is passed, and each of those rows lists every contract id. Reporting a Tier 3 row as passing from CI would be a claim the ledger cannot support.

---

## Adding a capability

Add an entry to `config/capability-manifest.yaml`. The manifest validator requires `title`, `supports_project_shapes`, `mutates_project` and `requires_approval`, and a capability that mutates the project must also declare a `mutation_class`. If it sets `mutates_project: true` it must also declare working `rollback_support`; `tests/test_capability_manifest.py` enforces the validator, and the ledger reports a mutating capability without working rollback as `broken`.

The validator does not require `verification_commands` or a delegate or entrypoint. Those are needed to keep the row out of `broken`: declare `verification_commands`, and point any `delegate_skill` or `command_entrypoint` at something that exists.

Capabilities that are known-broken or partially working should be declared as such rather than left out. The ledger records reality.
