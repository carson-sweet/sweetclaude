---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Generate HTML/CSS wireframes from user flows."
category: design
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Design Wireframes

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.design.base_path`. This is the base directory for all design artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. wireframes go to `{base_path}/wireframes/wireframe-*.html`).

4. Write artifacts to those paths.

Generate HTML/CSS wireframes from user flows. Each wireframe is a self-contained HTML file covering the primary, error, and success states of a flow. No external dependencies — files open directly in a browser.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:setup` first. Stop.

Read `.sweetclaude/state/ux-flows.yaml` — required. If missing:
> "Wireframes require user flows. Run `/sweetclaude:design-user-flows` first to define the flow steps. Want to do that now?"

Stop if user declines.

Read `.sweetclaude/state/ux.yaml` — optional. If present, use its color palette, layout pattern, density, and interaction style to inform the wireframe visual style. If absent, use neutral defaults (white background, #333 text, #6B7280 borders, Inter/system-ui font) and note:
> "No UX style spec found. Generating wireframes with neutral defaults. Run `/sweetclaude:design-ux` to define visual style and regenerate."

Read `.sweetclaude/state/personas.yaml` — optional. Use for annotation context if present.

Ensure `{base_path}/wireframes/` directory exists. Create it if not.

## Scope Selection

If more than three flows exist, ask:
> "There are {N} flows. Want wireframes for all of them, just the MVP/SLC scope, or specific story IDs?"

Proceed with the selected scope.

## Wireframe Generation

For each flow in scope, generate one self-contained HTML file.

### File naming

`{base_path}/wireframes/{story-id}-{kebab-slug}.html`

Example: `{base_path}/wireframes/us-adm-001-create-contact.html`

### React component annotations (optional)

If `.sweetclaude/state/tech.yaml` exists and `framework` contains `react`, or if the user mentions React during the session, ask once:
> "Want component boundaries annotated on the wireframes? I'll mark component outlines with dashed borders and label them — useful for mapping wireframe regions to React components."

If yes: wrap each distinct UI region in a `<div class="component-boundary">` with a `data-component="{ComponentName}"` attribute. Add a CSS rule rendering these as dashed `#94A3B8` outlines with a small label in the top-left corner. Default component names derived from the flow step and region role (e.g., `ContactForm`, `ContactList`, `ErrorBanner`). Do not add this annotation unless the user opts in.

### HTML structure per file

Each file contains all states of the flow as named sections, navigable via a simple fixed sidebar or top tab strip. States to include:

1. **Primary state** — the entry point screen as the user first sees it
2. **In-progress state** — if the flow has meaningful intermediate steps (e.g., a form being filled)
3. **Success state** — what the UI shows after the story is completed
4. **Error state(s)** — one section per distinct error defined in the flow

Use `<section id="{state-slug}">` with a sticky navigation so the user can jump between states without scrolling.

### Visual style from ux.yaml

Apply the following mappings if `ux.yaml` is present:

| ux.yaml field | Wireframe application |
|---|---|
| `color_palette.primary` | CTA buttons, active nav items, focus rings |
| `color_palette.secondary` | Secondary actions, badges |
| `color_palette.background` | Page background |
| `color_palette.text` | Body text |
| `layout_pattern: sidebar` | Left nav column, content on right |
| `layout_pattern: top-nav` | Horizontal nav bar, full-width content below |
| `layout_pattern: command-first` | Search/command bar centered, minimal chrome |
| `layout_pattern: single-column` | Centered single-column content |
| `density: dense` | Compact spacing (0.5rem gaps), small type (13px base) |
| `density: balanced` | Standard spacing (1rem gaps), 14–15px base |
| `density: open` | Generous spacing (1.5–2rem gaps), 16px base |
| `dark_mode: true` | Dark background, light text |

If a field is absent, use the neutral default for that property.

### Wireframe aesthetic

These are wireframes, not polished mockups:

- Real copy where available from the flow definition; placeholder copy labeled `[Label]` where not
- Real layout structure (nav, sidebar, content areas) — not boxes with X through them
- Components rendered recognizably: buttons look like buttons, inputs like inputs, tables like tables
- Muted color use: one accent color max (from palette if available, otherwise `#3B82F6`); backgrounds and surfaces in grays/whites
- No stock images — use `background: #E5E7EB; color: #9CA3AF;` placeholder blocks with a label describing the content (e.g., `[User avatar]`, `[Chart: revenue by month]`)

### Annotation layer

Each state section gets a fixed annotation panel (collapsed by default, expandable) showing:

- Story ID and title
- Flow step(s) this state covers
- Any open questions or edge cases from the flow definition

Toggle the annotation panel via a small `[?]` button in the corner.

### Self-contained requirement

All CSS is inline in `<style>`. No `<link>` tags, no external fonts (use system-ui stack), no JavaScript frameworks. One small `<script>` block for state navigation and annotation toggle is acceptable.

## Review

After generating each wireframe, present the file path and ask:
> "Wireframe for {story-id} written to `{base_path}/wireframes/{filename}`. Open it in a browser and let me know what to adjust."

Wait for feedback before proceeding to the next flow unless the user asks to generate all without pausing.

## Exit

Write `.sweetclaude/state/wireframes.yaml`:

```yaml
wireframes:
  - story_id: {}
    file: {}
    states: []
    style_source: ux.yaml | defaults
    last_updated: {}
generated_at: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-wireframes (n/a)

**Status:** completed | partial
**Produced:** {list of files}
**Flows covered:** {count} of {total}
**Style source:** ux.yaml | defaults
**Open questions:** {bullets}
```

Append to `.sweetclaude/state/checkpoint.md` (create if absent):

```markdown
## {ISO datetime} — design-wireframes

Done: Generated wireframes for {story IDs} — {count} files in {base_path}/wireframes/
Next: Run `/sweetclaude:design-ux-review` to get persona feedback on the wireframes
Open: {any open questions, or "none"}
```
