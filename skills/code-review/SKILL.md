---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Code, security, and compliance review."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:code-review" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Code Review

## Step 1: Choose review type

If $ARGUMENTS specifies a type (e.g. `security`, `compliance`, `caucus`, `1 3`), use that and skip the menu.

Otherwise present via AskUserQuestion:

```
What do you want reviewed?

  1. Code review      — logic errors, edge cases, regressions, performance
  2. Security review  — auth, injection, secrets, OWASP Top 10
  3. Compliance review — licenses, data handling, privacy, regulatory
  4. Caucus review    — 5 parallel specialty agents with consensus scoring (higher coverage, lower false positives)
```

Options 1–3 can be combined. Option 4 is standalone.

If options 1–3 selected: run chosen reviews in order: 1 → 2 → 3. Skip to Step 2.

If option 4 (caucus) selected: skip to **Caucus Review** section below.

## Step 2: Establish scope

If $ARGUMENTS specifies files or a PR number, use that.
Otherwise: review staged changes, or if nothing staged, the last commit.

## Step 2b: Run mode

For reviews involving multiple types (e.g. code + security) or large diffs (50+ files), proactively offer background execution:

Offer via AskUserQuestion:
- **Review now (inline)** — run in this conversation; findings appear as Claude works
- **Run in background** — dispatch as a background agent; continue working and get notified when findings are ready

If "Run in background":
Dispatch a background Agent with `run_in_background: true`. Pass:
- The review type(s) selected in Step 1
- The scope (files, diff, or PR number) from Step 2
- Any compliance context from `.sweetclaude/state/compliance-context.yaml` (for compliance reviews)
- Instruction: run the applicable review sections from this skill and produce the standard output format

Confirm: "Review running in background. Findings will appear when the agent completes."
Stop. Do not run the inline review sections below.

If "Review now (inline)": proceed to the review sections below.

For small focused reviews (single file, one type, short diff), skip the offer and run inline without asking.

---

## Code Review

**Focus areas:**
1. **Logic errors** — off-by-one, wrong operator, inverted condition, missing null check
2. **Edge cases** — empty input, boundary values, concurrent access, very large input
3. **Regressions** — does this change break existing behavior? Check callers and consumers.
4. **Missing error handling** — what happens when this fails? Network errors, invalid data, timeouts, disk full
5. **Performance** — N+1 queries, unbounded loops, missing pagination, unnecessary allocations, missing indexes
6. **Naming and contracts** — does the function do what its name says? Do types match reality?

**Do not flag:** style, formatting, naming conventions (linter handles that), or missing features not in scope.

**Output:**
```
Code Review: {scope}
════════════════════

✗ Critical (must fix):
  - {finding} — {file}:{line}
    Problem: {what is wrong}
    Fix: {specific suggestion}

⚠ Warning (should fix):
  - {finding} — {file}:{line}
    Problem: {what could go wrong}
    Fix: {specific suggestion}

→ Nit (consider):
  - {finding} — {file}:{line}
    {suggestion}

✓ Looks good:
  - {area reviewed with no findings}
```

---

## Security Review

**Focus areas:**
1. **Authentication and authorization** — are endpoints protected? Can a user access another user's data? Missing permission checks?
2. **Injection** — SQL injection, command injection, XSS, SSTI, path traversal
3. **Secrets exposure** — hardcoded credentials, API keys in source, secrets in logs or error messages
4. **Tenant isolation** — multi-tenant systems: can data from one tenant leak to another?
5. **Input validation** — is untrusted input validated at system boundaries? Are file uploads restricted?
6. **Cryptography** — weak algorithms, hardcoded IVs, broken key management, insecure random
7. **Dependency risks** — known CVEs in direct dependencies (check `npm audit` / `pip audit` / equivalent)
8. **OWASP Top 10** — verify the change does not introduce any of the top 10 categories

**Output:**
```
Security Review: {scope}
════════════════════════

✗ Critical (must fix before merge):
  - {finding} — {file}:{line}
    Risk: {what an attacker could do}
    Fix: {specific remediation}

⚠ Warning (should fix):
  - {finding} — {file}:{line}
    Risk: {potential exposure}
    Fix: {specific remediation}

→ Hardening (consider):
  - {finding} — {file}:{line}
    {suggestion}

✓ Looks good:
  - {area reviewed with no findings}
```

---

## Compliance Review

**Check for compliance context first:**

Look for `.sweetclaude/state/compliance-context.yaml`. If it exists and `derived_frameworks` is non-empty, use those frameworks directly — do not ask the user:
> "Using compliance context from discovery: [{frameworks listed}]. Running compliance review against these frameworks."

If the file does not exist or `derived_frameworks` is empty, ask:
> "What compliance frameworks apply to this project? (e.g. GDPR, HIPAA, SOC 2, PCI-DSS, CCPA, open source licenses — or 'general')"

**Focus areas:**
1. **License compliance** — do new dependencies have compatible licenses? Is attribution required?
2. **Data handling** — is PII collected, stored, or transmitted? Is it minimized, encrypted, and deletable?
3. **Consent and disclosure** — are users informed about data collection? Is consent recorded?
4. **Retention and deletion** — does the change affect data retention? Are deletion paths preserved?
5. **Audit logging** — do regulated actions produce audit trails?
6. **Framework-specific** — apply requirements from the stated frameworks (GDPR Article 5, HIPAA safeguards, SOC 2 criteria, etc.)
7. **Third-party data sharing** — does the change send data to external services? Is that disclosed and permissible?

**Output:**
```
Compliance Review: {scope} [{frameworks}]
══════════════════════════════════════════

✗ Violation (must fix):
  - {finding} — {file}:{line}
    Requirement: {specific rule or article}
    Risk: {regulatory or legal exposure}
    Fix: {specific remediation}

⚠ Gap (should address):
  - {finding} — {file}:{line}
    Requirement: {applicable standard}
    Fix: {specific remediation}

→ Recommendation (consider):
  - {suggestion}

✓ Compliant:
  - {area reviewed with no findings}
```

---

---

## Caucus Review

Five specialty agents review the same diff independently with no access to each other's findings. A coordinator then synthesizes by confidence.

**Isolation is mandatory.** Each agent sees only the diff and the codebase — never another agent's output. Cross-contamination collapses the diversity that produces low false positives.

### Step C1: Dispatch specialty agents in parallel

Dispatch all five agents simultaneously against the established scope (Step 2):

| Agent | Domain |
|---|---|
| `code-reviewer` | Logic errors, edge cases, regressions, error handling |
| `security-reviewer` | Auth, injection, secrets, OWASP Top 10 |
| `architecture-reviewer` | Module boundaries, coupling, API surface, design patterns |
| `performance-reviewer` | Complexity, N+1, unbounded growth, blocking calls |
| `tests-reviewer` | Missing tests, brittle assertions, untested edge cases |

Each agent receives: the diff (or file list), a pointer to the relevant codebase context, and its own system prompt only. No agent output is visible to any other agent.

Offer background dispatch per the run mode rules in Step 2b.

### Step C2: Collect and normalize findings

Wait for all five agents to complete. For each finding, record:
- `agent` — which agent raised it
- `location` — file and line
- `severity` — Critical / Warning / Nit (normalized across agents)
- `description` — what the problem is
- `fix` — specific suggestion

### Step C3: Deduplicate and score confidence

Group findings that refer to the same location and problem (fuzzy match on file + line ± 3 and topic). For each group:

- **Flagged by 3–5 agents → Consensus** (★★★)
- **Flagged by 2 agents → Corroborated** (★★☆)
- **Flagged by 1 agent → Unconfirmed** (★☆☆)

Within each confidence tier, sort by severity: Critical first, then Warning, then Nit.

### Step C4: Present synthesis

```
Caucus Review: {scope}
══════════════════════

★★★ Consensus (flagged by multiple agents — high confidence):

  ✗ Critical:
    - {finding} — {file}:{line}  [{agents who flagged it}]
      Problem: {description}
      Fix: {specific suggestion}

  ⚠ Warning:
    - ...

★★☆ Corroborated (2 agents):

  ✗ / ⚠ / → [same format]

★☆☆ Unconfirmed (single agent — review before acting):

  ✗ / ⚠ / → [same format, include which agent flagged it]

✓ No findings in: {domains with no findings}

Coverage: {N}/5 agents completed  |  {N} consensus  |  {N} corroborated  |  {N} unconfirmed
```

Unconfirmed findings are surfaced but visually separated — they are not suppressed. A single expert finding on a security issue is still worth seeing.

---

## Rules

- Be adversarial. Assume problems exist and find them.
- Every finding must have a specific fix suggestion.
- Read-only. Do not modify code.
- If the code is solid, say so. Do not manufacture findings.
- **Caucus isolation.** Never show one agent's output to another agent before synthesis. Violation collapses the confidence signal.
