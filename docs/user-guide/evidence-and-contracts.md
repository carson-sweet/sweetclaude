# Evidence and Success-Criteria Contracts

**Version:** 1.0
**Date:** 2026-06-10

SweetClaude's high-rigor story workflows do not let the model declare its own work "done." Completion is gated on a frozen contract and on evidence the harness observed — not on self-report. This page explains the success-criteria contract, how implementation evidence is captured, and how the verify gate fails closed.

> Not to be confused with [Behavioral Contracts](behavioral-contracts.md), which track *model behavior* (e.g. "never push for phase advancement"). The contracts on this page are about *work-item completion* — whether a specific story actually met its declared criteria.

---

## What a Success-Criteria Contract Is

A success-criteria contract is a frozen, hash-bound set of pass/fail criteria for one work item. Large/high-rigor story workflows must begin with a frozen contract before any downstream planning, design, test writing, implementation, review, release, or completion evaluation starts.

The contract is a YAML artifact. By default it lives at:

```
.sweetclaude/contracts/success-criteria-contract.yaml
```

Each contract records:

- a stable story/workflow id;
- the story objective, expected outcomes, and non-goals;
- a list of binary `success_criteria`, each with a unique `SC-NNN` id;
- one measurable `pass_condition` and one measurable `fail_condition` per criterion (they must differ);
- the expected `evidence_artifact`, `evidence_owner`, and the phase the criterion is allowed to be measured in;
- a `contract_freeze` block holding `frozen_at`, `frozen_by`, and a `contract_hash` computed after freeze.

A criterion is rejected if it leans on open-ended judgment — words like "adequate", "comprehensive", "robust", "production-ready", or "looks good" / "reviewer approved" without a concrete binary measurement. Each criterion must describe one observable behavior; criteria that bundle multiple outcomes are rejected so they can be split.

---

## Lifecycle: init → freeze → validate

The contract moves through three stages, driven by `scripts/success_criteria_contracts.py`:

1. **init** — write a schema-valid skeleton with placeholder criteria pre-filled:

   ```bash
   python3 scripts/success_criteria_contracts.py init-contract --story-id ISSUE-123
   ```

   `init-contract` refuses to overwrite while an active large-story workflow exists — post-freeze amendment is human-gated at the file layer.

2. **freeze** — after replacing every placeholder, compute and write the freeze hash:

   ```bash
   python3 scripts/success_criteria_contracts.py freeze-contract
   ```

   The hash is computed from the canonical contract content *excluding* the declared hash field. Any post-freeze edit changes the hash, so a stale contract fails validation.

3. **validate** — confirm the frozen contract is internally consistent:

   ```bash
   python3 scripts/success_criteria_contracts.py validate-contract \
     --contract .sweetclaude/contracts/success-criteria-contract.yaml
   ```

The canonical workflow-facing command wraps these stages per lifecycle point:

```bash
python3 scripts/success_criteria_contracts.py validate-workflow --stage define-exit
```

`--stage define-exit` runs before Plan, Design, Implementation, Verify, review, release, or completion evaluation. `--stage completion` runs the ledger check (below). Use `--workflow-id` to validate a stored orchestrator workflow, or explicit `--contract`/`--ledger` paths for non-standard locations.

---

## Implementation Evidence

During IMPLEMENT, a PostToolUse hook (`hooks/large-story-evidence.sh`, and the small-story equivalent) watches the work the harness actually performs. When a Write, Edit, NotebookEdit, or Bash tool touches a project file or runs a command, the hook appends a harness-observed entry to a controller-owned evidence log. It records the tool, the touched file path or command, the phase, the workflow id, and a timestamp.

The hook never blocks — it only observes. Controller-owned paths under `.sweetclaude/` and the controller's own scripts are excluded so the log reflects real implementation work, not bookkeeping.

The evidence log is a JSONL file at:

```
.sweetclaude/reports/large-story/<workflow_id>/implementation/evidence.jsonl
.sweetclaude/reports/small-story/<workflow_id>/implementation/evidence.jsonl
```

Because evidence is captured by the harness rather than self-reported, the model cannot claim a criterion was met without the underlying tool activity having been observed.

---

## The Verify Gate (Fails Closed)

Completion is checked against a `success-criteria-ledger.json`, by default at:

```
.sweetclaude/reports/success-criteria-ledger.json
```

The ledger must evaluate every frozen criterion id and expose one binary outcome: `all_success_criteria_passed == true` or `false`. Each ledger entry must carry a passing status, the frozen `success_criteria_contract_hash`, the contract-declared `evidence_artifact` and `evidence_owner`, and current evidence freshness.

Run the completion check with:

```bash
python3 scripts/success_criteria_contracts.py validate-ledger \
  --contract .sweetclaude/contracts/success-criteria-contract.yaml \
  --ledger .sweetclaude/reports/success-criteria-ledger.json
```

or the workflow-facing form:

```bash
python3 scripts/success_criteria_contracts.py validate-workflow --stage completion
```

**The gate fails closed.** No completion claim is valid when:

- the contract is missing or its hash is stale;
- any frozen criterion is missing from the ledger, fails, or is unevaluated;
- a criterion lacks its declared evidence, or that evidence is stale;
- **no hook-observed implementation evidence was recorded** — large/small-story VERIFY is blocked if `evidence.jsonl` is empty. If a story genuinely changed no project files, verify must be re-run with `--allow-no-file-changes`.

Manual "mark done" paths for work flagged as requiring a success-criteria contract also fail closed until completion validation passes. A separate `--allow-missing-evidence` flag may waive the generic receipt requirement, but it does **not** bypass the success-criteria ledger gate.

---

## Contract Amendment

A frozen contract is not silently editable. Every downstream phase must preserve the frozen contract path, hash, and criterion ids. No review, caucus, verification, release, or completion step may add new completion criteria.

If a reviewer finds a real issue outside the frozen criteria, it is routed to backlog, a split story, human escalation, or a `criteria-amendment-request.yaml`. Legitimate amendment is human-gated: each criterion's `amendment_policy` must be `human_approved_only`, and a changed contract must be re-frozen (producing a new hash) before it validates again.

---

## Control Receipts

Control receipts are small JSON artifacts that prove a high-stakes claim was backed by real command output, stored under `.sweetclaude/state/evidence/`. High-stakes lifecycle claims require a receipt before the claim is accepted.

`scripts/evidence.py` handles the core completion-class receipts. Its supported `receipt_type` values are:

- `completion`
- `verification`
- `ship`
- `release`
- `external-close`

`scripts/control_receipts.py` adds release- and review-bound receipt types for higher-assurance work, including (among others) `control-lint`, `source-discovery`, `source-precedence`, `contract-test`, `invariant-test`, `high-critical-exemption`, `objective-criteria`, `phase-exit`, `finding-disposition`, `backlog-promotion`, `change-context`, `release-identity`, `release-artifact-build`, `update-discovery-execution`, `installed-smoke`, and `public-distribution-inventory`. Several of these bind a receipt to a specific branch, commit, and file hash so a claim cannot drift from the artifact it describes.

Receipts are intentionally a small schema so skills can create them from real command output without a database. The verify gate (above) is separate from these receipts: waiving a generic receipt never waives the success-criteria ledger.

---

## How This Ties Into the Story Workflows

Contracts and evidence are the backbone of SweetClaude's bounded, evidence-gated large- and small-story workflows. The user flow:

1. Start or resume with `/sweetclaude:go <natural-language request>`. `/sweetclaude:go` routes high-rigor requests to the internal large-story workflow.
2. During Define, create and freeze the `success_criteria_contract`.
3. Run `validate-workflow --stage define-exit` before each downstream phase.
4. During Implement, the evidence hook records harness-observed activity to `evidence.jsonl`.
5. At completion, write `success-criteria-ledger.json` and run `validate-workflow --stage completion` before any `done` transition.

Skills such as `/sweetclaude:build code-feature`, `/sweetclaude:build code-issue`, and `/sweetclaude:build code-tdd` may do bounded implementation work inside a workflow, but they inherit the frozen contract from the calling workflow rather than minting their own.

See [Large-Story and Small-Story Workflows](large-story-workflow.md) for the
workflows in full, and [State and Memory](state-and-memory.md) for where these
artifacts live on disk.
