# Installing SweetClaude

**Version:** 1.1
**Date:** 2026-10-21

SweetClaude 5.x is the stable channel, tracked on `main`.

## Install for one project

Local scope is the recommended default: it enables SweetClaude for you in this repository only. User scope applies to every project on your machine and is not recommended. Project scope uses `.claude/settings.json`; if committed, it enables the plugin for collaborators who have it installed. Use it only when the whole team wants SweetClaude; each collaborator also needs the plugin and marketplace available.

From a terminal in the target repository, register the stable marketplace if it is not already registered, then install locally:

```bash
claude plugin marketplace add carson-sweet/sweetclaude@main
claude plugin install sweetclaude@sweetclaude-stable --scope local
```

Marketplace registration and the plugin cache are user-level Claude Code data; registration alone does not enable the plugin everywhere. The beta channel is retired. Repeat the local install in each repository where you want SweetClaude. Restart Claude Code in that repository and run `/sweetclaude:help`.

Claude Code stores the personal enablement in `.claude/settings.local.json`. Keep it untracked and gitignored: check with `git check-ignore .claude/settings.local.json`; if needed, add `.claude/settings.local.json` to `.gitignore` or your personal Git excludes. Do not commit this file. It does not enable the plugin for teammates. In worktrees, Claude Code may use the main checkout's local settings; see [Claude Code settings](https://code.claude.com/docs/en/settings).

**Settings precedence:** for each plugin entry, managed settings override local, which overrides project, which overrides user settings. A per-session `--settings` override sits below managed and above local. Thus project `true` overrides user `false`; a local `false` overrides project `true`, unless managed settings enforce it. Keep SweetClaude instructions in the repository's `CLAUDE.md` or `.claude/rules/`, never in `~/.claude/CLAUDE.md`.

### Verify scope

In the target repository run `claude plugin list` and `claude doctor`, then start Claude Code and check `/status` for loaded setting sources and `/sweetclaude:help` for the plugin. `/status` identifies sources, not the winning value of every setting. Next start a fresh session in an unrelated directory outside the repository. Check `/status`, the `/` skill menu, available agents, and `/hooks` for SweetClaude entries. `claude plugin list` can show installed plugins even when they are not active in the current directory, so the list alone does not prove isolation. Investigate user-level files or settings and managed settings if anything appears.

### Disable or uninstall in this repository

To opt out even when project settings enable it, merge this entry into the existing `.claude/settings.local.json` (preserve other settings):

```json
{
  "enabledPlugins": {
    "sweetclaude@sweetclaude-stable": false
  }
}
```

Restart Claude Code. For a local installation, uninstall from the repository with:

```bash
claude plugin uninstall sweetclaude@sweetclaude-stable --scope local
```

Uninstalling a local installation can expose an enabled project or user entry; retain the local `false` override if needed. Restart and repeat the checks above, including an unrelated directory. Plugin uninstall does not automatically remove project artifacts or old global files. `/sweetclaude:configure off` suspends the workflow; it is not the same as disabling the plugin and its components.

### Move an existing user-wide installation

1. Back up `~/.claude/settings.json` and inspect `enabledPlugins` for every SweetClaude ID, including `sweetclaude@sweetclaude-stable`, `sweetclaude@sweetclaude-beta`, `sweetclaude@inline`, and `sweetclaude@sweetclaude`. Uninstall each installed user-scope ID with `claude plugin uninstall <plugin-id> --scope user`, or set its entry to `false`. Do not remove unrelated settings.
2. Inspect `~/.claude/CLAUDE.md` and `~/.claude/rules/` for SweetClaude instructions; remove only the SweetClaude-specific content. Inspect `~/.claude/agents/sweetclaude/` and individual agent files including `implementer`, `test-writer`, `qa-caucus-component`, `qa-caucus-integration`, `qa-caucus-service`, `security-reviewer`, `code-reviewer`, and `workflow-guardian`; identify their contents before removing old SweetClaude copies. Inspect `~/.claude/skills/sweetclaude/`, `~/.claude/hooks/sweetclaude/`, `~/.claude/scripts/sweetclaude/`, `~/.claude/config/sweetclaude/`, and any `~/.claude/scripts/skills` symlink. Remove only confirmed obsolete SweetClaude files, and check hook commands in `~/.claude/settings.json` for references to them. Remove `plansDirectory` only if it is the unwanted SweetClaude value `.sweetclaude/plans`.
3. Inspect `~/.claude/backup-pre-sweetclaude-*` and `~/.claude/.sweetclaude-legacy-backup` as historical backups; retain them until you have reviewed their contents. Marketplace entries and caches under `~/.claude/plugins/` do not themselves enable a plugin. Use `claude plugin marketplace list` to inspect stable, beta and local-development registrations; remove an unwanted marketplace only after checking whether other plugins depend on it.
4. Check each repository's `.claude/settings.json`, `.claude/settings.local.json`, `CLAUDE.md`, and `.claude/rules/` for SweetClaude entries. Install locally using the commands above in each repository that needs it, then perform the isolation checks. See [migration and recovery](migration-and-recovery.md) for project data and older versions.

### Preview legacy global cleanup

Routine updates do not clean global hooks or rules. To review an optional cleanup, find the installed bundle path with `claude plugin list`, then run the following in a terminal, replacing `<bundle>` with that path:

```bash
python3 <bundle>/scripts/maintenance/global-cleanup.py preview
```

The preview lists the exact hook entries and legacy rules files it would remove, plus a `plan_hash`. If you want those changes, run the same script with `apply --plan-hash <plan_hash>`; otherwise do nothing. Apply refuses an outdated preview and saves a backup under the active Claude configuration directory's `.sweetclaude-legacy-backup/`. It removes only the listed global rules and recognized hooks; it does not clean agent files or other legacy paths. If `CLAUDE_CONFIG_DIR` is set, it uses that directory. Review and restore backups manually if needed.

**Current limitation:** local-scope enablement does not guarantee that older global artifacts are absent. Doctor can remove legacy global rules to a recoverable backup and can propose edits to existing global configuration; review those actions before running them. Doctor checks hooks in the plugin bundle and does not restore them into user-level hook directories. Local-scope hooks, agents, status line, and cross-project isolation have not been fully verified in an authenticated session for this release.

**Command verification:** on 2026-11-26, the installed Claude Code 2.1.332 CLI help was checked for marketplace add, install, list, uninstall, disable, and doctor. The install, migration, interactive session, and uninstall sequences were not executed end to end. Consult [Claude Code plugin documentation](https://code.claude.com/docs/en/discover-plugins) for current behavior.

**Upgrading from 4.x:** Run `/plugin marketplace update sweetclaude-stable`, then `/plugin update sweetclaude@sweetclaude-stable`, then restart Claude Code. Run `/sweetclaude:configure update` in each project after restarting. See [Upgrading to 5.0](upgrading-to-5.md).

**Upgrading from 3.x:** Older installs used `sweetclaude-stable` for the old marketplace. Check whether other projects depend on it, then run these commands in a terminal in the target repository:

```bash
claude plugin marketplace remove sweetclaude-stable
claude plugin marketplace add carson-sweet/sweetclaude@main
claude plugin install sweetclaude@sweetclaude-stable --scope local
```

Restart Claude Code and run `/sweetclaude:configure doctor` in each project. Doctor routes project repair or migration; update does not migrate project data.

### Switching from retired beta

In a terminal in the target repository, after checking whether other projects use the beta marketplace:

```bash
claude plugin marketplace add carson-sweet/sweetclaude@main
claude plugin install sweetclaude@sweetclaude-stable --scope local
claude plugin marketplace remove sweetclaude-beta
```

Restart Claude Code, then run `/sweetclaude:configure doctor` for project repair or migration. `/sweetclaude:configure update` does not migrate project data. Follow the user-scope migration steps above to remove any old global enablement.

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
