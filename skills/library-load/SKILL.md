---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Internal Tier 2 library loader."
---

!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

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
3. Before reading the selected workflow, evaluate the mode gates for this
   request:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gate_check.py load --skill sweetclaude:library-load --args "$ARGUMENTS" --project-dir .
   ```

   Exit 0 prints `{"allow": true, ...}` and the gates pass. If the command
   exits 2, it prints `{"allow": false, "reasons": [...], "unmet": [...]}` —
   do not read the workflow. Output every entry in `reasons` and stop.
4. Read `${CLAUDE_PLUGIN_ROOT}/skill-library/<category>/<skill>/SKILL.md`.
5. Use the session state shown at the top of this loader as the workflow's pre-loaded state. A workflow read from the library does not run its own preload lines, the lines near the top that call `hooks/read-state.sh <stem> [sentinel]`. For a preload of any other stem, use the Read tool on `.sweetclaude/state/<stem>.yaml` before doing anything else; if that file does not exist, the pre-loaded state is the sentinel (default `STATE_NOT_FOUND`).
6. Follow that workflow exactly. Its gates, hooks, and mutation limits remain
   authoritative.

Never expose the selected workflow as a new slash command. Report the chosen
category and workflow in the handoff, then carry out the workflow.
