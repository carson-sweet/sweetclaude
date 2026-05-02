# Installing SweetClaude

## Prerequisites

| Dependency | Check | Install |
|---|---|---|
| [Claude Code](https://claude.ai/code) | `claude --version` | [Install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| [GitHub CLI](https://cli.github.com/) | `gh --version` | `brew install gh` or [cli.github.com](https://cli.github.com/) |
| Node.js (for RAG) | `node --version` | [nodejs.org](https://nodejs.org/) — optional, needed only for corpus management and semantic search |

Claude Code requires an Anthropic subscription. [Superpowers](https://github.com/obra/superpowers) is required for code and TDD features; not required for strategy-skills-only installs.

---

## Full Install

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
cd sweetclaude
./install.sh
```

The installer:
- Checks prerequisites (Claude Code, Git; Superpowers for full install)
- Backs up your existing `~/.claude/` configuration
- Scans for conflicting plugins and offers to clean them up
- Copies skills, hooks, agents, rules, and config to `~/.claude/`
- Wires TDD enforcement hooks into `settings.json`
- Generates `uninstall.sh` and `restore-config.sh` for clean removal

After install, all skills are available as `/sweetclaude:skill-name` in every Claude Code session.

---

## Strategy Skills Only

If you want product thinking, strategy, and corpus management — without code and TDD phases:

```bash
./install.sh --strategy-skills-only
```

Installs strategy, product, corpus, and orchestration skills. No TDD hooks, no subagents, no Superpowers required. Upgrade to the full install later by running `./install.sh`.

---

## Try Without Global Install

Load SweetClaude for a single session without modifying your global `~/.claude/` configuration:

```bash
git clone https://github.com/carson-sweet/sweetclaude.git
claude --plugin-dir /path/to/sweetclaude
```

All skills are available for that session. TDD enforcement hooks and global configuration are not active — those require the full install.

---

## Updating

```bash
/sweetclaude:update
```

Fetches the latest version from GitHub and syncs to all installed locations. Shows what changed, migrates state schemas if needed, and prompts to onboard any skills marked `uninitialized`.

---

## Uninstalling

```bash
~/.claude/sweetclaude-uninstall.sh
```

The installer wrote this script during install. It restores your pre-install `~/.claude/` configuration from the backup.

To suspend SweetClaude for one project without uninstalling globally:

```bash
touch .sweetclaude/disabled
```

Run `/sweetclaude:on` to reactivate.
