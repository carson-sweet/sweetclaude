#!/usr/bin/env bash
# Enforces ambient injection policy for new SweetClaude skills.
#
# A staged skill.md must EITHER:
#   1. Set `disable-model-invocation: true` (skill is always explicitly invoked), OR
#   2. Be one of the protected ambient-core skills (bootstrap, find-skill,
#      master, go, status, help, code-feature, code-issue, _health, _migrate,
#      _features, _route).
#
# Otherwise the skill claims ambient injection and we fail the commit so
# the author has to make the decision deliberately.

set -euo pipefail

AMBIENT_CORE=(
    bootstrap code-feature code-issue find-skill go help master status
    _health _migrate _features _route
)

is_ambient_core() {
    local name="$1"
    for s in "${AMBIENT_CORE[@]}"; do
        [[ "$s" == "$name" ]] && return 0
    done
    return 1
}

FAIL=0
STAGED=$(git diff --cached --name-only --diff-filter=AM \
         | grep -E '^skills/[^/]+/skill\.md$' || true)

[ -z "$STAGED" ] && exit 0

for file in $STAGED; do
    skill_name=$(echo "$file" | awk -F/ '{print $2}')

    if is_ambient_core "$skill_name"; then
        continue
    fi

    content=$(git show ":$file")
    if echo "$content" | grep -qE '^disable-model-invocation:[[:space:]]*true[[:space:]]*$'; then
        continue
    fi

    echo "ERROR: $file is missing 'disable-model-invocation: true'."
    echo "  Either:"
    echo "    1. Add to frontmatter: disable-model-invocation: true"
    echo "       (skill is invoked explicitly by name — this is the default)"
    echo "    2. Or, if the skill belongs in the ambient core, add its name to"
    echo "       hooks/new-skill-lint.sh AMBIENT_CORE and justify in the commit."
    FAIL=1
done

exit $FAIL
