---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Show the full project at a glance — milestones in roadmap pipeline order with nested work items. Trigger on: 'big picture', 'whole project status', 'full status', 'what's the full state', 'project overview', 'where is everything', 'show me everything'."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Big Picture

Render the full project as a milestone pipeline. Milestones in dependency order. Work items nested under each. No background agents — reads state files directly.

## Step 0: v4 lint check

Before rendering the pipeline, run the v4 lint rules from `sweetclaude:_health` Step 3 inline. If any findings are present, surface them before the normal output:

```
## v4 Storage Warnings
- counter-drift:story (stored=3, max_id_seen=5)
- done-status-mismatch:STORY-002-foo.md has status=done but is not in done/
```

Roadmap-related warnings (cross-location-duplicate-id, roadmap-epic-structure) remain inert until Phase 2 (gated by `docs/product/roadmap/` existence). Counter-drift and done-status-mismatch findings are always surfaced.

Proceed to Step 1 regardless of findings — this is informational, not blocking.

## Step 1: Schema check

Use `phase_schema_version` from pre-loaded session state above:
- If absent or `1`: warn — "Your config is on schema v1. Run `/sweetclaude:update` to upgrade." Stop.
- If `2`: proceed.

## Step 2: Read artifact path

```bash
product_base=$(python3 -c "
import yaml, sys
d = yaml.safe_load(open('.sweetclaude/state/session-state.yaml')) or {}
print(d.get('paths', {}).get('product_base', '.sweetclaude/product'))
" 2>/dev/null || echo ".sweetclaude/product")

echo "PRODUCT_BASE=$product_base"
ls ${product_base}/milestones/MS-*.md 2>/dev/null || echo "NO_MILESTONES"
ls ${product_base}/backlog/BL-*.md 2>/dev/null | head -200 || echo "NO_BACKLOG"
ls ${product_base}/stories/US-*.md 2>/dev/null | head -200 || echo "NO_STORIES"
```

If output contains `NO_MILESTONES`, output:
> No milestones configured. Run `/sweetclaude:product-milestones` to create your first milestone.

Stop.

## Step 3: Build the pipeline

Run this Python block inline:

```bash
product_base=$(python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/session-state.yaml')) or {}
print(d.get('paths', {}).get('product_base', '.sweetclaude/product'))
" 2>/dev/null || echo ".sweetclaude/product")

python3 - "$product_base" << 'PYEOF'
import sys, os, re, glob, json

base = sys.argv[1]

def field(content, name):
    # Try markdown bold format first: **Name:** value
    m = re.search(rf'\*\*{name}:\*\*\s*(.+)', content)
    if m:
        return m.group(1).strip()
    # Fall back to YAML frontmatter: name: value (case-insensitive key)
    fm = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm:
        ym = re.search(rf'^{re.escape(name.lower())}:\s*(.+)', fm.group(1), re.MULTILINE | re.IGNORECASE)
        if ym:
            return ym.group(1).strip().strip('"\'')
    return ''

def h1(content):
    # Try YAML frontmatter title first, then fall back to markdown H1
    fm = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm:
        tm = re.search(r'^title:\s*(.+)', fm.group(1), re.MULTILINE)
        if tm:
            return tm.group(1).strip().strip('"\'')
    m = re.search(r'^# (.+)', content, re.MULTILINE)
    return m.group(1).strip() if m else ''

def status_tag(raw):
    s = raw.lower()
    if any(x in s for x in ['done', 'complete', 'achieved', 'shipped']):
        return 'done'
    if 'active' in s or 'in_progress' in s or 'in progress' in s:
        return 'active'
    if 'blocked' in s:
        return 'blocked'
    if 'proposed' in s:
        return 'proposed'
    if 'paused' in s:
        return 'paused'
    return s or 'unknown'

# --- Load milestones ---
milestones = {}
for f in sorted(glob.glob(os.path.join(base, 'milestones', 'MS-*.md'))):
    if 'INDEX' in f.upper():
        continue
    c = open(f).read()
    m = re.match(r'(MS-\d+)', os.path.basename(f))
    if not m:
        continue
    ms_id = m.group(1)
    status_raw = field(c, 'Status')

    # Parse depends_on — can be "MS-001 (title), MS-002 (title)" or "MS-001"
    depends_raw = field(c, 'Depends on')
    depends_on = []
    for part in re.split(r'[,;]', depends_raw):
        dm = re.match(r'\s*(MS-\d+)', part.strip())
        if dm:
            depends_on.append(dm.group(1))

    # Parse contributing work items section
    contrib_match = re.search(r'## Contributing work items\s*\n(.*?)(?=\n##|\Z)', c, re.DOTALL)
    work_items = []
    if contrib_match:
        for line in contrib_match.group(1).strip().splitlines():
            lm = re.match(r'-\s*(BL-\d+)\s*[—–-]\s*(.+?)(?:\s+\((.+?)\))?\s*$', line.strip())
            if lm:
                work_items.append({
                    'id': lm.group(1),
                    'title': lm.group(2).strip(),
                    'status_inline': lm.group(3) or '',
                })

    milestones[ms_id] = {
        'id': ms_id,
        'title': h1(c),
        'status_raw': status_raw,
        'status_tag': status_tag(status_raw),
        'depends_on': depends_on,
        'work_items': work_items,
    }

# --- Load backlog items (for current status) ---
bl_cache = {}
for f in sorted(glob.glob(os.path.join(base, 'backlog', 'BL-*.md'))):
    if 'INDEX' in f.upper():
        continue
    c = open(f).read()
    bm = re.match(r'(BL-\d+)', os.path.basename(f))
    if not bm:
        continue
    bl_id = bm.group(1)
    bl_cache[bl_id] = {
        'id': bl_id,
        'title': h1(c),
        'status_raw': field(c, 'Status'),
        'status_tag': status_tag(field(c, 'Status')),
        'milestone': field(c, 'Milestone'),
    }

# --- Load stories (optional — keyed by backlog item if linked) ---
story_map = {}  # BL-NNN -> [story objects]
for f in sorted(glob.glob(os.path.join(base, 'stories', 'US-*.md'))):
    c = open(f).read()
    sm = re.match(r'(US-\d+)', os.path.basename(f))
    if not sm:
        continue
    us_id = sm.group(1)
    bl_ref = field(c, 'Backlog Item') or field(c, 'Backlog') or field(c, 'BL')
    bl_ref_m = re.match(r'(BL-\d+)', bl_ref.strip()) if bl_ref else None
    if bl_ref_m:
        bl_key = bl_ref_m.group(1)
        if bl_key not in story_map:
            story_map[bl_key] = []
        story_map[bl_key].append({
            'id': us_id,
            'title': h1(c),
            'status_tag': status_tag(field(c, 'Status')),
        })

# --- Topological sort milestones ---
def topo_sort(ms_dict):
    visited = set()
    order = []

    def visit(ms_id):
        if ms_id in visited or ms_id not in ms_dict:
            return
        visited.add(ms_id)
        for dep in ms_dict[ms_id]['depends_on']:
            visit(dep)
        order.append(ms_id)

    for ms_id in sorted(ms_dict.keys()):
        visit(ms_id)
    return order

sorted_ids = topo_sort(milestones)

# --- Build output ---
output = []
prev_id = None

for ms_id in sorted_ids:
    ms = milestones[ms_id]
    tag = ms['status_tag']

    # Show ↓ arrow if this milestone directly depends on the previous one
    if prev_id and prev_id in ms['depends_on'] and tag not in ('done',):
        output.append('↓')

    # Milestone line
    ms_short_title = re.sub(r'^MS-\d+:\s*', '', ms['title'])  # strip "MS-NNN: " prefix if present
    if tag == 'done':
        ms_line = f"{ms_id} ✓  {ms_short_title}"
    elif tag == 'active':
        extra_deps = [d for d in ms['depends_on'] if milestones.get(d, {}).get('status_tag') == 'done']
        extra_note = ''
        if extra_deps and len(ms['depends_on']) > 1:
            extra_note = '  (also requires ' + ', '.join(
                f"{d} ✓" for d in extra_deps if milestones.get(d, {}).get('status_tag') == 'done'
            ) + ')'
        ms_line = f"{ms_id}  {ms_short_title}  [active]{extra_note}"
    else:
        ms_line = f"{ms_id}  {ms_short_title}  [{tag}]"

    output.append(ms_line)

    # Work items
    work_items = ms['work_items']
    for i, wi in enumerate(work_items):
        is_last = (i == len(work_items) - 1)
        connector = '└──' if is_last else '├──'
        cont = '    ' if is_last else '│   '

        # Prefer live status from bl_cache over inline annotation
        bl = bl_cache.get(wi['id'])
        if bl:
            bl_status = bl['status_tag']
            bl_title = bl['title']
            bl_title_clean = re.sub(r'^BL-\d+:\s*', '', bl_title)
        else:
            bl_status = status_tag(wi['status_inline'])
            bl_title_clean = wi['title']

        done_mark = ' ✓' if bl_status == 'done' else ''
        bl_line = f"{connector} {wi['id']}{done_mark}  {bl_title_clean}"
        output.append(bl_line)

        # Stories under this BL item
        stories = story_map.get(wi['id'], [])
        for j, story in enumerate(stories):
            is_last_story = (j == len(stories) - 1)
            s_conn = cont + ('└──' if is_last_story else '├──')
            s_done = ' ✓' if story['status_tag'] == 'done' else ''
            s_title_clean = re.sub(r'^US-\d+:\s*', '', story['title'])
            output.append(f"{s_conn} {story['id']}{s_done}  {s_title_clean}")

    prev_id = ms_id

# --- Derive summary counts ---
total = len(sorted_ids)
done_count = sum(1 for ms in milestones.values() if ms['status_tag'] == 'done')
active_count = sum(1 for ms in milestones.values() if ms['status_tag'] == 'active')
remaining = total - done_count

print(f"SUMMARY:{total}:{done_count}:{active_count}:{remaining}")
print('\n'.join(output))
PYEOF
```

## Step 4: Render

Parse the output from Step 3.

The first line starting with `SUMMARY:` contains `total:done:active:remaining` counts.
All subsequent lines are the pipeline display.

Output in this format. Use clean markdown — no ANSI codes, no horizontal dividers.

---

**{project name}** · {version_stage}

### Milestone Pipeline

`{total} milestones · {done} done · {active} active · {remaining} remaining`

Then output the pipeline lines verbatim, preserving `↓`, `├──`, `└──`, `│   `, and status annotations exactly as produced by Step 3.

If no milestones were produced (empty pipeline), output:
> No milestones found. Run `/sweetclaude:product-milestones` to create your first milestone.

---

Then output:

### Active Work

- If there is an `active_work_item` set in pre-loaded session state with a non-null `id`, output:
  > Currently in progress: **{id}** — {title} [{phase}]
- Otherwise:
  > No work item currently active. Run `/sweetclaude:go` to pick up where you left off.

---

Output nothing else. No closing question. No framework health. No trailing prompts.
