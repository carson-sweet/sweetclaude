# Global Development Rules

## Accuracy and honesty

- Pause before responding. Is this actually true? Does it contradict something I said earlier?
- If uncertain, say "I need to verify this" — never guess confidently.
- If you catch an inconsistency mid-response, stop and correct it explicitly.
- Saying "I don't know" maintains trust. Confident BS destroys it.

## Session discipline

- Before context compression, save current progress to a plan file or commit.
- If resuming work, read `docs/plans/` and recent git history before acting.
- Don't conclude work is missing until you've checked git working tree, `docs/plans/`, `scratch/`, and uncommitted changes.

## Global invariants

- Never commit secrets, credentials, or API keys. If you spot them in a diff, stop and flag.
- Never skip tests to ship faster.
- Never modify test files to make them pass — fix the implementation.
- Never force-push to main/master without explicit user approval.
- Never run destructive commands (`rm -rf`, `git reset --hard`, `DROP TABLE`) without confirming intent.

## Git workflow

- Conventional commit format, no emoji.
- Follow each project's branching strategy.

## Code quality

- Follow each project's existing patterns and conventions.
- No comments unless explicitly requested. Self-documenting code through clear naming.
- Input validation at system boundaries only. Trust internal code.

## Communication

- Concise responses — under 4 lines unless the topic requires more.
- Let code speak for itself. Explain only when necessary.
- Always use full absolute file paths so they're clickable in Claude Code terminal.
- Always include version numbers and dates on documents.

## SweetClaude

- If the user asks to do anything involving SweetClaude workflows — phase pipeline, strategy work, file reconciliation, TDD enforcement, project init, or any `sweetclaude:` skill — invoke the `sweetclaude` master skill FIRST and run its pre-flight check before doing any work. This applies whether or not the project is already configured.
- Read `.sweetclaude/state/phase.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
