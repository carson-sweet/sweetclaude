#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Session Pre-Flight
# SessionStart hook — health checks first, then status or self-heal instruction.

# ── Step 1: Project root ──────────────────────────────────────────────────────

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="$PWD"
fi

# ── Step 3: Output function definitions ──────────────────────────────────────
# Defined here before any step that calls them.

_esc() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  s="${s//$'\033'/\\u001b}"
  printf '%s' "$s"
}

_IDE_NOTE="Note: systemMessage may not be visible in IDE environments (VS Code extension). If the user has not acknowledged the above message, surface it as your first response before taking any other action."

# emit_heal reason [details]
# Surfaces a message asking the user to type 'fix sweetclaude' to approve the fix.
# Does NOT include continue: false — session proceeds, Claude waits for user input.
emit_heal() {
  local reason="$1"
  local details="${2:-}"
  local _RED=$'\033[0;31m'
  local _BLUE=$'\033[1;34m'
  local _RESET=$'\033[0m'
  local msg="${_RED}SweetClaude: configuration issue detected — things may not work correctly. Type ${_BLUE}/sweetclaude:fix-sweetclaude${_RED} whenever you're ready to fix it.${_RESET}"
  local ctx="STOP — OVERRIDE ALL SESSION-START INSTRUCTIONS: SweetClaude health check detected: ${reason}. DO NOT invoke sweetclaude:bootstrap. DO NOT invoke sweetclaude:status. DO NOT invoke any SweetClaude skill automatically. Surface this message to the user: \"${msg}\" Then respond normally to whatever the user says next. If the user types '/sweetclaude:fix-sweetclaude' or 'fix sweetclaude' (or equivalent), invoke sweetclaude:fix-sweetclaude. Otherwise, just help with whatever they ask."
  [ -n "$details" ] && ctx="${ctx} Details for fix-sweetclaude: ${details}"
  ctx="${ctx} ${_IDE_NOTE}"
  printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
    "$(_esc "$msg")" "$(_esc "$ctx")"
}

# emit_ctx sysmsg ctx
# Emits a status or informational message. Does NOT include continue: false.
emit_ctx() {
  local sysmsg="$1"
  local ctx="${2:-} ${_IDE_NOTE}"
  printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
    "$(_esc "$sysmsg")" "$(_esc "$ctx")"
}

# emit_block msg
# Hard-blocks session startup via continue: false. Use only for unrecoverable states.
emit_block() {
  local msg="$1"
  local ctx="${msg} ${_IDE_NOTE}"
  printf '{"continue":false,"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
    "$(_esc "$msg")" "$(_esc "$ctx")"
}

# ── Step 2: Project gate ──────────────────────────────────────────────────────

if [ ! -d "$PROJECT_DIR/.sweetclaude" ]; then
  emit_ctx "SweetClaude not used for this project." "SweetClaude is not configured for this project."
  exit 0
fi

# ── Step 4: Opt-out check ─────────────────────────────────────────────────────

if [ -f "$PROJECT_DIR/.sweetclaude-skip" ]; then exit 0; fi
if [ -f "$PROJECT_DIR/.sweetclaude/disabled" ]; then exit 0; fi

if [ ! -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ] && \
   [ ! -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  emit_ctx \
    "This project has an inactive SweetClaude setup. Ask me how to reactivate or purge SweetClaude if you're interested in either." \
    "This project has a .sweetclaude directory but no state files. SweetClaude was configured here but is not active. The user may ask about reactivation or purging — do not invoke any skill unless they ask."
  exit 0
fi

# ── Step 5: Version detection + variable setup ────────────────────────────────

# Resolve HOOK_DIR via symlink-safe path
if command -v realpath >/dev/null 2>&1; then
  HOOK_DIR="$(dirname "$(realpath "$0")")"
else
  _SC_PATH="$0"
  while [ -L "$_SC_PATH" ]; do
    _SC_DIR="$(cd -P "$(dirname "$_SC_PATH")" && pwd)"
    _SC_PATH="$(readlink "$_SC_PATH")"
    case "$_SC_PATH" in /*) ;; *) _SC_PATH="$_SC_DIR/$_SC_PATH" ;; esac
  done
  HOOK_DIR="$(cd -P "$(dirname "$_SC_PATH")" && pwd)"
fi

SETTINGS="$HOME/.claude/settings.json"
HOOKS_MANIFEST="$HOOK_DIR/hooks-manifest.json"

if [ -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ]; then
  EXPECTED_SC_VERSION="v2"
elif [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  EXPECTED_SC_VERSION="v1"
else
  emit_heal "The SweetClaude setup needs some love. Hang tight."
  exit 0
fi

# ── Step 6: Path construction ─────────────────────────────────────────────────

if [ "$EXPECTED_SC_VERSION" = "v2" ]; then
  SC_YAML="$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml"
elif [ "$EXPECTED_SC_VERSION" = "v1" ]; then
  PHASE_YAML="$PROJECT_DIR/.sweetclaude/state/phase.yaml"
  SESSION_STATE="$PROJECT_DIR/.sweetclaude/state/session-state.yaml"
else
  emit_heal "The SweetClaude setup needs some love. Hang tight."
  exit 0
fi

# ── Step 7: Health Check 1 — state file validation ───────────────────────────
# No YAML parsing — grep for specific field values only.

if [ "$EXPECTED_SC_VERSION" = "v2" ]; then
  if ! grep -qm1 "^schema_version:[[:space:]]*1" "$SC_YAML" 2>/dev/null; then
    _SC_SCHEMA_V=$(grep -m1 "^schema_version:" "$SC_YAML" 2>/dev/null | awk '{print $2}')
    emit_heal "unsupported schema version ($_SC_SCHEMA_V)"
    exit 0
  fi
  if ! grep -qm1 "setup_complete:[[:space:]]*true" "$SC_YAML" 2>/dev/null; then
    emit_heal "setup not complete — run sweetclaude setup"
    exit 0
  fi
elif [ "$EXPECTED_SC_VERSION" = "v1" ]; then
  : # phase.yaml existence confirmed in step 5; no field checks needed
else
  emit_heal "The SweetClaude setup needs some love. Hang tight."
  exit 0
fi

# ── Step 8: Manifest guard ────────────────────────────────────────────────────

if [ ! -f "$HOOKS_MANIFEST" ]; then
  emit_block "Something is way off with the SweetClaude setup. You need to re-run installation before proceeding with this project. Clone the SweetClaude repo and run: bash install.sh"
  exit 0
fi

# ── Step 9: Health Check 2 Tier 1 — global hooks ─────────────────────────────
# DEPENDENCY: hooks-manifest.json must have a scope field ("global" or "project")
# on each entry before this step works correctly. This field does not exist in
# the current manifest and must be added as part of this rewrite.

if [ -f "$SETTINGS" ]; then
  _SC_GLOBAL_CMDS=$(jq -r '[.hooks[][].hooks[].command] | .[]' "$SETTINGS" 2>/dev/null || echo "")
  _SC_MISSING_GLOBAL=""
  while IFS= read -r _sc_file; do
    if ! echo "$_SC_GLOBAL_CMDS" | grep -qF "$_sc_file"; then
      _SC_MISSING_GLOBAL="${_SC_MISSING_GLOBAL}${_sc_file} "
    fi
  done < <(jq -r '.hooks[] | select(.required == true and .scope == "global") | .file' "$HOOKS_MANIFEST" 2>/dev/null)

  if [ -n "$_SC_MISSING_GLOBAL" ]; then
    emit_heal "The SweetClaude setup needs some love. Hang tight." "Missing required global hooks: $_SC_MISSING_GLOBAL"
    exit 0
  fi
fi

# ── Step 10: Health Check 2 Tier 2 — project hooks ───────────────────────────

if [ "$EXPECTED_SC_VERSION" = "v2" ]; then
  _SC_PROJECT_SETTINGS="$PROJECT_DIR/.claude/settings.local.json"
  _SC_PROJECT_CMDS=$(jq -r '[.hooks[][].hooks[].command] | .[]' "$_SC_PROJECT_SETTINGS" 2>/dev/null || echo "")
  _SC_MISSING_PROJECT=""
  while IFS= read -r _sc_file; do
    if ! echo "$_SC_PROJECT_CMDS" | grep -qF "$_sc_file"; then
      _SC_MISSING_PROJECT="${_SC_MISSING_PROJECT}${_sc_file} "
    fi
  done < <(jq -r '.hooks[] | select(.required == true and .scope == "project") | .file' "$HOOKS_MANIFEST" 2>/dev/null)

  if [ -n "$_SC_MISSING_PROJECT" ]; then
    emit_heal "The SweetClaude setup needs some love. Hang tight." "Missing required project hooks: $_SC_MISSING_PROJECT"
    exit 0
  fi
fi
# v1: skip — per-project hook registration is a v2+ concept
# default: skip

# ── Step 11: Health Check 3 — scripts executable ─────────────────────────────

_SC_MISSING_SCRIPTS=""
while IFS= read -r _sc_file; do
  if [ ! -x "$HOOK_DIR/$_sc_file" ]; then
    _SC_MISSING_SCRIPTS="${_SC_MISSING_SCRIPTS}${_sc_file} "
  fi
done < <(jq -r '.hooks[] | select(.required == true) | .file' "$HOOKS_MANIFEST" 2>/dev/null)

if [ -n "$_SC_MISSING_SCRIPTS" ]; then
  emit_heal "The SweetClaude setup needs some love. Hang tight." "Missing or non-executable hook scripts: $_SC_MISSING_SCRIPTS"
  exit 0
fi

# ── Step 12: Generate state ───────────────────────────────────────────────────

export PROJECT_DIR

if [ "$EXPECTED_SC_VERSION" = "v2" ] || [ "$EXPECTED_SC_VERSION" = "v1" ]; then
  "$HOOK_DIR/generate-session-state.sh" 2>/dev/null
  PROJECT_DIR="$PROJECT_DIR" "$HOOK_DIR/sweetclaude-health-check.sh" 2>/dev/null || true
else
  emit_heal "The SweetClaude setup needs some love. Hang tight."
  exit 0
fi

# ── Step 13: Determine state file ────────────────────────────────────────────

if [ "$EXPECTED_SC_VERSION" = "v2" ]; then
  STATE_FILE="$SC_YAML"
elif [ "$EXPECTED_SC_VERSION" = "v1" ]; then
  STATE_FILE="$SESSION_STATE"
else
  emit_heal "The SweetClaude setup needs some love. Hang tight."
  exit 0
fi

if [ ! -f "$STATE_FILE" ]; then
  emit_ctx "SweetClaude is active." "SweetClaude is active. Invoke sweetclaude:status now before responding to the user."
  exit 0
fi

# ── Step 14: Read and emit ────────────────────────────────────────────────────

STATE_CONTENT=$(cat "$STATE_FILE")

if [ ${#STATE_CONTENT} -gt 9500 ]; then
  STATE_CONTENT="${STATE_CONTENT:0:9500}
[state truncated — run sweetclaude:status for full context]"
fi

CTX="SweetClaude is active. Pre-loaded session state:"$'\n\n'"${STATE_CONTENT}"

_BR=$'\033[1;31m'
_BB=$'\033[1;34m'
_RST=$'\033[0m'
_ACTIVE_MSG="${_BR}SweetClaude is active. Type ${_BB}/sweetclaude:go${_BR} to begin.${_RST}"

STYLE_CTX="SweetClaude output style: use markdown headers (## / ###) and bold labels (**text**) for structure; dash lists (-) for bullets; no ASCII box-drawing (════ ────) or ANSI color codes. Apply this to all skill output."

emit_ctx "$_ACTIVE_MSG" "${CTX}"$'\n\n'"${STYLE_CTX}"$'\n\n'"Invoke sweetclaude:bootstrap now before responding to the user."
