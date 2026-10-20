---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "DEPRECATED — use /sweetclaude:plan epics instead. Redirects automatically."
---


# Project Epics (Deprecated)

This skill has been merged into `/sweetclaude:plan epics`. All epic operations now live there.

Invoke `/sweetclaude:plan epics $ARGUMENTS` instead.

If the user invoked this skill directly, tell them:

> "The `project-epics` skill has been merged into `epics`. Redirecting now."

Then invoke `sweetclaude:library-load epics` with the same arguments.
