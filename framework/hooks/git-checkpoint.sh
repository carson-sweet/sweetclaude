#!/bin/bash
# SweetClaude Git Checkpoint
# Called by skills at phase transitions and TDD milestones.
# Commits .sweetclaude/ state changes to the project repo.
# Usage: git-checkpoint.sh <message>

MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
  echo "Usage: git-checkpoint.sh <message>" >&2
  exit 1
fi

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

if [ -z "$PROJECT_DIR" ]; then
  echo "Not in a git repo" >&2
  exit 1
fi

cd "$PROJECT_DIR"

# Stage .sweetclaude/ state changes specifically (not all project changes)
if [ -d ".sweetclaude" ]; then
  git add .sweetclaude/
fi

# Also stage strategy/ if it has changes (strategy artifacts are project-level)
if [ -d "strategy" ]; then
  git add strategy/
fi

# Commit if there are staged changes
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "$MESSAGE

Co-Authored-By: SweetClaude <noreply@sweetclaude.dev>" 2>/dev/null
  echo "Checkpoint committed: $MESSAGE" >&2
fi

exit 0
