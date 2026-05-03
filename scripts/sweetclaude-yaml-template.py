#!/usr/bin/env python3
import argparse, yaml, sys
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def build_template(name, project_type, version_stage, installed_version='unknown',
                   migrated_from=None):
    feat = lambda: {'status': 'not_offered', 'offered_at': None,
                    'decided_at': None, 'defer_until': None}
    return {
        'schema_version': 1,
        'project': {
            'name': name,
            'type': project_type,
            'version_stage': version_stage,
            'safety_snapshot': '',
        },
        'framework': {
            'installed_version': installed_version,
            'setup_complete': False,
            'migrated_at': now_iso() if migrated_from else None,
            'migrated_from': migrated_from,
            'migration_status': 'complete',
            'hook_last_ran': None,
            'consistency': {
                'last_checked': None,
                'status': 'ok',
                'drift': [],
                'check_error': None,
            },
            'update': {
                'available': None,
                'last_checked': None,
                'declined': False,
                'check_error': None,
            },
        },
        'session': {
            'deference_level': 'collaborative',
            'default_action': None,
        },
        'work': {
            'last_item_id': None,
            'active': {
                'id': None, 'type': None, 'workflow': [],
                'phase': None, 'title': None,
                'started': None, 'entry_category': None,
            },
        },
        'features': {
            'product_milestones': feat(),
            'product_backlog':    feat(),
            'product_personas':   feat(),
            'product_stories':    feat(),
            'document_corpus':    feat(),
            'usage_tracking':     feat(),
            'behavioral_regression': feat(),
        },
        'health': {
            'last_checked': None,
            'artifacts': {
                'milestones': 'not_configured',
                'backlog':    'not_configured',
                'personas':   'not_configured',
                'stories':    'not_configured',
                'corpus':     'not_configured',
            },
        },
        'work_history': [],
        'learnings': [],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=True)
    p.add_argument('--type', dest='project_type', default='existing-code')
    p.add_argument('--version-stage', default='IDEA')
    p.add_argument('--installed-version', default='unknown')
    p.add_argument('--migrated-from', default=None)
    p.add_argument('--output', default='-')
    args = p.parse_args()

    data = build_template(
        name=args.name,
        project_type=args.project_type,
        version_stage=args.version_stage,
        installed_version=args.installed_version,
        migrated_from=args.migrated_from,
    )

    content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    if args.output == '-':
        sys.stdout.write(content)
    else:
        with open(args.output, 'w') as f:
            f.write(content)

if __name__ == '__main__':
    main()
