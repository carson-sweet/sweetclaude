---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:design-ux
user-invocable: true
description: Define the visual and interaction design of the product — look, feel, layout, and style. Produces a UX/UI design spec for handoff to AI mockup tools or a design team.
category: design
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Design UX

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.design.base_path`. This is the base directory for all design artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. wireframes go to `{base_path}/wireframes/wireframe-*.html`).

4. Write artifacts to those paths.

Define the look, feel, and interaction design of your product. This skill conducts a design interview and produces a UX/UI specification suitable for handoff to mockup tools or a design team.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state:
- `.sweetclaude/state/brief.yaml` (audience and tone context)
- `.sweetclaude/state/personas.yaml` (user context for design empathy)
- `.sweetclaude/state/architecture.yaml` (platform constraints — web vs. native, etc.)
- `.sweetclaude/state/ux-flows.yaml` (existing user flows to design for)

## Step 1 — Inspiration (First Message Only)

The very first message to the user must be:

> "Before we start the design interview, do you have screenshots or URLs of apps or websites that inspire you — products that have a look, feel, or vibe you want to capture?
>
> Sharing existing references is by far the fastest way to establish design direction. If you have them, drop them here. If not, no problem — we'll build it up through the interview."

Accept images and URLs. If the user shares references, analyze them:
- What visual style do they share (minimal, bold, dense, playful, professional, etc.)?
- What layout patterns appear?
- What color approach (monochrome, accent color, colorful)?
- What interaction feel (static, subtle animation, rich animation)?

Summarize what you observe from the references. Confirm with the user before proceeding.

## Step 2 — Design Interview

Ask one question at a time.

1. **Vibe and feeling:** "Are there existing products or websites — beyond what you've already shared — that have the aesthetic or feeling you want?"

2. **Words:** "What words do you want people to use when describing your product? Pick 3–5." Offer examples: clean, powerful, friendly, professional, playful, minimal, dense, calm, energetic, trustworthy, innovative.

3. **Priority:** "If you had to rank these three in order of importance for your design, how would you rank them: usability (easy to learn and use), aesthetic (beautiful and distinctive), simplicity (as little as possible)?"

4. **Information density:** "When you think about screens full of information, which feels right for your product?
   - Dense: lots of data visible at once, efficient for power users
   - Balanced: clear hierarchy, moderate information per screen
   - Open: roomy, minimal, lots of whitespace, calm"

5. **Color and theme:**
   "Light mode, dark mode, or user-switchable?
   Do you have brand colors, a logo, or visual assets already? If yes, share them."

6. **Interactions:** "How should the product feel when you interact with it?
   - Simple and immediate: things happen instantly, no animation
   - Subtle: small transitions that feel polished but not distracting
   - Expressive: animations and motion that communicate state and delight"

7. **AI/Copilot features in the UI:** "Will there be any AI-assist or copilot features embedded in the interface — things like inline suggestions, a chat panel, command palette, or similar?"

8. **Layout structure:** "What general layout pattern feels right? Here are common approaches:
   - Sidebar navigation (persistent left nav, content on right — common for dashboards and SaaS apps)
   - Top navigation (horizontal nav bar, full-width content — common for marketing sites and simple apps)
   - Command/search-first (no persistent nav, everything via search or command palette — common for developer tools)
   - Single-column (content stacked vertically — common for editorial, documentation, mobile-first)
   Which feels closest, or describe what you're imagining?"

## Step 3 — Write the UX/UI Design Spec

Based on all interview responses and any shared references, write the UX/UI design specification. Sections:

- **Design principles** (3–5 principles derived from the interview — e.g., "Clarity over density", "Motion earns its place")
- **Visual style** (color palette, typography direction, iconography style, imagery style)
- **Layout system** (grid, spacing scale, breakpoints if responsive)
- **Component style** (buttons, forms, cards, navigation — describe the visual treatment)
- **Interaction design** (animation philosophy, transition types, feedback patterns)
- **Dark/light mode** (if applicable)
- **AI/copilot UI patterns** (if applicable — how AI features are presented and accessed)
- **Accessibility baseline** (contrast requirements, keyboard navigation, screen reader considerations)

## Step 4 — Handoff Guidance

After presenting the spec:
> "This spec can be handed off to AI mockup and design tools. Current tools worth trying:
> - **v0 by Vercel** (v0.dev) — excellent for React/Tailwind UI generation from descriptions
> - **Galileo AI** — UI design generation from natural language
> - **Figma with AI plugins** — traditional design tool with growing AI assist features
> - **Uizard** — wireframes and mockups from sketches or descriptions
>
> When handing off, share this spec plus any reference screenshots you provided. The more specific the spec, the better the output."

## Document Production System

File naming: `{base_path}/{project-name}-ux-design-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: standard schema.

## Exit

Write `.sweetclaude/state/ux.yaml`:

```yaml
style_keywords: []
color_palette:
  primary: {}
  secondary: {}
  background: {}
  text: {}
layout_pattern: sidebar | top-nav | command-first | single-column | other
interaction_style: simple | subtle | expressive
density: dense | balanced | open
dark_mode: true | false | user-switchable
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-ux (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets — style direction, layout, color approach}
**Open questions:** {bullets}
```
