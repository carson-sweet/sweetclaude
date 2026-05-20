# Next-Gen Strategy: Aligning SweetClaude with Claude Code Skills SOTA

**Version:** 1.0
**Date:** 2026-05-04
**Author:** External consulting review
**Audience:** Project owner, future maintainers
**Status:** Recommendations — no changes applied

---

## 0. Reading guide

This is a long document. Skim section 1 for the verdict. Read sections 2–3 if you want to know the gap. Read sections 4–6 for the prioritized recommendations and the migration plan. Section 7 is risks. Section 8 is the things I deliberately *don't* recommend.

---

## 1. Executive summary

**Verdict:** SweetClaude is doing the hard part well — opinionated workflow design, hook-enforced TDD, persistent state, behavioral contracts — but it is using roughly 30% of the Claude Code plugin surface area Anthropic now ships. The frontmatter conventions, the install path, and the hook registration model are all leftovers from an earlier era of Claude Code (pre-plugin marketplace, pre-Skills frontmatter expansion). The skills themselves are good; the wrapping around them is dated.

**The single biggest lift:** stop treating SweetClaude as "files copied into `~/.claude/`" and start treating it as a real plugin with `${CLAUDE_PLUGIN_ROOT}`-rooted hooks, marketplace-driven installation, and `${CLAUDE_PLUGIN_DATA}`-managed persistent state. That shift unlocks several other modernizations (proper updates, version pinning, dependency declarations, multi-scope installs).

**The "Skills 2.0" framing in the Medium article is partly Anthropic-shipped, partly aspirational.** Hot reload, forked context, progressive disclosure, and the frontmatter expansion (`when_to_use`, `paths`, `effort`, `agent`, `hooks`, `arguments`) are in Anthropic's official docs and are real. "Skill Creator," "structured evals," "A/B testing," and "trigger optimization" are the author's reframing of techniques you can build on top of the platform — they aren't features Anthropic ships. The recommendations below distinguish between the two.

**Top five recommendations in order:**

1. **Re-root the plugin on `${CLAUDE_PLUGIN_ROOT}`** — eliminate hard-coded `~/.claude/...` paths, fix hook registrations, replace `install.sh` with marketplace install. (High lift, very high payoff. Unlocks 4–11.)
2. **Adopt the modern frontmatter contract** on every skill — `when_to_use`, `paths`, `disable-model-invocation`, `allowed-tools`, `effort`, named `arguments`, per-skill `hooks`. (Mechanical but tedious. Big trigger-accuracy lift.)
3. **Move heavy skills to `context: fork` with `agent` pairing** — currently 1 of 89 skills uses fork. Skills like `code-feature`, `document-corpus`, `master`, `find-skill` should fork. (Medium lift, large context-budget payoff.)
4. **Build a structured-eval harness on top of `behavioral-regression`** — convert the existing 15 contracts into a runnable golden-suite with pass/fail per contract per model. (Medium lift, durable competitive moat.)
5. **Trim the skill-listing footprint** — 89 skills × 176 chars = ~16KB; default budget is ~8KB. Internal skills are crowding the listing. Use `disable-model-invocation` and tighter descriptions to fit. (Low lift, immediate quality lift.)

---

## 2. What I read to write this

- The Medium article: *Claude Skills 2.0: The Self-Improving AI Capabilities That Actually Work.* Useful for framing but not authoritative.
- Anthropic's official **plugins reference** at `https://code.claude.com/docs/en/plugins-reference`. This is the source of truth for plugin manifest schema, component locations, env vars, caching, CLI commands, and versioning.
- Anthropic's official **skills documentation** at `https://code.claude.com/docs/en/skills`. This is the source of truth for SKILL.md frontmatter, dynamic context injection, fork contexts, allowed-tools, paths, arguments, and the listing budget.
- The current SweetClaude repo: `README.md`, `docs/user-guide/*.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, all 89 skills, all 8 agents, all 19 hook scripts, the hooks manifest, and the install/uninstall scripts.

The terminology in this document follows Anthropic's official docs, not the Medium article's reframing.

---

## 3. Current state — the audit

### 3.1 Plugin manifest

`/Users/carsonsweet/dev/sweetclaude/.claude-plugin/plugin.json`:

| Field | Current | Anthropic-recommended | Gap |
|---|---|---|---|
| `name` | `sweetclaude` | required | OK |
| `version` | `1.27.0` | semver | OK, but **drifts** from `marketplace.json` (`1.0.0`) |
| `description` | "60 skills from first concept to shipped code" | accurate | **Wrong** — repo has 89 skills |
| `dependencies` | not set | array, supports semver | **Missing** — Superpowers is a soft dep, not declared |
| `userConfig` | not set | declarative user prompts | **Missing** — could replace setup interview |
| `agents` | not set (auto-discovered) | declared or default path | OK |
| `hooks` | not set (auto-discovered) | path or inline | **Should be set** — explicit declarations are easier to audit |
| `mcpServers` | not set | path or inline | OK (none bundled today) |
| `commands` | not set | for flat-file commands | OK (using directory skills) |

`marketplace.json` exists but its `version: 1.0.0` is wildly stale. Per Anthropic's spec, `plugin.json.version` wins, so this isn't breaking anything — it's just a smell.

### 3.2 Skills inventory

89 skills total. Organized as `skills/<name>/SKILL.md` — correct shape per Anthropic's spec.

**Frontmatter audit (89 skills sampled):**

| Field | Skills using it | Skills 2.0 SOTA usage |
|---|---|---|
| `name` | ~70 | should be on every skill — uses dirname fallback otherwise, fragile when dir name and intended slash command diverge |
| `description` | 89 | required, OK |
| `when_to_use` | **0** | should be on user-facing skills — separate trigger guidance from purpose |
| `user-invocable` | many | overused — not the same as `disable-model-invocation` (see 3.3) |
| `disable-model-invocation` | **0** | should be on workflow skills with side effects (`deploy-ship`, `purge`, `update`, `something-broke`) |
| `allowed-tools` | **0** | huge missed opportunity — every TDD skill needs `Bash(git *) Bash(npm *) ...` to avoid permission prompts |
| `effort` | **0** | should be `high` for `code-feature`, `design-architecture`; `medium` default; `low` for status/help |
| `paths` | **0** | should gate activation by file pattern — `code-tdd` only on test/source files, `design-wireframes` only on `.html`/`.tsx` |
| `arguments` | **0** | named args would replace many `$ARGUMENTS` parses inside skills (`product-milestones add MS-001`, etc.) |
| `hooks` (per-skill) | **0** | per-skill lifecycle hooks are now supported — could replace some global hook gymnastics |
| `context: fork` | **1** | only `caucus`-like skills should run inline; `code-feature`, `master`, `find-skill`, `document-corpus`, `code-issue` should fork |
| `agent` | **0** | pairs with `context: fork` — the 8 existing subagents in `agents/` aren't being used this way |
| `model` | a few subagents | could pin model per skill where reasoning depth differs |
| `argument-hint` | **0** | autocomplete UX miss — `[issue#]`, `[mode]`, `[type]` hints are documented in the docs but not surfaced in the menu |

**Description length:** average 176 chars. Anthropic caps the *combined* `description + when_to_use` at 1,536 chars per entry, so there is plenty of headroom for trigger phrases, synonyms, and example invocations.

**Listing budget pressure:** 89 skills × ~176 chars ≈ 16,000 chars in the listing alone. The default budget is ~8,000 chars (or 1% of context window, whichever is larger). The system **truncates** descriptions to fit. That means trigger phrases at the end of descriptions are *getting cut*. This is a silent quality issue.

### 3.3 `user-invocable: false` vs. `disable-model-invocation: true`

These are not equivalent and SweetClaude is conflating them.

| Field | Effect | When to use |
|---|---|---|
| `user-invocable: false` | Skill **hidden from the `/` menu**. Claude can still auto-invoke based on description. Description **stays in context** so Claude knows the skill exists. | Internal helper skills that aren't sensible user actions but Claude should call (`_route`, `_offer`, `_health`, `find-skill`). |
| `disable-model-invocation: true` | User can `/invoke` it. Claude **cannot** auto-trigger. Description is **removed from context** entirely. | Skills with side effects where you want explicit user control (`purge`, `deploy-ship`, `update`, `off`, `something-broke`, `john-wick`). |

SweetClaude currently uses `user-invocable: false` for both groups. The cost: skills like `purge`, `deploy-ship`, `something-broke`, `update` either show in the menu (explicit user trigger) but Claude can also auto-invoke them — risky. And internal skills marked `user-invocable: false` still sit in the listing budget.

### 3.4 Hooks

`/Users/carsonsweet/dev/sweetclaude/hooks/` has 19 scripts, registered via `hooks-manifest.json`. The session-preflight wires global hooks into `~/.claude/settings.json` and project hooks into `.claude/settings.local.json`.

This is where the architecture diverges most from current Anthropic guidance. Three issues:

**(a) Hard-coded paths.** Hook registrations point at absolute `${HOME}/.claude/hooks/sweetclaude/...`. The Anthropic recommended pattern is `${CLAUDE_PLUGIN_ROOT}/hooks/...`, which Claude Code substitutes at runtime. The current pattern only works for the global-install layout SweetClaude shipped originally; it is the reason SweetClaude requires `install.sh` instead of letting the marketplace handle install.

**(b) `hooks/hooks.json` exists but is not declared in `plugin.json`.** Anthropic's plugin loader auto-discovers `hooks/hooks.json` at the plugin root, so this works — but the plugin can't be cleanly forked, mirrored, or sub-installed because the hooks aren't part of the manifest.

**(c) Some hooks are documented as "registered by `sweetclaude:on`" or "registered when guardian-on activates."** This dynamic registration into the user's `settings.local.json` is fragile in the new plugin world: when Claude Code copies the plugin to its cache, mid-session edits to `settings.local.json` don't track the cache version. The intent is right (per-project enabling) but the mechanism is now obsolete — Anthropic's `paths` and per-skill `hooks` fields, plus `userConfig`, can replace most of it declaratively.

### 3.5 Subagents

8 agent files exist in `/Users/carsonsweet/dev/sweetclaude/agents/`. The shapes are correct (frontmatter with `name`, `description`, `tools`, `model`, body as system prompt). But:

- They aren't paired with `context: fork` skills via the `agent` field. Currently the agents are spawned ad-hoc inside skill bodies via Task/Agent tool calls.
- `model` is set on most. `effort` is not set on any. `maxTurns`, `disallowedTools`, `skills` (preload), `memory`, `background`, `isolation` are not used.
- `tools: Read, Grep, Glob, Write, Bash` is a comma-separated list. The Anthropic spec accepts space-separated or YAML list — both fine.

The opportunity: every "spawn isolated subagent" instruction in a skill body could become `context: fork` + `agent: test-writer` in the calling skill's frontmatter. That cleans up the skill bodies and gets the isolation contract into the manifest layer where it can be statically inspected.

### 3.6 MCP, LSP, monitors, themes, output-styles

| Component | Current | Could be useful? |
|---|---|---|
| MCP servers | none bundled | **Yes** — `mcp-local-rag` is a soft dep; could be optionally bundled or wrapped via `dependencies` |
| LSP servers | none | Probably not — SweetClaude is language-agnostic by design |
| Monitors | none | **Yes** — `auto-test-runner.sh` could become a monitor watching test output during IMPLEMENT, with results streamed as notifications. RAG corpus watcher is another candidate. |
| Themes | none | Skip |
| Output styles | none | **Maybe** — a "sweetclaude-terse" output style for autonomous mode could reduce token use |
| `bin/` | empty | **Yes** — `sc-artifact`, the install/uninstall helpers, scratch tools — these belong in `bin/` so they're invokable as bare commands |

### 3.7 Install / update / uninstall

`install.sh` is the primary install path. It backs up `~/.claude/`, copies skills/hooks/agents/rules, wires hooks into `settings.json`, and writes `uninstall.sh` and `restore-config.sh`. This is well-engineered — but it's solving a problem Claude Code's plugin marketplace now solves natively.

The Anthropic-supported flow is:

1. User has a marketplace (or runs `claude --plugin-dir /path/to/plugin` for one-off).
2. User runs `claude plugin install sweetclaude@<marketplace>`.
3. Claude Code copies the plugin to `~/.claude/plugins/cache/<id>/<version>/`.
4. Hooks reference `${CLAUDE_PLUGIN_ROOT}` — Claude Code resolves to the cache path at runtime.
5. Plugin updates: `claude plugin update sweetclaude` — version-pinned in `plugin.json`.
6. Persistent state: `${CLAUDE_PLUGIN_DATA}` survives version updates.
7. Uninstall: `claude plugin uninstall sweetclaude` — handled by the CLI.

SweetClaude can keep `install.sh` as a fallback for users who don't have the marketplace, but the recommended primary path needs to flip.

### 3.8 Plugin `description` in manifest is gimped

`"60 skills from first concept to shipped code"` — that's a stale count, and more importantly, the description doesn't describe *when* Claude should pull the plugin's commands into its working set. Marketplace discovery is going to ask for trigger keywords. This is the front door of the plugin and it's underwritten.

### 3.9 Doc cohesion

The user-guide is well-written and cohesive. Two notes:

- `docs/user-guide/skills-reference.md` lists skills by domain, but doesn't show the `argument-hint` or `paths` activation patterns (they don't exist yet). When you adopt the modern frontmatter, the reference needs a regen pass.
- `docs/user-guide/install.md` still describes `./install.sh` as the only path. Keep it as a fallback but move marketplace install to the top once the plugin is properly rooted.

---

## 4. Gap analysis vs Skills SOTA

### 4.1 What Anthropic actually ships (as of these docs)

These are the real, official capabilities I'd hold SweetClaude to:

- **Plugin manifest schema** — full `plugin.json` with `dependencies`, `userConfig`, `channels`, `monitors`, `lspServers`, etc.
- **`${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}`** — runtime path resolution + persistent data dir
- **Plugin caching** — copy-on-install to `~/.claude/plugins/cache/<id>/<version>`, 7-day grace period for orphaned versions
- **Plugin CLI** — `install`, `uninstall`, `update`, `enable`, `disable`, `prune`, `tag`, `list`, `validate`
- **Skill frontmatter** — `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell`
- **Dynamic context injection** — `` !`<command>` `` and ` ```! ` blocks
- **Forked subagent execution** — `context: fork`, agent selection
- **Live change detection** — hot reload of skill files within a session
- **Progressive disclosure** — descriptions in context, full body on invoke; auto-compaction carries skills forward at 5KB/skill, 25KB total budget
- **Listing budget management** — `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var; 1,536-char per-entry cap
- **Permission integration** — `Skill(name)` allow/deny rules, `disableSkillShellExecution` policy
- **Plugin scopes** — user / project / local / managed
- **Path-specific activation** — `paths` glob list
- **Subagents** — full spec with `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills` (preload), `memory`, `background`, `isolation`
- **Hooks** — 30+ event types including `InstructionsLoaded`, `SubagentStart`/`Stop`, `TaskCreated`/`Completed`, `FileChanged`, `WorktreeCreate`/`Remove`
- **Monitors** — persistent background commands streaming notifications

### 4.2 What the Medium article calls "Skills 2.0" but isn't an Anthropic feature

- **Skill Creator** — third-party tooling concept; you can build it yourself
- **Structured Evaluations** — a *technique* (golden suite + scoring), not an Anthropic feature
- **A/B Testing Framework** — same — a technique
- **Trigger Optimization** — what Anthropic calls "writing better descriptions" — in their docs, just guidance
- **Hot Reload / Forked Context / Progressive Disclosure** — these are real and shipped — the article is right about these

I'm calling this out because if you take the Medium article at face value, you'd expect Anthropic to ship a "Skill Creator" CLI and an "A/B testing framework." They don't. But the *concepts* are sound and you can implement them yourself — that's what most of section 5 is about.

### 4.3 The five biggest concrete gaps

| # | Gap | Severity | Notes |
|---|---|---|---|
| 1 | Hooks point at `~/.claude/hooks/sweetclaude/...` instead of `${CLAUDE_PLUGIN_ROOT}/hooks/...` | **Critical** | Blocks marketplace install, version cache, multi-scope, clean updates |
| 2 | 0 skills use `paths`, `when_to_use`, `allowed-tools`, `effort`, named `arguments` | **High** | Trigger accuracy + permission noise + no path-gated activation |
| 3 | 89 skills × 176 chars ≈ 16KB — exceeds 8KB default listing budget | **High** | Trigger phrases are silently truncated |
| 4 | 1 of 89 skills uses `context: fork` | **High** | Heavy skills load full body inline — context burn |
| 5 | `behavioral-regression` is instruction-tested, not a structured eval harness | **Medium** | Won't catch silent model drift reliably |

---

## 5. Prioritized recommendations

I've ordered these by **impact × ease**, not by topical grouping. Each item is concrete and refers to specific files in the repo.

### R1 — Re-root all hooks on `${CLAUDE_PLUGIN_ROOT}` ⭐ critical

**What:** Replace every `${HOME}/.claude/hooks/sweetclaude/<file>.sh` reference in `hooks-manifest.json`, `session-preflight.sh`, and any registration logic with `${CLAUDE_PLUGIN_ROOT}/hooks/<file>.sh`.

**Why:** This is the single change that lets SweetClaude install via marketplace, support multiple installed versions, get clean updates, and be packaged like a real plugin. It also breaks the implicit assumption that the user has run `install.sh`.

**Where to look:**
- `/Users/carsonsweet/dev/sweetclaude/hooks/hooks-manifest.json`
- `/Users/carsonsweet/dev/sweetclaude/hooks/session-preflight.sh` lines 99–100, 145–148
- `/Users/carsonsweet/dev/sweetclaude/install.sh` (regen wiring)
- `/Users/carsonsweet/dev/sweetclaude/skills/master/SKILL.md` step 1 of pre-flight (lines 26–30)

**Risk:** Existing installations won't migrate cleanly. Mitigate with an `install.sh --migrate` flag that detects the old layout and rewires.

**Status check:** verify the cache-vs-source path collision doesn't break the version-bump hook. The hook currently writes to `package.json` in the source repo; under the cached install model that file is read-only. Move the version-bump logic out of the cache.

### R2 — Adopt the modern frontmatter contract everywhere

**What:** Every skill gets a frontmatter audit. The fields to add or fix:

- `name:` on all skills (currently ~20 missing — relying on dirname fallback)
- `when_to_use:` on all user-facing skills — distinct from `description`, packed with trigger phrases
- `argument-hint:` on every skill that takes arguments — `[issue-number]`, `[mode]`, `[type]`, etc.
- `arguments:` (named) for skills with positional args (`migrate-component`, `product-milestones`, etc.)
- `disable-model-invocation: true` on side-effect skills: `deploy-ship`, `purge`, `update`, `off`, `john-wick`, `something-broke`, `behavioral-regression`, `hibernate`
- Reserve `user-invocable: false` for genuine internals: `_route`, `_offer`, `_health`, `_migrate`, `master`, `find-skill`, `bootstrap`, `next-steps`
- `allowed-tools:` on every skill — drastically reduces permission prompts. Examples below.
- `effort: high` on `code-feature`, `design-architecture`, `design-tech-spec`, `product-prd`, `code-issue`
- `paths:` on language-specific skills — `code-tdd` on `*.test.*, *.spec.*, src/**`; `design-wireframes` on `*.tsx, *.html`
- `model:` on heavy reasoning skills if you want to pin Opus

**Example modernized frontmatter for `code-feature`:**

```yaml
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:code-feature
description: Build a new feature end-to-end with TDD discipline and a PR at the end.
when_to_use: |
  Use when the user wants to implement a new feature, add functionality,
  build a story, ship something new, or work from a Gherkin spec, PRD, or
  user story. Trigger phrases include "build feature", "implement story",
  "add functionality", "ship the X feature", "work the auth story".
  Auto-invokes the full TDD Level 3 pipeline.
argument-hint: "[feature-description]"
arguments: feature
disable-model-invocation: false
allowed-tools: >
  Read Grep Glob Edit Write Bash(git *) Bash(npm *) Bash(npx *)
  Bash(yarn *) Bash(pnpm *) Bash(bun *) Bash(pytest *) Bash(go test *)
context: fork
agent: general-purpose
effort: high
paths: src/**, tests/**, *.feature, .sweetclaude/stories/**
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      command: ${CLAUDE_PLUGIN_ROOT}/hooks/test-guardian.sh
---
```

**Why:** Trigger accuracy goes up (the article's 50%→100% case study). Permission prompts go away. Listing pressure drops because internal skills get pulled out of the listing. Per-skill hooks let you remove the global hook-registration ceremony from `sweetclaude:on`.

**Where:** All 89 skills. Tedious but mechanical. Generate with a script.

### R3 — Move heavy skills to forked context

**What:** Add `context: fork` and an `agent:` to skills whose body and outputs blow past ~2,000 tokens or run in isolation by design.

**Candidates (priority order):**

| Skill | Why fork | Pair with agent |
|---|---|---|
| `master` | reads state, runs preflight, tons of inline body — never need it in main context | `general-purpose` |
| `code-feature` | full TDD pipeline, large body | `general-purpose` |
| `code-issue` | similar | `general-purpose` |
| `code-debt` | scope phase tests + refactor | `general-purpose` |
| `document-corpus` | corpus reads can be huge | `Explore` |
| `find-skill` | classifier + decision — clean fork is ideal | `Plan` |
| `design-architecture` | long body, deep reasoning | `Plan` |
| `design-ux-review` | already spawns parallel personas | `Explore` |
| `code-review` | needs to read code without polluting main | `code-reviewer` (existing) |
| `code-testing` | runs broad inspections | `general-purpose` |

**Why:** Each forked skill saves the inline cost of its body (often 2–4KB) plus the cost of any state/context it reads. With 89 skills in the plugin, listing budget is already tight; aggressive forking is the cleanest mitigation.

**Cost:** Forked skills don't see the main conversation. Skills that need conversational continuity (e.g. `go`, `status`, `help`, `next-steps`) must stay inline.

### R4 — Wire the existing 8 agents into skills via `agent:`

**What:** The agents in `/Users/carsonsweet/dev/sweetclaude/agents/` (`test-writer`, `implementer`, `qa-caucus-component`, `qa-caucus-integration`, `qa-caucus-service`, `code-reviewer`, `security-reviewer`, `workflow-guardian`) should be reachable via `context: fork` + `agent:<name>` in skill frontmatter — and via the `Task`-tool agent invocation path that's already in the codebase.

Currently most skills spawn agents via Task tool calls inside the body. That works but couples the dispatch logic to the skill text. Pulling it into frontmatter:

```yaml
---
name: sweetclaude:code-tdd-test-writer-pass
context: fork
agent: test-writer
allowed-tools: Read Grep Glob Write Bash
---
Write failing tests from the Gherkin specs in $ARGUMENTS.
```

Lets you statically declare the isolation contract.

**Why:** The contracts get clearer ("this skill ALWAYS runs in agent X with these tools"), the body shrinks, and Anthropic-side optimizations (like description preloading into subagents) become available.

### R5 — Build a structured eval harness on top of `behavioral-regression`

**What:** The current `behavioral-regression` skill is a checklist Claude self-reports against. Convert it into a runnable harness:

1. **Each contract gets a fixture file** — `evals/contracts/no-time-estimate/input.md`, `expected.json` (assertions about response).
2. **A small driver script** (Node or Python — pick what's already in repo) reads each fixture, sends `input.md` to a Claude API call, asserts against `expected.json`. Pass/fail per contract.
3. **A nightly or release-gated workflow** — runs the suite against the current target model, writes a markdown report.
4. **Per-model history** — stored in `evals/results/<model-id>-<date>.json`. Compare across model versions to detect drift.
5. **Surface the result** in `behavioral-regression` skill output: "13/15 passing on claude-sonnet-4-7. Failing: phase-dwelling, autonomous-respect."

**Why:** This is the closest thing to the "structured evals" the Medium article describes, and it's the most defensible technical claim SweetClaude makes (the README boasts 15/15 on sonnet-4-6). Right now that claim rests on Claude self-reporting. Build the harness, run it on every Claude model release, and the claim becomes auditable.

**Where to start:** existing `tests/` directory + `behavioral-regression` skill + Anthropic SDK Python or Node client.

### R6 — Listing-budget triage

**What:** Skills 2.0 docs note: when total skill descriptions exceed budget, *trailing characters are truncated*. With 89 skills × ~176 chars, you're at ~16KB; default budget ≈8KB. Trigger phrases at the end of descriptions are getting cut.

**Three fixes, layered:**

1. **Aggressive `disable-model-invocation: true` on skills with side effects** — removes them from the listing entirely. Targets: `purge`, `deploy-ship`, `update`, `something-broke`, `john-wick`, `john-wick-checkin`, `hibernate`, `off`. (~10 skills, ~1.7KB saved.)
2. **`user-invocable: false` for genuine internals** — these stay in the listing but don't show in `/menu`. (~15 skills already; audit the rest.)
3. **Trim descriptions to 100 chars where possible** — move trigger phrasing into `when_to_use` (which has its own slot). Currently description does double duty.
4. **Set `SLASH_COMMAND_TOOL_CHAR_BUDGET=20000`** in the recommended user setup — gives breathing room.

**Why:** The plugin's selling point is "70+ skills." If half their descriptions are getting truncated mid-sentence, half the trigger accuracy is gone.

### R7 — Replace `install.sh` with marketplace as primary install

**What:**

1. Fix `marketplace.json` version (1.27.0, not 1.0.0) and ship a CHANGELOG.
2. Document the marketplace install flow in `docs/user-guide/install.md` as the *primary* path.
3. Keep `install.sh` as a fallback for users without marketplace access, mark it as such.
4. Once R1 ships, move all hooks to `${CLAUDE_PLUGIN_ROOT}` and the install.sh script becomes simpler — it's just `claude plugin install sweetclaude --plugin-dir .`.

**Why:** The current install.sh is solving a problem that no longer exists. Plugin marketplaces handle install, update, version pinning, scope (user/project/local), enable/disable, and uninstall. Reusing them gets you all of that for free.

**Caveat:** Anthropic's own marketplace is opinionated about who gets in. If the goal is OSS distribution, document a self-hosted-marketplace pattern (just a git repo with a `marketplace.json` and the plugin source) and direct users to install via that.

### R8 — Use `userConfig` for declarative setup

**What:** The setup interview in `sweetclaude:on` and `sweetclaude:setup` asks several questions: deference level, mode, version stage, etc. Many of these are good candidates for `userConfig` in `plugin.json`:

```json
{
  "userConfig": {
    "default_deference": {
      "type": "string",
      "title": "Default deference level",
      "description": "Collaborative, Guided, or Autonomous",
      "default": "guided"
    },
    "default_mode": {
      "type": "string",
      "title": "Default project mode",
      "description": "Flow, Kanban, Level Up, or Agile",
      "default": "flow"
    },
    "rag_endpoint": {
      "type": "string",
      "title": "Local RAG endpoint",
      "description": "URL of mcp-local-rag if installed",
      "default": ""
    },
    "anthropic_api_key": {
      "type": "string",
      "title": "Anthropic API key (for behavioral-regression eval suite)",
      "description": "Only needed for the eval harness, not for normal use",
      "sensitive": true
    }
  }
}
```

These appear as `${user_config.default_deference}` in skill bodies and as `CLAUDE_PLUGIN_OPTION_DEFAULT_DEFERENCE` env vars in hooks. Sensitive values (API keys) go to keychain.

**Why:** Replaces several rounds of interview ceremony with one declarative dialog at install time. Users can change values later via `/plugin reconfigure`.

### R9 — Use `${CLAUDE_PLUGIN_DATA}` for cross-version persistence

**What:** Anything SweetClaude writes that should outlive a plugin update goes in `${CLAUDE_PLUGIN_DATA}`. Candidates:

- Behavioral-regression historical results (cross-version drift data)
- Usage tracking (`/sweetclaude:usage`)
- RAG corpus index metadata (the corpus itself is per-project, in `.sweetclaude/`, but some plugin-level state might warrant `${CLAUDE_PLUGIN_DATA}`)
- Skill-tracker logs (currently per-project, but a global log would help diagnose recurring issues across projects)

**Why:** Without this, every plugin update wipes plugin-level state. The data dir is exactly what Anthropic shipped to solve this.

### R10 — Convert `auto-test-runner.sh` to a monitor

**What:** During the IMPLEMENT phase, the auto-test-runner hook fires PostToolUse on every Write/Edit. That's correct but heavy. An alternative: a `monitors/monitors.json` entry that watches the test runner's output (`tail -F` on a log, or a wrapper around `npm test --watch`) and streams notifications to Claude when tests change state.

```json
[
  {
    "name": "test-watcher",
    "command": "${CLAUDE_PLUGIN_ROOT}/scripts/test-watcher.sh",
    "description": "TDD test status during IMPLEMENT phase",
    "when": "on-skill-invoke:code-tdd"
  }
]
```

**Why:** Two benefits: (a) tests run in their own watcher process, not as a synchronous PostToolUse hook (less latency on every edit), and (b) Claude gets a stream of test-state notifications it can react to.

**Caveat:** Monitors require Claude Code v2.1.105+. Document the version floor.

### R11 — Use `bin/` for utility scripts

**What:** Move `scripts/sc-artifact.sh`, install/uninstall scripts (where appropriate), and other CLI utilities to `bin/`. They become invokable as bare commands when the plugin is enabled.

**Why:** Cleaner UX in skill bodies (`sc-artifact get foo` instead of `${CLAUDE_PLUGIN_ROOT}/scripts/sc-artifact.sh get foo`), and they show up in the user's PATH only when the plugin is active.

### R12 — Declare Superpowers as a formal dependency

**What:**

```json
{
  "dependencies": [
    { "name": "superpowers", "version": "~5.0.7" }
  ]
}
```

**Why:** Currently Superpowers is a soft prereq the user has to know about. Formalizing it lets Claude Code resolve and install it transitively, version-pin, and remove gracefully via `claude plugin prune`.

**Risk:** If Superpowers isn't in the same marketplace, this needs the marketplace operator to mirror it — or you can document the manual install for now and add the dep later.

### R13 — Subscribe to the new lifecycle hooks

Three hook events are particularly relevant and currently unused:

- **`InstructionsLoaded`** — fires when CLAUDE.md or `.claude/rules/*.md` loads. Could replace some session-preflight detection (e.g. "is SweetClaude active for this project?" — can be answered by parsing the loaded CLAUDE.md once instead of from `session-preflight.sh`).
- **`SubagentStart` / `SubagentStop`** — could enforce TDD subagent contracts at the harness level. E.g., on `SubagentStart` for `implementer`, snapshot the test files; on `SubagentStop`, diff. If the implementer touched tests, log violation.
- **`TaskCreated` / `TaskCompleted`** — integrate Claude Code's TaskCreate tool with SweetClaude's work tracking. Currently SweetClaude has `active_work_item`; Claude Code has a separate task list. Bridge them.

### R14 — Trigger-phrase optimization pass on top 20 skills

**What:** The Medium article showed 50%→100% trigger accuracy gains by enriching descriptions with synonyms, file types, and trigger phrasing. SweetClaude's descriptions are functional but don't have this density.

**Process per top-20 skill:**

1. Brainstorm 6–10 ways a user would phrase a request that should hit this skill.
2. Test against the current description by quickly classifying which skill the description "owns" each phrasing for.
3. Enrich `description` and `when_to_use` to cover all the phrasings.
4. Re-test.

**Why:** Skill triggering is the single highest-leverage UX moment. If a user types "I need to ship a hotfix" and `something-broke` doesn't fire, the entire framework is invisible.

**Scope:** Top 20 = the most-invoked user-facing skills. Status, go, find-skill, code-feature, code-issue, code-review, design-architecture, product-brief, etc.

### R15 — A `sweetclaude:skill-doctor` skill (replaces some Skill Creator concept)

**What:** A skill that audits the SweetClaude skill set against the modern contract:

- Reports per-skill: missing fields, trigger gaps, description length, listing budget contribution
- Flags conflicts (two skills with overlapping triggers)
- Suggests improvements (trigger phrases to add, fields to populate)

**Why:** This is the maintainable replacement for "Skill Creator" from the Medium article. Anthropic doesn't ship one. SweetClaude can ship a useful one because it has authoritative knowledge of what a SweetClaude skill should look like.

---

## 6. Migration plan

I'd sequence the work in three waves. Each wave is independently shippable.

### Wave 1 — Plugin re-rooting (R1, R7, R12, R13 partial)

Foundation work. After this wave, SweetClaude is a real plugin.

- Move all hooks to `${CLAUDE_PLUGIN_ROOT}/hooks/...`
- Update `hooks-manifest.json` and registration logic
- Fix `marketplace.json` version sync
- Add `dependencies` for Superpowers (optional; depends on availability in the user's marketplace)
- Migrate `install.sh` to a thin marketplace-install wrapper with a fallback
- Document the marketplace flow in `docs/user-guide/install.md`
- Test on a clean machine — install via marketplace, verify all hooks fire, verify update works

**Exit criteria:** A user can `claude plugin install sweetclaude@<marketplace>` and have a working plugin with all hooks firing, no `install.sh` invocation needed.

### Wave 2 — Skill modernization (R2, R3, R4, R6)

Mass frontmatter modernization. This is mechanical and tedious. Probably scripted.

- Generate a frontmatter-fixer script that adds `name`, `when_to_use`, `argument-hint`, `arguments`, `allowed-tools`, `effort`, `paths` fields to all skills based on a manifest you write
- Audit each skill's `disable-model-invocation` vs `user-invocable` choice
- Add `context: fork` + `agent` to ~10 heavy skills
- Wire 8 agents into corresponding skills via `agent` field
- Trim description length / move triggers to `when_to_use`
- Re-run with `claude --debug` to confirm the listing fits the budget

**Exit criteria:** Listing budget under 6KB. Trigger accuracy on top 20 skills tested at >90%.

### Wave 3 — Self-improvement infrastructure (R5, R10, R11, R14, R15)

Higher-leverage but lower-priority. Builds the moat.

- Structured eval harness on top of behavioral-regression
- Auto-test-runner converted to monitor (or coexists with hook fallback)
- `bin/` directory populated with utilities
- Trigger-phrase optimization pass
- `skill-doctor` skill

**Exit criteria:** Eval harness runs in CI on each Anthropic model release. `skill-doctor` reports a clean audit.

### Things to do *during* the migration

- Keep `install.sh` working as a fallback throughout — don't break existing users mid-migration
- Bump major version (`2.0.0`) once Wave 1 ships, so the plugin marketplace knows it's a different generation
- Keep a `MIGRATION.md` for users on `1.x` so they know how to move
- Ship a `sweetclaude:doctor` skill (different from `skill-doctor` — this one fixes user-side migration issues) before Wave 1 lands

---

## 7. Risks

**R1's blast radius is large.** Re-rooting hooks affects every install. If a user has the old layout and you push the new, hooks will fail silently until the user re-installs. Mitigations: detect old layout in `session-preflight.sh` and prompt to migrate; ship a `sweetclaude:doctor` skill that fixes the layout.

**`context: fork` semantics are subtle.** Forked skills don't see the main conversation. If you fork a skill that needed conversational state, behavior changes. The migration to fork must be per-skill with testing — no batch flip.

**Listing-budget changes can hurt discoverability.** Aggressively pulling skills out of the listing (via `disable-model-invocation`) means Claude won't auto-invoke them. If you over-trim, useful skills become invisible. Test trigger coverage *after* the listing changes.

**Plugin cache + writable state.** Currently `version-bump.sh` writes to `package.json` in the source repo. Under the cached install model, that file is read-only. Either move the version bump out of runtime, or write to `${CLAUDE_PLUGIN_DATA}` and read from there. Don't ignore — it'll break on the first marketplace install.

**The Medium article's "self-improving" framing is partly aspirational.** If you sell SweetClaude as "self-improving" based on that article, expectations will outrun the platform. The real story — structured evals + drift detection + trigger optimization passes — is more honest and still differentiated.

**89 skills is a lot.** Even with all R6 fixes, the listing is dense. Claude's auto-trigger accuracy in a 89-skill set is fundamentally harder than a 20-skill set. Consider whether some skills should be merged or moved to a separate sub-plugin (e.g., a `sweetclaude-strategy` plugin and a `sweetclaude-code` plugin, sharing a core).

**Anthropic ships changes.** The frontmatter contract has expanded twice in the last year. R2 will not be the last frontmatter migration. Plan for this — keep the skill audit script around so the next migration is mechanical.

---

## 8. Things I deliberately don't recommend

**Don't build a "SweetClaude Skill Creator."** The Medium article makes it sound essential. It isn't. The right tool is `skill-doctor` (R15) — audit existing skills, suggest fixes — not a wizard that generates new ones. SweetClaude already has 89 skills. Generating more is a problem, not a solution.

**Don't add A/B testing infrastructure.** Lower priority than the eval harness. A/B testing only helps if you have two viable variants and a metric. SweetClaude's metrics are mostly subjective ("did the user feel like the framework helped?"). Skip until the eval harness is mature and reveals actual variants worth testing.

**Don't aggressively use `model:` overrides.** Pinning specific models per skill is brittle. Anthropic deprecates models. Pin only where reasoning depth genuinely demands it — `code-feature`, `design-architecture`, behavioral-regression — and use `effort:` instead where possible.

**Don't add LSP servers.** SweetClaude is language-agnostic. LSPs are language-specific. Wrong layer.

**Don't add themes or output styles unless there's user demand.** The maintenance cost is real, the value is small.

**Don't merge the user-guide and the README.** The README sells; the user guide explains. Two audiences, two docs. Keep separate.

**Don't preserve `install.sh` indefinitely.** Maintain it through the 2.x line, then deprecate. Two install paths is two failure surfaces.

**Don't try to make `paths`-gated activation a substitute for `find-skill`.** They solve different problems. `paths` activates a skill when relevant files are open. `find-skill` classifies a user's plain-English request. Both have value; they aren't substitutes.

---

## 9. Closing read

SweetClaude has the right opinions and the right shape. The phase model, the TDD enforcement, the persistent state, the deference levels — these are durable design choices that align with where Anthropic's tooling is heading (their docs explicitly discuss progressive disclosure, isolation contracts, and hook-enforced determinism). The work above is mostly about *expressing* those opinions in the modern plugin contract instead of the legacy `~/.claude/`-copy contract.

The single biggest bet I'd make: prioritize R1, R2, R5, R6 hard. Those four together turn SweetClaude from "well-engineered but dated plugin" into "modern plugin with a defensible eval harness." Everything else is incremental polish.

If you want a starting point, I'd open three issues — Wave 1, Wave 2, Wave 3 — and treat them as net-new feature work items in SweetClaude's own pipeline. Eat the dogfood. Discover what breaks.

---

## 10. Source links

- Medium article: https://medium.com/@reliabledataengineering/claude-skills-2-0-the-self-improving-ai-capabilities-that-actually-work-dc3525eb391b
- Anthropic plugins reference: https://code.claude.com/docs/en/plugins-reference
- Anthropic skills documentation: https://code.claude.com/docs/en/skills
- Project root (audited): `/Users/carsonsweet/dev/sweetclaude/`
- Plugin manifest: `/Users/carsonsweet/dev/sweetclaude/.claude-plugin/plugin.json`
- Skills directory: `/Users/carsonsweet/dev/sweetclaude/skills/` (89 skills)
- Hooks directory: `/Users/carsonsweet/dev/sweetclaude/hooks/` (19 scripts)
- Agents directory: `/Users/carsonsweet/dev/sweetclaude/agents/` (8 agents)
