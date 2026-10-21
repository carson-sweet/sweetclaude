# Installing SweetClaude

**Version:** 1.1
**Date:** 2026-10-21

SweetClaude 5.x is the stable channel, tracked on `main`.

## Marketplace Install

Inside Claude Code:

```text
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
```

Restart Claude Code after install. Then run:

```text
/sweetclaude:help
```

**Upgrading from 4.x:** Run `/plugin marketplace update sweetclaude-stable`, then `/plugin update sweetclaude@sweetclaude-stable`, then restart Claude Code. After the restart, run `/sweetclaude:configure update` in each project. See [Upgrading to 5.0](upgrading-to-5.md) for the new command names.

**Upgrading from 3.x:** The stable channel moved from `stable-3.x` to `main`. Old 3.x installs registered their marketplace as `sweetclaude-stable`, so remove it first, then add `main` and install:

```text
/plugin marketplace remove sweetclaude-stable
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
```

Restart Claude Code, then run `/sweetclaude:configure doctor` inside each project. Doctor routes legacy project state to recovery or migration; update does not migrate project data. To stay on 3.x, add `carson-sweet/sweetclaude@stable-3.x` and install `sweetclaude@sweetclaude-legacy`.

**The beta channel is retired.** It no longer receives updates and cannot be
installed. If `/plugin list` shows `sweetclaude@sweetclaude-beta`, make the
one-time switch to stable — run these in order so you are never
double-installed:

```text
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
/plugin marketplace remove sweetclaude-beta
```

Then restart Claude Code and run `/sweetclaude:configure update` to sync framework files. Update does not migrate project data; run `/sweetclaude:configure doctor` when the project needs repair or migration. If a former beta project is stuck from a prior update,
doctor, migrate, or repair flow, follow
[SweetClaude 4.x Beta Rescue](beta-rescue.md).

## Updating

Update the Claude Code plugin package first:

```text
/plugin update sweetclaude@sweetclaude-stable
```

If `/plugin list` shows the legacy key `sweetclaude@sweetclaude`, update
that exact key instead:

```text
/plugin update sweetclaude@sweetclaude
```

Restart Claude Code after plugin update. Then run this inside each SweetClaude
project:

```text
/sweetclaude:configure update
```

`/sweetclaude:configure update` syncs framework files and reports project drift. It does
not run project-state migrations or taxonomy migrations inline. For project
repair or migration prompts, run:

```text
/sweetclaude:configure doctor
```

## Optional Integrations

### Firecrawl (web research enhancement)

[Firecrawl](https://firecrawl.dev) adds JavaScript-rendered page extraction,
structured schema output, and autonomous multi-page research to
`/sweetclaude:plan product-research` and `/sweetclaude:plan product-competition`. Both workflows
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

Run `/sweetclaude:utils corpus-rag-setup` in the project. It writes a per-project `.mcp.json` that runs `mcp-local-rag` through `npx`, so no global install is needed:

```json
{
  "mcpServers": {
    "local-rag": {
      "command": "npx",
      "args": ["-y", "mcp-local-rag"],
      "env": {
        "BASE_DIR": ".",
        "DB_PATH": "./.rag-index/lancedb",
        "CACHE_DIR": "./.rag-index/models"
      }
    }
  }
}
```

Restart Claude Code. Without RAG installed, the corpus pipeline still works
through Promote; you can add semantic search later and run
`/sweetclaude:utils corpus-rag-reindex`.

## Uninstalling Or Suspending

To suspend SweetClaude for one project without uninstalling globally:

```bash
touch .sweetclaude/disabled
```

Run `/sweetclaude:go` to reactivate.
