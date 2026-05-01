# FAQ

**Version:** 1.0
**Date:** 2026-05-01

Honest answers. When SweetClaude is the right tool. When it is not. Common confusions cleared up.

---

## Is SweetClaude right for me?

**Yes if:**
- You are building software with Claude Code and want structured workflows for the parts before and after the code itself.
- You believe AI generates output faster than humans can verify, and you want guardrails that prevent the gap.
- You want strategic and product work (discovery, briefs, PRDs, competitive analysis) treated with as much discipline as the code.
- You are a solo developer or small team. SweetClaude was built for that shape.
- You want documentation, decisions, and assumptions to persist between sessions instead of being re-derived from scratch every time.

**Probably not if:**
- You want autocomplete-style assistance and nothing more. Cursor and similar IDE-integrated tools are a better fit.
- You are on a large team with a heavyweight existing process (Jira, sprint ceremonies, formal review boards). SweetClaude can coexist but it does not pretend to integrate with all of that.
- You hate opinionated frameworks. SweetClaude is opinionated. Phase gates exist. TDD enforcement is on by default. The framework will challenge your framing in early phases.
- You only write throwaway scripts. The setup overhead is not worth it for ten-line utilities.

---

## What is the difference between SweetClaude and Claude Code itself?

Claude Code is the runtime. SweetClaude is a plugin that runs inside Claude Code.

Claude Code gives you an AI that can read files, edit code, run commands, and navigate a codebase. SweetClaude adds:

- A 7-phase pipeline with explicit exit criteria
- Strategy and product workflows (discovery, briefs, PRDs, personas, competitive analysis, milestones)
- Design workflows (architecture, tech spec, data model, API design, decision logs)
- TDD enforcement via hooks (not advisory — actually blocking)
- Subagent isolation between test writers and implementers
- Document corpus pipeline with state-machine ordering
- Local semantic search (RAG)
- Persistent project state in `.sweetclaude/` that survives session crashes

If you want the underlying Claude Code experience, run Claude Code without SweetClaude. If you want the workflow discipline, install SweetClaude on top.

---

## What is the relationship between SweetClaude and Superpowers?

SweetClaude orchestrates Superpowers — it does not replace it. When you install SweetClaude, the recommended setup also installs Superpowers, and SweetClaude code skills (like `code-feature`) call into Superpowers skills (`writing-plans`, `executing-plans`, `using-git-worktrees`, `systematic-debugging`, `dispatching-parallel-agents`).

The split is:
- **Superpowers** provides the implementation primitives: plans, worktrees, parallel agent dispatch, debugging discipline.
- **SweetClaude** provides the surrounding workflow: phases, gates, strategy and product layers, TDD enforcement, state persistence.

You can use Superpowers without SweetClaude. You cannot use the full SweetClaude pipeline without Superpowers (the strategy-skills-only install does not require it).

---

## Do I have to use the whole pipeline?

No. The pipeline is a guide, not a cage.

You can:
- Skip directly to architecture if you already know what you are building.
- Use only the strategy skills (install with `--strategy-skills-only` for the lighter footprint).
- Use only the code skills if you do not want strategy and product workflows.
- Skip phases by saying "I've addressed this informally — proceed."
- Disable SweetClaude per project by touching `.sweetclaude/disabled`.

What you cannot do — physically cannot — is bypass hard gates. Hard gates apply to high-blast-radius work at GA+ stages: data migration integrity checks, security patch reviews, infrastructure change rollback plans. Hard gate overrides require explicit risk acceptance logged to the decision log.

---

## What about teams?

SweetClaude works for teams but was built solo-first. The state files in `.sweetclaude/` are committed to git, so they travel with the repo. Multiple team members on the same project see consistent state.

What it does not do:
- Real-time collaboration (multiple users editing state at once).
- Permissions or role-based access (everyone with repo access has equal SweetClaude access).
- Integration with team ceremonies (standups, retros, sprint planning rituals).

If your team uses SweetClaude, treat the state files as shared project context. Conflicts on `phase.yaml` get resolved like any merge conflict.

---

## Why won't SweetClaude give me time estimates?

Because AI-assisted solo development does not run on calendar time. Asking "how long will this take?" is the wrong question. The right question is "what needs to be done?" — and SweetClaude answers that.

If you ask anyway, SweetClaude says:

> I'm your implementation partner — I build with you at AI speed, not calendar speed. Traditional estimates don't apply here. Let's focus on what needs to be done and roll. We'll know how long it took when it's done.

This is a deliberate position, not a bug. Time estimates in AI-assisted development reinforce a paradigm that is broken. Phase gates measure progress in artifacts produced and quality criteria met. That is what matters.

If you have an external deadline, set a milestone (`/sweetclaude:product-milestones add`). Milestones have target dates without forcing the framework to pretend it knows how long things take.

---

## Can I disable parts I don't want?

Yes. The lever depends on what you want to disable.

| Want to disable | How |
|---|---|
| All of SweetClaude for one project | `touch .sweetclaude/disabled` |
| TDD hooks globally | Edit `~/.claude/settings.json`, remove the hook entries (the installer wires them in; you can wire them out) |
| Auto status at session start | Touch `.sweetclaude/disabled` then run `/sweetclaude:on` only when you want it |
| Specific skills | Skills are individual `.md` files in `~/.claude/skills/sweetclaude/`. Delete the directory of any skill you do not want. The framework continues working. |
| Protocol Guardian (when enabled) | `/sweetclaude:guardian-off` |

The framework is composed, not monolithic. You can dismantle it piece by piece without breaking what is left.

---

## Why is the test writer separate from the implementer at TDD Level 2-3?

Because information that flows backward from outcome to design corrupts the design. If the implementer can read the spec, it can rationalize a passing test by reasoning about what the spec "really meant" — and the test stops specifying behavior and starts describing implementation.

The principle is the same as double-blind clinical trials. Block the back-flow.

The cost is that occasionally a test cannot be made to pass without modification, and the implementer surfaces the conflict to you. That is good. It means the test was actually flawed, and you get to decide whether to fix the test or fix the implementation. The conflict is information.

---

## What if a phase gate blocks me and I genuinely think the criterion does not apply?

Override it. Soft gates accept "I've addressed this informally — proceed." That logs the override and continues. The override is in the decision log so you can revisit it later.

Hard gates (⚠️) require explicit risk acceptance with the override logged. The list of hard gates is short — about half a dozen — and they exist for situations where the blast radius justifies the friction. See [phases-and-workflows.md](phases-and-workflows.md) for the full list.

If you find yourself overriding the same gate repeatedly, that is a signal worth investigating. Either the gate is wrong for your context (file an issue) or your work is consistently skipping a step that matters.

---

## What survives a session crash?

Everything in `.sweetclaude/`. Specifically:

- `state/phase.yaml` — current phase, work item, deference level
- `state/project.yaml` — project metadata
- `state/decision-log.md` — every decision recorded
- `state/assumption-register.md` — assumptions worth checking
- `state/improvement-register.md` — feedback from past sessions
- `state/scope-changes.md` — scope additions and removals
- `traceability/` — story → requirement → test → code maps

Plus whatever skills wrote during the session — discovery output, persona files, briefs, PRDs, architecture docs, code commits.

What does not survive: in-flight conversation context. If you were in the middle of a discovery interview when the session died, you will need to resume it. SweetClaude does not silently lose work, but it cannot read your mind about what was about to be said. Run `/sweetclaude:go` to re-orient.

---

## How does SweetClaude work with Cursor / Aider / other AI coding tools?

It does not, directly. SweetClaude is a Claude Code plugin. It runs in Claude Code sessions. The state files in `.sweetclaude/` are plain markdown and YAML, so other tools can read them, but the workflow logic lives in Claude Code skills.

If you primarily use Cursor and want SweetClaude's structure, you would need a separate session in Claude Code for the SweetClaude work, then return to Cursor for the implementation. Some users do this. It is not seamless.

---

## Why are the docs opinionated about voice?

Because flat reference docs are how good frameworks get ignored. The README sells the idea; the docs make it usable. If the docs read like a dump of every option, users skim and miss the point.

You will see SweetClaude's docs take positions: phase dwelling matters, time estimates are broken, isolation between test writers and implementers prevents specific failure modes. These are arguments, not just facts. You are welcome to disagree — but you should not have to guess what the framework's position is.

---

## What if I find a bug or have a feature request?

[Open an issue on GitHub](https://github.com/carson-sweet/sweetclaude/issues). The maintainer is responsive. Pull requests welcome.

---

## What if I want to contribute?

Skills are markdown files. Read a few of the existing skill files in `~/.claude/skills/sweetclaude/` (after install) or in the cloned repo's `skills/` directory. The structure is consistent. New skills follow the same pattern: frontmatter with `name` and `description`, then a body that walks the user through the work.

If you want to propose a new work type or workflow shape, that is a config change in `config/workflow-templates.yaml` plus possibly new skills. Discuss in an issue first — these are coordinated changes.

---

## What's planned?

The `deploy/` bucket is the largest gap right now. There are also several Plan 2 and Plan 3 skills in flight (mockup pipeline, init/adopt as standalone skills, security planning, infrastructure change). See `docs/backlog/` in the repo for the live list of planned work.

---

## Where can I see SweetClaude in action?

The README has examples. The `/sweetclaude:help` command produces a live tour. The walkthroughs in this guide simulate end-to-end flows.

For a real demonstration, the SweetClaude repo itself dogfoods SweetClaude — `.sweetclaude/state/phase.yaml`, `decision-log.md`, and the rest are visible in the repo. You can see how the framework manages its own development.

---

## What to Read Next

- If you have not yet → [Getting Started](getting-started.md)
- The mental model → [How It Works](how-it-works.md)
- Concrete scenarios → [Walkthroughs](walkthroughs.md)
