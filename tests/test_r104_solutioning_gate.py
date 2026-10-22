import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill-library/design/design-solutioning-gate/SKILL.md"

FAIL_OUTCOME = re.compile(r"\b(fail|fails|failed|stop|stops|block|blocks)\b", re.I)


def _execute_steps() -> list[str]:
    text = SKILL.read_text()
    match = re.search(r"^## Execute\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, "SKILL.md must have an '## Execute' section"
    steps = re.split(r"^(?=\d+\.\s)", match.group(1), flags=re.M)
    return [" ".join(s.split()) for s in steps if re.match(r"\d+\.\s", s)]


class TestR104SolutioningGateRejectedAlternative:
    def test_step_checks_for_rejected_alternative_with_rationale(self):
        steps = [
            s for s in _execute_steps()
            if re.search(r"rejected alternative", s, re.I) and re.search(r"rationale", s, re.I)
        ]
        assert steps, "an Execute step must check for a rejected alternative with its rationale"

    def test_rejected_alternative_step_has_explicit_fail_or_stop_outcome(self):
        steps = [s for s in _execute_steps() if re.search(r"rejected alternative", s, re.I)]
        assert steps and any(FAIL_OUTCOME.search(s) for s in steps), (
            "the rejected-alternative check must state that the gate fails or stops when none is recorded"
        )


class TestR104SolutioningGateRollbackPlan:
    def test_step_checks_for_step_by_step_rollback_plan(self):
        steps = [
            s for s in _execute_steps()
            if re.search(r"rollback plan", s, re.I) and re.search(r"step-by-step", s, re.I)
        ]
        assert steps, "an Execute step must check for a step-by-step rollback plan"

    def test_rollback_step_has_explicit_fail_or_stop_outcome(self):
        steps = [s for s in _execute_steps() if re.search(r"rollback plan", s, re.I)]
        assert steps and any(FAIL_OUTCOME.search(s) for s in steps), (
            "the rollback-plan check must state that the gate fails or stops when none is recorded"
        )
