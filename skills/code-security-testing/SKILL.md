---
description: "Review code changes for security issues: auth problems, injection vulnerabilities, secrets exposure, tenant boundary violations. Returns prioritized findings."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Security Testing

Review code changes for security issues.

## Scope

If $ARGUMENTS specifies files or a PR, review those. Otherwise, review staged changes or recent commits.

## Checklist

For each file in scope, check:

### Authentication & Authorization
- [ ] Auth checks present on all endpoints/handlers that need them
- [ ] Authorization scoped correctly (tenant boundaries, role checks)
- [ ] No auth bypass paths (direct object reference, parameter manipulation)
- [ ] Session handling follows project patterns

### Injection
- [ ] SQL: parameterized queries, no string concatenation
- [ ] XSS: output encoding, no raw HTML insertion
- [ ] Command injection: no user input in shell commands
- [ ] Path traversal: no user input in file paths without validation

### Secrets & Data
- [ ] No hardcoded credentials, API keys, or secrets
- [ ] No secrets in logs or error messages
- [ ] Sensitive data not exposed in API responses that should not have it
- [ ] PII handling follows project patterns

### Dependencies
- [ ] No known-vulnerable dependencies introduced
- [ ] New dependencies from reputable sources

## Output

Present findings prioritized:

```
Security Review: {scope}

Critical:
  - {finding} — {file}:{line} — {what to fix}

Warning:
  - {finding} — {file}:{line} — {what to fix}

Info:
  - {finding} — {file}:{line} — {recommendation}

Clean:
  - {area checked with no findings}
```

## Rules

- Read-only. Do not modify code.
- If no issues found, say so. Do not manufacture findings.
- For ambiguous cases, flag as Info with context for the user to decide.
