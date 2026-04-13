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
PREREQ_WARN=false

# --- Helper: compare semver (returns 0 if $1 >= $2) ---
version_gte() {
  [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# Core tools
if ! command -v claude &> /dev/null; then
  echo "  ERROR: Claude Code CLI not found."
  echo "         Install: https://docs.anthropic.com/en/docs/claude-code/getting-started"
  PREREQ_OK=false
else
  CLAUDE_VER=$(claude --version 2>/dev/null | head -1)
  echo "  Claude Code CLI: $CLAUDE_VER"
fi

if ! command -v git &> /dev/null; then
  echo "  ERROR: git not found."
  echo "         Install: https://git-scm.com/downloads"
  PREREQ_OK=false
else
  GIT_VER=$(git --version 2>/dev/null)
  echo "  $GIT_VER"
fi

if ! command -v gh &> /dev/null; then
  echo "  WARNING: GitHub CLI (gh) not found. sweetclaude init requires it."
  echo "           Install: https://cli.github.com/"
  PREREQ_WARN=true
else
  GH_VER=$(gh --version 2>/dev/null | head -1)
  echo "  $GH_VER"
fi

# Superpowers plugin
SP_MIN="5.0.7"
PLUGINS_JSON="$CLAUDE_DIR/plugins/installed_plugins.json"
SP_VERSION=""

if [ -f "$PLUGINS_JSON" ]; then
  # Extract version from installed_plugins.json
  SP_VERSION=$(grep -A5 '"superpowers@' "$PLUGINS_JSON" 2>/dev/null | grep '"version"' | head -1 | sed 's/.*: *"\([^"]*\)".*/\1/')
fi

if [ -z "$SP_VERSION" ] || [ "$SP_VERSION" = "unknown" ]; then
  echo "  ERROR: Superpowers plugin not found."
  echo "         Install in Claude Code: /install superpowers"
  echo "         Minimum: $SP_MIN"
  PREREQ_OK=false
else
  echo "  Superpowers: v$SP_VERSION"
  if ! version_gte "$SP_VERSION" "$SP_MIN"; then
    echo "  ERROR: Superpowers $SP_VERSION is below minimum ($SP_MIN)."
    echo "         Update in Claude Code: /install superpowers"
    PREREQ_OK=false
  fi
fi

# BMAD Method
BMAD_MIN="6.0.0"
BMAD_VERSION=""

if [ -f "$CLAUDE_DIR/config/bmad/config.yaml" ]; then
  BMAD_VERSION=$(grep '^version:' "$CLAUDE_DIR/config/bmad/config.yaml" 2>/dev/null | sed 's/.*"\([^"]*\)".*/\1/')
fi

if [ -z "$BMAD_VERSION" ]; then
  # Fallback: check if skill files exist at all
  if [ -d "$CLAUDE_DIR/skills/bmad" ]; then
    echo "  WARNING: BMAD skills found but version unknown. Expecting $BMAD_MIN+."
    echo "           Check: https://github.com/bmad-code-org/BMAD-METHOD"
    PREREQ_WARN=true
  else
    echo "  ERROR: BMAD Method not found."
    echo "         Install: https://github.com/bmad-code-org/BMAD-METHOD#installation"
    echo "         Minimum: $BMAD_MIN"
    PREREQ_OK=false
  fi
else
  echo "  BMAD Method: v$BMAD_VERSION"
  if ! version_gte "$BMAD_VERSION" "$BMAD_MIN"; then
    echo "  ERROR: BMAD $BMAD_VERSION is below minimum ($BMAD_MIN)."
    echo "         Update: https://github.com/bmad-code-org/BMAD-METHOD#installation"
    PREREQ_OK=false
  fi
fi

if [ "$PREREQ_OK" = false ]; then
  echo ""
  echo "Fix the errors above and re-run."
  exit 1
fi

if [ "$PREREQ_WARN" = true ]; then
  echo ""
  echo "  Warnings above are non-blocking. Continuing..."
else
  echo "  All prerequisites OK."
fi
echo ""

# --- Backup ---

echo "Creating backup of current ~/.claude/ config..."
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/conflicts"

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

# --- Conflict Scan & Cleanup ---

echo "Scanning for potential conflicts..."
CONFLICTS=()
CLEANED_SKILLS=()
CLEANED_DONCHELI=false
HOOK_CONFLICT=false

# Skills that SweetClaude supersedes
CONFLICT_SKILLS=("real-tdd" "fix-issue" "pr-ready")
for skill in "${CONFLICT_SKILLS[@]}"; do
  SKILL_PATH="$CLAUDE_DIR/skills/$skill"
  if [ -d "$SKILL_PATH" ]; then
    CONFLICTS+=("$skill")
  fi
done

# Don Cheli (redundant with SweetClaude)
if [ -d "$CLAUDE_DIR/don-cheli" ]; then
  CONFLICTS+=("don-cheli")
fi

# Check for existing hooks that might conflict
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  if grep -q "test-guardian\|auto-test-runner\|test.guard\|tdd.guard" "$CLAUDE_DIR/settings.json" 2>/dev/null; then
    HOOK_CONFLICT=true
  fi
fi

if [ ${#CONFLICTS[@]} -eq 0 ] && [ "$HOOK_CONFLICT" = false ]; then
  echo "  No conflicts found."
else
  # Report what was found
  SKILL_CONFLICTS=()
  HAS_DONCHELI=false
  for item in "${CONFLICTS[@]}"; do
    if [ "$item" = "don-cheli" ]; then
      HAS_DONCHELI=true
    else
      SKILL_CONFLICTS+=("$item")
    fi
  done

  if [ ${#SKILL_CONFLICTS[@]} -gt 0 ]; then
    echo ""
    echo "  Found ${#SKILL_CONFLICTS[@]} superseded skill(s):"
    for skill in "${SKILL_CONFLICTS[@]}"; do
      echo "    - $skill → $CLAUDE_DIR/skills/$skill/ (replaced by sweetclaude:$skill)"
    done
    echo ""
    read -p "  Back up and remove these skills? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      for skill in "${SKILL_CONFLICTS[@]}"; do
        cp -r "$CLAUDE_DIR/skills/$skill" "$BACKUP_DIR/conflicts/skill-$skill"
        rm -rf "$CLAUDE_DIR/skills/$skill"
        CLEANED_SKILLS+=("$skill")
        echo "    Backed up and removed: $skill"
      done
    else
      echo "    Skipped — these skills will remain alongside SweetClaude."
    fi
  fi

  if [ "$HAS_DONCHELI" = true ]; then
    DONCHELI_SIZE=$(du -sh "$CLAUDE_DIR/don-cheli" 2>/dev/null | cut -f1)
    echo ""
    echo "  Found Don Cheli SDD framework ($DONCHELI_SIZE) — redundant with SweetClaude."
    echo "    Location: $CLAUDE_DIR/don-cheli/"
    echo ""
    read -p "  Back up and remove Don Cheli? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      cp -r "$CLAUDE_DIR/don-cheli" "$BACKUP_DIR/conflicts/don-cheli"
      rm -rf "$CLAUDE_DIR/don-cheli"
      CLEANED_DONCHELI=true
      echo "    Backed up and removed: don-cheli"
    else
      echo "    Skipped — Don Cheli will remain alongside SweetClaude."
    fi
  fi

  if [ "$HOOK_CONFLICT" = true ]; then
    echo ""
    echo "  WARNING: Existing TDD-related hooks found in settings.json."
    echo "  These cannot be auto-cleaned — review settings.json manually after install."
  fi
fi
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

- If the user asks to do anything involving SweetClaude workflows — phase pipeline, strategy work, file reconciliation, TDD enforcement, project init, or any `sweetclaude:` skill — invoke the `sweetclaude` master skill FIRST and run its pre-flight check before doing any work. This applies whether or not the project is already configured.
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

# --- Generate restore-config.sh ---

RESTORE_FILE="$SCRIPT_DIR/restore-config.sh"
cat > "$RESTORE_FILE" << RESTORE
#!/bin/bash
# SweetClaude Config Restore
# Restores pre-install configuration from backup.

set -e

CLAUDE_DIR="\$HOME/.claude"
BACKUP_DIR="$BACKUP_DIR"

echo "SweetClaude Config Restore"
echo "=========================="
echo ""

if [ ! -d "\$BACKUP_DIR" ]; then
  echo "  No backup found at \$BACKUP_DIR"
  echo "  Nothing to restore."
  exit 1
fi

echo "Backup contents:"
ls "\$BACKUP_DIR/" 2>/dev/null | sed 's/^/  /'
if [ -d "\$BACKUP_DIR/conflicts" ] && [ "\$(ls -A "\$BACKUP_DIR/conflicts" 2>/dev/null)" ]; then
  echo "  conflicts/"
  ls "\$BACKUP_DIR/conflicts/" 2>/dev/null | sed 's/^/    /'
fi
echo ""
RESTORE

# Add conflict restoration commands based on what was actually cleaned
if [ ${#CLEANED_SKILLS[@]} -gt 0 ] || [ "$CLEANED_DONCHELI" = true ]; then
  cat >> "$RESTORE_FILE" << 'RESTORE_CONFLICTS_HEADER'
read -p "Restore cleaned-up conflicts? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
RESTORE_CONFLICTS_HEADER

  for skill in "${CLEANED_SKILLS[@]}"; do
    cat >> "$RESTORE_FILE" << RESTORE_SKILL
  if [ -d "\$BACKUP_DIR/conflicts/skill-$skill" ]; then
    cp -r "\$BACKUP_DIR/conflicts/skill-$skill" "\$CLAUDE_DIR/skills/$skill"
    echo "  Restored skill: $skill"
  fi
RESTORE_SKILL
  done

  if [ "$CLEANED_DONCHELI" = true ]; then
    cat >> "$RESTORE_FILE" << 'RESTORE_DONCHELI'
  if [ -d "$BACKUP_DIR/conflicts/don-cheli" ]; then
    cp -r "$BACKUP_DIR/conflicts/don-cheli" "$CLAUDE_DIR/don-cheli"
    echo "  Restored: Don Cheli SDD framework"
  fi
RESTORE_DONCHELI
  fi

  cat >> "$RESTORE_FILE" << 'RESTORE_CONFLICTS_FOOTER'
  echo "  Conflicts restored."
else
  echo "  Skipped conflict restore."
fi
echo ""
RESTORE_CONFLICTS_FOOTER
fi

cat >> "$RESTORE_FILE" << 'RESTORE_SETTINGS'
# CLAUDE.md is NOT restored here — the uninstaller surgically removes only
# the SweetClaude section, preserving any changes you made since install.
# The pre-install backup is still available if you need it:
if [ -f "$BACKUP_DIR/CLAUDE.md" ]; then
  echo "Note: ~/CLAUDE.md was cleaned surgically (SweetClaude section removed)."
  echo "  Pre-install backup: $BACKUP_DIR/CLAUDE.md"
  echo ""
fi

if [ -f "$BACKUP_DIR/settings.json" ]; then
  read -p "Restore ~/.claude/settings.json to pre-install version? (y/n) " -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    cp "$BACKUP_DIR/settings.json" "$CLAUDE_DIR/settings.json"
    echo "  Restored settings.json"
  else
    echo "  Skipped settings.json restore."
  fi
  echo ""
fi

echo "Config restore complete."
RESTORE_SETTINGS

chmod +x "$RESTORE_FILE"

# --- Generate Uninstaller ---

cat > "$SCRIPT_DIR/uninstall.sh" << 'UNINSTALL'
#!/bin/bash
# SweetClaude Uninstaller
# Removes SweetClaude files and cleans CLAUDE.md, then offers to restore pre-install config.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
CLAUDE_MD="$HOME/CLAUDE.md"

echo "SweetClaude Uninstaller"
echo "======================="
echo ""

echo "Removing SweetClaude framework files..."
rm -rf "$CLAUDE_DIR/skills/sweetclaude"
rm -rf "$CLAUDE_DIR/hooks/sweetclaude"
rm -rf "$CLAUDE_DIR/agents/sweetclaude"
rm -rf "$CLAUDE_DIR/rules/sweetclaude"
rm -rf "$CLAUDE_DIR/config/sweetclaude"
echo "  Framework files removed."

# Always strip the SweetClaude section from CLAUDE.md — it references
# files we just deleted, so leaving it creates broken instructions.
if [ -f "$CLAUDE_MD" ] && grep -q "## SweetClaude" "$CLAUDE_MD" 2>/dev/null; then
  # Remove from "## SweetClaude" to the next heading or EOF
  sed -i.bak '/^## SweetClaude$/,/^## /{/^## SweetClaude$/d;/^## /!d;}' "$CLAUDE_MD"
  # Also remove any trailing blank lines left behind
  sed -i.bak -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CLAUDE_MD"
  rm -f "$CLAUDE_MD.bak"
  echo "  Removed SweetClaude section from ~/CLAUDE.md."
fi
echo ""

if [ -f "$SCRIPT_DIR/restore-config.sh" ]; then
  read -p "Restore pre-install configuration? (y/n) " -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    "$SCRIPT_DIR/restore-config.sh"
  fi
else
  echo "  No restore-config.sh found. Manual cleanup of settings.json may be needed."
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
echo ""
echo "  Skills:  $CLAUDE_DIR/skills/sweetclaude/"
echo "  Hooks:   $CLAUDE_DIR/hooks/sweetclaude/"
echo "  Agents:  $CLAUDE_DIR/agents/sweetclaude/"
echo "  Rules:   $CLAUDE_DIR/rules/sweetclaude/"
echo "  Config:  $CLAUDE_DIR/config/sweetclaude/"
echo ""
if [ ${#CLEANED_SKILLS[@]} -gt 0 ] || [ "$CLEANED_DONCHELI" = true ]; then
  echo "Cleaned up:"
  for skill in "${CLEANED_SKILLS[@]}"; do
    echo "  - Skill: $skill (backed up to $BACKUP_DIR/conflicts/)"
  done
  if [ "$CLEANED_DONCHELI" = true ]; then
    echo "  - Don Cheli SDD (backed up to $BACKUP_DIR/conflicts/)"
  fi
  echo ""
fi
if [ "$HOOK_CONFLICT" = true ]; then
  echo "ACTION NEEDED: Review TDD-related hooks in ~/.claude/settings.json."
  echo ""
fi
echo "Getting started:"
echo '  claude "sweetclaude init my-project"'
echo ""
echo "To restore pre-install config:  ./restore-config.sh"
echo "To uninstall SweetClaude:       ./uninstall.sh"
