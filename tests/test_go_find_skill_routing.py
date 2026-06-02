from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def _frontmatter(path: str) -> str:
    text = _read(path)
    assert text.startswith("---\n")
    return text.split("---\n", 2)[1]


def test_go_delegates_natural_language_requests_to_find_skill():
    text = _read("skills/go/SKILL.md")

    assert "## Step 0: Natural-language request path" in text
    assert "If the user passes a request after `/sweetclaude:go`" in text
    assert "Do not require the user to know a skill name" in text
    assert "Invoke `sweetclaude:find-skill` with the user's request as context" in text
    assert "/sweetclaude:go start a large story for the billing rewrite" in text


def test_find_skill_can_route_large_story_requests():
    text = _read("skills/find-skill/routing-tables.md")

    assert "| Large story / high-rigor story |" in text
    assert "| Large story / high-rigor story | DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:large-story` |" in text


def test_large_story_is_not_publicly_invocable():
    frontmatter = _frontmatter("skills/large-story/SKILL.md")
    text = _read("skills/large-story/SKILL.md")

    assert "user-invocable: false" in frontmatter
    assert "Internal bounded, evidence-gated large-story workflow." in frontmatter
    assert "Users start this through `/sweetclaude:go` using natural language." in text


def test_large_story_removed_from_public_skills_reference():
    text = _read("docs/user-guide/4.x-beta/skills-reference.md")

    assert "| **Large Story** |" not in text
    assert "`/sweetclaude:large-story`" not in text
