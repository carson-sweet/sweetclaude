---
spdx-license: AGPL-3.0-or-later
name: mockup-extract
user-invocable: true
description: "Pull an existing production component into the mockup sandbox as an accurate 'Current' baseline for design iteration. Traces the full import graph, stubs external dependencies, syncs design tokens. Use before mockup-sandbox when redesigning a component that already exists in the app."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Mockup Extract

Extracts an existing production component into the mockup sandbox as a self-contained baseline. Produces a `Current.tsx` that looks identical to the original — the correct starting point for design iteration.

**Why this exists:** Describing a component from memory and having Claude rebuild it always produces an inaccurate copy. Extract uses the real source code.

---

## Step 1: Sandbox check

```bash
ls artifacts/mockup-sandbox/src/ 2>/dev/null | head -3 && echo "SANDBOX_EXISTS" || echo "SANDBOX_MISSING"
```

If `SANDBOX_MISSING`:
> "The mockup sandbox hasn't been set up yet. Running `/sweetclaude:mockup-sandbox` to initialize it first."
Invoke `sweetclaude:mockup-sandbox`. Return here after setup.

---

## Step 2: Locate the target component

If the user gave a file path: read it directly.

If the user gave a description:
```bash
find . -maxdepth 6 \( -name "*.tsx" -o -name "*.jsx" \) 2>/dev/null \
  | grep -v node_modules | grep -v artifacts | grep -v ".git" \
  | xargs grep -l "{component keyword}" 2>/dev/null | head -10
```

Present matches and confirm with user: "Which file is the component you want to extract?"

Once confirmed: read the full file.

Determine the `group` for this extraction (feature or page name, kebab-case). Ask if not clear.

---

## Step 3: Trace the import graph

Read the target component. For each import, classify:

| Classification | Criteria | Action |
|---|---|---|
| **Inline** | Utility functions, simple hooks, sub-components < 50 lines | Copy code directly into the output file |
| **Copy** | Larger shared components, complex hooks, assets | Copy to `artifacts/mockup-sandbox/src/` with updated paths |
| **Stub** | API calls, routing, auth, global state, context providers | Replace with static mock data or no-ops |
| **Pass-through** | `@/components/ui/*` (shadcn/ui) | No change — sandbox has shadcn/ui pre-installed |

Walk the full chain recursively: component → hooks → contexts → API clients. Do not stop at the first level of imports.

**Standard stubs:**

| Dependency type | Replacement |
|---|---|
| API calls / data fetching | `const data = { /* realistic mock matching response shape */ }` |
| `useQuery`, `useSWR`, `useQuery` | Return `{ data: mockData, isLoading: false, error: null }` |
| Context providers (auth, theme) | `const authContext = { user: { name: 'Jane Doe', role: 'admin' }, ... }` |
| `useNavigate`, `useRouter` | `const navigate = () => {}` |
| `Link`, `NavLink` | Replace with `<a>` or `<button>` |
| `useParams` | `const params = { id: '1', slug: 'example' }` |
| Redux / Zustand / Jotai | `const [state] = useState(mockInitialState)` |

---

## Step 4: Determine the `@/` alias mapping

The sandbox uses a different `@/` root than the main app:

```bash
cat tsconfig.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('compilerOptions',{}).get('paths',{}))" 2>/dev/null || true
cat vite.config.ts 2>/dev/null | grep -A3 "alias" | head -8 || true
cat vite.config.js 2>/dev/null | grep -A3 "alias" | head -8 || true
```

Identify the `@/` source root (e.g., `client/src/`, `src/`, `app/`). All `@/` imports in the extracted component must resolve within `artifacts/mockup-sandbox/src/`. Files that need to be available in the sandbox must be either inlined or copied there.

---

## Step 5: Sync design tokens

Main app styles are not in the import graph — they come from global CSS. Collect them:

```bash
cat src/index.css 2>/dev/null | grep -A 200 ":root" | head -100 || \
cat client/src/index.css 2>/dev/null | grep -A 200 ":root" | head -100 || \
cat app/globals.css 2>/dev/null | grep -A 200 ":root" | head -100 || true

# Font links
grep -r "fonts.googleapis\|fonts.gstatic\|font-face" src/index.css client/src/index.css app/globals.css index.html 2>/dev/null | head -5
```

Create `artifacts/mockup-sandbox/src/components/mockups/{group}/_group.css`:
```css
/* Design tokens from main app — synced at extraction time */

:root {
  /* paste :root block from main app's global CSS */
}

.dark {
  /* paste .dark block if it exists */
}

/* Font imports */
@import url('https://fonts.googleapis.com/css2?...'); /* from main app's index.html */
```

---

## Step 6: Create Current.tsx

Create `artifacts/mockup-sandbox/src/components/mockups/{group}/Current.tsx`:

```tsx
import './_group.css'
// [inlined/copied imports]

// [stubs for external dependencies]
// const mockData = { ... }

export default function Current() {
  // [component code, adapted from original]
  return (
    <div className="min-h-screen">
      {/* original component JSX */}
    </div>
  )
}
```

Rules for the file:
- First import: `'./_group.css'`
- Export: `export default function Current()`
- Root element: `className="min-h-screen"`
- No imports from the main app source tree — all `@/` references resolve within `artifacts/mockup-sandbox/src/`
- Stubs declared at the top of the file, labeled with `// stub:`
- Inline code labeled with `// inlined from {original path}`

---

## Step 7: Type check

```bash
cd artifacts/mockup-sandbox && npx tsc --noEmit 2>&1 | head -30
```

Fix all type errors before sharing the preview URL. Common fixes:
- Missing type imports → import from `react` or `@/components/ui/*`
- Type mismatches in stubbed data → match the interface exactly
- Missing props → add defaults or make optional with `?`

---

## Step 8: Update registry

Append to `.sweetclaude/state/mockup-registry.yaml`:
```yaml
  - group: {group}
    name: Current
    file: artifacts/mockup-sandbox/src/components/mockups/{group}/Current.tsx
    preview_url: http://localhost:5174/preview/{group}/Current
    status: live
    created: {today}
    description: Extracted from {original file path}
    source_component: {original file path}
```

---

## Step 9: Establish as baseline

> "Extraction complete. The 'Current' version is available at:
> `http://localhost:5174/preview/{group}/Current`
>
> It should look identical to the original component in your app. If colors, fonts, or spacing look different, let me know — I'll adjust the token sync in `_group.css`.
>
> Ready to create design variants? Run `/sweetclaude:mockup-sandbox` to generate alternatives alongside this baseline."

---

## Rules

- **No imports from the main app source tree.** Every `@/` reference in Current.tsx must resolve inside `artifacts/mockup-sandbox/src/`.
- **Stubs must use realistic data.** Don't use `{ id: 1, name: 'test' }`. Use data that would appear in a real user's session.
- **Walk the full import graph — not just one level.** If a hook calls a context that calls an API client, stub the API client.
- **Type check must pass before sharing the preview URL.**
- **Do not modify any main app files** — extraction is read-only on the source.
- **For multi-component extraction** (e.g., an entire settings page with several sub-components), use parallel subagents — one per component — then combine in Current.tsx.
