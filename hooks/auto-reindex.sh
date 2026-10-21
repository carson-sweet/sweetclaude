#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Auto-Reindex Hook
# PostToolUse hook — triggers incremental RAG reindex when indexed files change.
# Requires: mcp-local-rag installed and configured for the project.

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

FILE=$(hook_field tool_input.file_path)

if [ -z "$FILE" ]; then
  exit 0
fi

# Find project root and config
PROJECT_DIR=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" project-dir)

CONFIG_FILE="${PROJECT_DIR}/.sweetclaude/state/rag-config.yaml"

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
  nohup mcp-local-rag ingest "$FILE" > /dev/null 2>&1 &
fi

exit 0
