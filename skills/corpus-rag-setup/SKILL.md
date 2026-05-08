---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:corpus-rag-setup
user-invocable: true
description: "Configure and run local semantic search on project documents using mcp-local-rag. Supports PDF, DOCX, TXT, Markdown. Default scope is canonical documents only — gates raw indexing with a noise check. Fully offline; no external services or API keys required."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Set Up RAG

Configure and run local semantic search on your project documents using `mcp-local-rag`.

## Step G0: Reconciliation gate

**Run on first indexing and any time new noise has appeared. Never skip on a first run.**

Indexing raw project contents blends authoritative documents with scratch notes, abandoned pivots, and versioned duplicates. RAG cannot distinguish them. The corpus pipeline exists to prevent this failure. This gate checks whether your content is clean enough to index usefully.

**G0a: Scan for noise indicators:**

```bash
noise_dirs=$(find . -maxdepth 4 -type d \( \
  -name "scratch" -o -name "attached_assets" -o -name "archive" \
  -o -name "drafts" -o -name "_old" -o -name "old" -o -name "backup" \
  -o -path "*/corpus/raw/inbox" \
  \) ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/.rag-index/*" 2>/dev/null | sort)

versioned_files=$(find . -type f \( -iname "*-v[0-9]*.*" -o -iname "*_v[0-9]*.*" \) \
  ! -path "./.rag-index/*" ! -path "./.git/*" ! -path "*/node_modules/*" 2>/dev/null | sort)
```

**G0b: If both are empty** — content is clean. Skip the gate. Proceed to G1 with default excludes.

**G0c: If noise was found**, check `.rag-index/.index-manifest.json` for a prior `noise_scan` decision:
- No manifest or no `noise_scan` → first-run, present the gate (G0d).
- Prior choice was **B (canonical-only)** → re-apply silently. Note to user.
- Prior choice was **C (proceed anyway)** → compare current scan to recorded one. If unchanged, re-apply silently. If new noise appeared, re-present the gate with a warning.

**G0d: Present the gate:**

```
⚠ Unreconciled content detected

Found:
- Directories: {list from noise_dirs}
- Versioned files: {first 10 from versioned_files}

If indexed raw, RAG treats all of these as equally authoritative.
A query for "the current design" blends an abandoned pivot, an
outdated draft, and the current spec with no distinction.

Three options:

  (A) RECONCILE FIRST — run the corpus pipeline (Consolidate →
      Triage → Reconcile → Promote), then return here. This is
      the right answer unless you have a specific reason not to.

  (B) CANONICAL-ONLY — index only docs/, strategy/, and
      corpus/canonical/. Skip everything else. Safe if those
      dirs are already clean.

  (C) PROCEED ANYWAY — index raw contents with default excludes.
      Logged as a decision. Only use if you explicitly want raw
      search across all drafts.
```

- **(A):** Stop. Tell the user to run `/sweetclaude:corpus-consolidate` to start the pipeline. Do not record `noise_scan`.
- **(B):** Set `CANONICAL_ONLY=true`. Record choice in manifest. Proceed to G1.
- **(C):** Ask for one-sentence rationale. Log in decision-log if it exists. Record choice in manifest. Proceed to G1 with default excludes.

## Step G1: Check mcp-local-rag installation

```bash
npm list -g mcp-local-rag 2>/dev/null || echo "NOT_INSTALLED"
```

If not installed: `npm install -g mcp-local-rag`. If global install fails, note that `npx -y mcp-local-rag` works without it — `.mcp.json` uses `npx`.

## Step G2: Determine project root

Use current working directory. Confirm if ambiguous.

## Step G3: Create or verify `.mcp.json`

If `.mcp.json` does not exist, create:
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

If `.mcp.json` exists: check for `local-rag` entry. If present, leave alone. If absent, merge the entry without disturbing other servers.

## Step G4: Update `.gitignore`

If `.gitignore` does not contain `.rag-index/`, append:
```
# Local RAG index (mcp-local-rag)
.rag-index/
```

## Step G5: Discover indexable files

If `CANONICAL_ONLY=true` (from Step G0): restrict to `docs/`, `strategy/`, `corpus/canonical/` only.

Otherwise (default):
```bash
find . -type f \( -iname "*.pdf" -o -iname "*.docx" -o -iname "*.txt" -o -iname "*.md" \) \
  ! -path "./.rag-index/*" ! -path "./.git/*" ! -path "*/node_modules/*" \
  ! -path "*/.venv/*" ! -path "*/venv/*" ! -path "*/__pycache__/*" \
  ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/scratch/*" \
  ! -path "*/attached_assets/*" ! -path "*/archive/*" ! -path "*/drafts/*" \
  ! -path "*/_old/*" ! -path "*/old/*" ! -path "*/backup/*" \
  ! -path "*/corpus/raw/*" | sort
```

Report file count and which default excludes applied before proceeding.

## Step G6: Check existing index state

Read `.rag-index/.index-manifest.json` if it exists.

- No manifest (first run): all discovered files need ingestion.
- Manifest exists (update run): compare — new files (ingest), modified files (re-ingest), deleted files (delete from index via `delete_file` MCP tool), unchanged files (skip). Report: "X new, Y modified, Z deleted, N unchanged."

If nothing changed: "Index is up to date." Stop.

## Step G7: Ingest files

For each file needing ingestion, call `ingest_file` MCP tool with absolute path. Process sequentially. Report progress every 10 files. If a file fails, log the error and continue.

The embedding model (~90MB) downloads on first use — warn the user.

## Step G8: Write manifest

Write `.rag-index/.index-manifest.json` with indexed files (paths, mtime, size) and `noise_scan` block if Step G0 produced one.

## Step G9: Confirm

Report:
- Files indexed
- Index location (`.rag-index/`)
- If first run: "Restart Claude Code for the MCP server to become active."
- How to search: "Ask questions naturally once the MCP server connects. The index supports semantic search — query by meaning, not just keywords."
- How to update: "Run `/sweetclaude:corpus-rag-setup` again to update the index when files change."

**Update project SOP:** After reporting, update `.sweetclaude/state/project-sop.md` — find the RAG Indexes table and update (or add) the row for this MCP with the scope used (canonical-only or full), today's date as Last Indexed, and a note if this was a canonical-only build. If `project-sop.md` does not exist, create it with just the RAG Indexes section populated — the MCP Tools and Corpus sections can be filled in by running `/sweetclaude:setup`.

**Supported formats:** PDF, DOCX, TXT, Markdown. Excel and PowerPoint are not supported.
