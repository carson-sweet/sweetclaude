#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude 24h health check — consistency scan + version check.
# Called by session-preflight.sh. Reads/writes sweetclaude.yaml.
# Requires: PROJECT_DIR env var set to project root.

set -euo pipefail

SC_YAML="${PROJECT_DIR}/.sweetclaude/state/sweetclaude.yaml"

[ -f "$SC_YAML" ] || exit 0

NOW_ISO=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat(timespec='seconds'))")

hours_since() {
  python3 -c "
import sys
from datetime import datetime, timezone
ts = sys.argv[1] if len(sys.argv) > 1 else ''
if not ts or ts == 'None': print(9999); exit()
try:
    t = datetime.fromisoformat(ts.replace('Z','+00:00'))
    diff = (datetime.now(timezone.utc) - t).total_seconds() / 3600
    print(int(diff))
except Exception: print(9999)
" "$1"
}

update_yaml_field() {
  local key="$1" val="$2"
  python3 - "$SC_YAML" "$key" "$val" << 'PY'
import sys, yaml
path, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f: d = yaml.safe_load(f) or {}
parts = key.split('.')
node = d
for p in parts[:-1]:
    node = node.setdefault(p, {})
node[parts[-1]] = None if val == 'null' else val
import tempfile, os as _os
with tempfile.NamedTemporaryFile('w', dir=_os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
_os.replace(tmp_name, path)
PY
}

# Always stamp hook_last_ran
update_yaml_field "framework.hook_last_ran" "$NOW_ISO"

# Always reconcile framework.installed_version with the plugin manifest.
# Without this, sweetclaude.yaml's installed_version stays at whatever value
# was written during the initial _migrate consolidation — it never advances
# when the installed plugin updates. Idempotent: only writes when values differ.
python3 - "$SC_YAML" << 'PY' 2>/dev/null
import sys, yaml, json, os, tempfile
sc_path = sys.argv[1]
try:
    with open(sc_path) as f:
        d = yaml.safe_load(f) or {}
except Exception:
    sys.exit(0)
recorded = (d.get('framework') or {}).get('installed_version')
actual = None
try:
    p = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [v for k, v in (p.get('plugins') or {}).items() if 'sweetclaude' in k.lower()]
    actual = entries[0][0].get('version') if entries and entries[0] else None
except Exception:
    pass
if actual and actual != recorded:
    d.setdefault('framework', {})['installed_version'] = actual
    with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(sc_path), suffix='.tmp', delete=False) as tmp:
        yaml.safe_dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
        tmp_name = tmp.name
    os.replace(tmp_name, sc_path)
PY

# Read timestamps
LAST_CONSISTENCY=$(python3 -c "
import yaml
d = yaml.safe_load(open('$SC_YAML')) or {}
print(d.get('framework',{}).get('consistency',{}).get('last_checked') or 'None')
" 2>/dev/null)

LAST_UPDATE=$(python3 -c "
import yaml
d = yaml.safe_load(open('$SC_YAML')) or {}
print(d.get('framework',{}).get('update',{}).get('last_checked') or 'None')
" 2>/dev/null)

# --- Consistency check (every 24h) ---
if [ "$(hours_since "$LAST_CONSISTENCY")" -ge 24 ]; then
  (
    DRIFT=""

    # Check hooks.json exists
    HOOKS_JSON="${HOME}/.claude/hooks/sweetclaude/hooks.json"
    if [ ! -f "$HOOKS_JSON" ]; then
      DRIFT="hooks.json_missing"
    else
      for required_hook in session-preflight.sh preflight-guard.sh; do
        if ! grep -q "$required_hook" "$HOOKS_JSON" 2>/dev/null; then
          DRIFT="${DRIFT} hook:${required_hook}"
        fi
      done
    fi

    # Check sweetclaude rules files
    RULES_DIR="$HOME/.claude/rules/sweetclaude"
    for rules_file in interaction-model.md phase-gates.md tdd-levels.md; do
      if [ ! -f "$RULES_DIR/$rules_file" ]; then
        DRIFT="${DRIFT} rules:${rules_file}"
      fi
    done

    DRIFT="${DRIFT# }"  # trim leading space

    if [ -n "$DRIFT" ]; then
      python3 - "$SC_YAML" "$DRIFT" << 'PY'
import sys, yaml
path, drift_str = sys.argv[1], sys.argv[2]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('consistency',{})['status'] = 'drift_detected'
d['framework']['consistency']['drift'] = drift_str.split()
d['framework']['consistency']['check_error'] = None
import tempfile, os as _os
with tempfile.NamedTemporaryFile('w', dir=_os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
_os.replace(tmp_name, path)
PY
    else
      python3 - "$SC_YAML" << 'PY'
import sys, yaml
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('consistency',{})['status'] = 'ok'
d['framework']['consistency']['drift'] = []
d['framework']['consistency']['check_error'] = None
import tempfile, os as _os
with tempfile.NamedTemporaryFile('w', dir=_os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
_os.replace(tmp_name, path)
PY
    fi
    update_yaml_field "framework.consistency.last_checked" "$NOW_ISO"
  ) || {
    python3 - "$SC_YAML" << 'PY'
import sys, yaml
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('consistency',{})['check_error'] = 'check_failed'
import tempfile, os as _os
with tempfile.NamedTemporaryFile('w', dir=_os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
_os.replace(tmp_name, path)
PY
  }
fi

# --- Version check (every 24h) ---
if [ "$(hours_since "$LAST_UPDATE")" -ge 24 ]; then
  (
    INSTALLED=$(python3 -c "
import json
try:
    d = json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e = [v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

    # Gap #1 — hybrid discovery:
    #   1. Local dev clone (per ~/.claude/sweetclaude-install.json repo_path)
    #   2. gh api releases/latest (if gh installed and authenticated)
    #   3. git ls-remote --tags <url> (universal fallback)
    # All network calls are wrapped in a 5-second timeout. Failures are
    # silent in user-facing surface; the result is recorded to
    # framework.update.check_error so fix-sweetclaude can surface it.
    REPO_VERSION=$(python3 - "$HOME" << 'PY' 2>/dev/null
import json, os, re, subprocess, sys
HOME = sys.argv[1]

def run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""

def repo_url_from_plugin():
    """Read repository URL from installed plugin manifest. Returns owner/repo str or None."""
    try:
        d = json.load(open(os.path.join(HOME, ".claude/plugins/installed_plugins.json")))
        entries = [v for k, v in (d.get("plugins") or {}).items() if "sweetclaude" in k.lower()]
        if not entries or not entries[0]:
            return None, None
        install_path = entries[0][0].get("installPath", "")
    except Exception:
        return None, None
    if not install_path:
        return None, None
    try:
        m = json.load(open(os.path.join(install_path, ".claude-plugin/plugin.json")))
        url = m.get("repository") or "https://github.com/carson-sweet/sweetclaude"
    except Exception:
        url = "https://github.com/carson-sweet/sweetclaude"
    # Parse owner/repo from URL.
    mo = re.search(r"github\.com[/:]([^/]+)/([^/.]+)", url)
    if not mo:
        return url, None
    return url, f"{mo.group(1)}/{mo.group(2)}"

def normalize_semver(tag):
    """Strip leading 'v' and trailing newline. Reject non-semver-shaped tags."""
    t = tag.strip().lstrip("v")
    return t if re.match(r"^\d+\.\d+\.\d+", t) else None

def semver_key(v):
    """Tuple for max() comparison."""
    parts = re.match(r"^(\d+)\.(\d+)\.(\d+)", v)
    return tuple(int(p) for p in parts.groups()) if parts else (0, 0, 0)

# Path 1: local dev clone.
install_json = os.path.join(HOME, ".claude/sweetclaude-install.json")
if os.path.exists(install_json):
    try:
        d = json.load(open(install_json))
        repo_path = d.get("repo_path", "")
        if repo_path and os.path.exists(os.path.join(repo_path, "package.json")):
            pkg = json.load(open(os.path.join(repo_path, "package.json")))
            v = pkg.get("version", "")
            if v:
                print(v); sys.exit()
    except Exception:
        pass

# Path 2/3: GitHub. Need the URL.
url, owner_repo = repo_url_from_plugin()

# Path 2: gh api (if available and auth'd).
if owner_repo:
    rc, out, _ = run(["gh", "api", f"repos/{owner_repo}/releases/latest", "-q", ".tag_name"])
    if rc == 0:
        v = normalize_semver(out)
        if v:
            print(v); sys.exit()

# Path 3: git ls-remote --tags.
if url:
    rc, out, _ = run(["git", "ls-remote", "--tags", url])
    if rc == 0:
        versions = []
        for line in out.splitlines():
            # Format: "<sha>\trefs/tags/<tag>" (optionally with ^{})
            if "\trefs/tags/" not in line:
                continue
            tag = line.split("\trefs/tags/", 1)[1].split("^{}")[0]
            v = normalize_semver(tag)
            if v:
                versions.append(v)
        if versions:
            best = max(versions, key=semver_key)
            print(best); sys.exit()

# All paths failed.
print("")
PY
)

    if [ -n "$REPO_VERSION" ] && [ "$REPO_VERSION" != "$INSTALLED" ] && [ "$REPO_VERSION" != "unknown" ] && [ "$INSTALLED" != "unknown" ]; then
      python3 - "$SC_YAML" "$REPO_VERSION" << 'PY'
import sys, yaml
path, ver = sys.argv[1], sys.argv[2]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('update',{})['available'] = ver
d['framework']['update']['check_error'] = None
import tempfile, os as _os
with tempfile.NamedTemporaryFile('w', dir=_os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
_os.replace(tmp_name, path)
PY
    else
      python3 - "$SC_YAML" << 'PY'
import sys, yaml
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('update',{})['available'] = None
d['framework']['update']['check_error'] = None
import tempfile, os as _os
with tempfile.NamedTemporaryFile('w', dir=_os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
_os.replace(tmp_name, path)
PY
    fi
    update_yaml_field "framework.update.last_checked" "$NOW_ISO"
  ) || {
    python3 - "$SC_YAML" << 'PY'
import sys, yaml
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f) or {}
d.setdefault('framework',{}).setdefault('update',{})['check_error'] = 'check_failed'
import tempfile, os as _os
with tempfile.NamedTemporaryFile('w', dir=_os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
_os.replace(tmp_name, path)
PY
  }
fi

# --- Doctor checkup prompt (every 7 days) ---
DOCTOR_MARKER="${PROJECT_DIR}/.sweetclaude/state/doctor-prompt-pending.json"
if [ ! -f "$DOCTOR_MARKER" ]; then
  LAST_DOCTOR=$(python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get('timestamp', ''))
except Exception:
    print('')
" "${PROJECT_DIR}/.sweetclaude/state/last-doctor-run.json" 2>/dev/null)

  if [ "$(hours_since "$LAST_DOCTOR")" -ge 168 ]; then
    python3 -c "
import json, os, sys, tempfile
from datetime import datetime, timezone
marker = {
    'trigger': 'time',
    'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds')
}
path = sys.argv[1]
os.makedirs(os.path.dirname(path), exist_ok=True)
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    json.dump(marker, tmp, indent=2)
    tmp_name = tmp.name
os.replace(tmp_name, path)
" "$DOCTOR_MARKER" 2>/dev/null || true
  fi
fi

exit 0
