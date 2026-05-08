# Installing SweetClaude

## Marketplace Install (Recommended)

Inside Claude Code, no terminal required:

```
/plugin marketplace add https://github.com/carson-sweet/sweetclaude
/plugin install sweetclaude@sweetclaude
```

All skills are immediately available. Then go to your project and run `/sweetclaude:go` to begin.

---

## Manual Install

Preferred if you want the `--strategy-skills-only` variant (explained below).

### Prerequisites

| Dependency | Check | Install |
|---|---|---|
| [Claude Code](https://claude.ai/code) | `claude --version` | [Install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| [GitHub CLI](https://cli.github.com/) | `gh --version` | `brew install gh` or [cli.github.com](https://cli.github.com/) |
| Node.js (for RAG) | `node --version` | [nodejs.org](https://nodejs.org/) — optional, needed only for corpus management and semantic search |

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude
./install.sh
```

The installer:
- Checks prerequisites (Claude Code, Git, GitHub CLI)
- Backs up your existing `~/.claude/` configuration
- Scans for conflicting plugins and offers to clean them up
- Copies skills, hooks, agents, rules, and config to `~/.claude/`
- Wires TDD enforcement hooks into `settings.json`
- Generates `uninstall.sh` and `restore-config.sh` for clean removal

### Strategy Skills Only

SweetClaude has two layers: a **strategy and product layer** (discovery, product briefs, PRDs, personas, roadmaps, corpus management) and a **code and TDD layer** (phase gates, test-first enforcement, multi-agent review, implementation workflows). The full install includes both. The strategy-only install includes just the first layer.

Use `--strategy-skills-only` if:
- You are a founder, PM, or non-engineer who wants product and strategy workflows without the coding scaffolding
- You are evaluating SweetClaude's product thinking capabilities before committing to the full install
- You want to run SweetClaude on a project that does not involve Claude Code-assisted coding

```bash
./install.sh --strategy-skills-only
```

This installs the discovery, brief, PRD, persona, roadmap, corpus, and project management skills. It does not install TDD hooks, subagents, or code-phase skills. Upgrade to the full install at any time by running `./install.sh` with no flags.

---

## Updating

```bash
/sweetclaude:update
```

Fetches the latest version from GitHub and syncs to all installed locations. Shows what changed, migrates state schemas if needed, and prompts to onboard any skills marked `uninitialized`.

---

## Optional Integrations

### Firecrawl (web research enhancement)

[Firecrawl](https://firecrawl.dev) adds JavaScript-rendered page extraction, structured schema output, and autonomous multi-page research to `sweetclaude:product-research` and `sweetclaude:product-competition`. Both skills degrade gracefully if Firecrawl is absent.

1. Create an account at [firecrawl.dev](https://firecrawl.dev) — Hobby tier ($16/mo) or free trial.
2. Add the MCP server to Claude Code settings:
   ```json
   {
     "mcpServers": {
       "firecrawl": {
         "command": "npx",
         "args": ["-y", "@firecrawl/mcp-server"],
         "env": { "FIRECRAWL_API_KEY": "YOUR_API_KEY" }
       }
     }
   }
   ```
3. Restart Claude Code. The research and competition skills will automatically detect Firecrawl and use it when present.

### Local RAG (semantic search over your documents)

SweetClaude's corpus management pipeline (`/sweetclaude:document-corpus`) can build a local semantic search index over your canonical documents. You can then ask questions like "what did we decide about authentication?" and get the relevant passages back — no external services, all on your machine.

This uses [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag), which runs a per-project [LanceDB](https://lancedb.com/) vector database.

**Prerequisites:** Node.js (any recent version).

1. Install the MCP server globally:
   ```bash
   npm install -g mcp-local-rag
   ```

2. Add it to Claude Code's MCP settings (`~/.claude/settings.json` or via `/config`):
   ```json
   {
     "mcpServers": {
       "local-rag": {
         "command": "mcp-local-rag",
         "args": []
       }
     }
   }
   ```

3. Restart Claude Code. The corpus pipeline's **Promote** and **Reindex RAG** steps will automatically use it when present.

Without RAG installed, the corpus pipeline still works through the Promote step — your canonical documents are organized and versioned. You just won't have the semantic search index. RAG can be added later without redoing any prior corpus work; just install and run `/sweetclaude:document-corpus reindex`.

---

## Uninstalling

```bash
./uninstall.sh
```

Run from the repository directory. The installer generated this script during install. It restores your pre-install `~/.claude/` configuration from the backup.

To suspend SweetClaude for one project without uninstalling globally:

```bash
touch .sweetclaude/disabled
```

Run `/sweetclaude:go` to reactivate.
