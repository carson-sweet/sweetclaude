# Severity Classifier

After each test run, classify the result as **significant** (escalate) or **not significant** (continue).

**On first evaluation (initial implementation, before any bug fix attempt):** Apply criteria 2-4 only. The 30% threshold does not apply until at least one fix attempt has been made.

**Escalate to IM2 if:**
- More than 30% of tests are failing after a bug fix attempt
- Any test with "happy path", "core flow", "main flow", or "critical" in its name is failing
- Compile errors or import errors prevent the suite from running at all
- A security review finding has severity High or Critical

**Continue if:**
- Isolated edge case failures with a clear, identified root cause
- Failures in features explicitly marked as optional or enhancement-only
- Test infrastructure issues (missing fixture, wrong env var) with a known workaround

When uncertain between escalate and continue: **escalate**. A false positive (unnecessary interruption) is better than a false negative (silent bad state).
