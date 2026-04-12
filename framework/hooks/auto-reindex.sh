#!/bin/bash
# SweetClaude Auto-Reindex Hook
# PostToolUse hook — triggers incremental RAG reindex when indexed files change.
#
# This hook fires after Write/Edit operations and checks if the modified file
# is in a directory that's part of the RAG index. If so, it triggers an
# incremental reindex of that file only.
#
# Requires: mcp-local-rag installed and configured for the project.

FILE="$CLAUDE_FILE_PATH"

# Check if file is in an indexed directory
# Read indexed directories from project config
CONFIG_FILE="${SWEETCLAUDE_WORKING_REPO}/state/rag-config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
  # No RAG config — skip silently
  exit 0
fi

# Check file extension — only reindex supported types
EXT="${FILE##*.}"
case "$EXT" in
  md|txt|pdf|docx|rst|yaml|yml|json)
    # Supported — continue
    ;;
  *)
    # Not an indexable file type — skip
    exit 0
    ;;
esac

# Check if file is in an indexed directory
INDEXED=false
while IFS= read -r dir; do
  if [[ "$FILE" == "$dir"* ]]; then
    INDEXED=true
    break
  fi
done < <(grep "^  - " "$CONFIG_FILE" | sed 's/^  - //')

if [ "$INDEXED" = true ]; then
  # Trigger incremental reindex in background (don't block the edit)
  echo "RAG: Reindexing $FILE" >&2
  # The actual reindex command depends on mcp-local-rag's CLI
  # This is a placeholder — actual implementation depends on mcp-local-rag API
  nohup mcp-local-rag ingest "$FILE" > /dev/null 2>&1 &
fi

exit 0
