#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Installer
# Copies framework files to ~/.claude/ for Claude Code to load.
# Backs up existing config, scans for conflicts, and offers restore via uninstall.sh.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
BACKUP_DIR="$CLAUDE_DIR/backup-pre-sweetclaude-$(date +%Y%m%d-%H%M%S)"

# --- Parse flags ---
STRATEGY_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --strategy-skills-only) STRATEGY_ONLY=true ;;
    --help|-h)
      echo "Usage: ./install.sh [--strategy-skills-only]"
      echo ""
      echo "  --strategy-skills-only  Install strategy, product, and corpus skills only."
      echo "                          No code/design skills, no TDD hooks, no subagents."
      echo ""
      echo "  (no flags)              Full install — all skills, TDD hooks, subagents."
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Run ./install.sh --help for usage."
      exit 1
      ;;
  esac
done

if [ "$STRATEGY_ONLY" = true ]; then
  echo "SweetClaude Installer (strategy skills only)"
  echo "============================================="
else
  echo "SweetClaude Installer"
  echo "====================="
fi
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

if [ "$STRATEGY_ONLY" = true ]; then
  echo "Installing SweetClaude (strategy skills only)..."
else
  echo "Installing SweetClaude..."
fi

mkdir -p "$CLAUDE_DIR/skills/sweetclaude"
mkdir -p "$CLAUDE_DIR/rules/sweetclaude"
mkdir -p "$CLAUDE_DIR/config/sweetclaude/templates"
mkdir -p "$CLAUDE_DIR/scripts/sweetclaude"

if [ "$STRATEGY_ONLY" = true ]; then
  SKILL_COUNT=0
  for skill_dir in "$SCRIPT_DIR/skills/"*/; do
    skill_name=$(basename "$skill_dir")
    case "$skill_name" in
      code-*|design-*|product-user-tdd-tests)
        ;;
      *)
        cp -r "$skill_dir" "$CLAUDE_DIR/skills/sweetclaude/"
        SKILL_COUNT=$((SKILL_COUNT + 1))
        ;;
    esac
  done
  echo "  Installed $SKILL_COUNT skills (strategy, product, corpus, orchestration)."
  echo "  Skipped: code, design, and TDD test generation skills."
else
  mkdir -p "$CLAUDE_DIR/hooks/sweetclaude"
  mkdir -p "$CLAUDE_DIR/agents/sweetclaude"
  cp -r "$SCRIPT_DIR/skills/"* "$CLAUDE_DIR/skills/sweetclaude/"
  cp -r "$SCRIPT_DIR/hooks/"* "$CLAUDE_DIR/hooks/sweetclaude/"
  cp -r "$SCRIPT_DIR/agents/"* "$CLAUDE_DIR/agents/sweetclaude/"
  chmod +x "$CLAUDE_DIR/hooks/sweetclaude/"*.sh
fi

cp -r "$SCRIPT_DIR/rules/"* "$CLAUDE_DIR/rules/sweetclaude/"
cp -r "$SCRIPT_DIR/config/"* "$CLAUDE_DIR/config/sweetclaude/"

if [ -d "$SCRIPT_DIR/scripts" ]; then
  cp -r "$SCRIPT_DIR/scripts/"* "$CLAUDE_DIR/scripts/sweetclaude/"
fi

echo "  Framework files installed."

# --- Hook Wiring (full install only) ---

if [ "$STRATEGY_ONLY" = true ]; then
  echo "  Hooks skipped (strategy-skills-only mode)."
else
  SETTINGS_FILE="$CLAUDE_DIR/settings.json"

  if [ -f "$SETTINGS_FILE" ]; then
    if grep -q "drift-gate" "$SETTINGS_FILE" 2>/dev/null; then
      echo "  Hooks already configured in settings.json."
    else
      python3 - "$SETTINGS_FILE" "$CLAUDE_DIR/hooks/sweetclaude" << 'PYMERGE'
import sys, json, os, tempfile

settings_path = sys.argv[1]
hooks_dir = sys.argv[2]

new_hooks = {
    "SessionStart": [
        {"matcher": "startup", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh"}]},
        {"matcher": "startup", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/drift-gate.sh"}]},
    ],
    "PreToolUse": [
        {"matcher": "Skill", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/master-preflight.sh"}]},
        {"matcher": "", "hooks": [{"type": "command", "command": f"{hooks_dir}/preflight-guard.sh"}]},
        {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": f"{hooks_dir}/test-guardian.sh"}]},
    ],
    "PostToolUse": [
        {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": f"{hooks_dir}/auto-test-runner.sh"}]},
    ],
    "Stop": [
        {"hooks": [{"type": "command", "command": f"{hooks_dir}/phase-dwelling-guard.sh"}]},
    ],
}

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})
for event, entries in new_hooks.items():
    existing = hooks.setdefault(event, [])
    for entry in entries:
        cmd = entry["hooks"][0]["command"]
        if not any(cmd in str(e) for e in existing):
            existing.append(entry)

with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(settings_path), suffix=".tmp", delete=False) as tmp:
    json.dump(settings, tmp, indent=2)
    tmp_name = tmp.name
os.replace(tmp_name, settings_path)
print("  Merged SweetClaude hooks into existing settings.json.")
PYMERGE
    fi
  else
    cat > "$SETTINGS_FILE" << 'SETTINGS'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-preflight.sh"
          }
        ]
      },
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/drift-gate.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/master-preflight.sh"
          }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/sweetclaude/preflight-guard.sh"
          }
        ]
      },
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
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/sweetclaude/phase-dwelling-guard.sh"
          }
        ]
      }
    ]
  }
}
SETTINGS
    echo "  Created settings.json with SweetClaude hooks."
  fi
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
- Read `.sweetclaude/state/sweetclaude.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
CLAUDEMD
    echo "  Added SweetClaude section to ~/CLAUDE.md."
  fi
else
  cat > "$CLAUDE_MD" << 'CLAUDEMD'
## SweetClaude

- If the user asks to do anything involving SweetClaude workflows — phase pipeline, strategy work, file reconciliation, TDD enforcement, project init, or any `sweetclaude:` skill — invoke the `sweetclaude` master skill FIRST and run its pre-flight check before doing any work. This applies whether or not the project is already configured.
- Read `.sweetclaude/state/sweetclaude.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist.
- Follow the interaction model in `~/.claude/rules/sweetclaude/interaction-model.md`.
- Respect the current deference level. Ask if not set.
- Never push for phase advancement. The user decides when to move on.
CLAUDEMD
  echo "  Created ~/CLAUDE.md with SweetClaude section."
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
rm -rf "$CLAUDE_DIR/scripts/sweetclaude"
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

# --- Write install config (path used by update/on skills to find local repo) ---
echo "{\"repo_path\": \"$SCRIPT_DIR\"}" > "$CLAUDE_DIR/sweetclaude-install.json"

# --- Summary ---

FIND_DIRS="$CLAUDE_DIR/skills/sweetclaude $CLAUDE_DIR/rules/sweetclaude $CLAUDE_DIR/config/sweetclaude"
if [ "$STRATEGY_ONLY" = false ]; then
  FIND_DIRS="$FIND_DIRS $CLAUDE_DIR/hooks/sweetclaude $CLAUDE_DIR/agents/sweetclaude"
fi
FILE_COUNT=$(find $FIND_DIRS -type f 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "================================================"
if [ "$STRATEGY_ONLY" = true ]; then
  echo "SweetClaude (strategy skills) installed successfully."
else
  echo "SweetClaude installed successfully."
fi
echo "================================================"
echo ""
echo "  Files installed: $FILE_COUNT"
echo "  Backup location: $BACKUP_DIR"
echo ""
echo "  Skills:  $CLAUDE_DIR/skills/sweetclaude/"
if [ "$STRATEGY_ONLY" = false ]; then
  echo "  Hooks:   $CLAUDE_DIR/hooks/sweetclaude/"
  echo "  Agents:  $CLAUDE_DIR/agents/sweetclaude/"
fi
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
if [ "$STRATEGY_ONLY" = true ]; then
  echo '  claude "sweetclaude sherpa-start"'
  echo ""
  echo "  Available: strategy, product, corpus, and orchestration skills."
  echo "  To upgrade to full install later: ./install.sh"
else
  echo '  claude "sweetclaude init my-project"'
fi
echo ""
echo "To restore pre-install config:  ./restore-config.sh"
echo "To uninstall SweetClaude:       ./uninstall.sh"
