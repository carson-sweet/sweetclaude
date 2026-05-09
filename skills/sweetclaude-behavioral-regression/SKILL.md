---
user-invocable: false
description: "Validates that mode enforcement is working correctly across all four modes."
version: 1.0.0
---

# SweetClaude Behavioral Regression

Run after implementing or modifying the modes system. Validates all three enforcement layers.

## Layer 1: Automated Tests

Run these commands. All must pass before proceeding to Layer 2.

```bash
# 1. Verify mode-gates.yaml is valid and has all four modes
python3 -c "
import yaml
with open('config/mode-gates.yaml') as f: d=yaml.safe_load(f)
modes = set(d.get('mode_defaults',{}).keys())
required = {'flow','kanban','shape_up','agile'}
missing = required - modes
assert not missing, f'Missing modes: {missing}'
print('PASS: mode-gates.yaml valid, all four modes present')
"

# 2. generate-effective-gates works for all four modes
for mode in flow kanban shape_up agile; do
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/.sweetclaude/state"
    printf "schema_version: 2\nmode: %s\n" "$mode" > "$tmpdir/.sweetclaude/state/sweetclaude.yaml"
    PROJECT_DIR="$tmpdir" bash scripts/generate-effective-gates.sh \
        && echo "PASS: effective-gates compiled for $mode" \
        || echo "FAIL: effective-gates failed for $mode"
    rm -rf "$tmpdir"
done

# 3. Artifact schema tests
python3 -m pytest tests/hooks/test-sc-artifact-impl.py -v

# 4. WIP limit hook tests
bash tests/hooks/test-wip-limit.sh

# 5. generate-effective-gates tests
bash tests/scripts/test-generate-effective-gates.sh
```

## Layer 2: Skill MODE_CHECK — Manual Checklist

For each check: set the mode in a test project's sweetclaude.yaml, invoke the skill, verify behavior.

- [ ] **project-sprints in flow mode:** Expected: blocked message with alternative. No sprint operation attempted.
- [ ] **project-sprints in kanban mode:** Expected: same blocked message.
- [ ] **project-sprints in shape_up mode:** Expected: blocked message mentioning cycles.
- [ ] **project-sprints in agile mode:** Expected: proceeds normally.
- [ ] **project-backlog in shape_up mode:** Expected: blocked message directing to pitches.
- [ ] **project-backlog in flow/kanban/agile:** Expected: proceeds normally.
- [ ] **project-issues create in shape_up without pitch:** Expected: asks for pitch source, blocks if none.
- [ ] **project-issues create in shape_up with pitch_id:** Expected: creates issue with pitch_id field.
- [ ] **project-assess-shape full flow (no mode set):** Expected: 5 questions one at a time. Mode written after confirmation. effective-gates.yaml generated.
- [ ] **project-assess-shape skip:** Expected: mode: flow written, effective-gates compiled, no questions.
- [ ] **project-mode shift agile (from kanban):** Expected: cascade check asks about backlog/epics. generate-effective-gates runs after. effective-gates shows mode: agile.
- [ ] **project-mode shift kanban (from agile with active sprint):** Expected: blocked until sprint closed.
- [ ] **Shape Up DEFINE — solo betting table:** Expected: 3 questions asked. Answers written to pitch artifact. Issues updated with betting_table_approved: true.

## Layer 3: Gate Enforcement — Manual Checklist

- [ ] **Kanban WIP block:** Set mode=kanban, wip_limit=2. Create 2 in_progress issues. Attempt IMPLEMENT entry. Expected: Bash hook blocks with "2/2 items in_progress" message.
- [ ] **Kanban WIP allow:** Same setup with 1 in_progress. Expected: proceeds.
- [ ] **Shape Up betting table gate:** Set mode=shape_up. Issue without betting_table_approved. Attempt IMPLEMENT. Expected: go skill blocks with betting table message.
- [ ] **Agile no-sprint gate:** Set mode=agile, no active sprint. Attempt IMPLEMENT. Expected: go skill blocks with sprint message.
- [ ] **Status drift — Kanban at limit:** mode=kanban, wip_limit=3, 3 in_progress issues. Run /sweetclaude:status. Expected: WIP warning in output.
- [ ] **Status drift — Agile no sprint:** mode=agile, no active sprint, phase=IMPLEMENT. Expected: drift warning in status.

## Regression Report

After completing all layers, report:

```
Layer 1 (automated): N/N tests passed
Layer 2 (skills — manual): N/N checks passed
Layer 3 (gates — manual): N/N checks passed

Overall: PASS / FAIL
```

Any failure is a blocking issue. Do not declare the modes system complete until all checks pass.
