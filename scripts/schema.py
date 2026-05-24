#!/usr/bin/env python3
"""Frontmatter schema validation for SweetClaude product artifacts."""
from __future__ import annotations

import re
from typing import Any

VALID_TYPES: frozenset[str] = frozenset({
    "epic", "milestone",
    "enhancement", "bug-fix", "tech-debt", "spike", "net-new-feature",
    "sprint", "theme", "goal",
})

REQUIRED_FIELDS: dict[str, list[str]] = {
    "_all": ["id", "title", "type", "status", "created"],
    "epic": ["milestone"],
    "milestone": ["target_release"],
}

_ID_PATTERN = re.compile(r"^(ISSUE|EP|MS)-\d{2,}$")
_MILESTONE_PATTERN = re.compile(r"^MS-\d{2,}$")

VALID_SOURCE_VALUES: frozenset[str] = frozenset({"auto", "manual"})

FIELD_VALIDATORS: dict[str, Any] = {
    "id": lambda v: bool(_ID_PATTERN.match(str(v))),
    "type": lambda v: v in VALID_TYPES,
    "status": lambda v: v in _get_canonical_statuses(),
    "milestone": lambda v: bool(_MILESTONE_PATTERN.match(str(v))),
    "source": lambda v: v in VALID_SOURCE_VALUES,
}


def _get_canonical_statuses() -> frozenset[str]:
    from status import CANONICAL_STATUSES
    return CANONICAL_STATUSES


def normalize_status(value: str) -> str:
    """Strip legacy annotations (em-dash suffixes, parentheticals) from status values."""
    if not value or not isinstance(value, str):
        return value
    for sep in [' — ', '—']:
        if sep in value:
            value = value.split(sep)[0]
            break
    if '(' in value:
        value = value.split('(')[0]
    return value.strip()


def normalize_milestone(value) -> str | None:
    """Extract bare milestone ID from annotated values."""
    if not value or not isinstance(value, str):
        return None
    val = value.strip()
    if not val or val.startswith('(') or val.lower() == 'tbd':
        return None
    m = re.match(r'^([^\s(]+)', val)
    return m.group(1) if m else val


def validate_frontmatter(fm: dict | None) -> list[str]:
    """Return list of violation strings. Empty list means valid."""
    if not fm or not isinstance(fm, dict):
        return ["frontmatter is empty or not a dict"]

    violations: list[str] = []

    for field in REQUIRED_FIELDS["_all"]:
        val = fm.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            violations.append(f"missing required field: {field}")

    entity_type = fm.get("type")
    if entity_type and entity_type in VALID_TYPES:
        for field in REQUIRED_FIELDS.get(entity_type, []):
            val = fm.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                violations.append(
                    f"missing required field for type '{entity_type}': {field}"
                )

    for field, validator in FIELD_VALIDATORS.items():
        value = fm.get(field)
        if value is not None and not validator(value):
            violations.append(f"invalid {field}: {value!r}")

    return violations
