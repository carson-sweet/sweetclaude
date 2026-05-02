---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:mockup-graduate
description: "Move an approved mockup from the sandbox into the main application. Wires real data, routing, auth, and error handling. Extracts acceptance criteria for TDD. The design-to-IMPLEMENT bridge."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Mockup Graduate

Takes an approved mockup from the sandbox and integrates it into the production app. Also extracts acceptance criteria to feed `sweetclaude:product-user-stories` and `sweetclaude:code-tdd`.

**Key rule:** Graduate what was approved — don't improve the design during graduation. Design changes go back to the sandbox.

---

## Step 1: Identify the approved mockup

```bash
cat .sweetclaude/state/mockup-registry.yaml 2>/dev/null || echo "REGISTRY_MISSING"
```

If `REGISTRY_MISSING`:
> "No mockup registry found. Run `/sweetclaude:mockup-sandbox` to create mockups first."
Stop.

Find entries with `status: approved`. If none:
> "No approved mockups found. Approve a design in `/sweetclaude:mockup-sandbox` first (say 'this one looks good' or 'I approve the [Name] variant')."
Stop.

If multiple approved entries: list them and ask which to graduate.

Read the approved component file(s).

Determine the current work item ID from session state for the graduation record filename (use `active_work_item.id` or `MANUAL` if not set).

---

## Step 2: Analyze main app patterns

Read 2-3 production components from the main app to understand conventions:

```bash
# Find representative components (not the extracted Current.tsx)
find . -maxdepth 6 \( -name "*.tsx" -o -name "*.jsx" \) 2>/dev/null \
  | grep -v node_modules | grep -v artifacts | grep -v ".git" \
  | grep -v "test\|spec" | head -20
```

Select 2-3 components that represent core patterns. Read them and identify:
- **Routing library:** react-router, Next.js router, TanStack Router, other
- **State management:** useState only, Redux, Zustand, Jotai, Context
- **Data fetching:** useQuery (TanStack), SWR, fetch + useEffect, server components
- **Styling approach:** Tailwind (same as sandbox), CSS modules, styled-components, other
- **UI component library:** shadcn/ui (same as sandbox), Material UI, Mantine, other
- **Data fetching pattern:** check how adjacent components call APIs and handle loading/error states

If the main app's UI library differs from shadcn/ui, note every shadcn/ui component used in the mockup and identify the main app's equivalent (e.g., `Button` → `MuiButton`, `Dialog` → `Modal`).

---

## Step 3: Plan the transformation

Before writing any code, present the transformation plan:

**Components to place:**
- `{MockupComponentName}.tsx` → `{target path in main app}`

**Stubs to replace:**
| Mockup stub | Production replacement |
|---|---|
| `const mockData = {...}` | `const { data } = useQuery({queryKey: [...], queryFn: ...})` |
| `const navigate = () => {}` | `const navigate = useNavigate()` or `useRouter()` |
| `const authContext = {...}` | `const auth = useAuth()` or equivalent |
| {other stubs} | {replacements} |

**Production additions (not in mockup):**
- Loading state: `if (isLoading) return <Skeleton />`
- Error state: `if (error) return <ErrorMessage error={error} />`
- Empty state: `if (!data?.length) return <EmptyState />`
- Accessibility: ARIA labels, keyboard navigation, focus management

**UI library translations** (if applicable):
| Sandbox component | Main app equivalent |
|---|---|
| `<Button>` (shadcn/ui) | `<{MainAppButton}>` |
| `<Dialog>` | `<{MainAppModal}>` |
| {others} | {equivalents} |

**Routing changes:**
- [ ] New route to add: `{path}` → `{component}` (if this is a new page)
- [ ] Existing imports to update: `{N} files reference {OldComponent}`

**Dependencies to install** (in main app):
```bash
cat artifacts/mockup-sandbox/package.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d.get('dependencies',{}).keys()))" 2>/dev/null
cat package.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d.get('dependencies',{}).keys()))" 2>/dev/null
```
List any packages the mockup uses that the main app does not have.

Present this plan to the user. Wait for approval before writing any code.

**High-impact check:** If replacing an existing component, check how widely it's used:
```bash
grep -r "{ComponentName}" . --include="*.tsx" --include="*.jsx" 2>/dev/null \
  | grep -v node_modules | grep -v artifacts | grep -c "import\|require" || true
```

If > 5 import sites:
> "This component is used in {N} places. I recommend running `/sweetclaude:design-change-impact-analysis` before graduating to understand the ripple effects. Continue anyway?"

---

## Step 4: Install missing dependencies

For any dependency in the mockup not present in the main app:

```bash
# Detect package manager
ls package-lock.json yarn.lock pnpm-lock.yaml bun.lock 2>/dev/null | head -1
```

Use the appropriate installer (`npm install`, `yarn add`, `pnpm add`, `bun add`).

---

## Step 5: Transform and place the component

Create or replace the production component file at the agreed target path.

**Visual elements to preserve exactly** (graduate what was approved):
- Colors, gradients, shadows, border radius
- Typography: font families, weights, sizes, line heights
- Layout: grid/flex structure, responsive breakpoints, spacing
- Animations: transitions, hover states, entry animations
- Icons: same library, same choices

**Production elements to add** (not in the mockup):
- Replace every stub with the real implementation pattern from adjacent components
- Add loading state: follow the pattern of adjacent components in the same route
- Add error state: surface user-facing error with retry option
- Add empty state: a designed empty state, not a blank screen
- Add accessibility: `aria-label`, `role`, keyboard navigation, focus management
- Remove `min-h-screen` wrapper if the component is embedded (not a full page)

---

## Step 6: Update routing

If the graduated component is a **new page**:
- Add a route entry in the app's routing configuration file
- Confirm with user the intended URL path before writing

If **replacing an existing component**:
- Update all import sites (Step 3 identified them)

Run linter and type checker:
```bash
npx tsc --noEmit 2>&1 | head -20
npm run lint 2>&1 | head -20 || npx eslint . --ext .tsx,.ts 2>&1 | head -20 || true
```

Fix all errors. Do not share the result as "done" until both pass.

---

## Step 7: Extract acceptance criteria

After the component is verified, extract testable acceptance criteria from the approved design.

For each visible state of the component:

```markdown
## Acceptance Criteria — {ComponentName}
Extracted from approved mockup: {mockup file path}
Date: {today}

### Normal state
**Given** {user context}
**When** {trigger or page load}
**Then** {what is visible/rendered}

### Loading state
**Given** data is being fetched
**When** the component mounts
**Then** a loading skeleton/spinner is shown

### Error state
**Given** the API returns an error
**When** the component attempts to load data
**Then** an error message is shown with a retry option

### Empty state
**Given** the user has no {items/data}
**When** the component renders
**Then** the empty state illustration and CTA are shown

### [User interaction N]
**Given** the user is viewing the component
**When** they click/hover/focus {element}
**Then** {expected behavior}
```

Write to `acceptance-criteria-{group}.md` in the project root (or `docs/` if it exists).

Tell the user:
> "Graduated successfully. Acceptance criteria are ready at `acceptance-criteria-{group}.md`.
>
> These are ready to paste into user stories (`/sweetclaude:product-user-stories`) or use as TDD test specs (`/sweetclaude:code-tdd`)."

---

## Step 8: Update state

Update `.sweetclaude/state/mockup-registry.yaml` — set graduated entry to `status: graduated`.

Write `.sweetclaude/state/graduation-{work-item-id}.yaml`:
```yaml
schema_version: 1
work_item: {active_work_item.id or 'MANUAL'}
group: {group}
mockup_file: {approved mockup file path}
production_file: {target path in main app}
graduated: {today}
stubs_replaced:
  - {list each stub and what it was replaced with}
ui_library_translations:
  - {list any shadcn → main app UI library mappings}
new_route: {path or null}
acceptance_criteria_file: acceptance-criteria-{group}.md
```

Update `.sweetclaude/traceability/requirements-map.md`:
```markdown
| Approved mockup: {group}/{ComponentName} | user story TBD | TBD | graduated |
```

---

## Step 9: Cleanup offer

> "Want to keep the graduated mockup in the sandbox for reference, or remove it?"

Do not auto-remove anything. If the user says remove:
```bash
rm artifacts/mockup-sandbox/src/components/mockups/{group}/{ComponentName}.tsx
# Update registry entry to status: removed
```

---

## Rules

- **Graduate what was approved. Do not improve the design during graduation.** If you notice something to improve, note it for the next mockup iteration cycle.
- **Present the transformation plan before writing any code.** Wait for user approval.
- **Every stub in the mockup must be replaced** with a real implementation using the main app's patterns.
- **Type check and linter must pass before declaring success.**
- **Acceptance criteria must be extracted** — this is the TDD handoff. Never skip Step 7.
- **High-import-count components need an impact check warning.** Offer `design-change-impact-analysis` at > 5 import sites.
