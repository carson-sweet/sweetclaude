---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:testing-accessibility
user-invocable: true
description: "WCAG 2.1 Level AA audit. Automated scan guidance + manual keyboard, screen reader, and visual checklist. Findings filed as issues."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"

ls .sweetclaude/testing/accessibility/A11Y-*.md 2>/dev/null | wc -l | xargs -I{} echo "AUDIT_COUNT={}"
ls .sweetclaude/testing/accessibility/A11Y-*.md 2>/dev/null | tail -3

# Open a11y issues
sc_artifact_query issue status=backlog,ready,in_progress 2>/dev/null | \
  python3 -c "
import json, sys
items = json.load(sys.stdin)
a11y = [i for i in items if 'accessibility' in str(i.get('tags',[])).lower() or 'a11y' in str(i.get('tags',[])).lower()]
print(f'OPEN_A11Y_ISSUES={len(a11y)}')
" 2>/dev/null || echo "OPEN_A11Y_ISSUES=0"
```

# Testing Accessibility

WCAG 2.1 Level AA audit — automated scan, keyboard, screen reader, and visual checks. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `audit` | → **Start** a new accessibility audit |
| `list` | → **List** past audits |
| `view <A11Y-NNN>` | → **View** audit report |
| `findings` | → **List** open accessibility issues |

---

## Audit

### Step 1: Scope

"What are you auditing?"
- A specific page or flow (e.g., "login page", "checkout flow")
- The full application
- A component or widget (e.g., "date picker", "modal")

"What's the URL or path?"

"WCAG conformance target?" Default: `AA`. Accept: `A`, `AA`, `AAA`.

Note: WCAG 2.1 Level AA is the standard required for most legal compliance (ADA, EN 301 549, AODA).

---

### Step 2: Automated scan

Guide the user through running an automated scan.

**Recommended tools:**
- **axe DevTools** (browser extension) — most widely used, low false-positive rate
- **WAVE** (browser extension) — visual overlays, good for contrast
- **Lighthouse** (Chrome DevTools → Lighthouse → Accessibility) — integrated, gives a score
- **Pa11y** (CLI) — `pa11y <url>` for CI integration

"Run your preferred tool against {scope} and share the results."

On results input — parse or summarize:
- Count of violations by severity (critical, serious, moderate, minor)
- Most common violation types

Note: "Automated tools catch ~30–40% of WCAG failures. Manual testing covers the rest."

---

### Step 3: Keyboard navigation

Walk through keyboard testing checklist. Present items in groups. Mark each pass/fail/na:

**Focus and navigation**
- [ ] All interactive elements reachable by Tab
- [ ] Tab order follows visual/logical reading order
- [ ] Focus indicator visible on all interactive elements (not removed by `outline: none` without replacement)
- [ ] No keyboard trap — focus can always move away from a component

**Interaction**
- [ ] All button and link actions triggerable with Enter or Space
- [ ] Dropdowns and menus operable with arrow keys
- [ ] Modals/dialogs trap focus while open and return focus on close
- [ ] Date pickers and custom widgets operable without a mouse

**Skip navigation**
- [ ] "Skip to main content" link present and functional (first focusable element)

---

### Step 4: Screen reader

"Test with a screen reader. Recommended:"
- macOS: VoiceOver (`Cmd + F5`)
- Windows: NVDA (free) or JAWS
- Mobile: iOS VoiceOver, Android TalkBack

Checklist:

**Images and icons**
- [ ] Decorative images have `alt=""` (empty string, not missing)
- [ ] Informative images have descriptive alt text
- [ ] Icon-only buttons have accessible labels (aria-label or visually hidden text)

**Structure and navigation**
- [ ] Page has a single `<h1>` that describes the page purpose
- [ ] Heading hierarchy is logical (h1 → h2 → h3, no skipping levels)
- [ ] Landmark regions present: `<main>`, `<nav>`, `<header>`, `<footer>`
- [ ] Links have descriptive text (not "click here" or "read more")

**Forms**
- [ ] All form inputs have associated `<label>` elements
- [ ] Required fields indicated programmatically (not just by color or asterisk)
- [ ] Error messages associated with their input via `aria-describedby`
- [ ] Error summary at top of form after failed submission

**Dynamic content**
- [ ] Status messages announced via `role="status"` or `aria-live`
- [ ] Modal open/close announced
- [ ] Loading states communicated (not just visual spinner)

**Tables**
- [ ] Data tables have `<th>` with `scope` attributes
- [ ] Complex tables have `id`/`headers` associations

---

### Step 5: Visual and cognitive

**Color contrast**
- [ ] Text contrast ratio ≥ 4.5:1 (normal text) — check with browser devtools or contrast checker
- [ ] Large text contrast ratio ≥ 3:1 (18pt regular or 14pt bold)
- [ ] UI components and icons contrast ratio ≥ 3:1 against background
- [ ] Information not conveyed by color alone (also shape, label, or pattern)

**Text and readability**
- [ ] Text can be resized to 200% without loss of content or functionality
- [ ] No horizontal scrolling at 320px viewport width (most mobile devices)
- [ ] Line height, letter spacing adjustable via user stylesheet without breaking layout

**Motion and animation**
- [ ] Animations respect `prefers-reduced-motion` media query
- [ ] No content flashes more than 3 times per second (seizure risk)
- [ ] Auto-playing video/audio has a pause/stop control

**Timeouts**
- [ ] Users warned before session timeout with option to extend
- [ ] Timed interactions have at least 20x default time available

---

### Step 6: Findings and filing

Compile violations across all steps. Classify:

| Severity | Definition |
|---|---|
| **Critical** | Users with disabilities cannot complete the task at all |
| **Serious** | Significantly difficult — workaround possible but painful |
| **Moderate** | Annoying or confusing, task completable with effort |
| **Minor** | Small friction, minimal impact |

Map to issue priority:
- Critical → `next`
- Serious → `sooner`
- Moderate → `soon`
- Minor → `later`

Present findings list:

```
Accessibility Audit: A11Y-NNN
Scope:  {scope}
Target: WCAG 2.1 AA
Date:   {date}

Findings ({N} total)
  [Critical]  Missing alt text on product images — screen readers announce "image"
  [Serious]   Focus indicator removed on all buttons (outline: none)
  [Serious]   Form errors not associated with inputs
  [Moderate]  Heading levels skip from h1 to h3 on settings page
  [Minor]     "Read more" links not descriptive
```

For each Critical and Serious finding, ask: "File as issue?" On yes:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_create issue '{
  "title": "A11y: <finding title>",
  "type": "bug",
  "status": "backlog",
  "priority": "<priority>",
  "description": "<WCAG criterion violated>\n\nIssue: <description>\nAffected: <element or page>\nRemediation: <suggested fix>",
  "tags": ["accessibility", "a11y", "A11Y-NNN"]
}'
```

---

### Step 7: Save audit

```bash
mkdir -p .sweetclaude/testing/accessibility/
```

Write `.sweetclaude/testing/accessibility/A11Y-NNN.md` with scope, date, checklist results, findings, and issues filed.

Present summary:

```
A11Y-NNN complete
Scope:    {scope}
Standard: WCAG 2.1 AA

Automated:    {N} violations found
Keyboard:     {pass}/{total} checks passed
Screen reader:{pass}/{total} checks passed
Visual:       {pass}/{total} checks passed

Findings:  {N} total ({critical} critical, {serious} serious, {moderate} moderate, {minor} minor)
Filed:     {N} issues
```

---

## Findings

Load open issues tagged `accessibility` or `a11y`:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue status=backlog,ready,in_progress
```

Present grouped by priority. If none: "No open accessibility issues."

---

## Rules

- Critical findings block release for anything targeting WCAG AA compliance. State this explicitly.
- Automated tools are the starting point, not the audit. A 100% Lighthouse score does not mean WCAG AA conformance.
- "We'll add accessibility later" has compound interest: retrofitting is significantly more expensive than building it in. Surface this if the team hasn't started.
- Screen reader testing requires testing on actual screen readers — DevTools overlays do not substitute for the real interaction.
- WCAG 2.2 introduced new criteria (2024). This audit covers WCAG 2.1 AA. Flag if WCAG 2.2 compliance is required.
