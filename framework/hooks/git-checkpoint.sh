#!/bin/bash
# SweetClaude Git Checkpoint
# Called by skills at phase transitions and TDD milestones.
# Usage: git-checkpoint.sh <message> [working-repo-path]

MESSAGE="$1"
WORKING_REPO="${2:-}"

if [ -z "$MESSAGE" ]; then
  echo "Usage: git-checkpoint.sh <message> [working-repo-path]" >&2
  exit 1
fi

# If working repo path provided, commit there
if [ -n "$WORKING_REPO" ] && [ -d "$WORKING_REPO" ]; then
  cd "$WORKING_REPO"
  git add -A
  git commit -m "$MESSAGE

Co-Authored-By: SweetClaude <noreply@sweetclaude.dev>" 2>/dev/null
  echo "Checkpoint committed to working repo: $MESSAGE" >&2
fi

# Also commit in the current project repo if there are staged changes
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -n "$PROJECT_DIR" ] && [ "$PROJECT_DIR" != "$WORKING_REPO" ]; then
  cd "$PROJECT_DIR"
  if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "$MESSAGE

Co-Authored-By: SweetClaude <noreply@sweetclaude.dev>" 2>/dev/null
    echo "Checkpoint committed to code repo: $MESSAGE" >&2
  fi
fi

exit 0
