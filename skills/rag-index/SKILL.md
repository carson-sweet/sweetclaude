---
description: Set up and manage local semantic search for any project using mcp-local-rag. Trigger on "set up RAG", "index this project", "enable semantic search", "update the index", "reindex", "refresh RAG", or any request to search documents by meaning. Handles initial setup (install, .mcp.json, full index) and incremental updates (new/modified files only).
---

# RAG Index Skill

Set up and manage local semantic search for any project directory using `mcp-local-rag`.

## What This Does

- Ensures `mcp-local-rag` is installed globally (installs via npm if needed)
- Creates a per-project `.mcp.json` pointing BASE_DIR at the project root, storing the index in `.rag-index/`
- Discovers all indexable files (PDF, DOCX, TXT, MD) in the project
- Ingests them into the local vector database via the `ingest_file` MCP tool
- On subsequent runs, detects new or modified files and ingests only those
- Adds `.rag-index/` to `.gitignore` if not already present

## Workflow

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

Find all indexable files. Exclude `.rag-index/`, `node_modules/`, `.git/`, and other non-content directories:

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
  | sort
```

Save the output as the file list to process. Report the count to the user before proceeding.

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
