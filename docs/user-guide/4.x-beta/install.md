# Installing SweetClaude 4.x Beta

Use this page only if you intentionally want the 4.x beta channel. For normal
active project work, use the [3.x stable install guide](../3.x/install.md).

## Marketplace Install

Inside Claude Code:

```text
/plugin marketplace add carson-sweet/sweetclaude@beta-4.x
/plugin install sweetclaude@sweetclaude-beta
```

Restart Claude Code after install. Then run:

```text
/sweetclaude:help
```

Use the current `beta-4.x` channel for beta testing. Do not install old 4.x beta
tags on active projects.

## Updating 4.x Beta

Update the Claude Code plugin package first:

```text
/plugin update sweetclaude@sweetclaude-beta
```

If `/plugin list` shows the legacy beta key `sweetclaude@sweetclaude`, update
that exact key instead:

```text
/plugin update sweetclaude@sweetclaude
```

Restart Claude Code after plugin update. Then run this inside each SweetClaude
project:

```text
/sweetclaude:update
```

In 4.x beta, `/sweetclaude:update` syncs framework files and reports project
drift. It does not run project-state migrations or taxonomy migrations inline.
For project repair or migration prompts, run:

```text
/sweetclaude:doctor
```

If a 4.x beta project is already stuck from a prior update, doctor, migrate, or
repair flow, follow [SweetClaude 4.x Beta Rescue](beta-rescue.md).

## Optional Integrations

### Firecrawl (web research enhancement)

[Firecrawl](https://firecrawl.dev) adds JavaScript-rendered page extraction,
structured schema output, and autonomous multi-page research to
`sweetclaude:product-research` and `sweetclaude:product-competition`. Both skills
degrade gracefully if Firecrawl is absent.

1. Create an account at [firecrawl.dev](https://firecrawl.dev).
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
3. Restart Claude Code.

### Local RAG (semantic search over your documents)

SweetClaude's corpus management pipeline can build a local semantic search index
over canonical documents using [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag).

```bash
npm install -g mcp-local-rag
```

Add it to Claude Code's MCP settings:

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

Restart Claude Code. Without RAG installed, the corpus pipeline still works
through Promote; you can add semantic search later and run
`/sweetclaude:document-corpus reindex`.

## Uninstalling Or Suspending

To suspend SweetClaude for one project without uninstalling globally:

```bash
touch .sweetclaude/disabled
```

Run `/sweetclaude:go` to reactivate.
