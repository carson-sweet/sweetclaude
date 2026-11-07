#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Session State Generator
# Builds .sweetclaude/state/session-state.yaml from constituent state files.
# Called by: session-preflight.sh (sync at startup), state-regenerator.sh (background after writes)
#
# ── paths.product_base contract ────────────────────────────────────────────
# Authoritative source: .sweetclaude/artifact-privacy.yaml → categories.product.base_path
# Derived snapshot:     .sweetclaude/state/session-state.yaml → paths.product_base
#
# This script READS from artifact-privacy.yaml and WRITES to session-state.yaml.
# NEVER write back to artifact-privacy.yaml from here — that file is the source
# of truth and is mutated only by sweetclaude:library-load setup, sweetclaude:library-load migrate, and
# explicit user action. session-state.yaml is regenerated every session and any
# divergence between the two is a bug (caught by _health Step 3a).

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then exit 0; fi

PHASE_YAML="$PROJECT_DIR/.sweetclaude/state/phase.yaml"
SC_YAML_STATE="$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml"
if [ ! -f "$PHASE_YAML" ] && [ ! -f "$SC_YAML_STATE" ]; then exit 0; fi

OUTPUT="$PROJECT_DIR/.sweetclaude/state/session-state.yaml"

export PROJECT_DIR

python3 - > "$OUTPUT" 2>/dev/null <<'PYEOF'
import yaml, os, json, sys
from datetime import datetime, timezone, date

project_dir = os.environ['PROJECT_DIR']
state_dir = os.path.join(project_dir, '.sweetclaude', 'state')

phase_path = os.path.join(state_dir, 'phase.yaml')
sc_path    = os.path.join(state_dir, 'sweetclaude.yaml')

# sweetclaude.yaml is canonical. phase.yaml is a mirror the story controllers
# write while a workflow is running, so it is only consulted when the canonical
# file is absent (a project mid-migration).
phase = {}
if os.path.exists(sc_path):
    with open(sc_path) as f:
        sc = yaml.safe_load(f) or {}
    proj = sc.get('project', {})
    sess = sc.get('session', {})
    work_data = sc.get('work', {})
    active = work_data.get('active') or {}
    phase = {
        'project_name': proj.get('name', ''),
        'version_stage': proj.get('version_stage', ''),
        'mode': proj.get('mode') or sc.get('mode') or '',
        'deference_level': sess.get('deference_level', ''),
        'schema_version': 2,
        'active_work_item': active,
    }
elif os.path.exists(phase_path):
    with open(phase_path) as f:
        phase = yaml.safe_load(f) or {}
else:
    sys.exit(0)

def effective_weight(entry):
    if entry.get('decay_exempt', False):
        return entry.get('weight', 1.0)
    try:
        entry_date = date.fromisoformat(entry['date'])
    except (KeyError, ValueError):
        return entry.get('weight', 1.0)
    weeks = (date.today() - entry_date).days / 7
    return entry.get('weight', 1.0) * (0.95 ** weeks)

jsonl_path = os.path.join(state_dir, 'improvement-register.jsonl')
md_path    = os.path.join(state_dir, 'improvement-register.md')
archive_path = os.path.join(state_dir, 'improvement-register-archive.jsonl')

# The jsonl is the source of truth and the md is rebuilt from it, but skills
# also append rows to the md. Rows the md has that the jsonl lacks are merged
# in before the rebuild, so an append is never overwritten. Rows this script
# rendered last time (recorded in the md's `rendered` marker) and that have
# since left the jsonl were edited or retired upstream, so they are not merged
# back. Losing that marker errs toward keeping rows, never toward dropping them.
import hashlib, re, shutil

RENDERED_MARKER = re.compile(r'<!--\s*rendered:\s*([0-9a-f,\s]*)-->')

def entry_key(d, etype, text):
    raw = '\x1f'.join([(d or '').strip(), (etype or '').strip().lower(), (text or '').strip()])
    return hashlib.sha1(raw.encode()).hexdigest()[:12]

def read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                out.append(entry)
    return out

def read_md(path):
    rows, rendered = [], None
    if not os.path.exists(path):
        return rows, rendered
    with open(path) as f:
        content = f.read()
    m = RENDERED_MARKER.search(content)
    if m:
        rendered = {k.strip() for k in m.group(1).split(',') if k.strip()}
    for line in content.splitlines():
        s = line.strip()
        if not s.startswith('|') or s.startswith('| #') or re.fullmatch(r'[|\s:-]+', s):
            continue
        parts = [p.strip().replace('\\|', '|') for p in re.split(r'(?<!\\)\|', s)[1:-1]]
        if len(parts) < 4 or not parts[3]:
            continue
        rows.append({'num': parts[0], 'date': parts[1], 'type': parts[2],
                     'entry': ' | '.join(parts[3:]), 'line': s})
    return rows, rendered

def next_lr_id(entries):
    nums = [int(m.group(1)) for e in entries
            for m in [re.fullmatch(r'lr-(\d+)', str(e.get('id', '')))] if m]
    return max(nums, default=0) + 1

jsonl_entries = read_jsonl(jsonl_path)
md_rows, rendered_keys = read_md(md_path)

known = {entry_key(e.get('date'), e.get('type'), e.get('entry'))
         for e in jsonl_entries + read_jsonl(archive_path)}
skip = known | (rendered_keys or set())

added = []
for row in md_rows:
    etype = row['type'].lower() or 'pattern'
    d = row['date'] or str(date.today())
    key = entry_key(d, etype, row['entry'])
    if key in skip:
        continue
    skip.add(key)
    added.append({
        'id': f'lr-{next_lr_id(jsonl_entries + added):03d}',
        'date': d,
        'type': etype,
        'entry': row['entry'],
        'source': 'migrated' if not jsonl_entries else 'md-append',
        'weight': 1.0,
        'decay_exempt': etype in ('correction', 'confirmation'),
    })

if added:
    jsonl_entries += added
    with open(jsonl_path, 'w') as f:
        for e in jsonl_entries:
            f.write(json.dumps(e) + '\n')

# Process jsonl: compute decay, archive low-weight, build summary
reg_count = 0
improvement_register_summary = []

if os.path.exists(jsonl_path):
    active, to_archive = [], []
    for entry in jsonl_entries:
        (to_archive if effective_weight(entry) < 0.1 else active).append(entry)

    if to_archive:
        with open(archive_path, 'a') as f:
            for e in to_archive:
                f.write(json.dumps(e) + '\n')
        with open(jsonl_path, 'w') as f:
            for e in active:
                f.write(json.dumps(e) + '\n')

    active.sort(key=effective_weight, reverse=True)
    reg_count = len(active)
    improvement_register_summary = [e['entry'] for e in active[:5]]

    new_keys = [entry_key(e.get('date'), e.get('type'), e.get('entry')) for e in active]
    kept_keys = set(new_keys) | {entry_key(e.get('date'), e.get('type'), e.get('entry'))
                                 for e in to_archive}
    dropped = [r for r in md_rows
               if entry_key(r['date'] or str(date.today()), r['type'].lower() or 'pattern', r['entry'])
               not in kept_keys]
    if dropped:
        shutil.copyfile(md_path, md_path + '.bak')

    with open(md_path, 'w') as f:
        f.write('# Improvement Register\n\n')
        f.write('<!-- Generated from improvement-register.jsonl. Rows appended below are '
                'merged into it on the next regeneration. -->\n')
        f.write(f"<!-- rendered: {','.join(new_keys)} -->\n\n")
        f.write('| # | Date | Type | Learning |\n')
        f.write('|---|---|---|---|\n')
        for i, e in enumerate(active, 1):
            text = e.get('entry', '').replace('|', '\\|')
            f.write(f"| {i} | {e.get('date','')} | {e.get('type','')} | {text} |\n")

# Last Next: line from checkpoint
checkpoint_next = None
cp_path = os.path.join(state_dir, 'checkpoint.md')
if os.path.exists(cp_path):
    with open(cp_path) as f:
        next_lines = [l for l in f.readlines() if l.strip().startswith('Next:')]
    if next_lines:
        checkpoint_next = next_lines[-1].replace('Next:', '').strip()

# Resolved artifact paths
product_base = '.sweetclaude/product'
strategy_base = '.sweetclaude/strategy'
technical_base = '.sweetclaude/technical'
design_base = '.sweetclaude/design'
privacy_path = os.path.join(project_dir, '.sweetclaude', 'artifact-privacy.yaml')
if os.path.exists(privacy_path):
    with open(privacy_path) as f:
        privacy = yaml.safe_load(f) or {}
    cats = privacy.get('categories', {})
    product_base = cats.get('product', {}).get('base_path', product_base)
    strategy_base = cats.get('strategy', {}).get('base_path', strategy_base)
    technical_base = cats.get('technical', {}).get('base_path', technical_base)
    design_base = cats.get('design', {}).get('base_path', design_base)

# First active milestone
active_milestone = None
milestones_dir = os.path.join(project_dir, product_base, 'milestones')
if os.path.exists(milestones_dir):
    for fn in sorted(os.listdir(milestones_dir)):
        if fn.startswith('MS-') and fn.endswith('.md'):
            with open(os.path.join(milestones_dir, fn)) as f:
                if '**Status:** active' in f.read():
                    active_milestone = fn[:-3]
                    break

awi = phase.get('active_work_item') or {}

# Feature flags from sweetclaude.yaml
sc_features = {}
if os.path.exists(sc_path):
    with open(sc_path) as f:
        sc_data = yaml.safe_load(f) or {}
    sc_features = sc_data.get('features', {})

work_item_artifacts_active = (
    isinstance(sc_features.get('work_item_artifacts'), dict)
    and sc_features['work_item_artifacts'].get('status') == 'active'
)

work_dir = None
if work_item_artifacts_active and awi.get('id'):
    work_dir = os.path.join('.sweetclaude', 'work', awi['id'])

ethos = [
    "Propose, don't ask. Give a recommendation with reasoning. Let the user redirect.",
    "Phase dwelling: never invite advancement. User decides when to move on.",
    "No time estimates. AI speed is not calendar speed.",
    "Concrete examples required. Abstract framing is not sufficient input.",
    "Challenge before acceptance. One framing question or gap before proceeding.",
    "Improvement register: apply learnings silently unless directly relevant.",
]

result = {
    'schema_version': 1,
    'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'project_name': phase.get('project_name', ''),
    'phase_schema_version': phase.get('schema_version', 1),
    'version_stage': phase.get('version_stage', ''),
    'mode': phase.get('mode', ''),
    'deference': phase.get('deference_level', ''),
    'active_work_item': dict(
        id=awi.get('id'),
        title=awi.get('title'),
        type=awi.get('type'),
        phase=awi.get('phase'),
        **({'work_dir': work_dir} if work_dir else {}),
    ),
    'active_milestone': active_milestone,
    'ethos': ethos,
    'improvement_register_count': reg_count,
    'improvement_register_summary': improvement_register_summary,
    'checkpoint_next': checkpoint_next,
    'paths': dict(
        product_base=product_base,
        strategy_base=strategy_base,
        technical_base=technical_base,
        design_base=design_base,
        **({'work_base': '.sweetclaude/work'} if work_item_artifacts_active else {}),
    ),
}

print(yaml.dump(result, default_flow_style=False, sort_keys=False), end='')
PYEOF

# Render pre-flight status block → .sweetclaude/state/session-status.txt
STATUS_OUTPUT="$PROJECT_DIR/.sweetclaude/state/session-status.txt"
export STATUS_OUTPUT

python3 - 2>/dev/null <<'PYEOF2'
import yaml, os, glob, re, subprocess

project_dir = os.environ.get('PROJECT_DIR', '')
state_dir   = os.path.join(project_dir, '.sweetclaude', 'state')
status_out  = os.environ.get('STATUS_OUTPUT', os.path.join(state_dir, 'session-status.txt'))

try:
    with open(os.path.join(state_dir, 'session-state.yaml')) as f:
        ss = yaml.safe_load(f) or {}
except Exception:
    import sys; sys.exit(0)

project_name     = ss.get('project_name') or 'Project'
checkpoint_next  = ss.get('checkpoint_next')
product_base     = ss.get('paths', {}).get('product_base', '.sweetclaude/product')
reg_count        = ss.get('improvement_register_count', 0)
product_base_abs = os.path.join(project_dir, product_base)

def field(content, name):
    m = re.search(rf'\*\*{name}:\*\*\s*(.+)', content)
    return m.group(1).strip() if m else ''

def title_from(content):
    m = re.search(r'^# (.+)', content, re.MULTILINE)
    return m.group(1).strip() if m else ''

DONE = {'done', 'complete', 'achieved', 'closed', 'cancelled'}

try:
    r = subprocess.run(['git', 'status', '--short'],
                       capture_output=True, text=True, cwd=project_dir)
    uncommitted = len([l for l in r.stdout.strip().split('\n') if l.strip()])
except Exception:
    uncommitted = 0

scratch_files = []
scratch_dir = os.path.join(project_dir, 'scratch')
if os.path.isdir(scratch_dir):
    try:
        scratch_files = [f for f in os.listdir(scratch_dir)
                         if re.search(r'checkpoint|continue|resume|handoff', f, re.IGNORECASE)][:5]
    except Exception:
        pass

roadmap, issues, backlog = [], [], []
for f in sorted(glob.glob(os.path.join(product_base_abs, 'roadmap', 'RM-*.md'))):
    try:
        c = open(f).read()
        roadmap.append({'id': os.path.basename(f).split('.')[0],
                        'title': title_from(c), 'status': field(c, 'Status').lower()})
    except Exception: pass

for f in sorted(glob.glob(os.path.join(product_base_abs, 'issues', 'I-*.md'))):
    try:
        c = open(f).read()
        s = field(c, 'Status').lower()
        issues.append({'id': os.path.basename(f).split('.')[0], 'title': title_from(c),
                       'status': s, 'roadmap': field(c, 'Roadmap Item'), 'open': s not in DONE})
    except Exception: pass

_HORIZON_ORDER = {'next': 1, 'sooner': 2, 'soon': 3, 'later': 4, 'someday': 5}
for f in sorted(glob.glob(os.path.join(product_base_abs, 'backlog', 'ISSUE-*.md'))):
    try:
        c = open(f).read()
        s = field(c, 'Status').lower()
        p = field(c, 'Priority').upper()
        h_raw = field(c, 'Horizon').lower()
        h = h_raw if h_raw in _HORIZON_ORDER else 'unscheduled'
        if 'DONE' not in s.upper() and 'COMPLETE' not in s.upper():
            backlog.append({'id': os.path.basename(f).split('.')[0],
                            'title': title_from(c), 'priority': p, 'status': s,
                            'horizon': h, 'horizon_order': _HORIZON_ORDER.get(h, 6)})
    except Exception:
        pass

in_progress = [i for i in issues if i['open'] and i['status'] == 'in_progress']
open_issues  = [i for i in issues if i['open']]
rm_achieved  = [r for r in roadmap if r['status'] in {'complete', 'achieved'}]
rm_active    = [r for r in roadmap if r['status'] in {'in_progress', 'active'}]
rm_planned   = [r for r in roadmap if r['status'] not in {'complete','achieved','in_progress','active'}]
_HORIZON_LABELS = ['next', 'sooner', 'soon', 'later', 'someday', 'unscheduled']
bl_by_horizon = {h: [b for b in backlog if b['horizon'] == h] for h in _HORIZON_LABELS}

L = []
L.append(project_name)
L.append('═' * 36)
L.append('')
L.append('UNFINISHED WORK')
L.append('─' * 15)
uf = []
if uncommitted > 0:
    uf.append(f'· {uncommitted} uncommitted file(s) in working tree')
if checkpoint_next:
    uf.append(f'· Checkpoint: {checkpoint_next}')
if scratch_files:
    uf.append(f'· Scratch: {", ".join(scratch_files)}')
if in_progress:
    ids = ', '.join(i['id'] for i in in_progress)
    uf.append(f'· {len(in_progress)} issue(s) in progress: {ids}')
L.extend(uf if uf else ['· Nothing open.'])

L.append('')
L.append('ROADMAP')
L.append('─' * 7)
if not roadmap:
    L.append('No roadmap configured. Ask me to build one.')
else:
    L.append(f'{len(roadmap)} items: {len(rm_achieved)} achieved · {len(rm_active)} active · {len(rm_planned)} planned')
    if rm_active:
        L.append('')
        L.append('  Active:')
        for r in rm_active:
            L.append(f'    {r["id"]}: {r["title"]}')
    elif rm_planned:
        L.append('')
        L.append('  Up next:')
        for r in rm_planned[:3]:
            L.append(f'    {r["id"]}: {r["title"]}')

L.append('')
L.append('EPICS')
L.append('─' * 5)
if not open_issues:
    L.append('No open epics.')
else:
    rm_lookup = {r['id']: r['title'] for r in roadmap}
    grouped, unlinked = {}, []
    for issue in open_issues:
        rm_id = (issue.get('roadmap') or '').strip()
        if rm_id and rm_id not in {'(none)', 'none', ''}:
            grouped.setdefault(rm_id, []).append(issue)
        else:
            unlinked.append(issue)
    if grouped or unlinked:
        for rm_id in sorted(grouped.keys()):
            L.append(f'  {rm_id} — {rm_lookup.get(rm_id, rm_id)}:')
            for issue in grouped[rm_id]:
                L.append(f'    · {issue["id"]}: {issue["title"]} [{issue["status"]}]')
        if unlinked:
            L.append('  Unlinked:')
            for issue in unlinked:
                L.append(f'    · {issue["id"]}: {issue["title"]} [{issue["status"]}]')
    else:
        L.append('No open epics.')

L.append('')
L.append('BACKLOG')
L.append('─' * 7)
if not backlog:
    L.append('Backlog is clear.')
else:
    total_bl = len(backlog)
    bucket_counts = ' · '.join(
        f'{len(bl_by_horizon[h])} {h}'
        for h in _HORIZON_LABELS if bl_by_horizon[h]
    )
    L.append(f'{total_bl} open: {bucket_counts}')
    for h in _HORIZON_LABELS:
        items = bl_by_horizon[h]
        if not items:
            continue
        label = 'UNSCHEDULED' if h == 'unscheduled' else h.upper()
        suffix = ' — no horizon set' if h == 'unscheduled' else ''
        L.append('')
        L.append(f'  {label} ({len(items)}{suffix})')
        for b in items[:5]:
            badge = f'[{b["priority"]}]' if b['priority'] else '[—]'
            L.append(f'    · {b["id"]}  {badge}  {b["title"]}')
    if total_bl > 10:
        L.append(f"  ({total_bl} total — ask me to run a backlog triage if it's getting unwieldy)")

L.append('')
if reg_count > 0:
    noun = 'learnings' if reg_count != 1 else 'learning'
    L.append(f'I absorbed {reg_count} new {noun} from previous sessions. Feel free to ask about them if you want.')
    L.append('')
L.append("Anything you want to look at more closely, or is there something above you'd like to work on — or something else entirely?")

with open(status_out, 'w') as f:
    f.write('\n'.join(L))
PYEOF2
