#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Storage Adapter
# Source this file in any skill to get sc_artifact_* functions.
#
# Usage in a skill:
#   source ~/.claude/hooks/sweetclaude/sc-artifact.sh
#   result=$(sc_artifact_read I-025)
#   sc_artifact_write I-025 '{"status":"in_progress"}'
#
# Requires: python3, pyyaml

SC_ARTIFACT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SC_IMPL="${SC_ARTIFACT_DIR}/sc-artifact-impl.py"

# Project root: prefer explicit override, fall back to PWD
SC_PROJECT_ROOT="${SWEETCLAUDE_PROJECT_ROOT:-$PWD}"

# Resolve product_base and storage_backend from project config
_sc_init() {
  if [[ -n "${_SC_INITIALIZED:-}" ]]; then return 0; fi

  if [[ ! -f "${SC_IMPL}" ]]; then
    echo "sc-artifact: ERROR — sc-artifact-impl.py not found at ${SC_IMPL}" >&2
    return 1
  fi

  local cfg
  cfg=$(python3 "${SC_IMPL}" _init "${SC_PROJECT_ROOT}" 2>&1)
  if [[ $? -ne 0 ]]; then
    echo "sc-artifact: ERROR — ${cfg}" >&2
    return 1
  fi

  eval "${cfg}"
  export SC_PROJECT_ROOT SC_PRODUCT_BASE SC_STATE_BASE SC_BACKEND
  export _SC_INITIALIZED=1
}

sc_artifact_read() {
  _sc_init || return 1
  python3 "${SC_IMPL}" read "${SC_PROJECT_ROOT}" "${SC_PRODUCT_BASE}" "${SC_STATE_BASE}" "$1"
}

sc_artifact_write() {
  _sc_init || return 1
  python3 "${SC_IMPL}" write "${SC_PROJECT_ROOT}" "${SC_PRODUCT_BASE}" "${SC_STATE_BASE}" "$1" "$2"
}

sc_artifact_create() {
  _sc_init || return 1
  python3 "${SC_IMPL}" create "${SC_PROJECT_ROOT}" "${SC_PRODUCT_BASE}" "${SC_STATE_BASE}" "$1" "$2"
}

sc_artifact_query() {
  _sc_init || return 1
  python3 "${SC_IMPL}" query "${SC_PROJECT_ROOT}" "${SC_PRODUCT_BASE}" "${SC_STATE_BASE}" "$@"
}

sc_artifact_delete() {
  _sc_init || return 1
  python3 "${SC_IMPL}" delete "${SC_PROJECT_ROOT}" "${SC_PRODUCT_BASE}" "${SC_STATE_BASE}" "$1"
}

sc_artifact_list() {
  _sc_init || return 1
  python3 "${SC_IMPL}" list "${SC_PROJECT_ROOT}" "${SC_PRODUCT_BASE}" "${SC_STATE_BASE}" "$1"
}
