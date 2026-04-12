#!/bin/bash
# SweetClaude Installer
# Copies framework files to ~/.claude/ for Claude Code to load.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRAMEWORK_DIR="$SCRIPT_DIR/framework"
CLAUDE_DIR="$HOME/.claude"

echo "SweetClaude Installer"
echo "====================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v claude &> /dev/null; then
  echo "ERROR: Claude Code CLI not found. Install it first: https://claude.ai/code"
  exit 1
fi

if ! command -v gh &> /dev/null; then
  echo "WARNING: GitHub CLI (gh) not found. sweetclaude init will not work without it."
  echo "Install: https://cli.github.com/"
fi

if ! command -v git &> /dev/null; then
  echo "ERROR: git not found."
  exit 1
fi

echo "Prerequisites OK."
echo ""

# Check for existing SweetClaude installation
if [ -d "$CLAUDE_DIR/skills/sweetclaude" ]; then
  echo "Existing SweetClaude installation detected."
  read -p "Overwrite? (y/n) " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# Create directories
echo "Installing SweetClaude..."
mkdir -p "$CLAUDE_DIR/skills/sweetclaude"
mkdir -p "$CLAUDE_DIR/hooks/sweetclaude"
mkdir -p "$CLAUDE_DIR/agents/sweetclaude"
mkdir -p "$CLAUDE_DIR/rules/sweetclaude"
mkdir -p "$CLAUDE_DIR/config/sweetclaude/templates"

# Copy framework files
cp -r "$FRAMEWORK_DIR/skills/"* "$CLAUDE_DIR/skills/sweetclaude/"
cp -r "$FRAMEWORK_DIR/hooks/"* "$CLAUDE_DIR/hooks/sweetclaude/"
cp -r "$FRAMEWORK_DIR/agents/"* "$CLAUDE_DIR/agents/sweetclaude/"
cp -r "$FRAMEWORK_DIR/rules/"* "$CLAUDE_DIR/rules/sweetclaude/"
cp -r "$FRAMEWORK_DIR/config/"* "$CLAUDE_DIR/config/sweetclaude/"

# Make hooks executable
chmod +x "$CLAUDE_DIR/hooks/sweetclaude/"*.sh

# Wire hooks into settings.json
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

if [ -f "$SETTINGS_FILE" ]; then
  # Check if hooks are already configured
  if grep -q "sweetclaude/test-guardian" "$SETTINGS_FILE" 2>/dev/null; then
    echo "Hooks already configured in settings.json."
  else
    echo ""
    echo "NOTE: SweetClaude hooks need to be added to your settings.json."
    echo "Add the following to your settings.json 'hooks' section:"
    echo ""
    cat << 'HOOKCONFIG'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/sweetclaude/test-guardian.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/sweetclaude/auto-test-runner.sh"
          }
        ]
      }
    ]
  }
}
HOOKCONFIG
    echo ""
    echo "Automatic settings.json merging is not yet implemented."
    echo "Please add the hooks manually to preserve your existing settings."
  fi
else
  # Create fresh settings.json with hooks
  cat > "$SETTINGS_FILE" << 'SETTINGS'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/sweetclaude/test-guardian.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/sweetclaude/auto-test-runner.sh"
          }
        ]
      }
    ]
  }
}
SETTINGS
  echo "Created settings.json with SweetClaude hooks."
fi

# Update global CLAUDE.md
CLAUDE_MD="$HOME/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  if grep -q "SweetClaude" "$CLAUDE_MD" 2>/dev/null; then
    echo "CLAUDE.md already has SweetClaude section."
  else
    echo "" >> "$CLAUDE_MD"
    cat >> "$CLAUDE_MD" << 'CLAUDEMD'

## SweetClaude

- If a SweetClaude working repo exists for the current project, read `state/phase.yaml` and `state/improvement-register.md` at session start.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
CLAUDEMD
    echo "Added SweetClaude section to ~/CLAUDE.md."
  fi
else
  cp "$FRAMEWORK_DIR/CLAUDE.md.global" "$CLAUDE_MD"
  echo "Created ~/CLAUDE.md from SweetClaude template."
fi

echo ""
echo "SweetClaude installed successfully."
echo ""
echo "Files installed to:"
echo "  Skills:  $CLAUDE_DIR/skills/sweetclaude/"
echo "  Hooks:   $CLAUDE_DIR/hooks/sweetclaude/"
echo "  Agents:  $CLAUDE_DIR/agents/sweetclaude/"
echo "  Rules:   $CLAUDE_DIR/rules/sweetclaude/"
echo "  Config:  $CLAUDE_DIR/config/sweetclaude/"
echo ""
echo "To start a new project:"
echo "  Open Claude Code and say: sweetclaude init my-project"
echo ""
echo "To use on an existing project:"
echo "  cd into your project and open Claude Code"
echo "  SweetClaude will detect the project and ask how to proceed"
