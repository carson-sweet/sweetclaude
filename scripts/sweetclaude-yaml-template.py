#!/usr/bin/env python3
import argparse
import yaml
import sys
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def build_template(name, project_type, version_stage, installed_version='unknown',
                   migrated_from=None, issue_tracker='local'):
    def feat():
        return {'status': 'not_offered', 'offered_at': None,
                'decided_at': None, 'defer_until': None}
    return {
        # Must match config/migration-registry.yaml current_version for
        # sweetclaude.yaml, or every new project is created already needing
        # migration and bootstrap prompts for it at first session (ISSUE-280).
        'schema_version': 2,
        'project': {
            'name': name,
            'type': project_type,
            'version_stage': version_stage,
            'mode': None,
            # The issue system of record for this project. Local remains the
            # compatible default; github makes project-issues use GitHub Issues.
            'issue_tracker': issue_tracker,
            'safety_snapshot': '',
        },
        'framework': {
            'installed_version': installed_version,
            'setup_complete': False,
            'migrated_at': now_iso() if migrated_from else None,
            'migrated_from': migrated_from,
            'migration_status': 'complete' if migrated_from else None,
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
                # None, not False: the v1->v2 migration exists to clear the
                # legacy boolean, so writing it fresh recreates v1 shape.
                'declined': None,
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
            'work_item_artifacts': feat(),
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
    p.add_argument('--issue-tracker', choices=('local', 'github'), default='local')
    p.add_argument('--output', default='-')
    args = p.parse_args()

    data = build_template(
        name=args.name,
        project_type=args.project_type,
        version_stage=args.version_stage,
        installed_version=args.installed_version,
        migrated_from=args.migrated_from,
        issue_tracker=args.issue_tracker,
    )

    content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    if args.output == '-':
        sys.stdout.write(content)
    else:
        with open(args.output, 'w') as f:
            f.write(content)

if __name__ == '__main__':
    main()
