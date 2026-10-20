# Test Report Format

After each test run (IP3, IP4, and each IM1 iteration), generate:

```markdown
# Test Report — {feature_name} — {timestamp}

## Summary
- Total: N | Pass: N | Fail: N | Skip: N
- Coverage: N% (if available)
- Run time: N seconds

## Failures
### {test name}
- File: {path:line}
- Expected: {value}
- Actual: {value}
- Stack: {first relevant frame}

## Passed
{collapsed list of passing test names}
```

Write to `.sweetclaude/reports/test-report-{issue-or-phase}-{timestamp}.md`. Append to aggregate report at `.sweetclaude/reports/test-report-{feature_name}.md`.
