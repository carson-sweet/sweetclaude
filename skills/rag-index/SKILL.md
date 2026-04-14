---
description: Set up and manage local RAG (semantic search) for any project using mcp-local-rag. Use this skill whenever the user says things like "set up RAG", "index this project", "enable semantic search", "update the index", "reindex", "add to RAG", "refresh RAG", or asks Claude to search project documents semantically. Also trigger when the user references wanting to search across documents by meaning rather than keyword, or mentions mcp-local-rag. This skill handles both initial setup (installing mcp-local-rag globally, creating per-project .mcp.json, and doing a full initial index) AND incremental updates (detecting new or modified files and ingesting only those). Use it even if the user just says "index everything" or "update the index" without explicitly mentioning RAG.
---

# RAG Index Skill

Set up and manage local semantic search (RAG) for any project directory using `mcp-local-rag`.

## What This Does

- Ensures `mcp-local-rag` is available globally (installs via npm if needed)
- Creates a per-project `.mcp.json` that points BASE_DIR at the project root and stores the index in `.rag-index/` inside the project
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

If npm global install is problematic on the user's system, note that `npx -y mcp-local-rag` works without global install — the `.mcp.json` uses `npx` so global install is a convenience, not a requirement. Skip global install failures gracefully.

### Step 2: Determine the project root

Use the current working directory as the project root. Confirm with the user if ambiguous.

### Step 3: Create or verify `.mcp.json`

Check if `<project_root>/.mcp.json` exists. If not, create it:

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

If `.mcp.json` already exists, check whether it already has a `local-rag` entry. If so, leave it alone. If it has other MCP servers but not `local-rag`, merge the `local-rag` entry into the existing file without disturbing other servers.

### Step 4: Update `.gitignore`

Check if `.gitignore` exists and whether it contains `.rag-index/`. If not, append:

```
# Local RAG index (mcp-local-rag)
.rag-index/
```

### Step 5: Discover indexable files

Run a find command to locate all indexable files. Exclude the `.rag-index/` directory, `node_modules/`, `.git/`, and other common non-content directories:

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

**If no manifest exists (first run):** All discovered files need ingestion. Proceed to Step 7 with the full file list.

**If manifest exists (update run):** Compare each discovered file against the manifest:
- **New files**: Present in the file system but not in the manifest → ingest
- **Modified files**: Present in both, but file's mtime or size differs → ingest (re-ingestion replaces old chunks automatically)
- **Deleted files**: Present in manifest but not on disk → use `delete_file` MCP tool to remove from index, then remove from manifest
- **Unchanged files**: Skip

Report the counts to the user: "Found X new files, Y modified files, Z deleted files. N files unchanged."

If nothing has changed, tell the user the index is up to date and stop.

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

**Important notes:**
- Process files sequentially — mcp-local-rag handles one ingestion at a time
- If a file fails to ingest (unsupported format, too large, corruption), log the error and continue with remaining files
- Report progress to the user periodically (e.g., every 10 files or every file if the total is small)
- Ingestion speed is roughly 5-10 seconds per MB, so warn the user if the corpus is large

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

- **Supported formats**: PDF, DOCX, TXT, Markdown. Excel and PowerPoint are NOT supported by mcp-local-rag.
- **First model download**: The embedding model (~90MB) downloads on first use. Requires internet for that initial download, then works offline.
- **Re-ingestion is safe**: Ingesting the same file again replaces old chunks — no duplicates.
- **The MCP server starts per-session**: It launches when Claude Code starts in the project directory and reads the `.mcp.json`. It does NOT run as a background daemon.
- **Search tuning**: The default hybrid search (semantic + keyword boost) works well for most document types. Users can adjust `RAG_HYBRID_WEIGHT` in the `.mcp.json` env if needed (0 = semantic only, 1 = maximum keyword boost, default 0.6).
