# Installing SweetClaude

## Marketplace Install (Recommended)

Inside Claude Code, no terminal required:

```
/plugin marketplace add https://github.com/carson-sweet/sweetclaude
/plugin install sweetclaude@sweetclaude
```

All skills are immediately available. Then go to your project and run `/sweetclaude:go` to begin.

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

To suspend SweetClaude for one project without uninstalling globally:

```bash
touch .sweetclaude/disabled
```

Run `/sweetclaude:go` to reactivate.
