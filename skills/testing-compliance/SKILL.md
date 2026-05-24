---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Compliance control testing and evidence collection."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:testing-compliance" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
COMPLIANCE_FILE="$PWD/.sweetclaude/state/compliance.yaml"
cat "$COMPLIANCE_FILE" 2>/dev/null || echo "COMPLIANCE_NOT_FOUND"

# Security planning state (from security-planning skill if run)
cat "$PWD/.sweetclaude/state/security-planning.yaml" 2>/dev/null | python3 -c "
import yaml, sys
d = yaml.safe_load(sys.stdin)
standards = d.get('applicable_standards', [])
print(f'PLANNED_STANDARDS={standards}')
" 2>/dev/null || echo "PLANNED_STANDARDS=[]"
```

# Testing Compliance

Track compliance control status, log evidence, and surface gaps. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `status` | → **Status** — overall compliance coverage |
| `assess <standard>` | → **Assess** — gap analysis for a standard |
| `log <control-id>` | → **Log evidence** for a control |
| `report` | → **Generate** gap report |
| `init <standard>` | → **Initialize** tracking for a new standard |

Valid standard names: `soc2`, `hipaa`, `gdpr`, `pci_dss`

---

## Status

Use `COMPLIANCE_NOT_FOUND` or compliance state from shell block.

If `COMPLIANCE_NOT_FOUND`: "No compliance tracking initialized. Run `testing-compliance init <standard>` to start."

Otherwise present:

```
Compliance Status
══════════════════════════════════════════════════

SOC 2 (Security TSC)
  Tested:           12 / 34 controls
  Evidence logged:   9 / 12 tested
  Gaps:              3 controls with no mitigation

GDPR
  Tested:            6 / 18 controls
  Evidence logged:   4 / 6 tested
  Gaps:              7 controls not started
```

---

## Init

Arguments: `init <standard>`

Ask: "Which Trust Service Categories / modules apply?"

**SOC 2:** Security (required) + optional: Availability, Processing Integrity, Confidentiality, Privacy

**HIPAA:** Administrative Safeguards, Physical Safeguards, Technical Safeguards

**GDPR:** Lawful Basis & Consent, Data Subject Rights, Data Minimization, Security & Breach, DPO & Documentation, International Transfers

**PCI-DSS:** All 12 requirements (ask which apply based on card data scope)

Load the control set for the selected modules. Write to compliance.yaml:

```bash
python3 - <<'PYEOF'
import yaml
from datetime import datetime

# Load existing or create new
try:
    with open('.sweetclaude/state/compliance.yaml') as f:
        state = yaml.safe_load(f) or {}
except FileNotFoundError:
    state = {'schema_version': 1, 'standards': {}}

# Add new standard with controls
# <standard> and controls populated from control catalog below
state['standards']['<standard>'] = {
    'initialized_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'modules': ['<selected modules>'],
    'controls': {
        '<control-id>': {
            'title': '<control title>',
            'status': 'not_started',
            'evidence': [],
            'notes': None
        }
        # ... all controls
    }
}

with open('.sweetclaude/state/compliance.yaml', 'w') as f:
    yaml.dump(state, f, default_flow_style=False, allow_unicode=True)
print('ok')
PYEOF
```

Confirm: `Initialized {standard} — {N} controls loaded`

---

## Control Catalogs

### SOC 2 — Security TSC (CC series, key controls)

| ID | Control |
|---|---|
| CC1.1 | Management demonstrates commitment to integrity and ethical values |
| CC1.2 | Board oversees internal controls |
| CC2.1 | Internal and external communication channels exist for compliance |
| CC3.1 | Risk assessment process defined and operating |
| CC3.2 | Fraud risk considered in risk assessment |
| CC4.1 | Monitoring activities evaluate controls |
| CC5.1 | Control activities are selected to mitigate risks |
| CC6.1 | Logical access security — authentication implemented |
| CC6.2 | Access provisioning process exists |
| CC6.3 | Access removal process exists |
| CC6.6 | Logical access restricted to authorized users only |
| CC6.7 | Transmission of sensitive data protected |
| CC6.8 | Malware detection controls in place |
| CC7.1 | Vulnerability scanning and patch management |
| CC7.2 | Anomaly detection processes in place |
| CC7.3 | Security events evaluated and responded to |
| CC7.4 | Incident response process defined |
| CC8.1 | Change management process controls infrastructure changes |
| CC9.1 | Risk mitigation activities in place |
| CC9.2 | Vendor risk management process exists |

### HIPAA — Technical Safeguards (key controls)

| ID | Control |
|---|---|
| TS-1 | Unique user identification for PHI access |
| TS-2 | Emergency access procedure for PHI |
| TS-3 | Automatic logoff after inactivity |
| TS-4 | Encryption/decryption of PHI |
| TS-5 | Audit controls — hardware/software activity logging |
| TS-6 | Integrity controls — PHI not improperly altered or destroyed |
| TS-7 | Person or entity authentication for PHI systems |
| TS-8 | Transmission security — PHI encrypted in transit |

### GDPR — Key controls

| ID | Control |
|---|---|
| G-1 | Lawful basis documented for each processing activity |
| G-2 | Consent mechanism implemented (if consent is the basis) |
| G-3 | Privacy notice published and accurate |
| G-4 | Data subject access request process defined |
| G-5 | Right to deletion (erasure) process defined |
| G-6 | Data portability process defined |
| G-7 | Data minimization — only necessary data collected |
| G-8 | Retention policy defined and enforced |
| G-9 | Data processing register (Record of Processing Activities) maintained |
| G-10 | Data breach detection and notification process (72-hour rule) |
| G-11 | DPO appointed or appointment decision documented |
| G-12 | International transfer mechanism (SCCs, adequacy decision) if applicable |
| G-13 | Vendor DPA agreements in place |
| G-14 | Privacy by design and default in new features |
| G-15 | Security measures appropriate to risk (Article 32) |

---

## Assess

Arguments: `assess <standard>`

Load controls from compliance.yaml. For each control not yet `tested` or `not_applicable`:

Present one control at a time:

```
─────────────────────────────────────────
Control CC6.1 — Logical access security

  Authentication implemented for all user-facing systems.

  Status:  not_started

  Questions to assess:
    1. Is authentication required for all access to protected resources?
    2. What authentication mechanism is in use?
    3. Is there a password policy or equivalent?
    4. Are privileged accounts using stronger controls (MFA)?
```

Wait for user response. Classify result:

- **Pass** — control is implemented, evidence exists or can be collected
- **Partial** — control partially implemented, gaps identified
- **Gap** — control not implemented, risk accepted or remediation needed
- **N/A** — control does not apply (must give reason)

```bash
python3 - <<'PYEOF'
import yaml
from datetime import datetime

with open('.sweetclaude/state/compliance.yaml') as f:
    state = yaml.safe_load(f)

state['standards']['<standard>']['controls']['<control-id>']['status'] = '<pass|partial|gap|na>'
state['standards']['<standard>']['controls']['<control-id>']['notes'] = '<assessment notes>'
state['standards']['<standard>']['controls']['<control-id>']['assessed_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')

with open('.sweetclaude/state/compliance.yaml', 'w') as f:
    yaml.dump(state, f, default_flow_style=False, allow_unicode=True)
print('ok')
PYEOF
```

For `gap` status: ask "File a remediation issue?" On yes — create a project issue:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create issue '{
  "title": "Compliance gap: <control title>",
  "type": "story",
  "status": "backlog",
  "priority": "sooner",
  "description": "<gap description and remediation approach>",
  "tags": ["compliance", "<standard>", "<control-id>"]
}'
```

---

## Log Evidence

Arguments: `log <control-id>`

Ask:
1. "What evidence exists for this control? (description)"
2. "Where is it stored? (file path, URL, or description)"
3. "Date of evidence?"

```bash
python3 - <<'PYEOF'
import yaml
from datetime import datetime

with open('.sweetclaude/state/compliance.yaml') as f:
    state = yaml.safe_load(f)

# Find the control across all standards
for std_name, std_data in state['standards'].items():
    if '<control-id>' in std_data.get('controls', {}):
        ctrl = std_data['controls']['<control-id>']
        if 'evidence' not in ctrl:
            ctrl['evidence'] = []
        ctrl['evidence'].append({
            'description': '<description>',
            'location': '<location>',
            'date': '<date>',
            'logged_at': datetime.now(timezone.utc).isoformat(timespec='seconds')
        })
        break

with open('.sweetclaude/state/compliance.yaml', 'w') as f:
    yaml.dump(state, f, default_flow_style=False, allow_unicode=True)
print('ok')
PYEOF
```

Confirm: `Evidence logged for <control-id>`

---

## Report

Generate a gap report for all initialized standards.

```
Compliance Gap Report — {date}
══════════════════════════════════════════════════

SOC 2 — Security TSC
  Pass:           18 controls
  Partial:         4 controls
  Gap:             3 controls
  Not applicable:  5 controls
  Not assessed:    4 controls

  Gaps requiring remediation:
    CC7.1  Vulnerability scanning — no automated scan in place
    CC9.2  Vendor risk management — no vendor review process
    CC8.1  Change management — deploys not logged or reviewed

  Partial controls:
    CC6.1  Authentication — MFA not enforced for admin accounts
    ...

GDPR
  ...

Open remediation issues: {N}
  I-042  Compliance gap: CC7.1 Vulnerability scanning    priority: sooner
  I-043  Compliance gap: CC9.2 Vendor risk management    priority: later
```

If saving: write to `.sweetclaude/testing/compliance-report-{date}.md`.

---

## Rules

- Gaps must have a remediation issue or a documented risk acceptance. Neither is optional — "we know about it" is not a status.
- N/A requires a documented reason. Challenge N/A on controls that seem applicable.
- Evidence location is required for `pass` controls at audit time. Prompt for it if missing.
- Compliance state is sensitive. It lives in `.sweetclaude/state/` — always private, never committed to public repos.
- This skill supports compliance preparation — it does not constitute a formal audit. Always confirm with a qualified auditor before making compliance claims to customers.
