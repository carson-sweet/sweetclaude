#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""SweetClaude project dashboard — local web UI with write-back API.

Serves a single-page dashboard from the SQLite cache, git log,
and skill event log. No external dependencies beyond Python stdlib.

Tabs align with the status view scopes spec (v3.1):
  Roadmap, Release, Epics, Backlog, Dependencies, Git, Activity

Write-back API (POST /api/update):
  Mutates status, priority, epic, epic_sequence on source files.
  All writes validate through status.py, produce audit trail entries,
  and trigger a cache rebuild.

Usage:
    python3 scripts/dashboard.py [--project-dir .] [--port 8411]
"""

import argparse
import http.server
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from status import CANONICAL_STATUSES, TERMINAL_STATUSES, derived_status

try:
    import yaml
except ImportError:
    yaml = None


def db_path(project_dir):
    return os.path.join(project_dir, '.sweetclaude', 'cache', 'roadmap.db')


def get_conn(project_dir):
    p = db_path(project_dir)
    if not os.path.exists(p):
        return None
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    return conn


def query_all_items(project_dir):
    conn = get_conn(project_dir)
    if not conn:
        return []
    rows = conn.execute("SELECT * FROM items ORDER BY type, id").fetchall()
    items = [dict(r) for r in rows]
    for item in items:
        tags = conn.execute(
            "SELECT tag FROM tags WHERE item_id=?", (item['id'],)
        ).fetchall()
        item['tags'] = [t['tag'] for t in tags]
        deps = conn.execute(
            "SELECT depends_on FROM dependencies WHERE item_id=?", (item['id'],)
        ).fetchall()
        item['depends_on'] = [d['depends_on'] for d in deps]
        if item['type'] == 'epic':
            criteria = conn.execute(
                "SELECT * FROM completion_criteria WHERE epic_id=? ORDER BY seq",
                (item['id'],),
            ).fetchall()
            item['completion_criteria'] = [dict(c) for c in criteria]
            item['criteria_done'] = sum(1 for c in criteria if c['done'])
            item['criteria_total'] = len(criteria)
            stories = conn.execute(
                """SELECT id, title, status, priority, effort, type
                   FROM items WHERE epic=? ORDER BY epic_sequence, id""",
                (item['id'],),
            ).fetchall()
            item['stories'] = [dict(s) for s in stories]
            child_statuses = [s['status'] for s in stories]
            item['derived_status'] = derived_status(child_statuses)
    conn.close()
    return items


def query_roadmap(project_dir):
    conn = get_conn(project_dir)
    if not conn:
        return {'milestones': [], 'orphan_epics': [], 'unlinked_open': 0}

    milestones = conn.execute(
        "SELECT * FROM items WHERE type='milestone' ORDER BY id"
    ).fetchall()
    result = []
    for ms in milestones:
        ms_dict = dict(ms)
        epics = conn.execute(
            "SELECT * FROM items WHERE type='epic' AND milestone=? ORDER BY id",
            (ms_dict['id'],),
        ).fetchall()
        epic_list = []
        for ep in epics:
            ed = dict(ep)
            stories = conn.execute(
                """SELECT id, title, status, priority, effort, type
                   FROM items WHERE epic=? ORDER BY epic_sequence, id""",
                (ed['id'],),
            ).fetchall()
            criteria = conn.execute(
                "SELECT * FROM completion_criteria WHERE epic_id=? ORDER BY seq",
                (ed['id'],),
            ).fetchall()
            ed['stories'] = [dict(s) for s in stories]
            ed['criteria'] = [dict(c) for c in criteria]
            ed['criteria_done'] = sum(1 for c in criteria if c['done'])
            ed['criteria_total'] = len(criteria)
            child_statuses = [s['status'] for s in stories]
            ed['derived_status'] = derived_status(child_statuses)
            epic_list.append(ed)

        epic_derived = [ep['derived_status'] for ep in epic_list]
        ms_dict['derived_status'] = derived_status(epic_derived)
        ms_dict['epics'] = epic_list
        result.append(ms_dict)

    orphan_epics = conn.execute(
        "SELECT * FROM items WHERE type='epic' AND (milestone IS NULL OR milestone='') ORDER BY id"
    ).fetchall()
    orphan_list = []
    for ep in orphan_epics:
        ed = dict(ep)
        stories = conn.execute(
            """SELECT id, title, status, priority, effort, type
               FROM items WHERE epic=? ORDER BY epic_sequence, id""",
            (ed['id'],),
        ).fetchall()
        criteria = conn.execute(
            "SELECT * FROM completion_criteria WHERE epic_id=? ORDER BY seq",
            (ed['id'],),
        ).fetchall()
        ed['stories'] = [dict(s) for s in stories]
        ed['criteria'] = [dict(c) for c in criteria]
        ed['criteria_done'] = sum(1 for c in criteria if c['done'])
        ed['criteria_total'] = len(criteria)
        child_statuses = [s['status'] for s in stories]
        ed['derived_status'] = derived_status(child_statuses)
        orphan_list.append(ed)

    unlinked = conn.execute(
        """SELECT COUNT(*) as c FROM items
           WHERE type NOT IN ('epic', 'milestone')
           AND (epic IS NULL OR epic='')
           AND status NOT IN ('done','abandoned','deferred')"""
    ).fetchone()

    conn.close()
    return {'milestones': result, 'orphan_epics': orphan_list, 'unlinked_open': unlinked['c']}


def query_dependencies(project_dir):
    conn = get_conn(project_dir)
    if not conn:
        return {'edges': [], 'items': {}}
    edges = conn.execute("SELECT item_id, depends_on FROM dependencies").fetchall()
    edge_list = [{'from': e['item_id'], 'to': e['depends_on']} for e in edges]
    involved_ids = set()
    for e in edge_list:
        involved_ids.add(e['from'])
        involved_ids.add(e['to'])
    items = {}
    for iid in involved_ids:
        row = conn.execute("SELECT id, title, status, epic FROM items WHERE id=?", (iid,)).fetchone()
        if row:
            items[iid] = dict(row)
        else:
            items[iid] = {'id': iid, 'title': '(not found)', 'status': 'unknown', 'epic': None}
    conn.close()
    return {'edges': edge_list, 'items': items}


def query_git_log(project_dir, limit=100):
    try:
        result = subprocess.run(
            ['git', '-C', project_dir, 'log', f'--max-count={limit}',
             '--format=%H|%h|%aI|%an|%s'],
            capture_output=True, text=True, timeout=10
        )
        commits = []
        for line in result.stdout.strip().splitlines():
            parts = line.split('|', 4)
            if len(parts) == 5:
                item_ids = re.findall(r'(?:ISSUE|STORY|BUG|DEBT|CHORE|EP|MS|REL)-\d+', parts[4])
                commits.append({
                    'sha': parts[0],
                    'short_sha': parts[1],
                    'date': parts[2],
                    'author': parts[3],
                    'message': parts[4],
                    'item_ids': item_ids,
                })
        return commits
    except Exception:
        return []


def query_git_status(project_dir):
    try:
        branch = subprocess.run(
            ['git', '-C', project_dir, 'branch', '--show-current'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        status = subprocess.run(
            ['git', '-C', project_dir, 'status', '--short'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        return {'branch': branch, 'changed_files': len(status.splitlines()) if status else 0}
    except Exception:
        return {'branch': 'unknown', 'changed_files': 0}


def query_events(project_dir):
    events_path = os.path.join(project_dir, '.sweetclaude', 'metrics', 'events.log')
    if not os.path.exists(events_path):
        return []
    events = []
    try:
        raw = Path(events_path).read_text()
        for block in raw.split('---'):
            block = block.strip()
            if not block:
                continue
            event = {}
            for line in block.splitlines():
                if ':' in line:
                    key, val = line.split(':', 1)
                    event[key.strip()] = val.strip()
            if event:
                events.append(event)
    except Exception:
        pass
    return events


def query_item_body(project_dir, item_id):
    conn = get_conn(project_dir)
    if not conn:
        return None
    row = conn.execute("SELECT source_path FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if not row or not row['source_path']:
        return None
    source = Path(project_dir) / row['source_path']
    if not source.exists():
        return None
    try:
        raw = source.read_text(encoding='utf-8-sig')
        normalized = raw.lstrip('﻿').replace('\r\n', '\n').replace('\r', '\n')
        parts = normalized.split('---', 2)
        if len(parts) < 3:
            return None
        body = parts[2].strip()
        extra = {}
        if yaml:
            try:
                fm = yaml.safe_load(parts[1])
                if isinstance(fm, dict):
                    for key in ('supersedes', 'blocked_reason', 'hold_reason', 'on_hold_reason'):
                        if fm.get(key):
                            extra[key] = fm[key]
            except Exception:
                pass
        return {'body': body, 'extra': extra}
    except Exception:
        return None


VALID_PRIORITIES = frozenset({'P0', 'P1', 'P2', 'P3'})
MUTABLE_FIELDS = frozenset({'status', 'priority', 'epic', 'epic_sequence'})


def _resolve_source_path(project_dir, item_id):
    conn = get_conn(project_dir)
    if not conn:
        return None
    row = conn.execute("SELECT source_path FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if not row or not row['source_path']:
        return None
    path = Path(project_dir) / row['source_path']
    return path if path.exists() else None


def _rebuild_cache(project_dir):
    try:
        from cache import rebuild
        rebuild(str(project_dir))
        return True
    except Exception as e:
        print(f"WARNING: cache rebuild failed after write: {e}", file=sys.stderr)
        return False


def _append_field_audit(project_dir, actor, item_id, filepath, field, old_val, new_val):
    from status import _audit_log_path
    log_path = _audit_log_path(Path(project_dir))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import datetime as _dt
    entry = {
        "ts": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": actor,
        "entity": item_id,
        "file": filepath,
        "field": field,
        "old": str(old_val) if old_val is not None else "",
        "new": str(new_val),
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _write_field(project_dir, item_id, field, value, actor):
    source = _resolve_source_path(project_dir, item_id)
    if not source:
        return {"error": f"Item {item_id} not found or source file missing"}

    from status import _parse_frontmatter, _atomic_write_frontmatter
    from schema import validate_frontmatter, normalize_status

    raw = source.read_text(encoding="utf-8-sig")
    try:
        fm, _fm_text, body = _parse_frontmatter(raw)
    except ValueError as e:
        return {"error": str(e)}

    fm_check = dict(fm)
    fm_check["status"] = normalize_status(fm_check.get("status", ""))
    violations = validate_frontmatter(fm_check)
    if violations:
        return {"error": f"Cannot write to structurally invalid file: {'; '.join(violations)}"}

    old_val = fm.get(field)
    fm[field] = value
    fm["updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    _atomic_write_frontmatter(source, fm, body)

    try:
        rel_path = str(source.relative_to(project_dir))
    except ValueError:
        rel_path = str(source)

    _append_field_audit(project_dir, actor, item_id, rel_path, field, old_val, value)
    _rebuild_cache(project_dir)

    return {"ok": True, "id": item_id, "field": field, "old": old_val, "new": value}


def handle_update(project_dir, payload):
    item_id = payload.get("id", "").strip()
    field = payload.get("field", "").strip()
    value = payload.get("value")
    actor = payload.get("actor", "dashboard").strip()

    if not item_id:
        return {"error": "Missing 'id'"}
    if field not in MUTABLE_FIELDS:
        return {"error": f"Field '{field}' is not mutable. Allowed: {sorted(MUTABLE_FIELDS)}"}

    if field == "status":
        src_path = _resolve_source_path(project_dir, item_id)
        if not src_path:
            return {"error": f"Item {item_id} not found"}
        new_status = str(value).strip()
        from status import validate, TERMINAL_STATUSES as TS, write_status, set_terminal
        from status import _parse_frontmatter
        if not validate(new_status):
            return {"error": f"Invalid status: {new_status!r}"}
        raw = src_path.read_text(encoding="utf-8-sig")
        try:
            fm, _, _ = _parse_frontmatter(raw)
            old_status = fm.get("status", "")
        except ValueError:
            old_status = ""
        try:
            if new_status in TS:
                set_terminal(str(src_path), new_status, actor, project_dir=str(project_dir), source="manual")
            else:
                write_status(str(src_path), new_status, actor, project_dir=str(project_dir), source="manual")
            return {"ok": True, "id": item_id, "field": "status", "old": old_status, "new": new_status}
        except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as e:
            return {"error": str(e)}

    if field == "priority":
        if value not in VALID_PRIORITIES:
            return {"error": f"Invalid priority: {value!r}. Valid: {sorted(VALID_PRIORITIES)}"}
        return _write_field(project_dir, item_id, "priority", value, actor)

    if field == "epic":
        if value is not None and not isinstance(value, str):
            return {"error": f"Epic must be a string, got {type(value).__name__}"}
        epic_val = (value or "").strip()
        if epic_val:
            conn = get_conn(project_dir)
            if conn:
                row = conn.execute("SELECT id FROM items WHERE id=? AND type='epic'", (epic_val,)).fetchone()
                conn.close()
                if not row:
                    return {"error": f"Epic {epic_val!r} does not exist"}
            else:
                return {"error": "Cache unavailable — cannot validate epic"}
        return _write_field(project_dir, item_id, "epic", epic_val, actor)

    if field == "epic_sequence":
        try:
            seq = int(value)
        except (TypeError, ValueError):
            return {"error": f"epic_sequence must be an integer, got {value!r}"}
        return _write_field(project_dir, item_id, "epic_sequence", seq, actor)

    return {"error": f"Unhandled field: {field}"}


def build_api_data(project_dir):
    all_items = query_all_items(project_dir)

    types = {}
    statuses = {}
    for item in all_items:
        t = item['type']
        if t not in types:
            types[t] = {'total': 0, 'done': 0, 'active': 0, 'new': 0, 'blocked': 0, 'other': 0}
        types[t]['total'] += 1
        s = item.get('status', 'new')
        if s in TERMINAL_STATUSES:
            types[t]['done'] += 1
        elif s == 'active':
            types[t]['active'] += 1
        elif s == 'new':
            types[t]['new'] += 1
        elif s == 'blocked':
            types[t]['blocked'] += 1
        else:
            types[t]['other'] += 1
        statuses[s] = statuses.get(s, 0) + 1

    return {
        'items': all_items,
        'summary': types,
        'status_counts': statuses,
        'roadmap': query_roadmap(project_dir),
        'dependencies': query_dependencies(project_dir),
        'git': {
            'status': query_git_status(project_dir),
            'commits': query_git_log(project_dir),
        },
        'events': query_events(project_dir),
        'generated_at': datetime.utcnow().isoformat() + 'Z',
    }


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SweetClaude Dashboard</title>
<style>
:root {
  --bg: #1a1a2e;
  --surface: #16213e;
  --surface-raised: #1c2a4a;
  --border: #2a3a5c;
  --text: #c8d0e0;
  --text-dim: #7a8599;
  --text-bright: #e8edf5;
  --accent: #4a9eff;
  --accent-dim: #2d6bc4;
  --green: #4ecdc4;
  --green-dim: #2a8a84;
  --amber: #e8a838;
  --red: #e05555;
  --purple: #9b72cf;
  --mono: 'SF Mono', 'Cascadia Code', 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  height: 100vh;
  margin: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 100;
  flex-shrink: 0;
}

.header h1 {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-bright);
  letter-spacing: 0.02em;
}

.header h1 span { color: var(--accent); font-weight: 600; }

.header-meta {
  font-size: 12px;
  color: var(--text-dim);
  font-family: var(--mono);
  display: flex;
  gap: 16px;
  align-items: center;
}

.branch-badge {
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
}

.main { max-width: 100%; padding: 24px; }

.summary-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.summary-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.summary-card .label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  margin-bottom: 4px;
}

.summary-card .value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-bright);
  font-family: var(--mono);
}

.summary-card .breakdown {
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 4px;
  font-family: var(--mono);
}

.controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.controls input[type="text"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  font-family: var(--sans);
  width: 240px;
  outline: none;
  transition: border-color 0.15s;
}

.controls input[type="text"]:focus { border-color: var(--accent); }

.controls select {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  font-family: var(--sans);
  outline: none;
  cursor: pointer;
}

.pill-group { display: flex; gap: 4px; }

.pill {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-dim);
  transition: all 0.15s;
  user-select: none;
}

.pill:hover { border-color: var(--accent-dim); color: var(--text); }
.pill.active { background: var(--accent-dim); border-color: var(--accent); color: var(--text-bright); }

.tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}

.tab {
  padding: 10px 20px;
  font-size: 13px;
  color: var(--text-dim);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
  user-select: none;
}

.tab:hover { color: var(--text); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.tab-count {
  background: var(--surface-raised);
  border-radius: 10px;
  padding: 1px 7px;
  font-size: 11px;
  margin-left: 6px;
  font-family: var(--mono);
}

.panel { display: none; }
.panel.active { display: block; }

.item-table {
  width: 100%;
  border-collapse: collapse;
}

.item-table th {
  text-align: left;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.item-table th:hover { color: var(--text); }
.item-table th .sort-arrow { margin-left: 4px; font-size: 10px; }

.item-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  vertical-align: top;
}

.item-table tr { cursor: pointer; transition: background 0.1s; }
.item-table tr:hover { background: var(--surface-raised); }

.id-cell {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 500;
  color: var(--accent);
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 500;
}

.status-done { background: rgba(78,205,196,0.15); color: var(--green); }
.status-active { background: rgba(74,158,255,0.15); color: var(--accent); }
.status-new { background: rgba(200,208,224,0.1); color: var(--text-dim); }
.status-ready { background: rgba(200,208,224,0.15); color: var(--text); }
.status-in-review { background: rgba(155,114,207,0.15); color: var(--purple); }
.status-blocked { background: rgba(224,85,85,0.15); color: var(--red); }
.status-on-hold { background: rgba(232,168,56,0.15); color: var(--amber); }
.status-deferred { background: rgba(200,208,224,0.1); color: var(--text-dim); font-style: italic; }
.status-declined { background: rgba(200,208,224,0.1); color: var(--text-dim); text-decoration: line-through; }
.status-abandoned { background: rgba(200,208,224,0.1); color: var(--text-dim); text-decoration: line-through; }
.status-superseded { background: rgba(200,208,224,0.1); color: var(--text-dim); font-style: italic; }
.status-unknown { background: rgba(224,85,85,0.1); color: var(--red); }

.priority-badge {
  font-size: 11px;
  font-family: var(--mono);
}
.pri-P0 { color: var(--red); font-weight: 600; }
.pri-P1 { color: var(--amber); font-weight: 500; }
.pri-P2 { color: var(--text); }
.pri-P3 { color: var(--text-dim); font-style: italic; }

.type-badge {
  font-size: 11px;
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.type-story { color: var(--accent); }
.type-enhancement { color: var(--accent); }
.type-bug { color: var(--red); }
.type-debt { color: var(--amber); }
.type-chore { color: var(--text-dim); }
.type-epic { color: var(--purple); }
.type-milestone { color: var(--green); }

.app-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.app-layout > .main {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
  transition: none;
}
.detail-overlay {
  display: none;
  position: relative;
  width: 480px;
  min-width: 300px;
  max-width: 70vw;
  background: var(--surface);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  flex-shrink: 0;
}
.detail-overlay.open { display: flex; flex-direction: column; }
.detail-resize-handle {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 5px;
  cursor: col-resize;
  z-index: 210;
}
.detail-resize-handle:hover,
.detail-resize-handle.dragging {
  background: var(--accent);
}

.detail-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.detail-eyebrow {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-eyebrow-id {
  font-size: 13px;
  font-family: var(--mono);
  color: var(--accent);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.detail-header-title {
  font-size: 16px;
  color: var(--text-bright);
  margin-top: 6px;
  font-weight: 500;
  line-height: 1.3;
}

.detail-close {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 20px;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  flex-shrink: 0;
}

.detail-close:hover { color: var(--text); }

.detail-body { padding: 0 24px 20px; }

.detail-section {
  border-bottom: 1px solid var(--border);
}

.detail-section > summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 0;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  cursor: pointer;
  list-style: none;
  user-select: none;
}

.detail-section > summary::-webkit-details-marker { display: none; }

.detail-section > summary::before {
  content: '▶';
  font-size: 9px;
  color: var(--accent);
  transition: transform 0.15s ease;
  display: inline-block;
}

.detail-section[open] > summary::before {
  transform: rotate(90deg);
}

.detail-section > .section-content {
  padding: 0 0 12px;
}

.detail-field {
  margin-bottom: 12px;
}

.detail-field .field-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  margin-bottom: 4px;
}

.detail-field .field-value {
  font-size: 13px;
  color: var(--text-bright);
}

.detail-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.criteria-list {
  list-style: none;
  padding: 0;
}

.criteria-list li {
  padding: 6px 0;
  font-size: 13px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.criteria-list li::before {
  flex-shrink: 0;
  font-size: 14px;
  line-height: 1.4;
}

.criteria-done::before { content: '\2713'; color: var(--green); }
.criteria-pending::before { content: '\00B7'; color: var(--text-dim); }

.commit-list {
  list-style: none;
  padding: 0;
}

.commit-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.commit-sha {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--accent);
}

.commit-date {
  font-size: 11px;
  color: var(--text-dim);
  margin-left: 8px;
}

.commit-msg { margin-top: 2px; }

.commit-ids {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.commit-id-tag {
  font-family: var(--mono);
  font-size: 10px;
  background: rgba(74,158,255,0.1);
  color: var(--accent);
  padding: 1px 6px;
  border-radius: 3px;
}

.event-timeline {
  list-style: none;
  padding: 0;
}

.event-item {
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 12px;
  font-size: 12px;
}

.event-time {
  font-family: var(--mono);
  color: var(--text-dim);
  white-space: nowrap;
  flex-shrink: 0;
}

.event-skill { color: var(--purple); font-family: var(--mono); }

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-dim);
  font-size: 14px;
}

.roadmap-section { margin-bottom: 24px; }

.release-header {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px 8px 0 0;
  padding: 14px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.release-header.standalone { border-radius: 8px; }

.release-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-bright);
  display: flex;
  align-items: center;
  gap: 10px;
}

.release-title .release-id {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-dim);
  font-weight: 400;
}

.current-badge {
  font-size: 10px;
  font-family: var(--mono);
  background: rgba(74,158,255,0.15);
  color: var(--accent);
  padding: 2px 8px;
  border-radius: 10px;
  letter-spacing: 0.04em;
}

.source-badge {
  font-size: 10px;
  font-family: var(--mono);
  padding: 2px 8px;
  border-radius: 10px;
  letter-spacing: 0.04em;
  color: var(--text-dim);
}

.source-manual {
  background: rgba(224,170,85,0.15);
  color: var(--yellow, #e0aa55);
}

.release-meta {
  font-size: 12px;
  font-family: var(--mono);
  color: var(--text-dim);
  display: flex;
  gap: 16px;
  align-items: center;
}

.epic-tree {
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 8px 8px;
  overflow: hidden;
}

.epic-node {
  padding: 14px 20px 14px 32px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.1s;
  position: relative;
}

.epic-node:last-child { border-bottom: none; }
.epic-node:hover { background: var(--surface-raised); }

.epic-node::before {
  content: '';
  position: absolute;
  left: 16px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--border);
}

.epic-node:last-child::before { bottom: 50%; }

.epic-node::after {
  content: '';
  position: absolute;
  left: 16px;
  top: 22px;
  width: 8px;
  height: 2px;
  background: var(--border);
}

.epic-header-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.epic-id {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--purple);
  font-weight: 500;
  flex-shrink: 0;
}

.epic-title-text {
  font-size: 13px;
  color: var(--text-bright);
  font-weight: 500;
}

.epic-stats {
  font-size: 11px;
  font-family: var(--mono);
  color: var(--text-dim);
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.progress-bar {
  width: 80px;
  height: 4px;
  background: var(--surface-raised);
  border-radius: 2px;
  overflow: hidden;
  flex-shrink: 0;
}

.progress-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s;
}

.progress-fill.green { background: var(--green); }
.progress-fill.amber { background: var(--amber); }
.progress-fill.blue { background: var(--accent); }

.story-toggle {
  font-size: 11px;
  color: var(--accent-dim);
  cursor: pointer;
  user-select: none;
  padding: 2px 0;
  margin-top: 4px;
  display: inline-block;
}

.story-toggle:hover { color: var(--accent); }

.story-rows {
  display: none;
  margin-top: 8px;
  margin-left: 4px;
  border-left: 1px solid var(--border);
  padding-left: 12px;
}

.story-rows.expanded { display: block; }

.story-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 12px;
  cursor: pointer;
}

.story-row:hover { color: var(--text-bright); }
.story-row:hover .drag-handle { opacity: 1; }

.story-row .story-id {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--accent);
  flex-shrink: 0;
  width: 80px;
}

.story-row .story-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.done-check { color: var(--green); font-size: 12px; }

.unlinked-summary {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-top: 24px;
  font-size: 13px;
  color: var(--text-dim);
}

.unlinked-summary strong { color: var(--text); font-family: var(--mono); }

.blocker-count {
  color: var(--red);
  font-weight: 500;
  font-family: var(--mono);
  font-size: 11px;
}

.horizon-group {
  margin-bottom: 20px;
}

.horizon-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-bright);
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.horizon-header .horizon-count {
  font-size: 11px;
  font-family: var(--mono);
  color: var(--text-dim);
  font-weight: 400;
}

.dep-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
}

.dep-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 12px;
}

.dep-chain {
  font-family: var(--mono);
  font-size: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.dep-chain:last-child { border-bottom: none; }

.dep-arrow { color: var(--text-dim); }

.dep-unresolved {
  color: var(--red);
  font-family: var(--mono);
  font-size: 12px;
  padding: 4px 0;
}

.release-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}

.release-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.release-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-bright);
}

.release-epic-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.release-epic-row:last-child { border-bottom: none; }

.release-blockers {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.release-blockers-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--red);
  margin-bottom: 8px;
}

.blocker-item {
  font-size: 12px;
  padding: 4px 0;
  display: flex;
  gap: 8px;
  align-items: center;
}

.release-progress {
  margin-top: 12px;
  font-size: 12px;
  font-family: var(--mono);
  color: var(--text-dim);
}

@media (max-width: 768px) {
  .summary-row { grid-template-columns: repeat(2, 1fr); }
  .app-layout { flex-direction: column; }
  .detail-overlay { width: 100% !important; max-width: 100%; min-width: 0; border-left: none; border-top: 1px solid var(--border); }
  .detail-resize-handle { display: none; }
  .controls { flex-direction: column; }
  .controls input[type="text"] { width: 100%; }
  .epic-node { padding-left: 24px; }
}
.dnd-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  z-index: 9999;
  opacity: 1;
  transition: opacity 0.4s;
  pointer-events: none;
}
.dnd-toast.success { background: var(--green); color: #000; }
.dnd-toast.error { background: var(--red); color: #fff; }
.dnd-toast.fade { opacity: 0; }

.backlog-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  cursor: pointer;
}
.backlog-row:hover { background: var(--surface-raised); }
.backlog-row .backlog-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 360px;
}
.backlog-row .backlog-epic {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--purple);
}

.sortable-ghost {
  opacity: 0.3;
}
.sortable-chosen {
  cursor: grabbing;
}
.drag-handle {
  cursor: grab;
  opacity: 0.3;
  font-size: 14px;
  user-select: none;
}
.backlog-row:hover .drag-handle { opacity: 1; }
</style>
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
</head>
<body>
<div class="header">
  <h1><span>SweetClaude</span> Dashboard</h1>
  <div class="header-meta">
    <span class="branch-badge" id="branch-badge"></span>
    <span id="generated-at"></span>
  </div>
</div>

<div class="app-layout">
<div class="main">
  <div class="summary-row" id="summary-row"></div>

  <div class="controls" id="controls-bar">
    <input type="text" id="search" placeholder="Filter by ID, title, tag...">
    <select id="status-filter">
      <option value="active">Active items</option>
      <option value="all">All items</option>
      <option value="done">Done only</option>
    </select>
    <select id="type-filter">
      <option value="all">All types</option>
      <option value="story">Stories</option>
      <option value="enhancement">Enhancements</option>
      <option value="bug">Bugs</option>
      <option value="debt">Debt</option>
      <option value="chore">Chores</option>
    </select>
    <div class="pill-group" id="sort-pills">
      <span class="pill active" data-sort="priority">Priority</span>
      <span class="pill" data-sort="id">ID</span>
      <span class="pill" data-sort="status">Status</span>
      <span class="pill" data-sort="type">Type</span>
      <span class="pill" data-sort="updated">Updated</span>
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" data-panel="roadmap">Roadmap <span class="tab-count" id="roadmap-count">0</span></div>
    <div class="tab" data-panel="releases">Releases <span class="tab-count" id="releases-count">0</span></div>
    <div class="tab" data-panel="epics">Epics <span class="tab-count" id="epics-count">0</span></div>
    <div class="tab" data-panel="backlog">Backlog <span class="tab-count" id="backlog-count">0</span></div>
    <div class="tab" data-panel="dependencies">Dependencies <span class="tab-count" id="dependencies-count">0</span></div>
    <div class="tab" data-panel="git">Git <span class="tab-count" id="git-count">0</span></div>
    <div class="tab" data-panel="activity">Activity <span class="tab-count" id="activity-count">0</span></div>
  </div>

  <div class="panel active" id="panel-roadmap"></div>

  <div class="panel" id="panel-releases"></div>

  <div class="panel" id="panel-epics">
    <table class="item-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Title</th>
          <th>Status</th>
          <th>Source</th>
          <th>Milestone</th>
          <th>Criteria</th>
          <th>Issues</th>
        </tr>
      </thead>
      <tbody id="epics-body"></tbody>
    </table>
  </div>

  <div class="panel" id="panel-backlog"></div>

  <div class="panel" id="panel-dependencies"></div>

  <div class="panel" id="panel-git">
    <ul class="commit-list" id="git-body"></ul>
  </div>

  <div class="panel" id="panel-activity">
    <ul class="event-timeline" id="activity-body"></ul>
  </div>
</div>

<div class="detail-overlay" id="detail-overlay">
  <div class="detail-resize-handle" id="detail-resize-handle"></div>
  <div class="detail-header">
    <div>
      <div class="detail-eyebrow" id="detail-eyebrow"></div>
      <div class="detail-header-title" id="detail-title"></div>
    </div>
    <button class="detail-close" onclick="closeDetail()">&times;</button>
  </div>
  <div class="detail-body" id="detail-body"></div>
</div>
</div><!-- /app-layout -->

<script>
let DATA = null;
let currentSort = 'priority';
const PRIORITY_ORDER = {P0: 0, now: 0, P1: 1, sooner: 1, P2: 2, soon: 2, P3: 3, later: 3, someday: 4};
const STATUS_ORDER = {blocked: 0, 'on-hold': 1, active: 2, 'in-review': 3, ready: 4, 'new': 5, deferred: 6, done: 7, declined: 8, abandoned: 9, superseded: 10};
const TERMINAL = new Set(['done', 'declined', 'abandoned', 'superseded']);
const HORIZON_LABELS = {P0: 'Now (P0)', P1: 'Sooner (P1)', P2: 'Soon (P2)', P3: 'Later (P3)', none: 'Unscheduled'};

async function load() {
  const resp = await fetch('/api/data');
  DATA = await resp.json();
  render();
}

function render() {
  renderSummary();
  renderRoadmap();
  renderReleases();
  renderBacklog();
  renderEpics();
  renderDependencies();
  renderGit();
  renderActivity();
  document.getElementById('branch-badge').textContent = DATA.git.status.branch;
  document.getElementById('generated-at').textContent = DATA.generated_at.replace('T',' ').split('.')[0] + ' UTC';
}

function renderSummary() {
  const row = document.getElementById('summary-row');
  const s = DATA.summary;
  const sc = DATA.status_counts || {};
  const total = Object.values(s).reduce((a, t) => a + t.total, 0);
  const done = Object.values(s).reduce((a, t) => a + t.done, 0);
  const active = Object.values(s).reduce((a, t) => a + t.active, 0);
  const blocked = Object.values(s).reduce((a, t) => a + t.blocked, 0);
  const open = total - done;
  row.innerHTML = `
    <div class="summary-card">
      <div class="label">Total Items</div>
      <div class="value">${total}</div>
      <div class="breakdown">${done} done, ${open} open</div>
    </div>
    <div class="summary-card">
      <div class="label">Active</div>
      <div class="value">${active}</div>
    </div>
    <div class="summary-card">
      <div class="label">Blocked</div>
      <div class="value" style="color:${blocked > 0 ? 'var(--red)' : 'var(--text-bright)'}">${blocked}</div>
    </div>
    <div class="summary-card">
      <div class="label">Epics</div>
      <div class="value">${s.epic?.total || 0}</div>
      <div class="breakdown">${s.epic?.done || 0} done</div>
    </div>
    <div class="summary-card">
      <div class="label">Issues</div>
      <div class="value">${(s.story?.total||0) + (s.enhancement?.total||0) + (s.bug?.total||0) + (s.debt?.total||0) + (s.chore?.total||0)}</div>
      <div class="breakdown">${(s.story?.done||0) + (s.enhancement?.done||0) + (s.bug?.done||0) + (s.debt?.done||0) + (s.chore?.done||0)} done</div>
    </div>
    <div class="summary-card">
      <div class="label">Commits</div>
      <div class="value">${DATA.git.commits.length}</div>
      <div class="breakdown">${DATA.git.status.changed_files} uncommitted</div>
    </div>
  `;
}

function renderRoadmap() {
  const rm = DATA.roadmap;
  const panel = document.getElementById('panel-roadmap');
  const totalEpics = rm.milestones.reduce((a, r) => a + r.epics.length, 0) + rm.orphan_epics.length;
  document.getElementById('roadmap-count').textContent = rm.milestones.length + ' ms / ' + totalEpics + ' ep';

  if (!rm.milestones.length && !rm.orphan_epics.length) {
    panel.innerHTML = '<div class="empty-state">No roadmap configured. Create milestones and epics to build your roadmap.</div>';
    return;
  }

  let html = '';
  for (const ms of rm.milestones) {
    const isCurrent = ms.status === 'active';
    const isDone = TERMINAL.has(ms.status);
    const totalStories = ms.epics.reduce((a, e) => a + e.stories.length, 0);
    const doneStories = ms.epics.reduce((a, e) => a + e.stories.filter(s => TERMINAL.has(s.status)).length, 0);

    html += `<div class="roadmap-section">`;
    html += `<div class="release-header${ms.epics.length ? '' : ' standalone'}">`;
    html += `<div class="release-title">`;
    html += `<span class="release-id">${ms.id}</span> ${esc(ms.title)}`;
    if (isDone) html += ` <span class="done-check">&#10003;</span>`;
    if (isCurrent) html += ` <span class="current-badge">current</span>`;
    html += ` ${sourceBadge(ms.source, ms.status, ms.derived_status)}`;
    html += `</div>`;
    html += `<div class="release-meta">`;
    html += `${statusBadge(ms.status)}`;
    if (totalStories > 0) html += `<span>${doneStories}/${totalStories} issues</span>`;
    html += `</div></div>`;

    if (ms.epics.length) {
      html += `<div class="epic-tree">`;
      html += ms.epics.map((ep, i) => renderEpicNode(ep, i, ms.id)).join('');
      html += `</div>`;
    }
    html += `</div>`;
  }

  if (rm.orphan_epics.length) {
    html += `<div class="roadmap-section">`;
    html += `<div class="release-header standalone">`;
    html += `<div class="release-title">Unassigned Epics</div>`;
    html += `<div class="release-meta"><span>${rm.orphan_epics.length} epic${rm.orphan_epics.length > 1 ? 's' : ''}</span></div>`;
    html += `</div>`;
    html += `<div class="epic-tree">`;
    html += rm.orphan_epics.map((ep, i) => renderEpicNode(ep, i, 'orphan')).join('');
    html += `</div></div>`;
  }

  if (rm.unlinked_open > 0) {
    html += `<div class="unlinked-summary">`;
    html += `<strong>${rm.unlinked_open}</strong> open items not linked to any epic`;
    html += `</div>`;
  }

  panel.innerHTML = html;
}

function renderReleases() {
  const rm = DATA.roadmap;
  const panel = document.getElementById('panel-releases');
  document.getElementById('releases-count').textContent = rm.milestones.length;

  if (!rm.milestones.length) {
    panel.innerHTML = '<div class="empty-state">No milestones configured.</div>';
    return;
  }

  let html = '';
  for (const ms of rm.milestones) {
    const totalIssues = ms.epics.reduce((a, e) => a + e.stories.length, 0);
    const doneIssues = ms.epics.reduce((a, e) => a + e.stories.filter(s => TERMINAL.has(s.status)).length, 0);
    const epicsDone = ms.epics.filter(e => TERMINAL.has(e.status)).length;
    const blockers = [];
    for (const ep of ms.epics) {
      for (const s of ep.stories) {
        if (s.status === 'blocked' || s.status === 'on-hold') {
          blockers.push({...s, epicId: ep.id});
        }
      }
    }

    html += `<div class="release-card">`;
    html += `<div class="release-card-header">`;
    html += `<div class="release-card-title"><span class="id-cell" style="margin-right:8px">${ms.id}</span>${esc(ms.title)}</div>`;
    html += `<div>${statusBadge(ms.status)} ${sourceBadge(ms.source, ms.status, ms.derived_status)}</div>`;
    html += `</div>`;

    for (const ep of ms.epics) {
      const sd = ep.stories.filter(s => TERMINAL.has(s.status)).length;
      const st = ep.stories.length;
      const blockerCount = ep.stories.filter(s => s.status === 'blocked' || s.status === 'on-hold').length;
      html += `<div class="release-epic-row" onclick="showDetail('${ep.id}')" style="cursor:pointer">`;
      html += `<span class="epic-id">${ep.id}</span>`;
      html += `<span class="epic-title-text" style="flex:1">${esc(ep.title)}</span>`;
      html += `${statusBadge(ep.status)}`;
      html += `<span style="font-family:var(--mono);font-size:11px;color:var(--text-dim)">${ep.criteria_done}/${ep.criteria_total} criteria</span>`;
      if (blockerCount > 0) html += ` <span class="blocker-count">${blockerCount} blocked</span>`;
      html += `</div>`;
    }

    if (blockers.length > 0) {
      html += `<div class="release-blockers">`;
      html += `<div class="release-blockers-title">Blockers (${blockers.length})</div>`;
      for (const b of blockers.slice(0, 10)) {
        html += `<div class="blocker-item">`;
        html += `<span class="id-cell">${b.id}</span>`;
        html += `<span style="flex:1">${esc(b.title)}</span>`;
        html += `${statusBadge(b.status)}`;
        html += `<span style="font-size:11px;color:var(--purple)">${b.epicId}</span>`;
        html += `</div>`;
      }
      if (blockers.length > 10) html += `<div style="font-size:11px;color:var(--text-dim);padding:4px 0">(+${blockers.length - 10} more)</div>`;
      html += `</div>`;
    }

    html += `<div class="release-progress">${epicsDone}/${ms.epics.length} epics done &middot; ${doneIssues}/${totalIssues} issues done</div>`;
    html += `</div>`;
  }
  panel.innerHTML = html;
}

function renderEpicNode(ep, idx, relId) {
  const isDone = TERMINAL.has(ep.status);
  const openStories = ep.stories.filter(s => !TERMINAL.has(s.status));
  const doneStories = ep.stories.filter(s => TERMINAL.has(s.status));
  const blockerStories = ep.stories.filter(s => s.status === 'blocked' || s.status === 'on-hold');
  const pct = ep.criteria_total > 0 ? Math.round((ep.criteria_done / ep.criteria_total) * 100) : 0;
  const barColor = pct === 100 ? 'green' : pct > 50 ? 'blue' : 'amber';
  const uid = relId + '-' + ep.id;

  let html = `<div class="epic-node" onclick="showDetail('${ep.id}')">`;
  html += `<div class="epic-header-row">`;
  html += `<span class="epic-id">${ep.id}</span>`;
  html += `<span class="epic-title-text">${esc(ep.title)}</span>`;
  if (isDone) html += ` <span class="done-check">&#10003;</span>`;
  html += ` ${statusBadge(ep.status)}`;
  html += ` ${sourceBadge(ep.source, ep.status, ep.derived_status)}`;
  html += `</div>`;

  html += `<div class="epic-stats">`;
  if (ep.criteria_total > 0) {
    html += `<span>Criteria: ${ep.criteria_done}/${ep.criteria_total}</span>`;
    html += `<div class="progress-bar"><div class="progress-fill ${barColor}" style="width:${pct}%"></div></div>`;
  }
  if (ep.stories.length > 0) {
    html += `<span>${openStories.length} open, ${doneStories.length} done</span>`;
  }
  if (blockerStories.length > 0) {
    html += `<span class="blocker-count">${blockerStories.length} blocked</span>`;
  }
  html += `</div>`;

  if (ep.stories.length > 0) {
    const visibleStories = openStories.slice(0, 20);
    const hiddenOpen = openStories.length - visibleStories.length;
    html += `<span class="story-toggle" onclick="event.stopPropagation(); toggleStories('${uid}')">${ep.stories.length} ${ep.stories.length === 1 ? 'issue' : 'issues'} &rsaquo;</span>`;
    html += `<div class="story-rows dnd-stories" id="stories-${uid}" data-epic="${ep.id}">`;
    html += visibleStories.map(s => {
      return `<div class="story-row" data-id="${s.id}" onclick="event.stopPropagation(); showDetail('${s.id}')">
        <span class="drag-handle" style="font-size:12px">&#x2630;</span>
        <span class="story-id">${s.id}</span>
        <span class="story-title">${esc(s.title)}</span>
        ${statusBadge(s.status)}
        ${s.priority ? priorityBadge(s.priority) : ''}
      </div>`;
    }).join('');
    if (hiddenOpen > 0) html += `<div style="font-size:11px;color:var(--text-dim);padding:4px 0">(+${hiddenOpen} more open)</div>`;
    if (doneStories.length > 0) html += `<div style="font-size:11px;color:var(--green-dim);padding:4px 0">(+${doneStories.length} done, not shown)</div>`;
    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

function toggleStories(uid) {
  const el = document.getElementById('stories-' + uid);
  if (el) el.classList.toggle('expanded');
}

function getFiltered() {
  const search = document.getElementById('search').value.toLowerCase();
  const statusFilter = document.getElementById('status-filter').value;
  const typeFilter = document.getElementById('type-filter').value;

  return DATA.items.filter(item => {
    if (typeFilter !== 'all' && item.type !== typeFilter) return false;
    if (statusFilter === 'active' && TERMINAL.has(item.status)) return false;
    if (statusFilter === 'done' && !TERMINAL.has(item.status)) return false;
    if (search) {
      const haystack = [item.id, item.title, item.epic, ...(item.tags||[])].join(' ').toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });
}

function sortItems(items) {
  return items.slice().sort((a, b) => {
    switch (currentSort) {
      case 'priority':
        return (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9) || a.id.localeCompare(b.id);
      case 'status':
        return (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9) || a.id.localeCompare(b.id);
      case 'type':
        return a.type.localeCompare(b.type) || a.id.localeCompare(b.id);
      case 'updated':
        return (b.updated || '').localeCompare(a.updated || '');
      default:
        return a.id.localeCompare(b.id);
    }
  });
}

function statusBadge(s) {
  const cls = {
    done:'done', active:'active', new:'new', ready:'ready',
    'in-review':'in-review', blocked:'blocked', 'on-hold':'on-hold',
    deferred:'deferred', declined:'declined', abandoned:'abandoned',
    superseded:'superseded'
  }[s] || 'unknown';
  return `<span class="status-badge status-${cls}">${s}</span>`;
}

function sourceBadge(source, status, derived) {
  const s = source || 'auto';
  if (s === 'manual' && derived && status !== derived) {
    return `<span class="source-badge source-manual" title="Children suggest: ${derived}">manual</span>`;
  }
  if (s === 'manual') return `<span class="source-badge source-manual">manual</span>`;
  return `<span class="source-badge">auto</span>`;
}

function priorityBadge(p) {
  if (!p) return '<span class="priority-badge">-</span>';
  return `<span class="priority-badge pri-${p}">${p}</span>`;
}

function typeBadge(t) {
  return `<span class="type-badge type-${t}">${t}</span>`;
}

function renderBacklog() {
  const items = sortItems(getFiltered().filter(i => !['epic','milestone'].includes(i.type)));
  document.getElementById('backlog-count').textContent = items.length;
  const panel = document.getElementById('panel-backlog');

  const horizons = {};
  for (const item of items) {
    const h = item.priority || 'none';
    if (!horizons[h]) horizons[h] = [];
    horizons[h].push(item);
  }

  const order = ['P0', 'now', 'P1', 'sooner', 'P2', 'soon', 'P3', 'later', 'someday', 'none'];
  let html = '';
  for (const h of order) {
    if (!horizons[h] || horizons[h].length === 0) continue;
    const label = HORIZON_LABELS[h] || h;
    const group = horizons[h];
    group.sort((a, b) => {
      const sa = a.epic_sequence ?? 9999, sb = b.epic_sequence ?? 9999;
      return sa - sb || a.id.localeCompare(b.id);
    });
    html += `<div class="horizon-group">`;
    html += `<div class="horizon-header">${label} <span class="horizon-count">${group.length} items</span></div>`;
    html += `<div class="dnd-container" data-priority="${h}">`;
    html += group.map(i => `
      <div class="backlog-row" data-id="${i.id}" onclick="showDetail('${i.id}')">
        <span class="drag-handle">&#x2630;</span>
        <span class="id-cell">${i.id}</span>
        ${typeBadge(i.type)}
        <span class="backlog-title">${esc(i.title)}</span>
        ${statusBadge(i.status)}
        ${priorityBadge(i.priority)}
        <span class="backlog-epic">${i.epic || ''}</span>
      </div>
    `).join('');
    html += `</div>`;
    html += `</div>`;
  }

  if (!html) html = '<div class="empty-state">No items in backlog.</div>';

  const unlinked = items.filter(i => !i.epic);
  const total = items.length;
  html += `<div style="font-size:12px;font-family:var(--mono);color:var(--text-dim);padding:12px 0">Total: ${total} items &middot; ${unlinked.length} unlinked (no epic)</div>`;

  panel.innerHTML = html;
}

function renderEpics() {
  const items = sortItems(getFiltered().filter(i => i.type === 'epic'));
  document.getElementById('epics-count').textContent = items.length;
  const tbody = document.getElementById('epics-body');
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No epics found.</td></tr>';
    return;
  }
  tbody.innerHTML = items.map(i => {
    const storiesDone = (i.stories||[]).filter(s => TERMINAL.has(s.status)).length;
    const storiesTotal = (i.stories||[]).length;
    return `
      <tr onclick="showDetail('${i.id}')">
        <td class="id-cell">${i.id}</td>
        <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(i.title)}</td>
        <td>${statusBadge(i.status)}</td>
        <td>${sourceBadge(i.source, i.status, i.derived_status)}</td>
        <td style="font-family:var(--mono);font-size:12px">${i.milestone || '-'}</td>
        <td style="font-family:var(--mono);font-size:12px">${i.criteria_done||0}/${i.criteria_total||0}</td>
        <td style="font-family:var(--mono);font-size:12px">${storiesDone}/${storiesTotal}</td>
      </tr>
    `;
  }).join('');
}

function renderDependencies() {
  const deps = DATA.dependencies;
  document.getElementById('dependencies-count').textContent = deps.edges.length;
  const panel = document.getElementById('panel-dependencies');

  if (!deps.edges.length) {
    panel.innerHTML = '<div class="empty-state">No dependencies defined. Add depends_on fields to issue frontmatter.</div>';
    return;
  }

  const graph = {};
  const reverseGraph = {};
  for (const e of deps.edges) {
    if (!graph[e.from]) graph[e.from] = [];
    graph[e.from].push(e.to);
    if (!reverseGraph[e.to]) reverseGraph[e.to] = [];
    reverseGraph[e.to].push(e.from);
  }

  const chains = [];
  const visited = new Set();
  function findChain(node, chain) {
    chain.push(node);
    visited.add(node);
    const deps_of = graph[node] || [];
    for (const dep of deps_of) {
      if (!visited.has(dep)) {
        findChain(dep, chain);
        return;
      }
    }
  }

  const roots = Object.keys(graph).filter(n => !reverseGraph[n] || reverseGraph[n].length === 0);
  const nonRoots = Object.keys(graph).filter(n => reverseGraph[n] && reverseGraph[n].length > 0);
  for (const r of [...roots, ...nonRoots]) {
    if (!visited.has(r)) {
      const chain = [];
      findChain(r, chain);
      if (chain.length > 1) chains.push(chain);
    }
  }

  const unresolved = deps.edges.filter(e => deps.items[e.to] && deps.items[e.to].title === '(not found)');

  let html = '';

  if (chains.length > 0) {
    html += `<div class="dep-section">`;
    html += `<div class="dep-section-title">Blocked Chains (${chains.length})</div>`;
    for (const chain of chains.slice(0, 15)) {
      html += `<div class="dep-chain">`;
      html += chain.map(id => {
        const item = deps.items[id];
        const cls = item ? `status-${item.status}` : 'status-unknown';
        return `<span class="id-cell" onclick="showDetail('${id}')" style="cursor:pointer">${id}</span><span class="status-badge ${cls}" style="font-size:10px">${item?.status || '?'}</span>`;
      }).join('<span class="dep-arrow"> &rarr; </span>');
      html += `</div>`;
    }
    if (chains.length > 15) html += `<div style="font-size:11px;color:var(--text-dim);padding:4px 0">(+${chains.length - 15} more chains)</div>`;
    html += `</div>`;
  }

  if (unresolved.length > 0) {
    html += `<div class="dep-section">`;
    html += `<div class="dep-section-title" style="color:var(--red)">Unresolved References (${unresolved.length})</div>`;
    for (const u of unresolved) {
      html += `<div class="dep-unresolved">${u.from} depends_on ${u.to} (not found)</div>`;
    }
    html += `</div>`;
  }

  html += `<div style="font-size:12px;font-family:var(--mono);color:var(--text-dim);padding:12px 0">${Object.keys(deps.items).length} items have dependencies &middot; ${chains.length} chains &middot; ${unresolved.length} unresolved</div>`;
  panel.innerHTML = html;
}

function renderGit() {
  document.getElementById('git-count').textContent = DATA.git.commits.length;
  const ul = document.getElementById('git-body');
  ul.innerHTML = DATA.git.commits.slice(0, 50).map(c => `
    <li class="commit-item">
      <span class="commit-sha">${c.short_sha}</span>
      <span class="commit-date">${formatDate(c.date)}</span>
      <div class="commit-msg">${esc(c.message)}</div>
      ${c.item_ids.length ? `<div class="commit-ids">${c.item_ids.map(id => `<span class="commit-id-tag">${id}</span>`).join('')}</div>` : ''}
    </li>
  `).join('');
}

function renderActivity() {
  const events = DATA.events.slice().reverse();
  document.getElementById('activity-count').textContent = events.length;
  const ul = document.getElementById('activity-body');
  if (!events.length) {
    ul.innerHTML = '<li class="empty-state">No skill events recorded.</li>';
    return;
  }
  ul.innerHTML = events.map(e => `
    <li class="event-item">
      <span class="event-time">${formatDate(e.timestamp)}</span>
      <span class="event-skill">${esc(e.skill || e.event)}</span>
      ${e.phase && e.phase !== 'none' ? `<span style="color:var(--text-dim)">[${e.phase}]</span>` : ''}
    </li>
  `).join('');
}

function showDetail(id) {
  const item = DATA.items.find(i => i.id === id);
  if (!item) return;

  const typeLabel = (item.type || '').toUpperCase().replace('-', ' ');
  let eyebrow = `<span class="detail-eyebrow-id">${typeLabel}: ${item.id}</span>`;
  eyebrow += statusBadge(item.status);
  if (item.type === 'epic' || item.type === 'milestone') {
    eyebrow += sourceBadge(item.source, item.status, item.derived_status);
  }
  if (item.priority) eyebrow += priorityBadge(item.priority);
  document.getElementById('detail-eyebrow').innerHTML = eyebrow;
  document.getElementById('detail-title').textContent = item.title;

  let html = '';

  // Details section
  let detailFields = '';
  if (item.epic) detailFields += `<div class="detail-field"><div class="field-label">Epic</div><div class="field-value"><span class="id-cell" style="cursor:pointer" onclick="showDetail('${item.epic}')">${item.epic}</span></div></div>`;
  if (item.milestone) detailFields += `<div class="detail-field"><div class="field-label">Milestone</div><div class="field-value" style="font-family:var(--mono)">${item.milestone}</div></div>`;
  if (item.depends_on?.length) {
    detailFields += `<div class="detail-field"><div class="field-label">Depends On</div><div class="field-value">${item.depends_on.map(d =>
      `<span class="id-cell" style="cursor:pointer;margin-right:8px" onclick="showDetail('${d}')">${d}</span>`
    ).join('')}</div></div>`;
  }
  if (item.effort) detailFields += `<div class="detail-field"><div class="field-label">Effort</div><div class="field-value" style="font-family:var(--mono)">${item.effort}</div></div>`;
  if (item.objective) detailFields += `<div class="detail-field"><div class="field-label">Objective</div><div class="field-value">${esc(item.objective)}</div></div>`;
  if (item.tags?.length) {
    detailFields += `<div class="detail-field"><div class="field-label">Tags</div><div class="field-value">${item.tags.map(t =>
      `<span style="background:var(--surface-raised);border-radius:4px;padding:2px 8px;font-size:11px;font-family:var(--mono);margin-right:4px">${t}</span>`
    ).join('')}</div></div>`;
  }
  function fmtDate(v) {
    if (!v) return '';
    if (v.includes('T')) {
      const d = new Date(v);
      return d.toISOString().replace('T', ' ').replace(/\\.\\d+Z$/, ' UTC');
    }
    return v + ' 00:00 UTC';
  }
  function completionTime(created, closed) {
    if (!created || !closed) return null;
    const c = new Date(created.includes('T') ? created : created + 'T00:00:00Z');
    const e = new Date(closed.includes('T') ? closed : closed + 'T00:00:00Z');
    const ms = e - c;
    if (ms < 0) return null;
    const totalMin = Math.floor(ms / 60000);
    const d = Math.floor(totalMin / 1440);
    const h = Math.floor((totalMin % 1440) / 60);
    const m = totalMin % 60;
    const parts = [];
    if (d) parts.push(d + 'd');
    if (h) parts.push(h + 'h');
    parts.push(m + 'm');
    return parts.join(', ');
  }
  const dateFields = [];
  if (item.created) dateFields.push(`<div class="detail-field"><div class="field-label">Created</div><div class="field-value" style="font-family:var(--mono);font-size:12px">${fmtDate(item.created)}</div></div>`);
  if (item.updated) dateFields.push(`<div class="detail-field"><div class="field-label">Updated</div><div class="field-value" style="font-family:var(--mono);font-size:12px">${fmtDate(item.updated)}</div></div>`);
  if (item.closed_date) dateFields.push(`<div class="detail-field"><div class="field-label">Closed</div><div class="field-value" style="font-family:var(--mono);font-size:12px">${fmtDate(item.closed_date)}</div></div>`);
  const ct = completionTime(item.created, item.closed_date);
  if (ct) dateFields.push(`<div class="detail-field"><div class="field-label">Completion Time</div><div class="field-value" style="font-family:var(--mono);font-size:12px">${ct}</div></div>`);
  if (dateFields.length) detailFields += `<div class="detail-meta-grid">${dateFields.join('')}</div>`;

  if (detailFields) {
    html += `<details class="detail-section" open><summary>Details</summary><div class="section-content">${detailFields}</div></details>`;
  }

  if (item.completion_criteria?.length) {
    html += `<details class="detail-section" open><summary>Completion Criteria (${item.criteria_done}/${item.criteria_total})</summary><div class="section-content">
      <ul class="criteria-list">${item.completion_criteria.map(c =>
        `<li class="${c.done ? 'criteria-done' : 'criteria-pending'}">${esc(c.criterion)}</li>`
      ).join('')}</ul></div></details>`;
  }

  if (item.stories?.length) {
    const nonDone = item.stories.filter(s => !TERMINAL.has(s.status));
    const doneCount = item.stories.length - nonDone.length;
    html += `<details class="detail-section" open><summary>Issues (${item.stories.filter(s=>TERMINAL.has(s.status)).length}/${item.stories.length} done)</summary><div class="section-content">
      <div class="dnd-stories" id="detail-stories" data-epic="${item.id}" style="margin-top:4px">${nonDone.map(s => `
        <div class="story-row" data-id="${s.id}" onclick="showDetail('${s.id}')" style="padding:6px 8px;border-bottom:1px solid var(--border)">
          <span class="drag-handle" style="font-size:12px">&#x2630;</span>
          <span class="id-cell">${s.id}</span>
          <span class="story-title">${esc(s.title)}</span>
          ${statusBadge(s.status)}
        </div>`).join('')}</div>`;
    if (doneCount > 0) html += `<div style="font-size:11px;color:var(--green-dim);padding:4px 0">(+${doneCount} done, not shown)</div>`;
    html += `</div></details>`;
  }

  const relatedCommits = DATA.git.commits.filter(c => c.item_ids.includes(item.id));
  if (relatedCommits.length) {
    html += `<details class="detail-section" open><summary>Git History (${relatedCommits.length})</summary><div class="section-content">
      <ul class="commit-list">${relatedCommits.map(c => `
        <li class="commit-item">
          <span class="commit-sha">${c.short_sha}</span>
          <span class="commit-date">${formatDate(c.date)}</span>
          <div class="commit-msg">${esc(c.message)}</div>
        </li>`).join('')}</ul></div></details>`;
  }

  html += `<details class="detail-section" open id="detail-desc-section"><summary>Description</summary><div class="section-content" id="detail-body-content">
    <div style="color:var(--text-dim);font-size:12px">Loading...</div>
  </div></details>`;

  document.getElementById('detail-body').innerHTML = html;
  document.getElementById('detail-overlay').classList.add('open');
  dndInitStories();

  fetch(`/api/body?id=${encodeURIComponent(id)}`)
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('detail-body-content');
      if (!el) return;
      let extra = '';
      if (data.extra) {
        if (data.extra.supersedes) extra += `<div class="detail-field"><div class="field-label">Supersedes</div><div class="field-value"><span class="id-cell" style="cursor:pointer" onclick="showDetail('${data.extra.supersedes}')">${data.extra.supersedes}</span></div></div>`;
        if (data.extra.blocked_reason) extra += `<div class="detail-field"><div class="field-label">Blocked Reason</div><div class="field-value" style="color:var(--red)">${esc(data.extra.blocked_reason)}</div></div>`;
        if (data.extra.hold_reason) extra += `<div class="detail-field"><div class="field-label">Hold Reason</div><div class="field-value" style="color:var(--amber)">${esc(data.extra.hold_reason)}</div></div>`;
        if (data.extra.on_hold_reason) extra += `<div class="detail-field"><div class="field-label">On-Hold Reason</div><div class="field-value" style="color:var(--amber)">${esc(data.extra.on_hold_reason)}</div></div>`;
      }
      if (data.body) {
        el.innerHTML = extra + `<div class="md-body">${renderMd(data.body)}</div>`;
      } else if (extra) {
        el.innerHTML = extra;
      } else {
        const section = document.getElementById('detail-desc-section');
        if (section) section.style.display = 'none';
      }
    })
    .catch(() => {
      const el = document.getElementById('detail-body-content');
      if (el) el.innerHTML = '';
    });
}

function renderMd(raw) {
  const lines = esc(raw).split('\n');
  let html = '';
  let inList = false;
  let inCode = false;
  let codeBuf = '';

  for (const line of lines) {
    if (line.startsWith('```')) {
      if (inCode) {
        html += `<pre style="background:var(--surface-raised);border:1px solid var(--border);border-radius:4px;padding:10px;font-size:12px;font-family:var(--mono);overflow-x:auto;margin:8px 0">${codeBuf}</pre>`;
        codeBuf = '';
        inCode = false;
      } else {
        if (inList) { html += '</ul>'; inList = false; }
        inCode = true;
      }
      continue;
    }
    if (inCode) { codeBuf += line + '\n'; continue; }
    if (line.match(/^#{1,4}\s/)) {
      if (inList) { html += '</ul>'; inList = false; }
      const text = line.replace(/^#{1,4}\s+/, '');
      html += `<div style="font-size:13px;font-weight:600;color:var(--text-bright);margin:12px 0 4px 0">${inlineMd(text)}</div>`;
    } else if (line.match(/^[-*]\s/)) {
      if (!inList) { html += '<ul style="margin:4px 0;padding-left:18px">'; inList = true; }
      html += `<li style="font-size:13px;margin:2px 0">${inlineMd(line.replace(/^[-*]\s+/, ''))}</li>`;
    } else if (line.match(/^\d+\.\s/)) {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<div style="font-size:13px;margin:2px 0;padding-left:8px">${inlineMd(line)}</div>`;
    } else if (line.trim() === '') {
      if (inList) { html += '</ul>'; inList = false; }
    } else {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<div style="font-size:13px;margin:2px 0">${inlineMd(line)}</div>`;
    }
  }
  if (inList) html += '</ul>';
  if (inCode) html += `<pre style="background:var(--surface-raised);border:1px solid var(--border);border-radius:4px;padding:10px;font-size:12px;font-family:var(--mono);overflow-x:auto;margin:8px 0">${codeBuf}</pre>`;
  return html;
}

function inlineMd(s) {
  return s
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--text-bright)">$1</strong>')
    .replace(/`(.+?)`/g, '<code style="background:var(--surface-raised);padding:1px 4px;border-radius:3px;font-size:12px;font-family:var(--mono)">$1</code>');
}

function closeDetail() {
  document.getElementById('detail-overlay').classList.remove('open');
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', {month:'short', day:'numeric'}) + ' ' +
           d.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', hour12:false});
  } catch { return iso; }
}

function esc(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDetail();
});

(function() {
  const handle = document.getElementById('detail-resize-handle');
  const panel = document.getElementById('detail-overlay');
  let startX, startW;
  handle.addEventListener('mousedown', e => {
    e.preventDefault();
    startX = e.clientX;
    startW = panel.offsetWidth;
    handle.classList.add('dragging');
    const onMove = ev => {
      const delta = startX - ev.clientX;
      panel.style.width = Math.max(300, Math.min(window.innerWidth * 0.7, startW + delta)) + 'px';
    };
    const onUp = () => {
      handle.classList.remove('dragging');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
})();

document.getElementById('search').addEventListener('input', () => { renderBacklog(); renderEpics(); });
document.getElementById('status-filter').addEventListener('change', () => { renderBacklog(); renderEpics(); });
document.getElementById('type-filter').addEventListener('change', () => { renderBacklog(); renderEpics(); });

document.querySelectorAll('.pill').forEach(pill => {
  pill.addEventListener('click', () => {
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    currentSort = pill.dataset.sort;
    renderBacklog();
    renderEpics();
  });
});

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
    const controlsBar = document.getElementById('controls-bar');
    const showControls = ['backlog', 'epics'].includes(tab.dataset.panel);
    controlsBar.style.display = showControls ? 'flex' : 'none';
  });
});

load();

// --- Drag-and-drop (SortableJS) ---

let dndSortables = [];

function dndInitBacklog() {
  dndSortables.forEach(s => s.destroy());
  dndSortables = [];
  document.querySelectorAll('.dnd-container').forEach(container => {
    const priority = container.dataset.priority;
    const s = Sortable.create(container, {
      group: 'backlog',
      animation: 150,
      handle: '.drag-handle',
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      onEnd: function(evt) {
        const id = evt.item.dataset.id;
        const fromPriority = evt.from.dataset.priority;
        const toPriority = evt.to.dataset.priority;
        const crossPriority = fromPriority !== toPriority;

        const updates = [];

        if (crossPriority) {
          const item = DATA.items.find(i => i.id === id);
          if (item) item.priority = toPriority;
          updates.push({id, field: 'priority', value: toPriority, actor: 'dashboard-dnd'});
        }

        const toRows = Array.from(evt.to.querySelectorAll('.backlog-row'));
        toRows.forEach((row, i) => {
          const rid = row.dataset.id;
          const item = DATA.items.find(x => x.id === rid);
          if (item) item.epic_sequence = i;
          updates.push({id: rid, field: 'epic_sequence', value: i, actor: 'dashboard-dnd'});
        });

        if (crossPriority) {
          const fromRows = Array.from(evt.from.querySelectorAll('.backlog-row'));
          fromRows.forEach((row, i) => {
            const rid = row.dataset.id;
            const item = DATA.items.find(x => x.id === rid);
            if (item) item.epic_sequence = i;
            updates.push({id: rid, field: 'epic_sequence', value: i, actor: 'dashboard-dnd'});
          });
        }

        dndPersist(updates, crossPriority);
      }
    });
    dndSortables.push(s);
  });
}

async function dndPersist(updates, rerender) {
  try {
    for (const u of updates) {
      const r = await fetch('/api/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(u)
      });
      const res = await r.json();
      if (!res.ok) { dndToast('Failed: ' + res.error, 'error'); load(); return; }
    }
    dndToast('saved', 'success');
    if (rerender) renderBacklog();
  } catch(err) {
    dndToast('Network error: ' + err.message, 'error');
    load();
  }
}

function dndToast(msg, type) {
  const existing = document.querySelector('.dnd-toast');
  if (existing) existing.remove();
  const el = document.createElement('div');
  el.className = 'dnd-toast ' + type;
  el.textContent = msg;
  document.body.appendChild(el);
  const delay = type === 'error' ? 4000 : 1400;
  setTimeout(() => el.classList.add('fade'), delay);
  setTimeout(() => el.remove(), delay + 600);
}

let dndStorySortables = [];

function dndInitStories() {
  dndStorySortables.forEach(s => s.destroy());
  dndStorySortables = [];
  document.querySelectorAll('.dnd-stories').forEach(container => {
    const epicId = container.dataset.epic;
    if (!epicId) return;
    const s = Sortable.create(container, {
      animation: 150,
      handle: '.drag-handle',
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      filter: '[style*="font-size:11px"]',
      onEnd: function(evt) {
        const rows = Array.from(container.querySelectorAll('.story-row[data-id]'));
        const updates = rows.map((row, i) => {
          const id = row.dataset.id;
          const item = DATA.items.find(x => x.id === id);
          if (item) item.epic_sequence = i;
          const epic = DATA.items.find(x => x.id === epicId);
          if (epic?.stories) {
            const story = epic.stories.find(x => x.id === id);
            if (story) story.epic_sequence = i;
          }
          return {id, field: 'epic_sequence', value: i, actor: 'dashboard-dnd'};
        });
        dndPersist(updates);
      }
    });
    dndStorySortables.push(s);
  });
}

const origRenderBacklog = renderBacklog;
renderBacklog = function() {
  origRenderBacklog();
  dndInitBacklog();
};

const origRenderRoadmap = renderRoadmap;
renderRoadmap = function() {
  origRenderRoadmap();
  dndInitStories();
};
</script>
</body>
</html>"""


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    project_dir = '.'

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/data':
            data = build_api_data(self.project_dir)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode())
        elif parsed.path == '/api/body':
            qs = urllib.parse.parse_qs(parsed.query)
            item_id = qs.get('id', [''])[0]
            result = query_item_body(self.project_dir, item_id) if item_id else None
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(result or {'body': '', 'extra': {}}).encode())
        elif parsed.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_error(404)

    _MAX_POST_BYTES = 65536

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/update':
            length = int(self.headers.get('Content-Length', 0))
            if length > self._MAX_POST_BYTES:
                self.send_response(413)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Request body too large"}).encode())
                return
            body = self.rfile.read(length) if length else b'{}'
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                return
            result = handle_update(self.project_dir, payload)
            status_code = 200 if result.get('ok') else 400
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(result, default=str).encode())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description='SweetClaude project dashboard')
    parser.add_argument('--project-dir', default='.', help='Project root directory')
    parser.add_argument('--port', type=int, default=8411, help='Port to serve on')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    if not os.path.exists(db_path(project_dir)):
        cache_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache.py')
        if os.path.exists(cache_script):
            subprocess.run(['python3', cache_script, '--project-dir', project_dir, '--rebuild'],
                           capture_output=True)

    DashboardHandler.project_dir = project_dir
    server = http.server.HTTPServer(('127.0.0.1', args.port), DashboardHandler)
    print(f'SweetClaude Dashboard: http://127.0.0.1:{args.port}')
    print(f'Project: {project_dir}')
    print('Press Ctrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
        server.server_close()


if __name__ == '__main__':
    main()
