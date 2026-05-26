# Installing SweetClaude

## Marketplace Install (Recommended)

Inside Claude Code, no terminal required. Install the stable 3.x channel explicitly:

```text
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-stable
```

All skills are immediately available. Then go to your project and run `/sweetclaude:help` or `/sweetclaude:go` to begin.

## Updating Stable 3.x

Update the Claude Code plugin package first:

```text
/plugin update sweetclaude@sweetclaude-stable
```

Restart Claude Code so the updated plugin package is loaded. Then, inside a SweetClaude project, run:

```text
/sweetclaude:update
```

`/sweetclaude:update` syncs SweetClaude framework files inside the installed stable channel and handles supported 3.x state migrations. It is not the package update mechanism, and it does not move a stable install onto 4.x beta.

## Legacy Install Names

Older docs used the unversioned source and plugin key:

```text
/plugin marketplace add https://github.com/carson-sweet/sweetclaude
/plugin install sweetclaude@sweetclaude
```

Do not use those commands for new installs. If `/plugin list` shows `sweetclaude@sweetclaude`, update that exact installed key first:

```text
/plugin update sweetclaude@sweetclaude
```

Then add and install the explicit stable channel when you are ready to standardize on the 3.x stable key.

## 4.x Beta Is Opt-In

Do not use `/sweetclaude:update` to move a 3.x stable project onto 4.x beta. If you intentionally want beta, add and install the beta marketplace as a separate channel and follow the beta branch migration docs.

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
