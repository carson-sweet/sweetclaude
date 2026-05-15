---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Structured security review."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:testing-security" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"

# Open security findings (issues tagged security)
sc_artifact_query issue status=backlog,ready,in_progress type=bug 2>/dev/null | \
  python3 -c "
import json, sys
items = json.load(sys.stdin)
sec = [i for i in items if 'security' in str(i.get('tags',[])).lower() or 'sec' in str(i.get('title','')).lower()]
print(f'OPEN_SECURITY_ISSUES={len(sec)}')
" 2>/dev/null || echo "OPEN_SECURITY_ISSUES=0"

ls .sweetclaude/testing/security/SR-*.md 2>/dev/null | wc -l | xargs -I{} echo "REVIEW_COUNT={}"
ls .sweetclaude/testing/security/SR-*.md 2>/dev/null | tail -3
```

# Testing Security

Structured security review for features, releases, or the full system. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `review` | → **Start** a new security review |
| `list` | → **List** past reviews |
| `view <SR-NNN>` | → **View** a past review |
| `findings` | → **List** open security issues |

---

## Review

### Step 1: Scope

"What is being reviewed?"
- `feature <RM-NNN or description>` — a specific feature
- `release <REL-NNN>` — everything going out in a release
- `system` — full system security posture

"What does the surface look like?" Prompt based on scope:
- Authentication? (yes/no)
- User-supplied input processed? (yes/no)
- External API calls made or received? (yes/no)
- File uploads or downloads? (yes/no)
- Sensitive data stored? (PII, payment, health — specify)
- Multi-tenant? (yes/no)

---

### Step 2: Threat model (STRIDE)

For each applicable threat category, assess whether it applies and rate the likelihood × impact.

Present one category at a time. For each: describe the threat, ask if it applies, ask for notes.

| Threat | Question |
|---|---|
| **Spoofing** | Can an attacker impersonate a legitimate user or service? |
| **Tampering** | Can an attacker modify data in transit or at rest? |
| **Repudiation** | Can users deny actions they took? Is there an audit trail? |
| **Information Disclosure** | Can sensitive data leak to unauthorized parties? |
| **Denial of Service** | Can an attacker degrade or disable the system? |
| **Elevation of Privilege** | Can a lower-privilege user gain higher-privilege access? |

For each that applies, note: attack vector, affected component, current mitigation (if any).

---

### Step 3: OWASP Top 10 checklist

Work through each item. For each: ask whether it applies, note current mitigations, flag gaps.

**1. Broken Access Control**
- Are authorization checks consistent across all endpoints?
- Are direct object references (IDs in URLs) validated against user permissions?
- Is CORS configured correctly?

**2. Cryptographic Failures**
- Is sensitive data encrypted at rest and in transit?
- Are deprecated algorithms (MD5, SHA1) in use anywhere?
- Are secrets stored in environment variables, not code?

**3. Injection**
- Are all database queries parameterized or using an ORM?
- Are shell command arguments sanitized?
- Is user input validated before use in system calls?

**4. Insecure Design**
- Were security requirements defined before implementation?
- Is there a rate limit on authentication endpoints?
- Is there account lockout or brute-force protection?

**5. Security Misconfiguration**
- Are default credentials changed?
- Are stack traces or debug info exposed in production?
- Are unnecessary features/services disabled?

**6. Vulnerable and Outdated Components**
- When were dependencies last audited?
- Are there known CVEs in current dependencies?
- Is there a process for dependency updates?

**7. Identification and Authentication Failures**
- Is session management secure (HttpOnly, Secure, SameSite cookies)?
- Is MFA available or enforced for privileged accounts?
- Are passwords hashed with a modern algorithm (bcrypt, argon2)?

**8. Software and Data Integrity Failures**
- Are CI/CD pipelines protected against unauthorized changes?
- Are third-party libraries verified (checksums, lockfiles)?

**9. Security Logging and Monitoring Failures**
- Are authentication events logged?
- Are failed access attempts logged?
- Are logs protected from tampering?

**10. Server-Side Request Forgery (SSRF)**
- If the application makes requests to user-supplied URLs, are those validated?
- Is there an allowlist for outbound requests?

---

### Step 4: Dependency audit

```bash
# Check for known vulnerabilities — run whichever applies
npm audit --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'NPM: {d.get(\"metadata\",{}).get(\"vulnerabilities\",{})}')" 2>/dev/null || true
pip-audit --format json 2>/dev/null | python3 -c "import json,sys; vulns=json.load(sys.stdin); print(f'PIP: {len(vulns)} vulnerabilities')" 2>/dev/null || true
bundle audit check 2>/dev/null | tail -3 || true
```

Note count of critical/high/medium vulnerabilities found.

---

### Step 5: Findings and report

Compile findings from STRIDE, OWASP, and dependency audit.

**Severity:**
- **P0 Critical** — exploitable now, data exposure or full compromise possible
- **P1 High** — significant risk, likely to be exploited
- **P2 Medium** — exploitable under specific conditions
- **P3 Low** — minor risk, defense-in-depth gap
- **Info** — observation, no direct risk

Present findings list:

```
Security Review: SR-NNN
Scope: {scope}
Date: {date}

Findings
  [P0]  SQL injection possible in /api/search — no parameterized query
  [P1]  Session cookies missing HttpOnly flag
  [P2]  Dependency: lodash 4.17.20 has prototype pollution CVE-2021-23337
  [P3]  Stack traces exposed in staging error responses
  [Info] No MFA — acceptable for current user base, revisit at scale
```

For each P0 and P1 finding, ask: "File this as an issue now?" On yes:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create issue '{
  "title": "<finding title>",
  "type": "bug",
  "status": "backlog",
  "priority": "next",
  "description": "<finding description with attack vector and remediation>",
  "tags": ["security", "SR-NNN"]
}'
```

---

### Step 6: Save review

```bash
mkdir -p .sweetclaude/testing/security/
```

Write `.sweetclaude/testing/security/SR-NNN.md` with scope, date, STRIDE results, OWASP checklist, findings, and issues filed.

Confirm: `SR-NNN complete — {N} findings ({P0} critical, {P1} high, {P2} medium, {P3} low)`

---

## List

```bash
ls .sweetclaude/testing/security/SR-*.md 2>/dev/null
```

Present each with date and finding counts.

---

## Findings

Load open issues tagged `security`:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue status=backlog,ready,in_progress
```

Filter for security tag. Present grouped by priority. If none: "No open security issues."

---

## Rules

- P0 findings block release. Raise them explicitly: "This is a P0 — it should block shipping until resolved."
- Never file a finding as `Info` severity if it is exploitable under any realistic condition.
- Dependency CVEs with no fix available: document the constraint and the compensating control, don't just close the finding.
- STRIDE is a guide, not a checklist. Skip categories that genuinely don't apply to the scope — but explain why.
- This skill assists a security review — it does not replace one for regulated or high-stakes systems.
