---
description: Set up and manage local semantic search for any project using mcp-local-rag. Trigger on "set up RAG", "index this project", "enable semantic search", "update the index", "reindex", "refresh RAG", or any request to search documents by meaning. Runs a reconciliation gate first so raw scratch, abandoned pivots, and versioned duplicates do not pollute the index. Handles initial setup (install, .mcp.json, full index) and incremental updates (new/modified files only).
---

# RAG Index Skill

Set up and manage local semantic search for any project directory using `mcp-local-rag`.

## What This Does

- Runs a reconciliation gate before indexing anything, so raw scratch and abandoned pivots do not pollute the index
- Ensures `mcp-local-rag` is installed globally (installs via npm if needed)
- Creates a per-project `.mcp.json` pointing BASE_DIR at the project root, storing the index in `.rag-index/`
- Discovers all indexable files (PDF, DOCX, TXT, MD) in the project
- Ingests them into the local vector database via the `ingest_file` MCP tool
- On subsequent runs, detects new or modified files and ingests only those
- Adds `.rag-index/` to `.gitignore` if not already present

## Workflow

### Step 0: Reconciliation Gate

**Run this on the first indexing of a project, and any time new noise has appeared since the last run. Never skip it on a first run.**

Indexing raw project contents mixes authoritative documents with scratch notes, abandoned pivots, versioned duplicates, and attached assets. RAG cannot tell them apart. Queries return blended results from incompatible sources. SweetClaude's `corpus-triage → corpus-reconcile → corpus-promote → corpus-reindex` pipeline exists to prevent exactly this failure.

**Step 0a: Scan for noise indicators.**

```bash
noise_dirs=$(find . -maxdepth 4 -type d \( \
  -name "scratch" -o -name "attached_assets" -o -name "archive" \
  -o -name "drafts" -o -name "_old" -o -name "old" -o -name "backup" \
  -o -path "*/corpus/raw/inbox" \
  \) ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/.rag-index/*" 2>/dev/null | sort)

versioned_files=$(find . -type f \( -iname "*-v[0-9]*.*" -o -iname "*_v[0-9]*.*" \) \
  ! -path "./.rag-index/*" ! -path "./.git/*" ! -path "*/node_modules/*" 2>/dev/null | sort)

versioned_count=$(echo -n "$versioned_files" | grep -c . 2>/dev/null || echo 0)
```

**Step 0b: If both `noise_dirs` and `versioned_files` are empty, skip the gate.** Proceed to Step 1 with default excludes. (Also clear any stale `noise_scan` from the manifest if present, since the noise is gone.)

**Step 0c: If noise was found, check whether it has changed since the last run.**

Read `.rag-index/.index-manifest.json` if it exists and look for a `noise_scan` field:

```json
{
  "indexed_at": "...",
  "files": { ... },
  "noise_scan": {
    "last_scan": "2026-04-15T10:30:00Z",
    "choice": "C",
    "noise_dirs": ["./scratch", "./docs/archive"],
    "versioned_count": 3
  }
}
```

Decision rules:

- **No manifest, or no `noise_scan` field:** First-run scenario. Present the gate (Step 0d).
- **Manifest has `noise_scan` and `choice == "B"`:** Re-apply CANONICAL-ONLY for this run. Skip the prompt. Proceed to Step 1 with `CANONICAL_ONLY=true`. Brief one-liner to user: "Re-using prior CANONICAL-ONLY choice. Run with `--reset-gate` to re-prompt."
- **Manifest has `noise_scan` and `choice == "C"`:** Compare current scan to recorded one:
  - **Same `noise_dirs` set AND `versioned_count` did not grow:** No new noise. Silently re-apply prior PROCEED choice with default excludes. Brief one-liner: "Re-using prior PROCEED-ANYWAY choice (no new noise since last run)."
  - **New noise dirs appeared OR `versioned_count` grew:** Re-present the gate (Step 0d) with a prefix: "⚠  Noise has grown since your last choice. New since [last_scan]: [diff list]. Re-confirm or change your decision."

**Step 0d: Present the gate.** Show the user:

```
⚠  Unreconciled content detected

Found:
- Directories: [list from noise_dirs]
- Versioned files: [first 10 from versioned_files]

If indexed raw, RAG will treat all of these as equally authoritative.
A query for "the current design" will blend an abandoned pivot, an
outdated draft, and the current spec with no distinction. This is the
failure mode reconciliation exists to prevent.

Three options:
  (A) RECONCILE FIRST — run /sweetclaude:corpus-triage to classify
      files, then /sweetclaude:corpus-reconcile, then re-run this
      skill. This is the right answer unless you have a reason not to.

  (B) CANONICAL-ONLY — index only docs/, strategy/, and
      corpus/canonical/. Skip everything else. Safe default if those
      dirs are already clean.

  (C) PROCEED ANYWAY — index raw contents with default excludes.
      Logged as a decision. Only use if you explicitly want raw
      search across all drafts.
```

Use `AskUserQuestion` to get the choice. Do not pick a default. The user must choose.

- **(A) RECONCILE FIRST:** Stop the skill. Tell the user to run `/sweetclaude:corpus-triage` and invoke this skill again when reconciliation is complete. Do not write `noise_scan` to the manifest — there is nothing to record yet.
- **(B) CANONICAL-ONLY:** Set `CANONICAL_ONLY=true` for this run. Step 5 will restrict file discovery to `docs/`, `strategy/`, and `corpus/canonical/`. Record the choice in the manifest's `noise_scan` field (Step 8). Proceed to Step 1.
- **(C) PROCEED ANYWAY:** If `.sweetclaude/state/decision-log.md` exists, append an entry with the date, the triggering directories/files, and the user's rationale (ask for one sentence). Record the choice in the manifest's `noise_scan` field (Step 8). Proceed to Step 1 with default excludes still applied.

### Step 1: Check if mcp-local-rag is installed globally

Run:
```bash
npm list -g mcp-local-rag 2>/dev/null || echo "NOT_INSTALLED"
```

If not installed:
```bash
npm install -g mcp-local-rag
```

If npm global install fails, skip it. `npx -y mcp-local-rag` works without a global install. The `.mcp.json` uses `npx`, so global install is a convenience, not a requirement.

### Step 2: Determine the project root

Use the current working directory as the project root. Confirm with the user if ambiguous.

### Step 3: Create or verify `.mcp.json`

Check if `<project_root>/.mcp.json` exists. If not, create it with:

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

If `.mcp.json` already exists, check for a `local-rag` entry. If present, leave it alone. If other MCP servers exist but not `local-rag`, merge the `local-rag` entry without disturbing other servers.

### Step 4: Update `.gitignore`

Check if `.gitignore` exists and whether it contains `.rag-index/`. If not, append:

```
# Local RAG index (mcp-local-rag)
.rag-index/
```

### Step 5: Discover indexable files

**If Step 0 set `CANONICAL_ONLY=true`:** Restrict discovery to `docs/`, `strategy/`, and `corpus/canonical/` only. Skip directories that do not exist:

```bash
search_roots=""
for d in docs strategy corpus/canonical; do
  [ -d "$d" ] && search_roots="$search_roots $d"
done

find $search_roots -type f \( -iname "*.pdf" -o -iname "*.docx" -o -iname "*.txt" -o -iname "*.md" \) \
  ! -path "*/.rag-index/*" \
  | sort
```

**Otherwise (default mode):** Find all indexable files. Exclude build artifacts, VCS, and — critically — the noise directories scanned in Step 0. These are excluded by default even on "proceed anyway." The user must explicitly override by passing `--include-scratch` or similar to re-enable them.

```bash
find . -type f \( -iname "*.pdf" -o -iname "*.docx" -o -iname "*.txt" -o -iname "*.md" \) \
  ! -path "./.rag-index/*" \
  ! -path "./.git/*" \
  ! -path "*/node_modules/*" \
  ! -path "*/.venv/*" \
  ! -path "*/venv/*" \
  ! -path "*/__pycache__/*" \
  ! -path "*/dist/*" \
  ! -path "*/build/*" \
  ! -path "*/scratch/*" \
  ! -path "*/attached_assets/*" \
  ! -path "*/archive/*" \
  ! -path "*/drafts/*" \
  ! -path "*/_old/*" \
  ! -path "*/old/*" \
  ! -path "*/backup/*" \
  ! -path "*/corpus/raw/*" \
  | sort
```

Save the output as the file list to process. Report the count to the user before proceeding, and note which default excludes applied (so the user sees what was filtered out).

### Step 6: Check for existing index state

Look for `.rag-index/.index-manifest.json`. This file tracks what has been indexed:

```json
{
  "indexed_at": "2026-04-10T12:00:00Z",
  "files": {
    "contracts/vendor-agreement.docx": {
      "last_modified": "2026-04-09T08:30:00Z",
      "size": 45230
    },
    "notes/research.md": {
      "last_modified": "2026-04-08T14:15:00Z",
      "size": 12400
    }
  }
}
```

**No manifest (first run):** All discovered files need ingestion. Proceed to Step 7 with the full file list.

**Manifest exists (update run):** Compare each discovered file against the manifest:
- **New files**: on disk but not in manifest. Ingest.
- **Modified files**: in both, but mtime or size differs. Ingest (re-ingestion replaces old chunks).
- **Deleted files**: in manifest but not on disk. Use `delete_file` MCP tool to remove from index, then remove from manifest.
- **Unchanged files**: skip.

Report counts: "Found X new, Y modified, Z deleted. N unchanged."

If nothing changed, tell the user the index is up to date and stop.

### Step 7: Ingest files

For each file that needs ingestion, use the `ingest_file` MCP tool. Files must be specified with absolute paths.

Get the absolute path of the project root:
```bash
pwd
```

Then for each file, call:
```
ingest_file with filepath: <absolute_path_to_file>
```

**Notes:**
- Process files sequentially. mcp-local-rag handles one ingestion at a time.
- If a file fails to ingest (unsupported format, too large, corruption), log the error and continue.
- Report progress every 10 files, or every file if the total is small.
- Ingestion runs at roughly 5-10 seconds per MB. Warn the user if the corpus is large.

### Step 8: Write the manifest

After all ingestions complete, write (or update) `.rag-index/.index-manifest.json` with the current state of all indexed files, including their modification times and sizes.

```bash
# Get file stats for the manifest
for f in <list of successfully ingested files>; do
  stat -f '{"file":"%N","mtime":"%Sm","size":%z}' -t "%Y-%m-%dT%H:%M:%SZ" "$f"
done
```

Note: On Linux, the `stat` syntax differs:
```bash
stat --printf='{"file":"%n","mtime":"%y","size":%s}\n' "$f"
```

**Also write the `noise_scan` block** if Step 0 produced one (choices B or C only — choice A stops the skill before reaching here, and a clean Step 0b run should clear any stale `noise_scan`):

```json
{
  "indexed_at": "2026-04-19T12:00:00Z",
  "files": { ... },
  "noise_scan": {
    "last_scan": "2026-04-19T12:00:00Z",
    "choice": "C",
    "noise_dirs": ["./scratch", "./docs/archive"],
    "versioned_count": 3
  }
}
```

`noise_dirs` is the sorted output of the Step 0a directory scan. `versioned_count` is the count of versioned files found. These are what Step 0c compares against on the next run to decide whether to silently re-apply the prior choice or re-prompt.

Construct the manifest JSON and write it to `.rag-index/.index-manifest.json`.

### Step 9: Confirm completion

Tell the user:
- How many files were indexed
- Where the index is stored (`.rag-index/`)
- That they need to restart Claude Code for the MCP server to become active (first run only)
- That they can search their documents by asking questions naturally once the MCP server is connected
- That they can run this skill again to update the index when files change

## Notes

- **Supported formats**: PDF, DOCX, TXT, Markdown. Excel and PowerPoint are not supported.
- **First model download**: The embedding model (~90MB) downloads on first use. Requires internet once, then works offline.
- **Re-ingestion is safe**: Ingesting the same file again replaces old chunks. No duplicates.
- **MCP server starts per-session**: It launches when Claude Code starts in the project directory and reads `.mcp.json`. It does not run as a background daemon.
- **Search tuning**: The default hybrid search (semantic + keyword boost) works for most document types. Adjust `RAG_HYBRID_WEIGHT` in `.mcp.json` env if needed (0 = semantic only, 1 = maximum keyword boost, default 0.6).
