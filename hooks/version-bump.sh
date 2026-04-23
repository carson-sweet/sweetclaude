#!/bin/bash
# SweetClaude Version Bump Hook
# PostToolUse on Bash — auto-bumps version after successful git commits.
# Opt-in per project via .sweetclaude/version-bump.yaml.

INPUT=$(cat)

if ! echo "$INPUT" | grep -q 'git commit'; then
  exit 0
fi

if ! echo "$INPUT" | grep -qE '\[[a-zA-Z0-9/_.-]+ [a-f0-9]+\]'; then
  exit 0
fi

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

CONFIG="$PROJECT_DIR/.sweetclaude/version-bump.yaml"
if [ ! -f "$CONFIG" ]; then
  exit 0
fi

ENABLED=$(grep "^enabled:" "$CONFIG" 2>/dev/null | awk '{print $2}')
if [ "$ENABLED" != "true" ]; then
  exit 0
fi

cd "$PROJECT_DIR"

COMMIT_MSG=$(git log -1 --format=%s 2>/dev/null)

if echo "$COMMIT_MSG" | grep -q "^chore(version):"; then
  exit 0
fi

BUMP_TYPE="patch"
if echo "$COMMIT_MSG" | grep -qE '^feat(\(|:)'; then
  BUMP_TYPE="minor"
fi
if echo "$COMMIT_MSG" | grep -qiE 'BREAKING.CHANGE|^[a-z]+(\([^)]*\))?!:'; then
  BUMP_TYPE="major"
fi

VERSION_FILES=$(grep "^  - " "$CONFIG" 2>/dev/null | sed 's/^  - //')
if [ -z "$VERSION_FILES" ]; then
  exit 0
fi

FIRST_FILE=$(echo "$VERSION_FILES" | head -1)
if [ ! -f "$FIRST_FILE" ]; then
  exit 0
fi

CURRENT=$(grep '"version"' "$FIRST_FILE" | head -1 | sed 's/.*"\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\)".*/\1/')
if [ -z "$CURRENT" ]; then
  exit 0
fi

MAJOR=$(echo "$CURRENT" | cut -d. -f1)
MINOR=$(echo "$CURRENT" | cut -d. -f2)
PATCH=$(echo "$CURRENT" | cut -d. -f3)

case "$BUMP_TYPE" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

UPDATED=0
while IFS= read -r FILE; do
  if [ -f "$FILE" ]; then
    sed -i '' "s/\"version\": \"$CURRENT\"/\"version\": \"$NEW_VERSION\"/" "$FILE"
    git add "$FILE"
    UPDATED=$((UPDATED + 1))
  fi
done <<< "$VERSION_FILES"

if [ "$UPDATED" -eq 0 ]; then
  exit 0
fi

git commit -m "chore(version): bump to $NEW_VERSION"

CREATE_TAG=$(grep "^tag:" "$CONFIG" 2>/dev/null | awk '{print $2}')
if [ "$CREATE_TAG" = "true" ]; then
  git tag "v$NEW_VERSION" -m "v$NEW_VERSION"
fi

cat <<EOF
{"additionalContext": "✓ Auto-bumped version: $CURRENT → $NEW_VERSION ($BUMP_TYPE from '$COMMIT_MSG')"}
EOF

exit 0
