import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skill-library" / "build" / "code-feature" / "SKILL.md"


def _step_1() -> str:
    text = SKILL.read_text(encoding="utf-8")
    match = re.search(r"### Step 1: Locate specs\n(.*?)(?=\n### Step )", text, re.S)
    assert match, "code-feature SKILL.md has no Step 1 section"
    return match.group(1)


class TestR195CodeFeatureSearchesProductBase:
    def test_step_1_does_not_search_the_directory_setup_never_creates(self):
        assert ".sweetclaude/stories" not in _step_1()

    def test_step_1_searches_default_product_base_for_stories(self):
        step = _step_1()
        assert ".sweetclaude/product/" in step
        assert re.search(r"stor(y|ies)", step, re.I)

    def test_step_1_searches_product_base_for_issue_artifacts(self):
        step = _step_1()
        assert re.search(r"ISSUE-\d{3}|issue", step, re.I)
        assert ".sweetclaude/product/" in step

    def test_step_1_honors_the_configured_product_base(self):
        step = _step_1()
        assert "product_base" in step or "configured product base" in step.lower()
