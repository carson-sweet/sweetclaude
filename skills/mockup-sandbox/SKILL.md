---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:mockup-sandbox
user-invocable: true
description: "Create and iterate on interactive UI mockups in an isolated Vite + React + Tailwind + shadcn/ui sandbox. Bridges UX spec to production-ready components. Design phase skill. Leads to mockup-extract (for redesigns of existing components) and mockup-graduate (when a design is approved)."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Mockup Sandbox

Isolated frontend prototyping environment. Create, compare, and iterate on UI components — then graduate the approved design into the main app.

**Stack:** Vite + React + TypeScript + Tailwind CSS + shadcn/ui.
**For React/TypeScript projects only.** If your main app uses a different stack, note it before proceeding — the sandbox always uses this stack; graduation handles the translation.

---

## Step 1: Read design context

```bash
cat .sweetclaude/state/ux.yaml 2>/dev/null || echo "UX_SPEC_MISSING"
cat .sweetclaude/state/ux-flows.yaml 2>/dev/null || echo "UX_FLOWS_MISSING"
cat .sweetclaude/state/mockup-registry.yaml 2>/dev/null || echo "REGISTRY_MISSING"
ls artifacts/mockup-sandbox/ 2>/dev/null | head -5 && echo "SANDBOX_EXISTS" || echo "SANDBOX_MISSING"
```

If `UX_SPEC_MISSING`: note that UX spec context is unavailable; continue anyway but flag that the user should run `/sweetclaude:design-ux` first if they want design-token-aware mockups.

---

## Step 2: Sandbox setup (runs once per project)

**If `SANDBOX_EXISTS`:** skip to Step 3.

**If `SANDBOX_MISSING`:** scaffold the sandbox.

Inform the user: "Setting up an isolated mockup sandbox at `artifacts/mockup-sandbox/`. This is a one-time setup — subsequent mockup sessions reuse it. Node.js and npm are required."

```bash
node --version 2>/dev/null || echo "NODE_MISSING"
npm --version 2>/dev/null || echo "NPM_MISSING"
```

If Node/npm missing: "Node.js and npm are required. Install from nodejs.org then re-run `/sweetclaude:mockup-sandbox`." Stop.

```bash
mkdir -p artifacts/mockup-sandbox
cd artifacts/mockup-sandbox && npm create vite@latest . -- --template react-ts --yes 2>&1 | tail -5
```

After Vite scaffold:

```bash
cd artifacts/mockup-sandbox && npm install tailwindcss @tailwindcss/vite 2>&1 | tail -3
npx shadcn@latest init --defaults 2>&1 | tail -5
mkdir -p src/components/mockups
```

Create `artifacts/mockup-sandbox/src/MockupRouter.tsx`:
```tsx
import { useEffect, useState } from 'react'

export default function MockupRouter() {
  const path = window.location.pathname
  const match = path.match(/^\/preview\/(.+?)\/(.+)$/)
  if (!match) return <div className="p-8 text-gray-500">No mockup at this path. Try /preview/&lt;group&gt;/&lt;ComponentName&gt;</div>
  const [group, name] = [match[1], match[2]]
  const [Component, setComponent] = useState<React.ComponentType | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    import(`./components/mockups/${group}/${name}.tsx`)
      .then(m => setComponent(() => m.default))
      .catch(() => setError(`Component not found: mockups/${group}/${name}.tsx`))
  }, [group, name])
  if (error) return <div className="p-8 text-red-500">{error}</div>
  if (!Component) return <div className="p-8 text-gray-400">Loading...</div>
  return <Component />
}
```

Update `artifacts/mockup-sandbox/src/main.tsx` to use `MockupRouter`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import MockupRouter from './MockupRouter'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MockupRouter />
  </StrictMode>,
)
```

Update `artifacts/mockup-sandbox/vite.config.ts` to use port 5174 and enable SPA routing:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
  },
  resolve: {
    alias: { '@': '/src' },
  },
})
```

Initialize `.sweetclaude/state/mockup-registry.yaml`:
```yaml
# .sweetclaude/state/mockup-registry.yaml
schema_version: 1
mockups: []
```

Tell the user:
> "Mockup sandbox ready at `artifacts/mockup-sandbox/`. Start the preview server with:
> ```
> cd artifacts/mockup-sandbox && npm run dev
> ```
> Components will be available at `http://localhost:5174/preview/{group}/{ComponentName}`."

---

## Step 3: Determine what to mockup

Ask exactly one question if the user hasn't specified:
> "What would you like to mockup? You can describe a screen, a component, or paste a reference (screenshot path, Figma description, existing component path)."

After the user answers, determine:

**Does this component already exist in the main app's codebase?**

```bash
# Search for the component by name (adapt to user's description)
find . -maxdepth 6 -name "*.tsx" -o -name "*.jsx" 2>/dev/null | grep -v node_modules | grep -v artifacts | grep -i "{component-name}" | head -5
```

If it exists → offer: "This component already exists in the app. Want to extract it as the baseline first? (Recommended: yes — iteration on an accurate copy produces better results.) Run `/sweetclaude:mockup-extract` first, then come back here."

If starting fresh → proceed to Step 4.

Determine variants:
> "Do you want a single design, or multiple variants to compare? (e.g., 'minimal vs. detailed', 'light vs. bold')"

---

## Step 4: Gather design context

Read UX spec if available:
- From `ux.yaml`: color scheme, typography direction, layout pattern, density preference, accessibility requirements
- From `ux-flows.yaml`: which component states the mockup must demonstrate

If UX spec missing, ask:
> "What design direction? (color palette, tone — minimal/detailed, any brand constraints)"

Determine the `group` for this mockup session (usually the feature name or page name, kebab-case).

---

## Step 5: Create components

For **single component**: create directly.
For **2+ variants**: use parallel subagents — one subagent per variant.

Each component lives at:
`artifacts/mockup-sandbox/src/components/mockups/{group}/{ComponentName}.tsx`

Component rules:
- Fully self-contained (no imports from the main app)
- Uses Tailwind + shadcn/ui
- Realistic mock data hardcoded inline
- Single default export matching the filename
- Root element uses `min-h-screen` for full-height preview
- TypeScript with no `any` types

For parallel variants, spawn agents:

```
Agent: Create variant {N}: {variant description}
- Output file: artifacts/mockup-sandbox/src/components/mockups/{group}/{VariantName}.tsx
- Stack: Tailwind + shadcn/ui, self-contained, no main app imports
- Realistic mock data inline
- Design direction: {direction for this variant}
```

After components are created, run type check:
```bash
cd artifacts/mockup-sandbox && npx tsc --noEmit 2>&1 | head -20
```

Fix any type errors before proceeding.

---

## Step 6: Preview presentation

Update `.sweetclaude/state/mockup-registry.yaml` with each new component:
```yaml
mockups:
  - group: {group}
    name: {ComponentName}
    file: artifacts/mockup-sandbox/src/components/mockups/{group}/{ComponentName}.tsx
    preview_url: http://localhost:5174/preview/{group}/{ComponentName}
    status: live
    created: {today}
    description: {one-line description}
```

Tell the user the preview URLs:

> "Mockups are ready. View them at:
> {list of preview URLs, one per line}
>
> If the previews aren't loading, make sure the sandbox dev server is running:"

```bash
cd artifacts/mockup-sandbox && npm run dev
```

If multiple variants: suggest opening them in separate tabs for comparison.

---

## Step 7: Iteration loop

Accept user feedback and modify the relevant component file in place.

If the user wants to **preserve a version before modifying**:
```bash
cp artifacts/mockup-sandbox/src/components/mockups/{group}/{ComponentName}.tsx \
   artifacts/mockup-sandbox/src/components/mockups/{group}/{ComponentName}V{n}.tsx
```
Update the registry with the preserved version, then modify the original.

Continue iterating until the user approves a design or ends the session.

---

## Step 8: Approval gate

When the user approves a design:

1. Update registry entry to `status: approved`.
2. Surface next steps:
> "{ComponentName} approved.
>
> Next options:
> - **Integrate into the app:** `/sweetclaude:mockup-graduate` — moves the approved design to production and extracts acceptance criteria for TDD.
> - **Extract acceptance criteria now:** I can generate a list of testable states and interactions from this design.
> - **Keep iterating:** If there's more to refine, just say what to change."

Do NOT push for graduation — the user decides when they're ready.

---

## Rules

- **Sandbox isolation is absolute.** No imports from the main app. No `../../src`, no `@/` aliases pointing outside `artifacts/mockup-sandbox/src/`.
- **Do not embed the main app in the sandbox.** No iframes of the running app.
- **Multiple variants are built in parallel.** Use subagents for 2+ variants.
- **Type check before sharing preview URLs.** Fix errors, don't share broken previews.
- **Graduate what was approved — don't improve during graduation.** Changes go back to the sandbox for another iteration cycle.
- **Dev server must be started by the user** — Claude cannot run a persistent background process. Always tell the user the `npm run dev` command.
