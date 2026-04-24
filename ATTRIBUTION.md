# Attribution

## Authors

Design: Carson Sweet, assisted by Anthropic, Google, and OpenAI
Code: Carson Sweet, assisted by Claude Code (Opus 4.6)
Review: Carson Sweet, assisted by GPT-5.3-Codex (OpenAI)

## Runtime Dependencies

SweetClaude requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as its host environment.

### Upstream Plugins (Required for Full Install)

| Dependency | License | Min Version | Role |
|---|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | MIT | 5.0.7 | Dev mechanics: plans, worktrees, debugging, code review, parallel agents |
| [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | MIT | 6.0.0 | Product lifecycle: brainstorm, PRD, architecture, stories, sprint planning |

**Superpowers skills used directly:**
- `superpowers:writing-plans`
- `superpowers:executing-plans`
- `superpowers:using-git-worktrees`
- `superpowers:systematic-debugging`
- `superpowers:dispatching-parallel-agents`
- `superpowers:subagent-driven-development`
- `superpowers:verification-before-completion`

**BMAD skills wrapped by SweetClaude:**
- `bmad:product-brief` → `sweetclaude:product/product-brief`
- `bmad:prd` → `sweetclaude:product/prd`
- `bmad:create-story` → `sweetclaude:product/user-story`
- `bmad:research` → `sweetclaude:product/research`
- `bmad:sprint-planning` → `sweetclaude:product/sprint-plan`
- `bmad:architecture` → `sweetclaude:design/architecture`
- `bmad:tech-spec` → `sweetclaude:design/tech-spec`
- `bmad:create-ux-design` → `sweetclaude:design/ux`
- `bmad:solutioning-gate-check` → `sweetclaude:design/solutioning-gate`

### Standalone Claude Code Skills (Used, Not Wrapped)

These are third-party skills invoked by name but not forked or modified:

- `caucus` — multi-perspective review (strategy, design phases)
- `reasoning-frameworks` — structured analysis (strategy, design phases)
- `reconciling-documents` — document consolidation (product phase)
- `hibernate-project` — project freeze/thaw (extended by `sweetclaude:hibernate`)

### MCP Servers

| Server | Install | Role |
|---|---|---|
| [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) | `npm install -g mcp-local-rag` | Local semantic search via per-project vector index |

mcp-local-rag uses [LanceDB](https://lancedb.com/) as its embedded vector database (index stored at `.rag-index/lancedb/`).

### CLI Tools

| Tool | Required | Role |
|---|---|---|
| git | Yes | Version control, branching, commit hooks |
| [GitHub CLI (gh)](https://cli.github.com/) | Recommended | Project init, issue/PR management |
| Node.js | Optional | Required only for RAG indexing (`mcp-local-rag`) |

## License

SweetClaude is released under the [PolyForm Shield License 1.0.0](LICENSE).
