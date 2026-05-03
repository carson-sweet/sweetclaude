#!/usr/bin/env python3
import argparse, yaml, os, sys, shutil
from datetime import datetime, timezone
from pathlib import Path

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

SKILL_KEY_MAP = {
    'product-milestones':    'product_milestones',
    'product-backlog':       'product_backlog',
    'product-user-personas': 'product_personas',
    'product-user-stories':  'product_stories',
    'document-corpus':       'document_corpus',
    'usage':                 'usage_tracking',
    'behavioral-regression': 'behavioral_regression',
    'product-sprint-plan':   None,
}

def blank_feature():
    return {'status': 'not_offered', 'offered_at': None,
            'decided_at': None, 'defer_until': None}

def migrate(project_dir, installed_version):
    state_dir = Path(project_dir) / '.sweetclaude' / 'state'
    sc_yaml   = state_dir / 'sweetclaude.yaml'
    phase_f   = state_dir / 'phase.yaml'
    skills_f  = state_dir / 'skills.yaml'
    ir_f      = state_dir / 'improvement-register.md'
    archive   = state_dir / 'archive'

    # Guard: already migrated and complete
    if sc_yaml.exists():
        existing = yaml.safe_load(sc_yaml.read_text()) or {}
        if existing.get('framework', {}).get('migration_status') == 'complete':
            print("Already migrated — nothing to do.")
            return

    # Step 1: write in_progress sentinel immediately
    sentinel = {'schema_version': 1,
                'framework': {'migration_status': 'in_progress'}}
    state_dir.mkdir(parents=True, exist_ok=True)
    sc_yaml.write_text(yaml.dump(sentinel))

    # Step 2: read phase.yaml
    phase = yaml.safe_load(phase_f.read_text()) if phase_f.exists() else {}
    phase = phase or {}

    # Step 3: read skills.yaml
    skills_raw = yaml.safe_load(skills_f.read_text()) if skills_f.exists() else {}
    skills_raw = skills_raw or {}
    skills_raw.pop('schema_version', None)

    # Step 4: read improvement-register.md (extract bullet lines, max 15)
    learnings = []
    if ir_f.exists():
        for line in ir_f.read_text().splitlines():
            line = line.strip()
            if line.startswith('- ') and len(line) > 2:
                learnings.append(line[2:])
                if len(learnings) >= 15:
                    break

    # Step 5: build features map
    features = {}
    all_keys = ['product_milestones','product_backlog','product_personas',
                'product_stories','document_corpus','usage_tracking','behavioral_regression']
    for key in all_keys:
        features[key] = blank_feature()

    for old_key, new_key in SKILL_KEY_MAP.items():
        if new_key and old_key in skills_raw:
            entry = skills_raw[old_key]
            old_status = entry.get('status', 'uninitialized')
            if old_status == 'active':
                features[new_key] = {
                    'status': 'active',
                    'offered_at': entry.get('last_changed_at'),
                    'decided_at': entry.get('last_changed_at'),
                    'defer_until': None,
                }
            elif old_status == 'uninitialized':
                features[new_key] = blank_feature()
            else:
                print(f"Warning: unknown status '{old_status}' for '{old_key}' — treating as not_offered", file=sys.stderr)

    # Step 6: active work item
    awi = phase.get('active_work_item', {}) or {}

    # Step 7: build complete sweetclaude.yaml
    data = {
        'schema_version': 1,
        'project': {
            'name': '',
            'type': phase.get('project_type', 'existing-code'),
            'version_stage': phase.get('version_stage', 'BETA'),
            'safety_snapshot': phase.get('safety_snapshot', ''),
        },
        'framework': {
            'installed_version': installed_version,
            'setup_complete': True,
            'migrated_at': now_iso(),
            'migrated_from': installed_version,
            'migration_status': 'complete',
            'hook_last_ran': None,
            'consistency': {
                'last_checked': None, 'status': 'ok',
                'drift': [], 'check_error': None,
            },
            'update': {
                'available': None, 'last_checked': None,
                'declined': False, 'check_error': None,
            },
        },
        'session': {
            'deference_level': phase.get('deference_level', 'collaborative'),
            'default_action': None,
        },
        'work': {
            'last_item_id': phase.get('last_work_item_id'),
            'active': {
                'id':             awi.get('id'),
                'type':           awi.get('type'),
                'workflow':       awi.get('workflow', []),
                'phase':          awi.get('phase'),
                'title':          awi.get('title'),
                'started':        awi.get('started'),
                'entry_category': awi.get('entry_category'),
            },
        },
        'features': features,
        'health': {
            'last_checked': None,
            'artifacts': {k: 'not_configured' for k in
                          ['milestones','backlog','personas','stories','corpus']},
        },
        'work_history': [],
        'learnings': learnings,
    }

    # Step 8: write final file
    sc_yaml.write_text(yaml.dump(data, default_flow_style=False,
                                 allow_unicode=True, sort_keys=False))

    # Step 9: archive old files
    archive.mkdir(exist_ok=True)
    for src, name in [(phase_f, 'phase.yaml.bak'),
                      (skills_f, 'skills.yaml.bak')]:
        if src.exists():
            shutil.move(src, archive / name)

    print(f"Migration complete. Old files archived to {archive}/")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project-dir', required=True)
    p.add_argument('--installed-version', default='unknown')
    args = p.parse_args()
    migrate(args.project_dir, args.installed_version)

if __name__ == '__main__':
    main()
