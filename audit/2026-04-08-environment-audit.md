# Claude Code Environment Audit Report

**Date**: 2026-04-08  
**User**: carsonsweet  
**Purpose**: Exhaustive inventory of all "extras" beyond native Claude Code capabilities, for cleanup and optimization.

---

## CRITICAL SECURITY ISSUE

**`~/.claude/settings.json` contains plaintext AWS credentials** in the permissions allow-list:

- Line 46: `export AWS_ACCESS_KEY_ID=AKIAUGTMYTSLW655Z3FR`
- Line 47: `export AWS_SECRET_ACCESS_KEY=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`
- Line 52: `export AWS_ACCESS_KEY_ID=AKIAUGTMYTSLWUFCRWYN`
- Line 72: `export AWS_SECRET_ACCESS_KEY=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`

**Action required**: Rotate these keys immediately and remove them from `settings.json`. Use `~/.aws/credentials` or environment variables instead. These appear to have been auto-added when the user approved `export` commands during sessions.

---

## 1. Global CLAUDE.md (`~/CLAUDE.md`)

- **Size**: 9,755 bytes (~280 lines)
- **What it does**:
  - Mandates accuracy/trust protocols (stop-before-responding, contradiction checks)
  - Defines a `cli_history/` progress tracking system with templates for PROGRESS.md and CONVERSATION_CONTEXT.md
  - Sets code style, documentation, testing, and git conventions
  - Mandates Superpowers plugin usage as non-overridable
  - Defines CLAUDE.md resolution order (project > parent dirs > home)
  - Requires full git working tree investigation on session start
  - Requires auto-save of progress on session end and before context compression

**Observations**:
- Heavy session-start requirements (read latest progress files, investigate git tree, read scratch/, docs/plans/, etc.) add latency and token cost to every conversation start
- The progress tracking templates alone are ~100 lines of boilerplate injected into context
- "Superpowers usage is ALWAYS mandatory" creates a hard dependency on that plugin

---

## 2. Installed Plugins

### 2a. Superpowers (`superpowers@claude-plugins-official` v5.0.7)

- **Source**: `anthropics/claude-plugins-official` marketplace (author: Jesse Vincent / obra)
- **Location**: `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.7/`
- **14 skills**:
  - `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `using-superpowers`, `verification-before-completion`, `writing-plans`, `writing-skills`
- **1 agent**: `code-reviewer.md`
- **Hooks**: SessionStart hook that runs on startup/clear/compact
- **SessionStart behavior**: Injects a large system-reminder that mandates skill checking before ANY response, with a "red flags" table discouraging skipping skills

**Observations**:
- The `using-superpowers` skill is injected at session start via hook and is very aggressive — it says "even a 1% chance a skill might apply means you should invoke the skill"
- This creates significant overhead: every user message triggers skill-relevance evaluation before any work begins
- Several skills overlap with Don Cheli functionality (TDD, debugging, code review, brainstorming)

### 2b. Frontend Design (`frontend-design@claude-plugins-official` v unknown)

- **Source**: `anthropics/claude-plugins-official` marketplace
- **Location**: `~/.claude/plugins/cache/claude-plugins-official/frontend-design/unknown/`
- **1 skill**: `frontend-design`
- Lightweight; no hooks or agents

---

## 3. Don Cheli SDD Framework (v1.26.0)

- **Location**: `~/.claude/don-cheli/`
- **Source**: `doncheli/don-cheli-sdd` (GitHub, auto-updates from remote)
- **What it is**: "Specification-Driven Development" framework — a comprehensive opinionated development methodology

### 3a. Commands (Slash Commands)

| Namespace | Count | Total Size | Language |
|-----------|-------|------------|----------|
| `/dc:*` | 76 | 331 KB | English |
| `/especdev:*` | 76 | 331 KB | Spanish (names) / Same content |
| `/razonar:*` | 15 | 34 KB | Spanish |
| Top-level (`/bucle*`, `/historias-generar`) | 4 | ~4 KB | Spanish |

**Key finding: `/dc:*` and `/especdev:*` are byte-identical content with different filenames.** This is 331 KB of pure duplication. The `especdev` namespace appears to be a Spanish-named alias set.

**Total slash commands: 171 commands, ~700 KB**

Command categories include:
- **Lifecycle**: `init`, `start`, `implement`, `apply`, `close-session`, `continue`
- **Specification**: `specify`, `validate-spec`, `spec-score`, `detect-ambiguity`, `clarify`, `drift`
- **Design**: `diseñar`, `tech-plan`, `pseudocode`, `api-contract`, `ui-contract`, `prd`
- **Review**: `review`, `pr-review`, `guardian`, `security-audit`, `clean-slop`
- **Estimation**: `estimate`, `preflight`
- **Collaboration**: `debate`, `roundtable`, `tech-panel`, `caucus`
- **Reasoning models**: 15 `/razonar:*` commands (first-principles, Pareto, inversion, pre-mortem, etc.)
- **Ops**: `doctor`, `diagnostic`, `validate`, `update`, `marketplace`, `webhook`
- **Autonomous loop**: `/bucle`, `/bucle-estado`, `/bucle-completar`, `/historias-generar`

### 3b. Internal Skills (48 skill directories)

Located at `~/.claude/don-cheli/skills/`, total ~156 KB:

`arnes-agente`, `auto-correccion`, `brainstorming`, `cambio-carpeta`, `code-rag`, `contabilidad-tokens`, `custom-gates`, `delta-specs`, `desarrollo-subagentes`, `deteccion-loops`, `deteccion-stubs`, `devlog`, `documentacion-viva`, `estimacion`, `extensiones-presets`, `generador-prd`, `generador-specs`, `ingenieria-contexto`, `integracion-mcp`, `leyes-hierro`, `mapa-arquitectonico`, `memoria-persistente`, `metricas-sesion`, `obsidian`, `optimizacion-tokens`, `optimizador-contexto`, `orquestacion-autonoma`, `permisos-seguridad`, `persona`, `planning-equipo`, `preflight`, `presentaciones`, `proyecciones-costo`, `prueba-trabajo`, `razonamiento`, `recuperacion-sesion`, `refactorizacion-solid`, `reflexion`, `rigor-progresivo`, `rlm`, `routing-modelos`, `salud-habilidades`, `schemas-dbml`, `time-travel`, `trazabilidad`, `ui-ux-design`, `validacion-nyquist`, `worktrees`

### 3c. Rules

Located at `~/.claude/don-cheli/rules/` (~27 KB):

- `constitucion.md` — Framework constitution
- `hooks-parar.md` — Stop hooks
- `i18n.md` — Internationalization rules
- `leyes-hierro.md` — "Iron laws" (TDD, debugging, verification)
- `protocolo-debugging.md` — Debugging protocol
- `puertas-calidad.md` — Quality gates
- `reglas-desviacion.md` — Deviation rules
- `reglas-trabajo-globales.md` — Global work rules
- `skills-best-practices.md` — Skills best practices

### 3d. Hooks

- `parar.md` — Stop hook
- `post-herramienta.md` — Post-tool hook
- `pre-herramienta.md` — Pre-tool hook

### 3e. Auto-Update Mechanism

Don Cheli's CLAUDE.md instructs Claude to:
1. Check remote VERSION on GitHub at every session start
2. Clone, audit for security, validate structure, then auto-apply updates
3. Weekly check for third-party skill updates

### 3f. Templates, Scripts, Locales

- Templates: `checklist-requisitos.md`, docker configs, especdev configs, gate templates, PRD templates
- Scripts: `actualizar.sh`, `bucle.sh`, `generar-config.sh`, `instalar.sh`, `sdd-check.sh`, `skill-updater.sh`, `validar.sh`
- Locales: `en`, `es`, `pt` (JSON and YAML configs)
- Agents: `~/.claude/don-cheli/agents/` (directory exists, contents not enumerated)

---

## 4. User-Created Skills (`~/.claude/skills/`)

| Skill | Files | Description |
|-------|-------|-------------|
| `backlog-management` | SKILL.md | Backlog item management |
| `caucus` | SKILL.md, persona-presets.md, proctor-guide.md | Multi-expert perspective evaluation |
| `real-tdd` | SKILL.md | Strict TDD enforcement |
| `reconciling-documents` | SKILL.md | Document reconciliation and conflict finding |

**Total**: ~37 KB across 4 skills

---

## 5. MCP Servers (Connected)

Based on available tool definitions, the following MCP servers are configured:

| Server | Tools | Purpose |
|--------|-------|---------|
| **Neon** | 30+ tools | Postgres database management (branches, migrations, queries, schema) |
| **Figma** (claude.ai) | 17 tools | Design-to-code, screenshots, Code Connect, FigJam |
| **Gmail** (claude.ai) | authenticate | Email (needs auth) |
| **Google Calendar** (claude.ai) | authenticate | Calendar (needs auth) |
| **Notion** (claude.ai) | 16 tools | Page/database CRUD, comments, views, search |
| **Tavily** (claude.ai) | 6 tools | Web search, crawl, extract, research |
| **Cloudflare R2** | authenticate | Object storage (needs auth) |
| **Neo4j** | authenticate | Graph database (needs auth) |
| **VoiceMode** | 3 tools | Voice interaction |

**Total MCP tools available**: ~80+

---

## 6. Settings & Permissions

### 6a. `settings.json`

- **Default permission mode**: `acceptEdits`
- **`skipDangerousModePermissionPrompt`**: `true`
- **148 explicit allow rules** including:
  - Broad AWS CLI access (`Bash(aws:*)`)
  - SSH, SCP, docker, nmap
  - Git operations (add, commit, push, merge, branch, pull, checkout, worktree)
  - Python, pip, make, rm, mv, mkdir
  - Several domain-specific WebFetch allows
  - **Hardcoded AWS credentials** (see CRITICAL issue above)

### 6b. `settings.local.json`

- 22 additional WebFetch domain allows (personal sites, LinkedIn, Crunchbase, Anthropic docs, GitHub raw, etc.)
- `Bash(claude plugin info:*)` allow

### 6c. Plugin Blocklist

2 entries in `~/.claude/plugins/blocklist.json`:
- `code-review@claude-plugins-official` — blocked, reason: "just-a-test"
- `fizz@testmkt-marketplace` — blocked, reason: "security"

### 6d. Plugin Marketplaces

2 registered marketplaces:
- `claude-plugins-official` (anthropics/claude-plugins-official)
- `superpowers-marketplace` (obra/superpowers-marketplace)

---

## 7. Overlap & Redundancy Analysis

### 7a. Duplicate Command Namespaces

`/dc:*` and `/especdev:*` are **100% byte-identical** (verified via MD5). This is **331 KB of pure duplication** in the commands directory, and **~152 duplicate skill entries** in the session system prompt.

### 7b. Competing TDD Implementations

| Source | Skill | Approach |
|--------|-------|----------|
| Superpowers | `test-driven-development` | RED-GREEN-REFACTOR |
| Don Cheli | `leyes-hierro` + `/dc:implement` | TDD as "iron law" |
| User skill | `real-tdd` | Strict TDD enforcement |
| Global CLAUDE.md | Superpowers section | Mandates Superpowers TDD |

Three separate TDD enforcement mechanisms that may conflict or confuse the model.

### 7c. Competing Debugging Approaches

| Source | Skill |
|--------|-------|
| Superpowers | `systematic-debugging` |
| Don Cheli | `protocolo-debugging.md` rule |
| Global CLAUDE.md | Mandates Superpowers debugging |

### 7d. Competing Brainstorming/Design

| Source | Skill |
|--------|-------|
| Superpowers | `brainstorming` |
| Don Cheli | `brainstorming` skill + `/dc:debate` + `/dc:roundtable` + `/dc:tech-panel` |
| User skill | `caucus` |
| Global CLAUDE.md | Mandates Superpowers brainstorming |

### 7e. Competing Code Review

| Source | Skill |
|--------|-------|
| Superpowers | `requesting-code-review`, `receiving-code-review`, `code-reviewer` agent |
| Don Cheli | `/dc:review`, `/dc:pr-review`, `/dc:guardian` |

### 7f. Competing Session Recovery

| Source | Mechanism |
|--------|-----------|
| Global CLAUDE.md | `cli_history/` progress files |
| Don Cheli | `/dc:continue`, `/dc:close-session`, recovery skills |
| Superpowers | Plans in `docs/plans/` |

---

## 8. Context Token Cost Estimate

Every session start injects or makes available:

| Component | Approximate Size |
|-----------|-----------------|
| Global CLAUDE.md | ~10 KB |
| Don Cheli CLAUDE.md | ~3 KB |
| Superpowers SessionStart hook output | ~5 KB |
| Skill registry in system prompt (all skill names + descriptions) | ~15-20 KB |
| MCP tool definitions (deferred, loaded on demand) | Variable |
| **Always-loaded total** | **~35-40 KB** |

The ~700 KB of slash command content is loaded on-demand (only when invoked), so it doesn't consume baseline context. But the skill registry listing alone (~170 entries) consumes significant prompt space.

---

## 9. Summary of Installed Extras

| Category | Item | Source | Notes |
|----------|------|--------|-------|
| Plugin | Superpowers v5.0.7 | claude-plugins-official | 14 skills, 1 agent, hooks |
| Plugin | Frontend Design | claude-plugins-official | 1 skill |
| Framework | Don Cheli SDD v1.26.0 | doncheli/don-cheli-sdd | 76 EN + 76 ES commands, 48 skills, 9 rules, hooks, auto-updater |
| Slash Commands | `/razonar:*` | Don Cheli | 15 reasoning model commands |
| Slash Commands | `/bucle*`, `/historias-generar` | Don Cheli | 4 autonomous loop commands |
| User Skill | backlog-management | User-created | Backlog management |
| User Skill | caucus | User-created | Multi-expert evaluation |
| User Skill | real-tdd | User-created | Strict TDD |
| User Skill | reconciling-documents | User-created | Document reconciliation |
| MCP Server | Neon | Cloud | Postgres management |
| MCP Server | Figma | claude.ai | Design-to-code |
| MCP Server | Gmail | claude.ai | Email (needs auth) |
| MCP Server | Google Calendar | claude.ai | Calendar (needs auth) |
| MCP Server | Notion | claude.ai | Knowledge management |
| MCP Server | Tavily | claude.ai | Web research |
| MCP Server | Cloudflare R2 | Cloud | Object storage (needs auth) |
| MCP Server | Neo4j | Cloud | Graph DB (needs auth) |
| MCP Server | VoiceMode | Local | Voice interaction |
| Config | Global CLAUDE.md | ~/CLAUDE.md | 280 lines of behavioral rules |

---

## 10. Cleanup Recommendations (for reviewer)

1. **URGENT: Remove AWS credentials from `settings.json`** and rotate keys
2. **Delete `/especdev:*` commands** — byte-identical duplicate of `/dc:*` (saves 331 KB)
3. **Resolve TDD conflict** — pick ONE of: Superpowers TDD, Don Cheli TDD, or `real-tdd` skill
4. **Resolve debugging conflict** — pick ONE of: Superpowers or Don Cheli
5. **Resolve brainstorming conflict** — pick ONE of: Superpowers, Don Cheli debate/roundtable, or caucus
6. **Resolve session recovery conflict** — pick ONE of: `cli_history/` system or Don Cheli's
7. **Evaluate Don Cheli necessity** — if Superpowers is the preferred methodology, Don Cheli adds 76 commands + 48 skills + auto-updater of marginal additional value. If Don Cheli is preferred, Superpowers becomes redundant
8. **Trim settings.json allow-list** — 148 rules, many very specific to past sessions (CloudFormation stack names, specific deploy scripts). Consider pruning stale entries
9. **Disable unused MCP servers** — Gmail, Google Calendar, Cloudflare R2, Neo4j all show "needs auth" and may not be actively used
10. **Review `skipDangerousModePermissionPrompt: true`** — this disables safety confirmations for destructive operations
