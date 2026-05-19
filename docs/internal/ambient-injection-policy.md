# Ambient Injection Policy

**Version:** 1.0
**Date:** 2026-05-07

## Rule

Every skill must declare its ambient injection behavior in frontmatter.

- **Default:** `disable-model-invocation: true`. The skill's description does
  NOT load into Claude Code's context at session start. The skill is invoked
  explicitly by name (`/sweetclaude:<name>`) or by another skill via the
  `Skill` tool.
- **Exception:** No `disable-model-invocation` field. The description loads
  ambiently and Claude can suggest the skill from natural-language intent.
  Use this only for the ambient core listed below.

## Ambient core

These 12 skills must keep ambient injection. They are the natural-language
entry points for everything else.

| Skill            | Triggered by                                   |
|------------------|------------------------------------------------|
| `bootstrap`      | Session start                                  |
| `master`         | "use SweetClaude", session-level orchestration |
| `find-skill`     | "what skill should I use for X"                |
| `help`           | "how do I use SweetClaude"                     |
| `status`         | "where are we", "what's the state"             |
| `go`             | "what should I work on next"                   |
| `code-feature`   | "build a new feature"                          |
| `code-issue`     | "implement this issue"                         |
| `_route`         | Internal: classifier called by `master`        |
| `_features`      | Internal: feature configuration display/toggle |
| `_health`        | Internal: consistency check                    |
| `_migrate`       | Internal: schema upgrade                       |

## Enforcement

`hooks/new-skill-lint.sh` runs as a pre-commit check. New skills missing
the disable flag (and not in the ambient core) are rejected at commit time.

The hook is installed in `.git/hooks/pre-commit` (not tracked by git).
Wire it in a fresh clone:

```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/usr/bin/env bash
set -e
"$(git rev-parse --show-toplevel)/hooks/new-skill-lint.sh"
EOF
chmod +x .git/hooks/pre-commit
```

## Budget monitoring

Run `python3 scripts/check-budget.py` to verify ambient description char
usage stays within the configured budget. Target: positive headroom.

The `skillListingBudgetFraction` setting in `~/.claude/settings.json`
controls the char budget. The default (0.01) gives ~8,000 chars on a
200K-token context. After this policy is applied, the 12 ambient skills
use ~2,900 chars — well within the default budget. The setting can be
raised to 0.02 for additional headroom, but it is not required.

## Adding a new skill

1. Create `skills/<name>/skill.md` with frontmatter including
   `disable-model-invocation: true`.
2. If the skill should be user-invocable from the `/` menu, set
   `user-invocable: true`; otherwise `user-invocable: false`.
3. Sync to both installed locations:
   ```bash
   cp skills/<name>/skill.md ~/.claude/skills/sweetclaude/<name>/SKILL.md
   mkdir -p ~/.claude/plugins/sweetclaude@sweetclaude/skills/<name>
   cp skills/<name>/skill.md \
     ~/.claude/plugins/sweetclaude@sweetclaude/skills/<name>/SKILL.md
   ```
4. Run `python3 scripts/check-budget.py` to confirm headroom is positive.

## Adding to the ambient core

This requires explicit justification. The skill must be a natural-language
entry point — something a user would trigger by describing intent, not by
knowing the skill name. To add:

1. Remove `disable-model-invocation` from the skill's frontmatter.
2. Add the skill name to `AMBIENT_CORE` in `hooks/new-skill-lint.sh`.
3. Update the ambient core table above.
4. Commit with a rationale explaining why this skill requires ambient
   injection rather than explicit invocation.

## Family-size policy

When any `<prefix>-*` family has 5+ skills OR total skill count reaches
120, the next addition to that family should be a subcommand of an existing
parent skill, not a new top-level skill. Current family sizes (2026-05-07):

| Family       | Count |
|--------------|-------|
| `design-*`   | 11    |
| `product-*`  | 18    |
| `project-*`  | 12    |
| `testing-*`  | 6     |
| `code-*`     | 7     |
| `documents-*`| 3     |
| `mockup-*`   | 3     |

All families except `documents-*` and `mockup-*` are already past the
trigger. New skills in those families should extend an existing parent.
