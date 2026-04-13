---
name: notion-scaffold
description: Create a structured Notion workspace for a SweetClaude project. Creates pages for PRD, tech spec, ADRs, stories, and sprint tracking. Optional — invoked during sweetclaude init if user opts in.
---

# Notion Project Scaffold

Create a structured Notion workspace for project $ARGUMENTS.

## Prerequisites

- Notion MCP server connected and authenticated
- User has confirmed they want Notion integration during init

## Process

1. **Search for existing workspace.** Check if a Notion page/database already exists for this project name. If yes, ask user: use existing or create new?

2. **Create project root page** with title: "SweetClaude: [project-name]"

3. **Create child pages:**
   - Product Brief (template with sections from BMAD product-brief workflow)
   - PRD (template with FR/NFR/Epic sections)
   - Tech Spec (empty, populated during Design phase)
   - Architecture (empty, populated during Design phase)
   - ADRs (database — columns: ID, Title, Status, Date, Decision Makers)
   - Stories (database — columns: ID, Epic, Title, Status, Priority, Gherkin Link)
   - Sprint Board (database — columns: Story, Sprint, Status, Assignee)

4. **Link to working repo.** Add a "Links" section to the root page with:
   - Code repo GitHub URL
   - Working repo GitHub URL
   - Local paths

5. **Update project config.** Write Notion page IDs to `state/notion-links.yaml` in working repo so future sessions can navigate directly.

## Rules

- If Notion MCP is not available, skip gracefully with a warning.
- Never create duplicate workspaces — always check first.
- Page structure should match SweetClaude's phase model.
