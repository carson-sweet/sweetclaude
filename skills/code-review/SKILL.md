---
description: "Code, security, and compliance review. Opens a menu at start — pick one or several. Adversarial: assumes problems exist and finds them."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Code Review

## Step 1: Choose review type

If $ARGUMENTS specifies a type (e.g. `security`, `compliance`, `1 3`), use that and skip the menu.

Otherwise present:

```
What do you want reviewed? (pick one or several)

  1. Code review      — logic errors, edge cases, regressions, performance
  2. Security review  — auth, injection, secrets, OWASP Top 10
  3. Compliance review — licenses, data handling, privacy, regulatory

Selection:
```

Wait for selection. Run chosen reviews in order: 1 → 2 → 3.

## Step 2: Establish scope

If $ARGUMENTS specifies files or a PR number, use that.
Otherwise: review staged changes, or if nothing staged, the last commit.

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

Begin by asking:
> "What compliance frameworks apply to this project? (e.g. GDPR, HIPAA, SOC 2, PCI-DSS, CCPA, open source licenses — or 'general')"

Then review accordingly.

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

## Rules

- Be adversarial. Assume problems exist and find them.
- Every finding must have a specific fix suggestion.
- Read-only. Do not modify code.
- If the code is solid, say so. Do not manufacture findings.
