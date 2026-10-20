---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Internal Tier 2 library loader."
---

# Tier 2 Library Loader

Arguments are either a category (`plan`, `design`, `build`, `maintain`,
`configure`, or `utils`) plus the user's request, or a known library skill
identifier plus context. For an identifier, locate the unique matching
`${CLAUDE_PLUGIN_ROOT}/skill-library/*/<identifier>/SKILL.md` before reading it;
if it is absent or ambiguous, route through `find-skill` instead.

1. Read `${CLAUDE_PLUGIN_ROOT}/skill-library/<category>/INDEX.md`.
2. Select exactly one workflow whose trigger and non-goals fit the request.
   Ask one focused question if the choice changes mutation authority, project
   state, or evidence requirements.
3. Read `${CLAUDE_PLUGIN_ROOT}/skill-library/<category>/<skill>/SKILL.md`.
4. Follow that workflow exactly. Its gates, hooks, and mutation limits remain
   authoritative.

Never expose the selected workflow as a new slash command. Report the chosen
category and workflow in the handoff, then carry out the workflow.
