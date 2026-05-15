#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude metrics event recorder.
# Usage: record-event.sh <event_type> <skill_name> [key=value ...]
# Example: record-event.sh skill_invoked sweetclaude:status

EVENT_TYPE="${1:-unknown}"
SKILL_NAME="${2:-}"
shift 2 2>/dev/null || shift $#

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
[ -z "$PROJECT_DIR" ] && exit 0

METRICS_CONFIG="$PROJECT_DIR/.sweetclaude/metrics/config.yaml"
EVENTS_LOG="$PROJECT_DIR/.sweetclaude/metrics/events.log"

[ -f "$METRICS_CONFIG" ] || exit 0
grep -q "enabled: true" "$METRICS_CONFIG" 2>/dev/null || exit 0

PHASE=$(python3 -c "
import yaml
try:
    d = yaml.safe_load(open('$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml')) or {}
    print(d.get('work', {}).get('active', {}).get('phase') or 'none')
except Exception:
    print('none')
" 2>/dev/null || echo "none")

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
{
    printf -- '---\ntimestamp: %s\nevent: %s\n' "$TIMESTAMP" "$EVENT_TYPE"
    [ -n "$SKILL_NAME" ] && printf 'skill: %s\n' "$SKILL_NAME"
    [ -n "$PHASE" ] && printf 'phase: %s\n' "$PHASE"
    for kv in "$@"; do
        printf '%s\n' "$kv"
    done
} >> "$EVENTS_LOG"

exit 0
