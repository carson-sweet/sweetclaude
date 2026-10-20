---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Internal fast router to Tier 1 commands."
---

# Route

For a natural-language request, invoke `sweetclaude:find-skill` with the
original request. The only public workflow entry points are `go`, `plan`,
`design`, `build`, `maintain`, `configure`, `utils`, `status`, and `help`.
Tier 2 workflows are loaded from the library only after category routing.
