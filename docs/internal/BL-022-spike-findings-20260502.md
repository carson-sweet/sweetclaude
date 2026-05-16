# BL-022 Spike Findings: Corpus Directory Integrity Protection
Date: 2026-05-02
Status: COMPLETE — implementing Approach 4 now

## Is This a Real Problem?

**Yes, but bounded.** Corpus corruption from outside the corpus skillset happens when:
1. Claude modifies files in `corpus/canonical/` or `corpus/chunked/` during a general coding/document task without realizing it's in corpus/ territory
2. A user asks Claude to "clean up docs/" and Claude reaches into corpus/canonical/ treating it as documentation
3. A refactoring task moves or deletes files that include corpus chunks

It is not catastrophic (git tracks changes, the intake flow can re-run), but it silently invalidates the RAG index and causes stale/wrong search results downstream.

---

## Approach Assessment

### Approach 1: Monitor hook (PostToolUse)

**Fundamental problem:** Hooks see the tool call but not which skill triggered it. A `PostToolUse` hook on Write/Edit cannot distinguish "document-corpus moving a file" (legitimate) from "code-feature accidentally touching corpus/" (not legitimate). Any rule that fires on corpus/ path writes would block legitimate corpus skill operations.

Partial mitigation: emit a *warning* (not a block) when corpus/ is modified. This creates noise during legitimate corpus work. Better than nothing, but not clean.

**Verdict: Partial, noisy. Not the primary mechanism.**

### Approach 2: Snapshot + compare

Snapshot on corpus skill entry, compare on exit. Detects unintended changes during corpus skill execution but misses corruption from outside the corpus skillset entirely (the whole problem case).

**Verdict: Detects the wrong failure mode. Skip.**

### Approach 3: Git-based revert skill

Requires corpus content to be committed (not true if corpus is gitignored via artifact-privacy.yaml). Destructive. Reactive.

**Verdict: Too destructive, wrong precondition. Skip.**

### Approach 4: LLM_README / DO_NOT_EDIT file

Drop a `corpus/LLM_README.md` at the corpus root with strong instructions. Claude reads and respects file-level guidance consistently — the "I didn't notice I was in corpus/ territory" failure mode is the most common one, and a visible warning file fixes it.

**Why this works:** Corpus corruption almost always happens because Claude didn't notice it was operating in corpus/ territory. A strongly-worded, clearly-named file in the root of the directory surfaces this immediately.

**Verdict: Zero implementation cost, addresses the primary failure mode directly. IMPLEMENT.**

---

## Decision: Approach 4 + a light PostToolUse warning

**Minimum viable protection (implement now):**
- Write `corpus/LLM_README.md` in the project corpus root with a clear "DO NOT MODIFY DIRECTLY" instruction
- Update `sweetclaude:on` to auto-create this file when corpus is configured
- Update `sweetclaude:document-corpus` to check for the file and create it if missing

**Optional supplement (defer to MS-005):**
- Add a soft PostToolUse warning (not block) when Write/Edit/Bash touches `corpus/canonical/**` or `corpus/chunked/**` and the word "corpus" doesn't appear in the active skill context. Emits once per session: "Note: you're modifying files in corpus/. If this is unintentional, use /sweetclaude:document-corpus for corpus operations."

---

## LLM_README Content

```markdown
# corpus/ — DO NOT MODIFY DIRECTLY

This directory is managed by `sweetclaude:document-corpus`. Modifying files here 
directly corrupts the RAG index and causes stale search results downstream.

**To add documents:** Place them in `corpus/raw/inbox/` and run `/sweetclaude:document-corpus intake`

**To update canonical documents:** Run `/sweetclaude:document-corpus` and use the update flow

**To reindex after any manual change:** Run `/sweetclaude:document-corpus reindex`

If you are Claude and you are about to write to a file in this directory outside of 
a corpus skill context, STOP and surface this to the user instead.
```

---

## Opt-in vs. Always-present

Protection should be **opt-in, automatic on corpus configuration.** When `sweetclaude:on` detects the user wants corpus setup, or when `sweetclaude:document-corpus` initializes the pipeline, write the warning file. Don't write it to projects that have no corpus.
