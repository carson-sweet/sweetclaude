#!/bin/bash
# SweetClaude Session Pre-Flight
# SessionStart hook — checks if SweetClaude is configured for the current project.
# If not configured, writes a flag file that the PreToolUse preflight-guard reads.
# The guard blocks ALL tool calls until the project is configured or skipped.
# Per-project opt-out: create .sweetclaude-skip in the project root.

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

# No git repo — nothing to do
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

PROJECT_HASH=$(echo -n "$PROJECT_DIR" | md5 2>/dev/null || echo -n "$PROJECT_DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
FLAG="/tmp/.sweetclaude-needs-preflight-${PROJECT_HASH}"

# Project explicitly opts out
if [ -f "$PROJECT_DIR/.sweetclaude-skip" ]; then
  rm -f "$FLAG"
  exit 0
fi

# Check if configured — .sweetclaude/ inside project (current) or legacy -sweetclaude/ repo
if [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  rm -f "$FLAG"
  exit 0
fi

# Legacy fallback: separate working repo
LEGACY_REPO="${PROJECT_DIR}-sweetclaude"
if [ -f "$LEGACY_REPO/state/phase.yaml" ]; then
  rm -f "$FLAG"
  exit 0
fi

# Not configured — plant the flag and tell Claude
touch "$FLAG"
cat << 'EOF'
<sweetclaude-preflight>
STOP. SweetClaude is installed but this project is not configured. You MUST run the sweetclaude pre-flight check before doing any work. Invoke the sweetclaude skill now. Every tool call will be blocked until this is resolved.
</sweetclaude-preflight>
EOF
