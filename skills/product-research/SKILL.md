---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Survey the solution field — what exists commercially and open source — so the user understands what they're entering before building."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:product-research" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Product Research

Survey the solution landscape for the problem you're solving. This skill produces a state-of-the-art assessment and an initial list of competing solutions — commercial and open source.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:setup` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/discovery.yaml` if it exists. Use `project_type` and `problem_summary` to inform the research and depth suggestion. If missing, note this and proceed without it.

## Offer to Run

Before starting, explain what this skill does and ask if the user wants it:

> "Product research surveys what already exists in your problem space — commercial products, open-source projects, and the general state of the art. It answers two questions: 'Should I just use something that exists?' and 'Is what I'm building novel, entering a crowded space, or going somewhere with no market?'
>
> Based on your project type ({project_type from discovery, or 'the information you've shared'}), I'd suggest {L1 for utilities/hobby | L2 for internal tools | L2 or L3 for commercial}. Want to run it?"

If the user declines, write a skipped entry to the log and stop.

## Depth Levels

**L1 — Landscape survey:**
- What product categories exist that address this problem?
- Who are the main commercial players? (name, one-line description, general positioning)
- Who are the notable open-source projects? (name, one-line description)
- What is the general community and user sentiment about existing solutions?

**L2 — Comparative assessment** (includes L1):
- Which solutions are most relevant to what the user is building?
- What do they do well and where do they fall short?
- Pricing and distribution model for the main commercial options
- Initial competitive seed list (name, type: commercial/open_source, one-line description) — this feeds `product-competition`

**L3 — SOTA depth** (includes L1 and L2):
- Deep research on the most relevant 3–5 solutions
- Industry analyst or journalist coverage
- Developer community discussions (Reddit, Hacker News, Stack Overflow)
- Emerging or experimental approaches
- Assessment of whether the space is crowded, novel, or lacks a market

## Research Process

**Firecrawl detection:** Check if `mcp__firecrawl__scrape` is available in your tool list (i.e., a Firecrawl MCP server is connected). If yes, use the **Firecrawl path**. If not, use the **Standard path**.

### Firecrawl path (when mcp__firecrawl__scrape is available)

Use Firecrawl for richer, JS-rendered research:

- `mcp__firecrawl__search` to find competitors: `"{problem domain} software"`, `"best {problem domain} tools {current year}"`
- `mcp__firecrawl__scrape` on each competitor's homepage and pricing page for structured extraction
- For L3: `mcp__firecrawl__deep_research` with a research question for autonomous multi-source synthesis
- Extract structured data: name, URL, pricing, target user, key features, positioning

For each solution: name, type (commercial/open_source), URL, one-line description, notable strengths, notable weaknesses.

### Standard path (when Firecrawl is not available)

Use web search to conduct research. Search for:
- "{problem domain} software" / "{problem domain} tools"
- "{problem domain} open source alternatives"
- "best {problem domain} solutions {current year}"
- "{top competitor names} reviews" / "{top competitor names} alternatives"
- Community discussions: site:reddit.com, news.ycombinator.com

For each solution found, record: name, type (commercial/open_source), URL, one-line description, notable strengths, notable weaknesses (from user reviews and community discussion).

## Two-Lens Output

Present findings through two lenses:

**"Should I just use something that exists?"**
Honest assessment for the self-solver case. If a good existing solution covers the need, say so clearly.

**"Is what I'm building novel, crowded, or in a space with no market?"**
Commercial viability framing. Characterize the space: emerging (few solutions, growing need), crowded (many solutions, differentiation hard), established (mature solutions, requires clear differentiation), or nascent (problem identified but no real solutions yet).

## Frustration and Skip Handling

If the user seems frustrated or wants to skip, offer to proceed with what's gathered. Log the shortcut.

## Exit

Write `.sweetclaude/state/research.yaml`:

```yaml
sota_summary: {paragraph summary}
solution_field_assessment: crowded | novel | no_market | emerging | established | unclear
depth_run: L1 | L2 | L3
competitor_seeds:
  - name: {}
    type: commercial | open_source
    url: {}
    description: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-research ({depth})

**Status:** completed | skipped | degraded
**Degraded because:** {if applicable}
**Depth:** {L1 | L2 | L3}
**Produced:** {deliverable filename or none}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```

Write deliverable document to `docs/{project-name}-research-draft-v1.0-{yyyymmdd}.md` with standard front matter.
