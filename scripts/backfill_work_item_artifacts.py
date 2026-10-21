#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backfill per-work-item artifact directories.

Scans known artifact directories for files matching work item IDs,
creates .sweetclaude/work/<ITEM-ID>/ directories with manifest.yaml,
and symlinks discovered artifacts into the appropriate subdirectories.

Usage:
    python3 scripts/backfill_work_item_artifacts.py --project-dir .
    python3 scripts/backfill_work_item_artifacts.py --project-dir . --dry-run
    python3 scripts/backfill_work_item_artifacts.py --project-dir . --item ISSUE-170
"""
import argparse
import json
import os
import re
import yaml
from datetime import datetime, timezone


ARTIFACT_SUBDIRS = ['design', 'plans', 'contracts', 'reports', 'decisions', 'scratch']

CATEGORY_MAP = {
    'technical': 'design',
    'plans': 'plans',
    'contracts': 'contracts',
    'reports': 'reports',
}


def load_work_items(project_dir):
    """Build list of all work item IDs from work_history + active roadmap/backlog."""
    items = {}
    sc_path = os.path.join(project_dir, '.sweetclaude', 'state', 'sweetclaude.yaml')
    if os.path.exists(sc_path):
        with open(sc_path) as f:
            sc = yaml.safe_load(f) or {}
        for entry in sc.get('work_history', []):
            item_id = entry.get('id', '')
            if item_id:
                items[item_id] = {
                    'title': entry.get('title', ''),
                    'type': guess_type(item_id),
                    'status': entry.get('outcome', 'done'),
                }
        active = (sc.get('work', {}) or {}).get('active') or {}
        if active.get('id'):
            items[active['id']] = {
                'title': active.get('title', ''),
                'type': guess_type(active['id']),
                'status': 'active',
            }

    for subdir in ['roadmap/issues', 'roadmap/issues/done',
                    'roadmap/epics', 'roadmap/epics/done',
                    'roadmap/milestones', 'roadmap/milestones/done',
                    'backlog', 'backlog/done']:
        scan_dir = os.path.join(project_dir, '.sweetclaude', 'product', subdir)
        if not os.path.isdir(scan_dir):
            continue
        for fn in os.listdir(scan_dir):
            if not fn.endswith('.md'):
                continue
            item_id = extract_id_from_filename(fn)
            if item_id and item_id not in items:
                title = fn.replace('.md', '').split('-', 2)[-1].replace('-', ' ') if '-' in fn else fn
                items[item_id] = {
                    'title': title,
                    'type': guess_type(item_id),
                    'status': 'done' if '/done' in subdir else 'active',
                }
    return items


def build_alias_table(project_dir, items):
    """Map STORY-NNN aliases to ISSUE-NNN IDs using migrated_from fields."""
    aliases = {}
    for subdir in ['roadmap/issues', 'roadmap/issues/done', 'backlog', 'backlog/done']:
        scan_dir = os.path.join(project_dir, '.sweetclaude', 'product', subdir)
        if not os.path.isdir(scan_dir):
            continue
        for fn in os.listdir(scan_dir):
            if not fn.endswith('.md'):
                continue
            fpath = os.path.join(scan_dir, fn)
            try:
                with open(fpath) as f:
                    content = f.read()
                if not content.startswith('---'):
                    continue
                end = content.find('---', 3)
                if end < 0:
                    continue
                fm = yaml.safe_load(content[3:end])
                if not isinstance(fm, dict):
                    continue
                migrated = fm.get('migrated_from', '')
                item_id = fm.get('id', '')
                if migrated and item_id:
                    aliases[str(migrated)] = str(item_id)
            except Exception:
                continue

    for entry_id in list(items.keys()):
        if entry_id.startswith('STORY-'):
            num = entry_id.split('-', 1)[1]
            issue_id = f'ISSUE-{num}'
            if issue_id not in aliases.values():
                aliases[entry_id] = entry_id
    return aliases


def guess_type(item_id):
    if item_id.startswith('ISSUE-') or item_id.startswith('STORY-'):
        return 'issue'
    if item_id.startswith('EP-'):
        return 'epic'
    if item_id.startswith('MS-'):
        return 'milestone'
    return 'issue'


def extract_id_from_filename(fn):
    m = re.match(r'(ISSUE-\d+|EP-\d+|MS-\d+|STORY-\d+)', fn, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def normalize_id_for_search(item_id):
    """Return search patterns for an item ID: lowercase with dash, and uppercase."""
    return [
        item_id.lower().replace('-', '-'),
        item_id.upper(),
    ]


def find_item_path(project_dir, item_id):
    """Find the definition file path for a work item."""
    for subdir in ['roadmap/issues', 'roadmap/issues/done',
                    'roadmap/epics', 'roadmap/epics/done',
                    'roadmap/milestones', 'roadmap/milestones/done',
                    'backlog', 'backlog/done']:
        scan_dir = os.path.join(project_dir, '.sweetclaude', 'product', subdir)
        if not os.path.isdir(scan_dir):
            continue
        for fn in os.listdir(scan_dir):
            if fn.endswith('.md') and fn.upper().startswith(item_id.upper()):
                return os.path.join('.sweetclaude', 'product', subdir, fn)
    return None


def scan_artifacts(project_dir, item_id, aliases):
    """Find all artifacts matching an item ID in known directories."""
    found = []
    search_ids = [item_id]
    for alias, canonical in aliases.items():
        if canonical == item_id:
            search_ids.append(alias)
        if alias == item_id:
            search_ids.append(canonical)

    search_ids = list(set(search_ids))
    search_patterns = []
    for sid in search_ids:
        search_patterns.extend(normalize_id_for_search(sid))
    search_patterns = list(set(search_patterns))

    scan_dirs = {
        'technical': os.path.join(project_dir, '.sweetclaude', 'technical'),
        'plans': os.path.join(project_dir, '.sweetclaude', 'plans'),
        'contracts': os.path.join(project_dir, '.sweetclaude', 'contracts'),
        'reports': os.path.join(project_dir, '.sweetclaude', 'reports'),
    }

    for category, scan_dir in scan_dirs.items():
        if not os.path.isdir(scan_dir):
            continue
        for fn in os.listdir(scan_dir):
            if os.path.isdir(os.path.join(scan_dir, fn)):
                continue
            fn_lower = fn.lower()
            for pattern in search_patterns:
                if pattern.lower() in fn_lower:
                    found.append({
                        'category': category,
                        'source': os.path.join('.sweetclaude', os.path.basename(scan_dir), fn),
                        'filename': fn,
                        'subdirectory': CATEGORY_MAP.get(category, category),
                    })
                    break

    for docs_subdir in ['docs/internal', 'docs/plans']:
        docs_dir = os.path.join(project_dir, docs_subdir)
        if not os.path.isdir(docs_dir):
            continue
        for fn in os.listdir(docs_dir):
            if not fn.endswith('.md'):
                continue
            fpath = os.path.join(docs_dir, fn)
            try:
                with open(fpath) as f:
                    content = f.read(4096)
                for sid in search_ids:
                    if sid in content or sid.lower() in content.lower():
                        found.append({
                            'category': 'docs',
                            'source': os.path.join(docs_subdir, fn),
                            'filename': fn,
                            'subdirectory': 'design',
                        })
                        break
            except Exception:
                continue

    return found


def find_effort_link(project_dir, item_id):
    """Check if an effort directory references this item."""
    efforts_dir = os.path.join(project_dir, '.sweetclaude', 'efforts')
    if not os.path.isdir(efforts_dir):
        return None
    id_lower = item_id.lower().replace('-', '-')
    for entry in os.listdir(efforts_dir):
        entry_path = os.path.join(efforts_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        if id_lower in entry.lower():
            return os.path.join('.sweetclaude', 'efforts', entry)
        effort_yaml = os.path.join(entry_path, 'effort.yaml')
        if os.path.exists(effort_yaml):
            try:
                with open(effort_yaml) as f:
                    data = yaml.safe_load(f) or {}
                if item_id in str(data):
                    return os.path.join('.sweetclaude', 'efforts', entry)
            except Exception:
                continue
    return None


def create_work_dir(project_dir, item_id, item_info, artifacts, effort_link, dry_run=False):
    """Create the work item directory with manifest and symlinks."""
    work_dir = os.path.join(project_dir, '.sweetclaude', 'work', item_id)
    result = {
        'item_id': item_id,
        'work_dir': os.path.join('.sweetclaude', 'work', item_id),
        'artifacts_linked': [],
        'created': False,
        'skipped': False,
    }

    if os.path.exists(work_dir):
        result['skipped'] = True
        return result

    if dry_run:
        for art in artifacts:
            result['artifacts_linked'].append({
                'from': art['source'],
                'to': os.path.join('.sweetclaude', 'work', item_id, art['subdirectory'], art['filename']),
            })
        result['created'] = True
        return result

    os.makedirs(work_dir, exist_ok=True)
    for subdir in ARTIFACT_SUBDIRS:
        os.makedirs(os.path.join(work_dir, subdir), exist_ok=True)

    item_path = find_item_path(project_dir, item_id)

    manifest = {
        'schema_version': 1,
        'item_id': item_id,
        'item_type': item_info.get('type', 'issue'),
        'title': item_info.get('title', ''),
        'created': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'item_path': item_path,
        'backfill': {
            'ran_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'artifacts_linked': [],
        },
        'cross_references': [],
        'effort_link': effort_link,
    }

    for art in artifacts:
        target_dir = os.path.join(work_dir, art['subdirectory'])
        os.makedirs(target_dir, exist_ok=True)
        link_path = os.path.join(target_dir, art['filename'])
        source_abs = os.path.join(project_dir, art['source'])

        if os.path.exists(link_path) or not os.path.exists(source_abs):
            continue

        rel_source = os.path.relpath(source_abs, target_dir)
        os.symlink(rel_source, link_path)

        link_record = {
            'from': art['source'],
            'to': os.path.join('.sweetclaude', 'work', item_id, art['subdirectory'], art['filename']),
        }
        manifest['backfill']['artifacts_linked'].append(link_record)
        result['artifacts_linked'].append(link_record)

    manifest_path = os.path.join(work_dir, 'manifest.yaml')
    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    result['created'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description='Backfill per-work-item artifact directories')
    parser.add_argument('--project-dir', required=True, help='Project root directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without making changes')
    parser.add_argument('--item', help='Backfill a single item ID only')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    items = load_work_items(project_dir)
    aliases = build_alias_table(project_dir, items)

    if args.item:
        if args.item not in items:
            items[args.item] = {'title': '', 'type': guess_type(args.item), 'status': 'unknown'}
        items = {args.item: items[args.item]}

    results = []
    for item_id, item_info in sorted(items.items()):
        artifacts = scan_artifacts(project_dir, item_id, aliases)
        effort_link = find_effort_link(project_dir, item_id)

        if not artifacts and not effort_link:
            continue

        result = create_work_dir(project_dir, item_id, item_info, artifacts, effort_link, dry_run=args.dry_run)
        results.append(result)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        created = [r for r in results if r['created']]
        skipped = [r for r in results if r['skipped']]
        mode = 'DRY RUN' if args.dry_run else 'BACKFILL'

        print(f"[{mode}] Scanned {len(items)} work items, found artifacts for {len(results)} items")
        if skipped:
            print(f"  Skipped {len(skipped)} (already have work directories)")

        for r in created:
            count = len(r['artifacts_linked'])
            print(f"  {r['item_id']}: {count} artifact{'s' if count != 1 else ''}")
            for link in r['artifacts_linked']:
                print(f"    {link['from']} -> {link['to']}")

        if not args.dry_run:
            print(f"\nCreated {len(created)} work-item directories in .sweetclaude/work/")


if __name__ == '__main__':
    main()
