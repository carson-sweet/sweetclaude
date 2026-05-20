#!/usr/bin/env python3
"""SweetClaude roadmap cache — SQLite cache built from markdown source files.

Scans docs/product/backlog/ and docs/product/roadmap/ for markdown files with
YAML frontmatter, builds a SQLite database at .sweetclaude/cache/roadmap.db,
and exposes query commands for skills to consume.

The cache is gitignored. It is rebuilt on session start and after writes.
Markdown files are the source of truth.
"""
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip install pyyaml")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    priority TEXT,
    effort TEXT,
    epic TEXT,
    epic_sequence INTEGER,
    release TEXT,
    objective TEXT,
    source_path TEXT NOT NULL,
    created TEXT,
    updated TEXT,
    closed_date TEXT
);

CREATE TABLE IF NOT EXISTS completion_criteria (
    epic_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    criterion TEXT NOT NULL,
    done INTEGER DEFAULT 0,
    PRIMARY KEY (epic_id, seq),
    FOREIGN KEY (epic_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS epic_dependencies (
    epic_id TEXT NOT NULL,
    depends_on TEXT NOT NULL,
    PRIMARY KEY (epic_id, depends_on),
    FOREIGN KEY (epic_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS tags (
    item_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    UNIQUE(item_id, tag),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE INDEX IF NOT EXISTS idx_items_type ON items(type);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_epic ON items(epic);
CREATE INDEX IF NOT EXISTS idx_items_release ON items(release);
CREATE INDEX IF NOT EXISTS idx_items_priority ON items(priority);
CREATE INDEX IF NOT EXISTS idx_tags_item ON tags(item_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""


def db_path(project_dir):
    return os.path.join(project_dir, '.sweetclaude', 'cache', 'roadmap.db')


def parse_frontmatter(path):
    try:
        raw = Path(path).read_text(encoding='utf-8')
    except Exception:
        return None
    parts = raw.split('---', 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
        return fm if isinstance(fm, dict) else None
    except Exception:
        return None


def scan_files(project_dir):
    backlog = os.path.join(project_dir, 'docs', 'product', 'backlog')
    roadmap = os.path.join(project_dir, 'docs', 'product', 'roadmap')
    skip_dirs = {os.path.join(backlog, 'epics')}
    files = []
    for base in [backlog, roadmap]:
        if not os.path.isdir(base):
            continue
        for root, dirs, filenames in os.walk(base):
            if root in skip_dirs or os.path.dirname(root) in skip_dirs:
                continue
            for fname in filenames:
                if fname.endswith('.md') and fname != 'SCHEMA.md':
                    full = os.path.join(root, fname)
                    files.append(full)
    return files


def _rebuild_cache(project_dir):
    dbp = db_path(project_dir)
    os.makedirs(os.path.dirname(dbp), exist_ok=True)
    tmp_path = dbp + '.tmp'
    conn = sqlite3.connect(tmp_path)
    conn.executescript(SCHEMA_SQL)

    for fpath in scan_files(project_dir):
        fm = parse_frontmatter(fpath)
        if not fm or 'id' not in fm or 'type' not in fm:
            continue

        rel_path = os.path.relpath(fpath, project_dir)
        item_type = fm.get('type', '')

        conn.execute(
            """INSERT OR REPLACE INTO items
               (id, type, title, status, priority, effort, epic, epic_sequence,
                release, objective, source_path, created, updated, closed_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fm['id'],
                item_type,
                fm.get('title', ''),
                fm.get('status', 'new'),
                fm.get('priority'),
                fm.get('effort'),
                fm.get('epic') if fm.get('epic') not in (None, 'null') else None,
                fm.get('epic_sequence'),
                fm.get('release') if fm.get('release') not in (None, 'null') else None,
                fm.get('objective'),
                rel_path,
                fm.get('created'),
                fm.get('updated'),
                fm.get('closed_date'),
            ),
        )

        for tag in fm.get('tags', []) or []:
            conn.execute(
                "INSERT OR IGNORE INTO tags (item_id, tag) VALUES (?, ?)",
                (fm['id'], tag),
            )

        if item_type == 'epic':
            done_indexes = set(fm.get('completion_criteria_done', []) or [])
            for i, crit in enumerate(fm.get('completion_criteria', []) or []):
                conn.execute(
                    """INSERT OR REPLACE INTO completion_criteria
                       (epic_id, seq, criterion, done) VALUES (?, ?, ?, ?)""",
                    (fm['id'], i, crit, 1 if i in done_indexes else 0),
                )
            for dep in fm.get('depends_on', []) or []:
                conn.execute(
                    "INSERT OR IGNORE INTO epic_dependencies (epic_id, depends_on) VALUES (?, ?)",
                    (fm['id'], dep),
                )

    conn.commit()
    conn.close()
    os.replace(tmp_path, dbp)
    return dbp


def rebuild(project_dir):
    return _rebuild_cache(project_dir)


def get_conn(project_dir):
    dbp = db_path(project_dir)
    if not os.path.exists(dbp):
        rebuild(project_dir)
    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    return conn


def query_item_count(project_dir):
    conn = get_conn(project_dir)
    row = conn.execute("SELECT COUNT(*) as total FROM items").fetchone()
    conn.close()
    return {"total": row["total"]}


def query_active_epic(project_dir):
    conn = get_conn(project_dir)
    row = conn.execute(
        "SELECT * FROM items WHERE type='epic' AND status='active' ORDER BY id LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    return result


def query_epic_stories(project_dir, epic_id, include_done=False):
    conn = get_conn(project_dir)
    if include_done:
        rows = conn.execute(
            """SELECT * FROM items WHERE epic=? AND type IN ('story','bug','chore','debt')
               ORDER BY epic_sequence, id""",
            (epic_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM items WHERE epic=? AND type IN ('story','bug','chore','debt')
               AND status NOT IN ('done', 'abandoned', 'deferred')
               ORDER BY epic_sequence, id""",
            (epic_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_backlog(project_dir, unlinked_only=False):
    conn = get_conn(project_dir)
    sql = """SELECT * FROM items
           WHERE type IN ('story','bug','chore','debt')
           AND status NOT IN ('done', 'abandoned', 'deferred')"""
    if unlinked_only:
        sql += " AND (epic IS NULL OR epic = '')"
    sql += """
           ORDER BY
             CASE priority
               WHEN 'now' THEN 1
               WHEN 'sooner' THEN 2
               WHEN 'soon' THEN 3
               WHEN 'later' THEN 4
               WHEN 'someday' THEN 5
               ELSE 6
             END,
             id"""
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_next_id(project_dir, prefix):
    conn = get_conn(project_dir)
    rows = conn.execute(
        "SELECT id FROM items WHERE id LIKE ?", (f"{prefix}-%",)
    ).fetchall()
    conn.close()
    max_num = 0
    for row in rows:
        m = re.match(rf'{re.escape(prefix)}-(\d+)', row['id'])
        if m:
            max_num = max(max_num, int(m.group(1)))
    return {"next_id": f"{prefix}-{max_num + 1:03d}"}


def query_releases(project_dir):
    conn = get_conn(project_dir)

    releases = conn.execute(
        "SELECT * FROM items WHERE type='release' ORDER BY id"
    ).fetchall()

    result = []
    for rel in releases:
        rel_dict = dict(rel)
        epics = conn.execute(
            "SELECT * FROM items WHERE type='epic' AND release=? ORDER BY id",
            (rel_dict['id'],),
        ).fetchall()

        epic_list = []
        for ep in epics:
            ep_dict = dict(ep)
            stories = conn.execute(
                """SELECT * FROM items WHERE epic=? AND type IN ('story','bug','chore','debt')
                   ORDER BY epic_sequence, id""",
                (ep_dict['id'],),
            ).fetchall()
            criteria = conn.execute(
                "SELECT * FROM completion_criteria WHERE epic_id=? ORDER BY seq",
                (ep_dict['id'],),
            ).fetchall()

            ep_dict['stories'] = [dict(s) for s in stories]
            ep_dict['completion_criteria'] = [dict(c) for c in criteria]
            ep_dict['criteria_done'] = sum(1 for c in criteria if c['done'])
            ep_dict['criteria_total'] = len(criteria)
            epic_list.append(ep_dict)

        rel_dict['epics'] = epic_list
        result.append(rel_dict)

    conn.close()
    return result


def query_epics(project_dir, include_done=False):
    conn = get_conn(project_dir)
    if include_done:
        rows = conn.execute(
            "SELECT * FROM items WHERE type='epic' ORDER BY id"
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM items WHERE type='epic'
               AND status NOT IN ('done', 'abandoned')
               ORDER BY id"""
        ).fetchall()

    result = []
    for row in rows:
        ep = dict(row)
        criteria = conn.execute(
            "SELECT * FROM completion_criteria WHERE epic_id=? ORDER BY seq",
            (ep['id'],),
        ).fetchall()
        ep['completion_criteria'] = [dict(c) for c in criteria]
        ep['criteria_done'] = sum(1 for c in criteria if c['done'])
        ep['criteria_total'] = len(criteria)
        stories = conn.execute(
            """SELECT * FROM items WHERE epic=? AND type IN ('story','bug','chore','debt')
               ORDER BY epic_sequence, id""",
            (ep['id'],),
        ).fetchall()
        ep['stories'] = [dict(s) for s in stories]
        result.append(ep)

    conn.close()
    return result


def query_summary(project_dir):
    conn = get_conn(project_dir)
    work_types = "('story','bug','chore','debt')"

    type_counts = {}
    for row in conn.execute("SELECT type, COUNT(*) as c FROM items GROUP BY type"):
        type_counts[row['type']] = row['c']

    status_counts = {}
    for row in conn.execute("SELECT status, COUNT(*) as c FROM items GROUP BY status"):
        status_counts[row['status']] = row['c']

    epic_by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as c FROM items WHERE type='epic' GROUP BY status"):
        epic_by_status[row['status']] = row['c']

    release_count = conn.execute("SELECT COUNT(*) as c FROM items WHERE type='release'").fetchone()['c']

    linked_total = conn.execute(
        f"SELECT COUNT(*) as c FROM items WHERE type IN {work_types} AND epic IS NOT NULL AND epic != ''"
    ).fetchone()['c']
    linked_open = conn.execute(
        f"SELECT COUNT(*) as c FROM items WHERE type IN {work_types} AND epic IS NOT NULL AND epic != '' AND status NOT IN ('done','abandoned','deferred')"
    ).fetchone()['c']
    linked_done = conn.execute(
        f"SELECT COUNT(*) as c FROM items WHERE type IN {work_types} AND epic IS NOT NULL AND epic != '' AND status = 'done'"
    ).fetchone()['c']

    unlinked_total = conn.execute(
        f"SELECT COUNT(*) as c FROM items WHERE type IN {work_types} AND (epic IS NULL OR epic = '')"
    ).fetchone()['c']
    unlinked_open = conn.execute(
        f"SELECT COUNT(*) as c FROM items WHERE type IN {work_types} AND (epic IS NULL OR epic = '') AND status NOT IN ('done','abandoned','deferred')"
    ).fetchone()['c']

    unlinked_by_priority = {}
    for row in conn.execute(
        f"SELECT COALESCE(priority, 'none') as p, COUNT(*) as c FROM items WHERE type IN {work_types} AND (epic IS NULL OR epic = '') AND status NOT IN ('done','abandoned','deferred') GROUP BY p"
    ):
        unlinked_by_priority[row['p']] = row['c']

    conn.close()

    return {
        "total_items": sum(type_counts.values()),
        "by_type": type_counts,
        "by_status": status_counts,
        "epics": {"total": type_counts.get('epic', 0), "by_status": epic_by_status},
        "releases": {"total": release_count},
        "linked": {"total": linked_total, "open": linked_open, "done": linked_done},
        "unlinked": {"total": unlinked_total, "open": unlinked_open, "by_priority": unlinked_by_priority},
    }


def query_tags(project_dir, tag):
    conn = get_conn(project_dir)
    rows = conn.execute(
        """SELECT i.* FROM items i
           JOIN tags t ON t.item_id = i.id
           WHERE t.tag = ?
           ORDER BY i.id""",
        (tag,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def main():
    parser = argparse.ArgumentParser(description='SweetClaude roadmap cache')
    parser.add_argument('--project-dir', default='.', help='Project root directory')
    parser.add_argument('--rebuild', action='store_true', help='Rebuild the cache from source files')
    parser.add_argument('--query', choices=[
        'item-count', 'active-epic', 'epic-stories', 'epics', 'backlog',
        'next-id', 'releases', 'tags', 'summary',
    ], help='Query to run')
    parser.add_argument('--epic', help='Epic ID for epic-stories query')
    parser.add_argument('--prefix', help='ID prefix for next-id query')
    parser.add_argument('--tag', help='Tag name for tags query')
    parser.add_argument('--include-done', action='store_true', help='Include done items')
    parser.add_argument('--unlinked-only', action='store_true', help='Only return items not linked to an epic')

    args = parser.parse_args()

    if args.rebuild:
        dbp = rebuild(args.project_dir)
        print(json.dumps({"rebuilt": True, "path": dbp}))
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    if args.query == 'item-count':
        result = query_item_count(args.project_dir)
    elif args.query == 'active-epic':
        result = query_active_epic(args.project_dir)
    elif args.query == 'epic-stories':
        if not args.epic:
            sys.exit("--epic required for epic-stories query")
        result = query_epic_stories(args.project_dir, args.epic, args.include_done)
    elif args.query == 'epics':
        result = query_epics(args.project_dir, args.include_done)
    elif args.query == 'backlog':
        result = query_backlog(args.project_dir, unlinked_only=args.unlinked_only)
    elif args.query == 'next-id':
        if not args.prefix:
            sys.exit("--prefix required for next-id query")
        result = query_next_id(args.project_dir, args.prefix)
    elif args.query == 'releases':
        result = query_releases(args.project_dir)
    elif args.query == 'summary':
        result = query_summary(args.project_dir)
    elif args.query == 'tags':
        if not args.tag:
            sys.exit("--tag required for tags query")
        result = query_tags(args.project_dir, args.tag)
    else:
        sys.exit(f"Unknown query: {args.query}")

    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
