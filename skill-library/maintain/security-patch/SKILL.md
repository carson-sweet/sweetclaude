---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Security patch — vulnerability fix with mandatory security review and disclosure tracking."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Security Patch

Fix a security vulnerability with mandatory review. The patch is minimal — it closes the vulnerability and nothing else.

**Phases:** DIAGNOSE → IMPLEMENT → VERIFY (⚠️ HARD GATE) → SHIP.

---

## Step 1: Identify the vulnerability (DIAGNOSE)

> "Describe the security vulnerability:
>
> 1. **What is it?** — CVE number (if assigned), internal report reference, or description
> 2. **What is exposed?** — data, systems, or access that an attacker could reach
> 3. **Affected versions** — which versions or deployments are vulnerable
> 4. **Is there a disclosure deadline?** — coordinated disclosure date, if any"

Record: `VULN_ID`, `VULN_DESCRIPTION`, `BLAST_RADIUS`, `AFFECTED_VERSIONS`, `DISCLOSURE_DEADLINE`.

---

## Step 2: Assess blast radius and severity (DIAGNOSE)

Classify severity:

| Severity | Criteria |
|---|---|
| **P0 — Immediate** | Active exploitation, data breach in progress, auth bypass, RCE |
| **P1 — Urgent** | Exploitable vulnerability, no evidence of active exploitation yet |
| **P2 — Important** | Vulnerability requires specific conditions to exploit, limited blast radius |

> "This is a **P{N}** vulnerability: {one-sentence justification}.
>
> **Blast radius:** {what data or systems are exposed, who is affected}
> **Temporary mitigation:** {can exposure be reduced while the patch is built? WAF rule, feature flag, network restriction}"

If a temporary mitigation exists and severity is P0, recommend applying it before starting the patch:

> "Recommend applying the temporary mitigation now to reduce exposure while we build the proper fix."

Log to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | Security vulnerability: {VULN_ID or description} | Severity: P{N}. Blast radius: {summary}. Mitigation: {applied/none}. | N/A |
```

---

## Step 3: Scope the patch (DIAGNOSE → IMPLEMENT gate)

Identify the affected code:

```bash
# Read affected files based on user description
```

State the fix:

> "Here's the minimal patch:
>
> - **What changes:** {specific fix}
> - **What does NOT change:** no refactoring, no feature work, no unrelated cleanup
> - **Files to touch:** {list}
> - **New attack surface introduced:** none (verify this claim during review)"

Wait for approval.

---

## Step 4: Implement the patch (IMPLEMENT)

1. Write a regression test proving the vulnerability is closed (RED).
2. Implement the minimal fix (GREEN).
3. Verify the patch does not introduce new attack surface.
4. Run the full test suite.

```bash
# Run project test suite
```

**Scope enforcement:** The patch fixes only the vulnerability. If you find related issues, note them for follow-on work — do not expand the patch scope.

If the root cause is a dependency: update the dependency to the patched version. Do not pin to a specific version unless the latest introduces breaking changes.

```bash
# Check if vulnerability is in a dependency
```

---

## Step 5: Security review (VERIFY) — ⚠️ HARD GATE

**This gate is mandatory. It cannot be soft-bypassed. No exceptions regardless of severity or time pressure.**

The patch must be reviewed for security before shipping. At minimum:

> "Security review required before this patch can ship. Options:"

Present via AskUserQuestion:

| Option | Description |
|---|---|
| **Invoke security review skill** | Run `/sweetclaude:build testing-security` for a structured security review of the patch |
| **Manual peer review** | A teammate reviews the patch with security focus — confirm when complete |
| **Self-review with security checklist** | Walk through a security-focused checklist (solo dev / no teammates available) |

**If security review skill:** invoke `sweetclaude:library-load testing-security` on the patch diff. Resume here after it completes.

**If manual peer review:** wait for the user to confirm the review is complete. Ask: "Who reviewed it, and were any concerns raised?"

**If self-review checklist:** walk through each item, log pass/fail:

1. Patch closes the identified vulnerability
2. Patch does not introduce new injection points (SQL, command, XSS, template)
3. Patch does not weaken authentication or authorization
4. Patch does not expose secrets, tokens, or credentials
5. Patch does not introduce new untrusted input paths without validation
6. Regression test proves the vulnerability is closed
7. No new dependencies with known vulnerabilities

Log the review to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | Security review: {method} for {VULN_ID} | {pass/fail summary}. Reviewed by: {reviewer}. | N/A |
```

If the review finds issues: fix them and re-review. Do not proceed to SHIP with open security findings.

---

## Step 6: Ship (SHIP)

```bash
git diff --stat
```

> "Patch ready to ship.
>
> **Severity:** P{N} — {expedited window for P0/P1, normal cadence for P2}
> **Rollback plan:** {how to undo if the patch causes problems}
> **Disclosure deadline:** {deadline or 'none'}"

Offer via AskUserQuestion:

| Option | Description |
|---|---|
| **Commit and open PR** | Commit with conventional message, open PR via `gh pr create` |
| **Commit, merge, and push** | Fastest path — for P0/P1 active exploitation |
| **Commit only** | I'll handle deploy myself |

After deploy, confirm:

> "Verify the patch in production:
>
> 1. Vulnerability confirmed closed?
> 2. No new errors or regressions?
> 3. Monitoring showing normal behavior?"

---

## Step 7: Post-ship obligations

**Disclosure (if applicable):**

If `DISCLOSURE_DEADLINE` was set:

> "Coordinated disclosure deadline: {date}. Publish the advisory when ready, or at the deadline — whichever comes first."

**User notification (if data was exposed):**

> "Was any user data exposed before the patch? If yes, affected users need to be notified per your data breach policy."

**Follow-on work:**

> "The patch is shipped. Any broader audit needed? Common follow-ons:
> - Audit related code paths for the same vulnerability pattern
> - Review other dependencies for similar issues
> - Update security documentation or runbook"

For each follow-on the user identifies, create a backlog item:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --query next-id --prefix ISSUE
```

Log completion to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | Security patch shipped: {VULN_ID} | Deployed, verified, {N} follow-on items created. | N/A |
```

---

## Rules

- **Minimal patch only.** Fix the vulnerability and nothing else. Related improvements are follow-on work.
- **Security review is a HARD GATE.** Cannot be bypassed at any severity level. P0 urgency does not override review — it compresses the review, not eliminates it.
- **No new attack surface.** If the patch introduces new input paths, new auth flows, or new data exposure, it fails review.
- **Disclosure tracking is mandatory when applicable.** If a disclosure deadline exists, track it through to publication.
- **Do not discuss vulnerability details in public channels** (PR descriptions, commit messages, changelog) until the disclosure is published. Use generic language: "security fix" not "SQL injection in login endpoint."
- **Dependency patches:** update the dependency, do not fork or vendor a patched version unless the maintainer is unresponsive and the vulnerability is P0.
