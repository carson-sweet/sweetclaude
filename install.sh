#!/bin/bash
# SweetClaude Installer
# Copies framework files to ~/.claude/ for Claude Code to load.
# Backs up existing config, scans for conflicts, and offers restore via uninstall.sh.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRAMEWORK_DIR="$SCRIPT_DIR/framework"
CLAUDE_DIR="$HOME/.claude"
BACKUP_DIR="$CLAUDE_DIR/backup-pre-sweetclaude-$(date +%Y%m%d-%H%M%S)"

echo "SweetClaude Installer"
echo "====================="
echo ""

# --- Prerequisites ---

echo "Checking prerequisites..."

PREREQ_OK=true

if ! command -v claude &> /dev/null; then
  echo "  ERROR: Claude Code CLI not found."
  echo "         Install: https://claude.ai/code"
  PREREQ_OK=false
fi

if ! command -v git &> /dev/null; then
  echo "  ERROR: git not found."
  PREREQ_OK=false
fi

if ! command -v gh &> /dev/null; then
  echo "  WARNING: GitHub CLI (gh) not found. sweetclaude init requires it."
  echo "           Install: https://cli.github.com/"
fi

if [ "$PREREQ_OK" = false ]; then
  echo ""
  echo "Fix the errors above and re-run."
  exit 1
fi

echo "  Prerequisites OK."
echo ""

# --- Conflict Scan ---

echo "Scanning for potential conflicts..."
CONFLICTS=()

# Skills that SweetClaude supersedes
CONFLICT_SKILLS=("real-tdd" "fix-issue" "pr-ready")
for skill in "${CONFLICT_SKILLS[@]}"; do
  SKILL_PATH="$CLAUDE_DIR/skills/$skill"
  if [ -d "$SKILL_PATH" ]; then
    CONFLICTS+=("Skill: $skill → $SKILL_PATH (SweetClaude includes sweetclaude:$skill)")
  fi
done

# Don Cheli (should be removed but check)
if [ -d "$CLAUDE_DIR/don-cheli" ]; then
  CONFLICTS+=("Framework: Don Cheli SDD → $CLAUDE_DIR/don-cheli/ (redundant with SweetClaude)")
fi

# Check for existing hooks that might conflict
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  if grep -q "test-guardian\|auto-test-runner\|test.guard\|tdd.guard" "$CLAUDE_DIR/settings.json" 2>/dev/null; then
    CONFLICTS+=("Hooks: Existing TDD-related hooks in settings.json may conflict")
  fi
fi

if [ ${#CONFLICTS[@]} -gt 0 ]; then
  echo ""
  echo "  Found ${#CONFLICTS[@]} potential conflict(s):"
  for conflict in "${CONFLICTS[@]}"; do
    echo "    - $conflict"
  done
  echo ""
  echo "  These won't be removed automatically. SweetClaude will be installed"
  echo "  alongside them. You can clean them up after verifying SweetClaude works."
  echo ""
  read -p "  Continue? (y/n) " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
else
  echo "  No conflicts found."
fi
echo ""

# --- Backup ---

echo "Creating backup of current ~/.claude/ config..."
mkdir -p "$BACKUP_DIR"

# Backup existing SweetClaude files if upgrading
if [ -d "$CLAUDE_DIR/skills/sweetclaude" ]; then
  cp -r "$CLAUDE_DIR/skills/sweetclaude" "$BACKUP_DIR/skills-sweetclaude" 2>/dev/null || true
fi
if [ -d "$CLAUDE_DIR/hooks/sweetclaude" ]; then
  cp -r "$CLAUDE_DIR/hooks/sweetclaude" "$BACKUP_DIR/hooks-sweetclaude" 2>/dev/null || true
fi
if [ -d "$CLAUDE_DIR/agents/sweetclaude" ]; then
  cp -r "$CLAUDE_DIR/agents/sweetclaude" "$BACKUP_DIR/agents-sweetclaude" 2>/dev/null || true
fi
if [ -d "$CLAUDE_DIR/rules/sweetclaude" ]; then
  cp -r "$CLAUDE_DIR/rules/sweetclaude" "$BACKUP_DIR/rules-sweetclaude" 2>/dev/null || true
fi
if [ -d "$CLAUDE_DIR/config/sweetclaude" ]; then
  cp -r "$CLAUDE_DIR/config/sweetclaude" "$BACKUP_DIR/config-sweetclaude" 2>/dev/null || true
fi

# Always backup settings.json and CLAUDE.md
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  cp "$CLAUDE_DIR/settings.json" "$BACKUP_DIR/settings.json"
fi
if [ -f "$HOME/CLAUDE.md" ]; then
  cp "$HOME/CLAUDE.md" "$BACKUP_DIR/CLAUDE.md"
fi

echo "  Backup saved to: $BACKUP_DIR"
echo ""

# --- Install ---

echo "Installing SweetClaude..."

mkdir -p "$CLAUDE_DIR/skills/sweetclaude"
mkdir -p "$CLAUDE_DIR/hooks/sweetclaude"
mkdir -p "$CLAUDE_DIR/agents/sweetclaude"
mkdir -p "$CLAUDE_DIR/rules/sweetclaude"
mkdir -p "$CLAUDE_DIR/config/sweetclaude/templates"

cp -r "$FRAMEWORK_DIR/skills/"* "$CLAUDE_DIR/skills/sweetclaude/"
cp -r "$FRAMEWORK_DIR/hooks/"* "$CLAUDE_DIR/hooks/sweetclaude/"
cp -r "$FRAMEWORK_DIR/agents/"* "$CLAUDE_DIR/agents/sweetclaude/"
cp -r "$FRAMEWORK_DIR/rules/"* "$CLAUDE_DIR/rules/sweetclaude/"
cp -r "$FRAMEWORK_DIR/config/"* "$CLAUDE_DIR/config/sweetclaude/"

chmod +x "$CLAUDE_DIR/hooks/sweetclaude/"*.sh

echo "  Framework files installed."

# --- Hook Wiring ---

SETTINGS_FILE="$CLAUDE_DIR/settings.json"

if [ -f "$SETTINGS_FILE" ]; then
  if grep -q "sweetclaude/test-guardian" "$SETTINGS_FILE" 2>/dev/null; then
    echo "  Hooks already configured in settings.json."
  else
    echo ""
    echo "  NOTE: SweetClaude hooks need to be added to your settings.json."
    echo "  Add the following to your settings.json 'hooks' section:"
    echo ""
    cat << 'HOOKCONFIG'
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
HOOKCONFIG
    echo ""
    echo "  Automatic settings.json merging is not yet supported."
    echo "  Please add hooks manually to preserve your existing settings."
  fi
else
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
  echo "  Created settings.json with SweetClaude hooks."
fi

# --- CLAUDE.md ---

CLAUDE_MD="$HOME/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  if grep -q "SweetClaude" "$CLAUDE_MD" 2>/dev/null; then
    echo "  CLAUDE.md already has SweetClaude section."
  else
    echo "" >> "$CLAUDE_MD"
    cat >> "$CLAUDE_MD" << 'CLAUDEMD'

## SweetClaude

- If a SweetClaude working repo exists for the current project, read `state/phase.yaml` and `state/improvement-register.md` at session start.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
CLAUDEMD
    echo "  Added SweetClaude section to ~/CLAUDE.md."
  fi
else
  cp "$FRAMEWORK_DIR/CLAUDE.md.global" "$CLAUDE_MD"
  echo "  Created ~/CLAUDE.md from SweetClaude template."
fi

# --- Generate Uninstaller ---

cat > "$SCRIPT_DIR/uninstall.sh" << UNINSTALL
#!/bin/bash
# SweetClaude Uninstaller
# Removes SweetClaude and restores from backup.

set -e

CLAUDE_DIR="\$HOME/.claude"
BACKUP_DIR="$BACKUP_DIR"

echo "SweetClaude Uninstaller"
echo "======================="
echo ""

echo "Removing SweetClaude files..."
rm -rf "\$CLAUDE_DIR/skills/sweetclaude"
rm -rf "\$CLAUDE_DIR/hooks/sweetclaude"
rm -rf "\$CLAUDE_DIR/agents/sweetclaude"
rm -rf "\$CLAUDE_DIR/rules/sweetclaude"
rm -rf "\$CLAUDE_DIR/config/sweetclaude"
echo "  SweetClaude files removed."

if [ -d "\$BACKUP_DIR" ]; then
  echo ""
  read -p "Restore from backup at \$BACKUP_DIR? (y/n) " -n 1 -r
  echo ""
  if [[ \$REPLY =~ ^[Yy]\$ ]]; then
    if [ -f "\$BACKUP_DIR/settings.json" ]; then
      cp "\$BACKUP_DIR/settings.json" "\$CLAUDE_DIR/settings.json"
      echo "  Restored settings.json"
    fi
    if [ -f "\$BACKUP_DIR/CLAUDE.md" ]; then
      cp "\$BACKUP_DIR/CLAUDE.md" "\$HOME/CLAUDE.md"
      echo "  Restored CLAUDE.md"
    fi
    echo "  Backup restored."
  fi
else
  echo "  No backup found. Manual cleanup of settings.json and CLAUDE.md may be needed."
fi

echo ""
echo "SweetClaude uninstalled."
UNINSTALL

chmod +x "$SCRIPT_DIR/uninstall.sh"

# --- Summary ---

FILE_COUNT=$(find "$CLAUDE_DIR/skills/sweetclaude" "$CLAUDE_DIR/hooks/sweetclaude" "$CLAUDE_DIR/agents/sweetclaude" "$CLAUDE_DIR/rules/sweetclaude" "$CLAUDE_DIR/config/sweetclaude" -type f 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "================================================"
echo "SweetClaude installed successfully."
echo "================================================"
echo ""
echo "  Files installed: $FILE_COUNT"
echo "  Backup location: $BACKUP_DIR"
echo "  Uninstaller:     $SCRIPT_DIR/uninstall.sh"
echo ""
echo "  Skills:  $CLAUDE_DIR/skills/sweetclaude/"
echo "  Hooks:   $CLAUDE_DIR/hooks/sweetclaude/"
echo "  Agents:  $CLAUDE_DIR/agents/sweetclaude/"
echo "  Rules:   $CLAUDE_DIR/rules/sweetclaude/"
echo "  Config:  $CLAUDE_DIR/config/sweetclaude/"
echo ""
echo "Getting started:"
echo "  Open Claude Code and say: sweetclaude init my-project"
echo ""
if [ ${#CONFLICTS[@]} -gt 0 ]; then
  echo "Reminder: ${#CONFLICTS[@]} potential conflict(s) detected."
  echo "Review and clean up after verifying SweetClaude works."
  echo ""
fi
echo "To uninstall and restore your previous config:"
echo "  ./uninstall.sh"
