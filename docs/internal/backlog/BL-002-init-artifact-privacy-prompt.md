# BL-002: `/sweetclaude:init` should ask about artifact privacy

**Priority:** P2
**Depends on:** none
**Created:** 2026-04-20

## Summary

When `/sweetclaude:init` runs on a git-tracked project, it currently leaves the user to figure out whether SweetClaude's generated artifacts (`.sweetclaude/`, `strategy/`, `corpus/`, `docs/backlog/`) should be committed or gitignored. For public repos — especially this one (SweetClaude dogfooding on itself) — committing those directories leaks internal planning, draft strategy, raw inbox files, and personal decision logs into a distribution that users install from. Init should ask the question up front and wire `.gitignore` accordingly, matching the user's intent rather than silently defaulting either way.

## Initial Thinking

**What the prompt should ask:**
A single question early in init, after the safety-snapshot step and before creating `.sweetclaude/`:

> Should SweetClaude artifacts (`.sweetclaude/`, `strategy/`, `corpus/`) be committed to this repo, or kept private via `.gitignore`?
> - **Committed** — strategy and state are part of the project history. Good for private repos or solo work.
> - **Gitignored (recommended for public repos)** — artifacts stay local. `.gitignore` is updated to exclude them.
> - **Ask me per directory** — choose for each of `.sweetclaude/`, `strategy/`, `corpus/`, `docs/backlog/` separately.

**Detection heuristic for the recommendation:**
- Check `git remote -v` — if a remote exists and the URL points to a known public host (github.com/public, gitlab.com/public), recommend Gitignored.
- Fallback: if no remote, recommend Committed (likely local/solo).
- User can always override.

**What init should do with the answer:**
- If Gitignored, append to `.gitignore`:
  ```
  # SweetClaude artifacts (private)
  .sweetclaude/
  /strategy/
  /corpus/
  /docs/backlog/
  ```
- If Committed, skip the .gitignore step. Artifacts are tracked as normal.
- If Ask-per-directory, iterate and build the gitignore block from selections.

**Key technical decisions:**
1. Where in the init flow does this question go? After Step 1 (safety snapshot) but before Step 2 (state dir creation) seems right — it affects where things land.
2. Does the distribution warning in generated CLAUDE.md get adjusted based on this choice? If user committed, the warning "remove before pushing" is wrong.
3. What if the user changes their mind later? A `/sweetclaude:fix-config` branch already exists — this should be handled there.

**Risks and open questions:**
- Risk: adding another question to init increases friction. Mitigate by making it single-question, with a defaulted recommendation the user can accept by pressing Enter.
- Open: should `docs/backlog/` be its own bucket or bundled with `.sweetclaude/`? It is currently under `docs/` which is typically committed.

**Architecture implications:**
- No changes to state model. Just init flow + .gitignore manipulation.
- Distribution warning in CLAUDE.md generation should branch on the answer.

**Connection to other backlog items:**
- Tangentially related to BL-001 (if agentic skills change init mechanics, worth revisiting simultaneously).

## Origin

Surfaced during first-time dogfooding of SweetClaude on the SweetClaude repo itself on 2026-04-20. The user explicitly requested: "we should ask the user on setup if they want to include SweetClaude artifacts in their codebase, or add them to gitignore." Without the prompt, the user had to manually reason through what should be gitignored before init could proceed safely.

## Open Questions

- Should `docs/backlog/` be privacy-aware by default, or always committed as public roadmap? (This dogfood session treated it as private; the general default is less clear.)
- Should `strategy/` privacy be separate from `.sweetclaude/` privacy, given some projects may want to publish strategy (e.g., open-source products with public roadmaps) while keeping state private?
