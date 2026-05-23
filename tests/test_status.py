"""
Tests for scripts/status.py (ISSUE-182).

Translates: tests/features/issue-182-canonical-status-validation.feature

Covers:
  - Validation API (validate, assert_valid)
  - Transition validation (validate_transition)
  - Non-terminal status writes (write_status)
  - Terminal status writes with file moves (set_terminal)
  - CLI entry point
  - doctor.py integration (CANONICAL_STATUSES import)
  - Cache verification
  - Storage-lint integration
  - Audit log format and append behavior
  - Milestone vocabulary alignment
"""
import json
import os
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from status import (
    CANONICAL_STATUSES,
    TERMINAL_STATUSES,
    STATUS_PRECEDENCE,
    derived_status,
    validate,
    assert_valid,
    validate_transition,
    write_status,
    set_terminal,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _frontmatter_file(path: Path, frontmatter: dict, body: str = "## Description\nTest issue.") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(frontmatter, default_flow_style=False)
    path.write_text(f"---\n{fm_text}---\n\n{body}", encoding="utf-8")
    return path


def _read_frontmatter(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").lstrip("﻿")
    parts = raw.split("---", 2)
    assert len(parts) >= 3, f"No valid frontmatter in {path}"
    return yaml.safe_load(parts[1])


def _audit_log_path(project_dir: Path) -> Path:
    return project_dir / ".sweetclaude" / "metrics" / "status-audit.jsonl"


def _read_audit_entries(project_dir: Path) -> list[dict]:
    log = _audit_log_path(project_dir)
    if not log.exists():
        return []
    lines = [ln.strip() for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def _setup_project_dir(tmp_path: Path) -> Path:
    (tmp_path / ".sweetclaude" / "metrics").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sweetclaude" / "cache").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sweetclaude" / "product" / "backlog").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sweetclaude" / "product" / "roadmap").mkdir(parents=True, exist_ok=True)
    privacy_path = tmp_path / ".sweetclaude" / "artifact-privacy.yaml"
    privacy_path.write_text(yaml.safe_dump({
        "categories": {"product": {"base_path": ".sweetclaude/product"}},
    }))
    return tmp_path


def _make_issue(project_dir: Path, rel_path: str, status: str, issue_id: str = None) -> Path:
    path = project_dir / rel_path
    derived_id = issue_id or Path(rel_path).stem.split("-")[0] + "-" + Path(rel_path).stem.split("-")[1]
    _frontmatter_file(path, {
        "id": derived_id,
        "title": f"Test issue {derived_id}",
        "status": status,
        "type": "enhancement",
        "created": "2026-05-22",
    })
    return path


def _get_cache_row(project_dir: Path, item_id: str) -> dict | None:
    db = project_dir / ".sweetclaude" / "cache" / "roadmap.db"
    if not db.exists():
        return None
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Scenario Outline: validate() accepts canonical status values
# ---------------------------------------------------------------------------

class TestValidateAcceptsCanonical:
    @pytest.mark.parametrize("status", [
        "new", "ready", "active", "in-review", "blocked",
        "on-hold", "deferred", "done", "declined", "abandoned", "superseded",
    ])
    def test_returns_true_for_canonical(self, status):
        assert validate(status) is True


# ---------------------------------------------------------------------------
# Scenario Outline: validate() rejects non-canonical status values
# ---------------------------------------------------------------------------

class TestValidateRejectsNonCanonical:
    @pytest.mark.parametrize("status", [
        "backlog", "in_progress", "cancelled", "proposed",
        "achieved", "dropped", "compleet", "",
    ])
    def test_returns_false_for_non_canonical(self, status):
        assert validate(status) is False


# ---------------------------------------------------------------------------
# Scenario Outline: validate() rejects values with whitespace or wrong case
# ---------------------------------------------------------------------------

class TestValidateRejectsWhitespaceAndCase:
    @pytest.mark.parametrize("status", [
        " active",   # leading space
        "done ",     # trailing space (note: Gherkin shows "done" with trailing space)
        "Active",
        "DONE",
        "In-Review",
    ])
    def test_returns_false_for_bad_case_or_whitespace(self, status):
        assert validate(status) is False


# ---------------------------------------------------------------------------
# Scenario: validate() rejects None
# ---------------------------------------------------------------------------

class TestValidateRejectsNone:
    def test_returns_false_for_none(self):
        assert validate(None) is False


# ---------------------------------------------------------------------------
# Scenario: assert_valid() raises ValueError for non-canonical status
# ---------------------------------------------------------------------------

class TestAssertValid:
    def test_raises_value_error_with_invalid_value_and_valid_list(self):
        with pytest.raises(ValueError) as exc_info:
            assert_valid("backlog")
        msg = str(exc_info.value)
        assert "backlog" in msg
        # Message should include at least one canonical value to be "helpful"
        assert any(s in msg for s in ("new", "active", "done"))

    def test_does_not_raise_for_canonical(self):
        # Must not raise
        assert_valid("active")


# ---------------------------------------------------------------------------
# Scenario: CANONICAL_STATUSES and TERMINAL_STATUSES constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_canonical_statuses_is_frozenset(self):
        assert isinstance(CANONICAL_STATUSES, frozenset)

    def test_canonical_statuses_has_11_values(self):
        assert len(CANONICAL_STATUSES) == 11

    def test_canonical_statuses_exact_values(self):
        expected = frozenset({
            "new", "ready", "active", "in-review", "blocked",
            "on-hold", "deferred", "done", "declined", "abandoned", "superseded",
        })
        assert CANONICAL_STATUSES == expected

    def test_terminal_statuses_is_frozenset(self):
        assert isinstance(TERMINAL_STATUSES, frozenset)

    def test_terminal_statuses_exact_values(self):
        expected = frozenset({"done", "declined", "abandoned", "superseded"})
        assert TERMINAL_STATUSES == expected

    def test_terminal_statuses_subset_of_canonical(self):
        assert TERMINAL_STATUSES.issubset(CANONICAL_STATUSES)


# ---------------------------------------------------------------------------
# Scenario Outline: validate_transition() allows non-terminal to any status
# ---------------------------------------------------------------------------

class TestValidateTransitionAllowed:
    @pytest.mark.parametrize("old,new", [
        ("new", "ready"),
        ("ready", "active"),
        ("active", "in-review"),
        ("active", "blocked"),
        ("active", "on-hold"),
        ("new", "deferred"),
        ("active", "done"),
        ("new", "declined"),
    ])
    def test_allows_non_terminal_to_any(self, old, new):
        result = validate_transition(old, new, "issue")
        assert result is True


# ---------------------------------------------------------------------------
# Scenario Outline: validate_transition() blocks terminal → non-terminal
# ---------------------------------------------------------------------------

class TestValidateTransitionBlocked:
    @pytest.mark.parametrize("old,new", [
        ("done", "active"),
        ("declined", "ready"),
        ("abandoned", "active"),
        ("superseded", "new"),
    ])
    def test_blocks_terminal_to_non_terminal_without_reopen(self, old, new):
        with pytest.raises((ValueError, PermissionError, RuntimeError)) as exc_info:
            validate_transition(old, new, "issue")
        msg = str(exc_info.value).lower()
        assert "reopen" in msg or "terminal" in msg or "cannot" in msg


# ---------------------------------------------------------------------------
# Scenario: validate_transition() allows terminal → non-terminal with reopen
# ---------------------------------------------------------------------------

class TestValidateTransitionReopen:
    def test_allows_terminal_to_non_terminal_with_reopen_flag(self):
        result = validate_transition("done", "new", "issue", reopen=True)
        assert result is True


# ---------------------------------------------------------------------------
# Scenario: validate_transition() allows no-op
# ---------------------------------------------------------------------------

class TestValidateTransitionNoop:
    def test_allows_same_status_noop(self):
        result = validate_transition("active", "active", "issue")
        assert result is True


# ---------------------------------------------------------------------------
# Scenario Outline: validate_transition() rejects non-canonical values
# ---------------------------------------------------------------------------

class TestValidateTransitionNonCanonical:
    @pytest.mark.parametrize("old,new", [
        ("backlog", "active"),
        ("active", "shipped"),
    ])
    def test_rejects_non_canonical_old_or_new(self, old, new):
        with pytest.raises((ValueError, RuntimeError)):
            validate_transition(old, new, "issue")


# ---------------------------------------------------------------------------
# Scenario: write_status() updates frontmatter and preserves file body
# ---------------------------------------------------------------------------

class TestWriteStatusBasic:
    def test_updates_frontmatter_and_preserves_body(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-200-test.md", "new", "ISSUE-200")

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        fm = _read_frontmatter(path)
        assert fm["status"] == "active"

    def test_body_content_unchanged(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-200-test.md"
        body = "## Description\nTest issue."
        _frontmatter_file(path, {
            "id": "ISSUE-200", "title": "Test", "status": "new",
            "type": "enhancement", "created": "2026-05-22",
        }, body=body)

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        fm = _read_frontmatter(path)
        assert fm["status"] == "active"
        raw = path.read_text(encoding="utf-8")
        assert "## Description" in raw
        assert "Test issue." in raw

    def test_creates_audit_log_entry(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-200-test.md", "new", "ISSUE-200")

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        entries = _read_audit_entries(project_dir)
        assert len(entries) >= 1
        entry = next(e for e in entries if e.get("entity") == "ISSUE-200")
        assert entry["actor"] == "go"
        assert entry["old"] == "new"
        assert entry["new"] == "active"

    def test_cache_rebuilt_after_write(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        # Place file in cache-scanned location
        path = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-200-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-200", "title": "Test", "status": "new",
            "type": "enhancement", "created": "2026-05-22",
        })

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        row = _get_cache_row(project_dir, "ISSUE-200")
        assert row is not None
        assert row["status"] == "active"


# ---------------------------------------------------------------------------
# Scenario: write_status() uses atomic write pattern
# ---------------------------------------------------------------------------

class TestWriteStatusAtomic:
    def test_no_temp_files_remain(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-201-test.md", "new", "ISSUE-201")

        write_status(str(path), "ready", "project-backlog-triage", project_dir=str(project_dir))

        leftover = list(path.parent.glob("*.tmp")) + list(path.parent.glob("*.~*"))
        assert leftover == [], f"Temp files remain: {leftover}"

    def test_file_not_corrupted(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-201-test.md", "new", "ISSUE-201")

        write_status(str(path), "ready", "project-backlog-triage", project_dir=str(project_dir))

        # File should still be parseable
        fm = _read_frontmatter(path)
        assert fm["status"] == "ready"


# ---------------------------------------------------------------------------
# Scenario: write_status() rejects invalid status
# ---------------------------------------------------------------------------

class TestWriteStatusRejectsInvalid:
    def test_rejected_with_validation_error(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-202-test.md", "new", "ISSUE-202")

        with pytest.raises((ValueError, RuntimeError)):
            write_status(str(path), "backlog", "test", project_dir=str(project_dir))

    def test_file_status_unchanged_on_rejection(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-202-test.md", "new", "ISSUE-202")

        try:
            write_status(str(path), "backlog", "test", project_dir=str(project_dir))
        except Exception:
            pass

        fm = _read_frontmatter(path)
        assert fm["status"] == "new"

    def test_no_audit_entry_on_rejection(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-202-test.md", "new", "ISSUE-202")

        try:
            write_status(str(path), "backlog", "test", project_dir=str(project_dir))
        except Exception:
            pass

        entries = _read_audit_entries(project_dir)
        issue_entries = [e for e in entries if e.get("entity") == "ISSUE-202"]
        assert issue_entries == []


# ---------------------------------------------------------------------------
# Scenario: write_status() rejects blocked transition
# ---------------------------------------------------------------------------

class TestWriteStatusRejectsBlockedTransition:
    def test_rejected_with_transition_error(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-203-test.md", "done", "ISSUE-203")

        with pytest.raises((ValueError, PermissionError, RuntimeError)):
            write_status(str(path), "active", "test", project_dir=str(project_dir))

    def test_file_status_unchanged_on_transition_rejection(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-203-test.md", "done", "ISSUE-203")

        try:
            write_status(str(path), "active", "test", project_dir=str(project_dir))
        except Exception:
            pass

        fm = _read_frontmatter(path)
        assert fm["status"] == "done"


# ---------------------------------------------------------------------------
# Scenario: write_status() handles file with UTF-8 BOM
# ---------------------------------------------------------------------------

class TestWriteStatusUtf8Bom:
    def test_handles_utf8_bom_and_updates_status(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-204-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = {"id": "ISSUE-204", "title": "BOM test", "status": "new",
              "type": "enhancement", "created": "2026-05-22"}
        content = "﻿---\n" + yaml.safe_dump(fm) + "---\n\n## Body\nContent."
        path.write_bytes(content.encode("utf-8-sig"))

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        result_fm = _read_frontmatter(path)
        assert result_fm["status"] == "active"

    def test_body_unchanged_after_bom_write(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-204-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = {"id": "ISSUE-204", "title": "BOM test", "status": "new",
              "type": "enhancement", "created": "2026-05-22"}
        content = "﻿---\n" + yaml.safe_dump(fm) + "---\n\n## Body\nContent."
        path.write_bytes(content.encode("utf-8-sig"))

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        result_fm = _read_frontmatter(path)
        assert result_fm["status"] == "active"
        raw = path.read_text(encoding="utf-8").lstrip("﻿")
        assert "## Body" in raw
        assert "Content." in raw


# ---------------------------------------------------------------------------
# Scenario: write_status() handles file with CRLF line endings
# ---------------------------------------------------------------------------

class TestWriteStatusCrlf:
    def test_handles_crlf_and_updates_status(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-205-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = {"id": "ISSUE-205", "title": "CRLF test", "status": "new",
              "type": "enhancement", "created": "2026-05-22"}
        lines = ["---", yaml.safe_dump(fm).rstrip(), "---", "", "## Body", "Content."]
        content = "\r\n".join(lines)
        path.write_bytes(content.encode("utf-8"))

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        result_fm = _read_frontmatter(path)
        assert result_fm["status"] == "active"

    def test_body_unchanged_after_crlf_write(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-205-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = {"id": "ISSUE-205", "title": "CRLF test", "status": "new",
              "type": "enhancement", "created": "2026-05-22"}
        lines = ["---", yaml.safe_dump(fm).rstrip(), "---", "", "## Body", "Content."]
        content = "\r\n".join(lines)
        path.write_bytes(content.encode("utf-8"))

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        result_fm = _read_frontmatter(path)
        assert result_fm["status"] == "active"
        raw = path.read_text(encoding="utf-8").lstrip("﻿")
        assert "## Body" in raw
        assert "Content." in raw


# ---------------------------------------------------------------------------
# Scenario: write_status() rejects file with empty frontmatter
# ---------------------------------------------------------------------------

class TestWriteStatusEmptyFrontmatter:
    def test_rejected_with_clear_error_about_missing_status(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-206-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n---\n\n## Body\nContent.", encoding="utf-8")

        with pytest.raises((ValueError, RuntimeError, KeyError)) as exc_info:
            write_status(str(path), "active", "go", project_dir=str(project_dir))
        msg = str(exc_info.value).lower()
        assert "status" in msg or "frontmatter" in msg or "missing" in msg


# ---------------------------------------------------------------------------
# Scenario: write_status() rejects file with no frontmatter delimiters
# ---------------------------------------------------------------------------

class TestWriteStatusNoFrontmatter:
    def test_rejected_with_clear_error_about_missing_frontmatter(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-207-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Just markdown\n\nNo frontmatter here.", encoding="utf-8")

        with pytest.raises((ValueError, RuntimeError)) as exc_info:
            write_status(str(path), "active", "go", project_dir=str(project_dir))
        msg = str(exc_info.value).lower()
        assert "frontmatter" in msg or "---" in msg or "delimiter" in msg or "missing" in msg


# ---------------------------------------------------------------------------
# Scenario: write_status() rejects file with no status key in frontmatter
# ---------------------------------------------------------------------------

class TestWriteStatusNoStatusKey:
    def test_rejected_with_clear_error_about_missing_status_field(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-208-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nid: ISSUE-208\ntitle: No status key\ntype: enhancement\n---\n\n## Body\n",
            encoding="utf-8",
        )

        with pytest.raises((ValueError, RuntimeError, KeyError)) as exc_info:
            write_status(str(path), "active", "go", project_dir=str(project_dir))
        msg = str(exc_info.value).lower()
        assert "status" in msg or "missing" in msg


# ---------------------------------------------------------------------------
# Scenario: write_status() rejects nonexistent file
# ---------------------------------------------------------------------------

class TestWriteStatusNonexistentFile:
    def test_rejected_with_file_not_found_error(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)

        with pytest.raises((FileNotFoundError, ValueError, RuntimeError)) as exc_info:
            write_status(
                str(project_dir / "backlog" / "ISSUE-209-nonexistent.md"),
                "active", "go", project_dir=str(project_dir),
            )
        msg = str(exc_info.value).lower()
        assert "not found" in msg or "no such file" in msg or "exist" in msg


# ---------------------------------------------------------------------------
# Scenario: write_status() rejects non-terminal write on file in done directory
# ---------------------------------------------------------------------------

class TestWriteStatusDoneDirectoryRejection:
    def test_rejected_for_non_terminal_status_in_done_dir(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir,
            "roadmap/issues/done/ISSUE-204-test.md",
            "done",
            "ISSUE-204",
        )

        with pytest.raises((ValueError, PermissionError, RuntimeError)) as exc_info:
            write_status(str(path), "active", "test", project_dir=str(project_dir))
        msg = str(exc_info.value).lower()
        assert "done" in msg or "terminal" in msg or "directory" in msg or "non-terminal" in msg


# ---------------------------------------------------------------------------
# write_status() rejects terminal statuses — use set_terminal() instead
# (I-037 prevention: write_status("done") must not silently succeed)
# ---------------------------------------------------------------------------

class TestWriteStatusRejectsTerminalStatus:
    @pytest.mark.parametrize("terminal_status", ["done", "declined", "abandoned", "superseded"])
    def test_rejects_terminal_status_outside_done_dir(self, tmp_path, terminal_status):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-250-test.md", "active", "ISSUE-250")

        with pytest.raises((ValueError, RuntimeError)) as exc_info:
            write_status(str(path), terminal_status, "test", project_dir=str(project_dir))
        msg = str(exc_info.value).lower()
        assert "terminal" in msg or "set_terminal" in msg

    @pytest.mark.parametrize("terminal_status", ["done", "declined", "abandoned", "superseded"])
    def test_file_unchanged_after_terminal_rejection(self, tmp_path, terminal_status):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-251-test.md", "active", "ISSUE-251")

        try:
            write_status(str(path), terminal_status, "test", project_dir=str(project_dir))
        except Exception:
            pass

        fm = _read_frontmatter(path)
        assert fm["status"] == "active"

    @pytest.mark.parametrize("terminal_status", ["done", "declined", "abandoned", "superseded"])
    def test_no_audit_entry_on_terminal_rejection(self, tmp_path, terminal_status):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-252-test.md", "active", "ISSUE-252")

        try:
            write_status(str(path), terminal_status, "test", project_dir=str(project_dir))
        except Exception:
            pass

        entries = _read_audit_entries(project_dir)
        issue_entries = [e for e in entries if "ISSUE-252" in e.get("entity", "")]
        assert issue_entries == []


# ---------------------------------------------------------------------------
# Scenario: write_status() no-op transition produces no audit entry
# ---------------------------------------------------------------------------

class TestWriteStatusNoop:
    def test_noop_succeeds_silently(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-205-noop-test.md", "active", "ISSUE-205")

        # Must not raise
        write_status(str(path), "active", "go", project_dir=str(project_dir))

    def test_noop_creates_no_audit_entry(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "backlog" / "ISSUE-205-noop-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-205",
            "title": "Noop test",
            "status": "active",
            "type": "enhancement",
            "created": "2026-05-22",
        })

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        entries = _read_audit_entries(project_dir)
        noop_entries = [e for e in entries if e.get("entity") == "ISSUE-205"]
        assert noop_entries == []


# ---------------------------------------------------------------------------
# Scenario: set_terminal() writes status and moves file to done directory
# ---------------------------------------------------------------------------

class TestSetTerminalMovesToDone:
    def test_file_exists_at_new_path(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-210-test.md", "active", "ISSUE-210"
        )

        set_terminal(str(path), "done", "project-issues", project_dir=str(project_dir))

        assert (project_dir / "roadmap" / "issues" / "done" / "ISSUE-210-test.md").exists()

    def test_file_not_at_original_path(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-210-test.md", "active", "ISSUE-210"
        )

        set_terminal(str(path), "done", "project-issues", project_dir=str(project_dir))

        assert not path.exists()

    def test_frontmatter_status_is_done(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-210-test.md", "active", "ISSUE-210"
        )

        set_terminal(str(path), "done", "project-issues", project_dir=str(project_dir))

        moved = project_dir / "roadmap" / "issues" / "done" / "ISSUE-210-test.md"
        fm = _read_frontmatter(moved)
        assert fm["status"] == "done"

    def test_frontmatter_has_closed_date(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-210-test.md", "active", "ISSUE-210"
        )

        set_terminal(str(path), "done", "project-issues", project_dir=str(project_dir))

        moved = project_dir / "roadmap" / "issues" / "done" / "ISSUE-210-test.md"
        fm = _read_frontmatter(moved)
        assert "closed_date" in fm and fm["closed_date"]

    def test_audit_log_entry_created(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-210-test.md", "active", "ISSUE-210"
        )

        set_terminal(str(path), "done", "project-issues", project_dir=str(project_dir))

        entries = _read_audit_entries(project_dir)
        entry = next((e for e in entries if e.get("entity") == "ISSUE-210"), None)
        assert entry is not None
        assert entry["actor"] == "project-issues"
        assert entry["old"] == "active"
        assert entry["new"] == "done"

    def test_cache_rebuilt(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        # Use cache-scanned location
        base = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues"
        base.mkdir(parents=True, exist_ok=True)
        path = base / "ISSUE-210-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-210", "title": "Test", "status": "active",
            "type": "enhancement", "created": "2026-05-22",
        })

        set_terminal(str(path), "done", "project-issues", project_dir=str(project_dir))

        row = _get_cache_row(project_dir, "ISSUE-210")
        assert row is not None
        assert row["status"] == "done"


# ---------------------------------------------------------------------------
# Scenario: set_terminal() moves backlog declines to archived
# ---------------------------------------------------------------------------

class TestSetTerminalBacklogToArchived:
    def test_declined_moves_to_archived(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-211-test.md", "new", "ISSUE-211")

        set_terminal(str(path), "declined", "project-issues", project_dir=str(project_dir))

        assert (project_dir / "backlog" / "archived" / "ISSUE-211-test.md").exists()

    def test_original_not_present_after_decline(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-211-test.md", "new", "ISSUE-211")

        set_terminal(str(path), "declined", "project-issues", project_dir=str(project_dir))

        assert not path.exists()

    def test_frontmatter_status_declined(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-211-test.md", "new", "ISSUE-211")

        set_terminal(str(path), "declined", "project-issues", project_dir=str(project_dir))

        moved = project_dir / "backlog" / "archived" / "ISSUE-211-test.md"
        fm = _read_frontmatter(moved)
        assert fm["status"] == "declined"


# ---------------------------------------------------------------------------
# Scenario: set_terminal() rejects non-terminal status
# ---------------------------------------------------------------------------

class TestSetTerminalRejectsNonTerminal:
    def test_rejected_for_non_terminal_status(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "roadmap/issues/ISSUE-212-test.md", "active", "ISSUE-212")

        with pytest.raises((ValueError, RuntimeError)) as exc_info:
            set_terminal(str(path), "ready", "test", project_dir=str(project_dir))
        msg = str(exc_info.value).lower()
        assert "terminal" in msg or "ready" in msg

    def test_file_has_not_moved_on_rejection(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "roadmap/issues/ISSUE-212-test.md", "active", "ISSUE-212")

        try:
            set_terminal(str(path), "ready", "test", project_dir=str(project_dir))
        except Exception:
            pass

        assert path.exists()


# ---------------------------------------------------------------------------
# Scenario: set_terminal() is atomic — file move failure rolls back everything
# ---------------------------------------------------------------------------

class TestSetTerminalAtomic:
    def test_rollback_on_move_failure(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-213-test.md", "active", "ISSUE-213"
        )
        done_dir = project_dir / "roadmap" / "issues" / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        # Make done dir not writable
        done_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            with pytest.raises(Exception):
                set_terminal(str(path), "done", "test", project_dir=str(project_dir))

            fm = _read_frontmatter(path)
            assert fm["status"] == "active"

            assert path.exists()
            assert not (done_dir / "ISSUE-213-test.md").exists()

            entries = _read_audit_entries(project_dir)
            assert not any(e.get("entity") == "ISSUE-213" for e in entries)
        finally:
            done_dir.chmod(stat.S_IRWXU)

    def test_cache_does_not_reflect_done_on_rollback(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        base = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues"
        base.mkdir(parents=True, exist_ok=True)
        path = base / "ISSUE-213-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-213", "title": "Atomic test", "status": "active",
            "type": "enhancement", "created": "2026-05-22",
        })
        # Build initial cache
        from cache import rebuild as _rebuild
        _rebuild(str(project_dir))

        done_dir = base / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        done_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            try:
                set_terminal(str(path), "done", "test", project_dir=str(project_dir))
            except Exception:
                pass

            row = _get_cache_row(project_dir, "ISSUE-213")
            if row is not None:
                assert row["status"] != "done"
        finally:
            done_dir.chmod(stat.S_IRWXU)


# ---------------------------------------------------------------------------
# Scenario: set_terminal() creates destination directory if it does not exist
# ---------------------------------------------------------------------------

class TestSetTerminalCreatesDestDir:
    def test_creates_done_directory(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-214-test.md", "active", "ISSUE-214"
        )
        done_dir = project_dir / "roadmap" / "issues" / "done"
        assert not done_dir.exists()

        set_terminal(str(path), "done", "go", project_dir=str(project_dir))

        assert done_dir.is_dir()
        assert (done_dir / "ISSUE-214-test.md").exists()


# ---------------------------------------------------------------------------
# Scenario: set_terminal() rejects move when destination file already exists
# ---------------------------------------------------------------------------

class TestSetTerminalCollision:
    def test_rejected_with_collision_error(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-215-test.md", "active", "ISSUE-215"
        )
        # Pre-create the destination
        done_dir = project_dir / "roadmap" / "issues" / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        collision = done_dir / "ISSUE-215-test.md"
        collision.write_text("existing content", encoding="utf-8")

        with pytest.raises((FileExistsError, ValueError, RuntimeError)) as exc_info:
            set_terminal(str(path), "done", "go", project_dir=str(project_dir))
        msg = str(exc_info.value).lower()
        assert "exist" in msg or "collision" in msg or "already" in msg

    def test_original_file_status_unchanged_on_collision(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-215-test.md", "active", "ISSUE-215"
        )
        done_dir = project_dir / "roadmap" / "issues" / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        (done_dir / "ISSUE-215-test.md").write_text("existing", encoding="utf-8")

        try:
            set_terminal(str(path), "done", "go", project_dir=str(project_dir))
        except Exception:
            pass

        fm = _read_frontmatter(path)
        assert fm["status"] == "active"

    def test_original_file_not_moved_on_collision(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(
            project_dir, "roadmap/issues/ISSUE-215-test.md", "active", "ISSUE-215"
        )
        done_dir = project_dir / "roadmap" / "issues" / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        (done_dir / "ISSUE-215-test.md").write_text("existing", encoding="utf-8")

        try:
            set_terminal(str(path), "done", "go", project_dir=str(project_dir))
        except Exception:
            pass

        assert path.exists()


# ---------------------------------------------------------------------------
# CLI tests — helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_STATUS_SCRIPT = str(_REPO_ROOT / "scripts" / "status.py")


def _run_cli(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, _STATUS_SCRIPT] + args,
        capture_output=True, text=True, cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Scenario: CLI set command succeeds
# ---------------------------------------------------------------------------

class TestCliSetSuccess:
    def test_exit_code_zero(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "backlog/ISSUE-220-test.md", "new", "ISSUE-220")

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-220-test.md"),
            "--status", "active",
            "--actor", "go",
            "--project-dir", str(project_dir),
        ])
        assert result.returncode == 0

    def test_stdout_json_with_status(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "backlog/ISSUE-220-test.md", "new", "ISSUE-220")

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-220-test.md"),
            "--status", "active",
            "--actor", "go",
            "--project-dir", str(project_dir),
        ])

        out = json.loads(result.stdout)
        assert out["status"] == "active"


# ---------------------------------------------------------------------------
# Scenario: CLI set command fails on invalid status
# ---------------------------------------------------------------------------

class TestCliSetInvalidStatus:
    def test_exit_code_one(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "backlog/ISSUE-221-test.md", "new", "ISSUE-221")

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-221-test.md"),
            "--status", "backlog",
            "--actor", "test",
            "--project-dir", str(project_dir),
        ])
        assert result.returncode == 1

    def test_stdout_json_with_error(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "backlog/ISSUE-221-test.md", "new", "ISSUE-221")

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-221-test.md"),
            "--status", "backlog",
            "--actor", "test",
            "--project-dir", str(project_dir),
        ])

        out = json.loads(result.stdout)
        assert "error" in out
        assert "backlog" in out["error"].lower() or "invalid" in out["error"].lower() or "canonical" in out["error"].lower()


# ---------------------------------------------------------------------------
# Scenario: CLI set-terminal command moves file
# ---------------------------------------------------------------------------

class TestCliSetTerminal:
    def test_exit_code_zero(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "roadmap/issues/ISSUE-222-test.md", "active", "ISSUE-222")

        result = _run_cli([
            "set-terminal",
            "--file", str(project_dir / "roadmap" / "issues" / "ISSUE-222-test.md"),
            "--status", "done",
            "--actor", "go",
            "--project-dir", str(project_dir),
        ])
        assert result.returncode == 0

    def test_file_moved_to_done(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "roadmap/issues/ISSUE-222-test.md", "active", "ISSUE-222")

        _run_cli([
            "set-terminal",
            "--file", str(project_dir / "roadmap" / "issues" / "ISSUE-222-test.md"),
            "--status", "done",
            "--actor", "go",
            "--project-dir", str(project_dir),
        ])

        assert (project_dir / "roadmap" / "issues" / "done" / "ISSUE-222-test.md").exists()


# ---------------------------------------------------------------------------
# Scenario: CLI set command fails when --actor is omitted
# ---------------------------------------------------------------------------

class TestCliMissingActor:
    def test_exit_code_one_when_actor_omitted(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "backlog/ISSUE-223-test.md", "new", "ISSUE-223")

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-223-test.md"),
            "--status", "active",
            # --actor omitted
            "--project-dir", str(project_dir),
        ])
        assert result.returncode == 1

    def test_error_mentions_actor(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        _make_issue(project_dir, "backlog/ISSUE-223-test.md", "new", "ISSUE-223")

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-223-test.md"),
            "--status", "active",
            "--project-dir", str(project_dir),
        ])

        out = json.loads(result.stdout)
        assert "error" in out
        assert "actor" in out["error"].lower()


# ---------------------------------------------------------------------------
# Scenario: CLI set command fails when --file points to nonexistent file
# ---------------------------------------------------------------------------

class TestCliNonexistentFile:
    def test_exit_code_one(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-224-nonexistent.md"),
            "--status", "active",
            "--actor", "test",
            "--project-dir", str(project_dir),
        ])
        assert result.returncode == 1

    def test_error_mentions_file_not_found(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)

        result = _run_cli([
            "set",
            "--file", str(project_dir / "backlog" / "ISSUE-224-nonexistent.md"),
            "--status", "active",
            "--actor", "test",
            "--project-dir", str(project_dir),
        ])

        out = json.loads(result.stdout)
        assert "error" in out
        msg = out["error"].lower()
        assert "not found" in msg or "no such file" in msg or "exist" in msg


# ---------------------------------------------------------------------------
# Scenario: CLI validate command checks a value
# ---------------------------------------------------------------------------

class TestCliValidate:
    def test_canonical_status_exit_zero(self, tmp_path):
        result = _run_cli(["validate", "--status", "in-review"])
        assert result.returncode == 0

    def test_non_canonical_status_exit_one(self, tmp_path):
        result = _run_cli(["validate", "--status", "cancelled"])
        assert result.returncode == 1


# ---------------------------------------------------------------------------
# Scenario: doctor.py validates against the canonical 11 statuses
# ---------------------------------------------------------------------------

class TestDoctorIntegration:
    def _build_doctor_project(self, tmp_path):
        project_dir = tmp_path / "project"
        sc = project_dir / ".sweetclaude"
        state_dir = sc / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "sweetclaude.yaml").write_text(yaml.safe_dump({
            "phase_schema_version": 2,
            "framework": {"installed_version": "4.0.8-beta"},
        }))
        (state_dir / "session-state.yaml").write_text(yaml.safe_dump({
            "paths": {"product_base": ".sweetclaude/product"},
        }))
        (sc / "artifact-privacy.yaml").write_text(yaml.safe_dump({
            "categories": {"product": {"base_path": ".sweetclaude/product"}},
        }))
        (state_dir / "skills.yaml").write_text(yaml.safe_dump({"schema_version": 2, "skills": {}}))
        (project_dir / ".sweetclaude" / "product" / "backlog").mkdir(parents=True, exist_ok=True)
        (project_dir / ".sweetclaude" / "product" / "roadmap").mkdir(parents=True, exist_ok=True)
        (project_dir / "CLAUDE.md").write_text("# Project\n")
        (project_dir / "hooks").mkdir(exist_ok=True)
        runner_dir = project_dir / "scripts" / "migrations"
        runner_dir.mkdir(parents=True, exist_ok=True)
        (runner_dir / "runner.py").write_text(
            "#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps([]))\n"
        )
        return project_dir

    def test_canonical_status_produces_no_finding(self, tmp_path, monkeypatch):
        project_dir = self._build_doctor_project(tmp_path)
        path = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-230-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-230", "title": "Test", "status": "in-review",
            "type": "enhancement", "created": "2026-05-22",
        })

        monkeypatch.setattr("pathlib.Path.home", staticmethod(
            lambda: tmp_path / "home"
        ))
        (tmp_path / "home" / ".claude" / "hooks" / "sweetclaude").mkdir(parents=True)
        (tmp_path / "home" / ".claude" / "hooks" / "sweetclaude" / "hooks.json").write_text(
            json.dumps({"hooks": []})
        )
        (tmp_path / "home" / ".claude" / "rules" / "sweetclaude").mkdir(parents=True)
        for rf in ["interaction-model.md", "phase-gates.md", "tdd-levels.md"]:
            (tmp_path / "home" / ".claude" / "rules" / "sweetclaude" / rf).write_text(f"# {rf}")
        (tmp_path / "home" / ".claude" / "settings.json").write_text(
            json.dumps({"plansDirectory": ".sweetclaude/plans"})
        )
        (tmp_path / "home" / ".claude" / "plugins").mkdir(parents=True)
        (tmp_path / "home" / ".claude" / "plugins" / "installed_plugins.json").write_text(
            json.dumps({"plugins": {"sweetclaude/sweetclaude": [{"version": "4.0.8-beta"}]}})
        )

        from doctor import build_project_state, check_file_diagnostics
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)
        file_ids = [f.id for f in findings]
        assert not any("ISSUE-230-test.md" in fid and "unknown-status" in fid for fid in file_ids), (
            f"Expected no finding for ISSUE-230-test.md, got: {file_ids}"
        )

    def test_legacy_status_produces_finding(self, tmp_path, monkeypatch):
        project_dir = self._build_doctor_project(tmp_path)
        path = project_dir / ".sweetclaude" / "product" / "backlog" / "ISSUE-231-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-231", "title": "Test", "status": "in_progress",
            "type": "enhancement", "created": "2026-05-22",
        })

        monkeypatch.setattr("pathlib.Path.home", staticmethod(
            lambda: tmp_path / "home"
        ))
        (tmp_path / "home" / ".claude" / "hooks" / "sweetclaude").mkdir(parents=True)
        (tmp_path / "home" / ".claude" / "hooks" / "sweetclaude" / "hooks.json").write_text(
            json.dumps({"hooks": []})
        )
        (tmp_path / "home" / ".claude" / "rules" / "sweetclaude").mkdir(parents=True)
        for rf in ["interaction-model.md", "phase-gates.md", "tdd-levels.md"]:
            (tmp_path / "home" / ".claude" / "rules" / "sweetclaude" / rf).write_text(f"# {rf}")
        (tmp_path / "home" / ".claude" / "settings.json").write_text(
            json.dumps({"plansDirectory": ".sweetclaude/plans"})
        )
        (tmp_path / "home" / ".claude" / "plugins").mkdir(parents=True)
        (tmp_path / "home" / ".claude" / "plugins" / "installed_plugins.json").write_text(
            json.dumps({"plugins": {"sweetclaude/sweetclaude": [{"version": "4.0.8-beta"}]}})
        )

        from doctor import build_project_state, check_file_diagnostics
        state = build_project_state(project_dir)
        findings = check_file_diagnostics(state)
        file_ids = [f.id for f in findings]
        assert any("ISSUE-231-test.md" in fid and "unknown-status" in fid for fid in file_ids), (
            f"Expected finding for ISSUE-231-test.md with unknown-status, got: {file_ids}"
        )


# ---------------------------------------------------------------------------
# Scenario: doctor.py imports CANONICAL_STATUSES from status.py
# ---------------------------------------------------------------------------

class TestDoctorImportsFromStatus:
    def test_doctor_uses_canonical_statuses_from_status_module(self):
        """doctor.py must import CANONICAL_STATUSES from status, not hardcode its own set."""
        import ast
        doctor_path = _REPO_ROOT / "scripts" / "doctor.py"
        source = doctor_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imports_from_status = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "status":
                    names = [alias.name for alias in node.names]
                    if "CANONICAL_STATUSES" in names:
                        imports_from_status = True
                        break

        assert imports_from_status, (
            "doctor.py must import CANONICAL_STATUSES from status; "
            "it currently hardcodes its own status set"
        )

    def test_doctor_raises_import_error_when_status_not_importable(self, tmp_path, monkeypatch):
        """When status.py is not importable, doctor.py should fail with ImportError."""
        import sys

        saved_status = sys.modules.pop("status", None)
        saved_doctor = sys.modules.pop("doctor", None)
        sys.modules["status"] = None  # type: ignore  # Blocks import

        try:
            with pytest.raises(ImportError):
                import doctor  # noqa: F401
        finally:
            sys.modules.pop("status", None)
            sys.modules.pop("doctor", None)
            if saved_status is not None:
                sys.modules["status"] = saved_status
            if saved_doctor is not None:
                sys.modules["doctor"] = saved_doctor


# ---------------------------------------------------------------------------
# Scenario: Cache reflects new status after write_status
# ---------------------------------------------------------------------------

class TestCacheAfterWriteStatus:
    def test_cache_row_has_updated_status(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        base = project_dir / ".sweetclaude" / "product" / "backlog"
        base.mkdir(parents=True, exist_ok=True)
        path = base / "ISSUE-232-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-232", "title": "Cache test", "status": "new",
            "type": "enhancement", "created": "2026-05-22",
        })

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        row = _get_cache_row(project_dir, "ISSUE-232")
        assert row is not None, "Expected cache row for ISSUE-232"
        assert row["status"] == "active"


# ---------------------------------------------------------------------------
# Scenario: Cache reflects new path after set_terminal
# ---------------------------------------------------------------------------

class TestCacheAfterSetTerminal:
    def test_cache_row_has_done_status(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        base = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues"
        base.mkdir(parents=True, exist_ok=True)
        path = base / "ISSUE-233-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-233", "title": "Cache path test", "status": "active",
            "type": "enhancement", "created": "2026-05-22",
        })

        set_terminal(str(path), "done", "go", project_dir=str(project_dir))

        row = _get_cache_row(project_dir, "ISSUE-233")
        assert row is not None, "Expected cache row for ISSUE-233"
        assert row["status"] == "done"

    def test_cache_row_source_path_contains_done(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        base = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues"
        base.mkdir(parents=True, exist_ok=True)
        path = base / "ISSUE-233-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-233", "title": "Cache path test", "status": "active",
            "type": "enhancement", "created": "2026-05-22",
        })

        set_terminal(str(path), "done", "go", project_dir=str(project_dir))

        row = _get_cache_row(project_dir, "ISSUE-233")
        assert row is not None
        assert "done/ISSUE-233-test.md" in row["source_path"]


# ---------------------------------------------------------------------------
# Scenario: set_terminal followed by doctor storage-lint produces zero findings
# ---------------------------------------------------------------------------

class TestStorageLintIntegration:
    def test_no_done_status_mismatch_finding_after_set_terminal(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "project"
        sc = project_dir / ".sweetclaude"
        state_dir = sc / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "sweetclaude.yaml").write_text(yaml.safe_dump({
            "phase_schema_version": 2,
            "framework": {"installed_version": "4.0.8-beta"},
        }))
        (state_dir / "session-state.yaml").write_text(yaml.safe_dump({
            "paths": {"product_base": ".sweetclaude/product"},
        }))
        (sc / "artifact-privacy.yaml").write_text(yaml.safe_dump({
            "categories": {"product": {"base_path": ".sweetclaude/product"}},
        }))
        (state_dir / "skills.yaml").write_text(yaml.safe_dump({"schema_version": 2, "skills": {}}))
        (project_dir / ".sweetclaude" / "product" / "backlog").mkdir(parents=True, exist_ok=True)
        (project_dir / ".sweetclaude" / "product" / "roadmap").mkdir(parents=True, exist_ok=True)
        (project_dir / "CLAUDE.md").write_text("# Project\n")
        (project_dir / "hooks").mkdir(exist_ok=True)
        runner_dir = project_dir / "scripts" / "migrations"
        runner_dir.mkdir(parents=True, exist_ok=True)
        (runner_dir / "runner.py").write_text(
            "#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps([]))\n"
        )
        (sc / "metrics").mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr("pathlib.Path.home", staticmethod(lambda: tmp_path / "home"))
        (tmp_path / "home" / ".claude" / "hooks" / "sweetclaude").mkdir(parents=True)
        (tmp_path / "home" / ".claude" / "hooks" / "sweetclaude" / "hooks.json").write_text(
            json.dumps({"hooks": []})
        )
        (tmp_path / "home" / ".claude" / "rules" / "sweetclaude").mkdir(parents=True)
        for rf in ["interaction-model.md", "phase-gates.md", "tdd-levels.md"]:
            (tmp_path / "home" / ".claude" / "rules" / "sweetclaude" / rf).write_text(f"# {rf}")
        (tmp_path / "home" / ".claude" / "settings.json").write_text(
            json.dumps({"plansDirectory": ".sweetclaude/plans"})
        )
        (tmp_path / "home" / ".claude" / "plugins").mkdir(parents=True)
        (tmp_path / "home" / ".claude" / "plugins" / "installed_plugins.json").write_text(
            json.dumps({"plugins": {"sweetclaude/sweetclaude": [{"version": "4.0.8-beta"}]}})
        )

        issues_dir = project_dir / ".sweetclaude" / "product" / "roadmap" / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        path = issues_dir / "ISSUE-234-test.md"
        _frontmatter_file(path, {
            "id": "ISSUE-234", "title": "Storage lint test", "status": "active",
            "type": "enhancement", "created": "2026-05-22",
        })

        set_terminal(str(path), "done", "go", project_dir=str(project_dir))

        from doctor import build_project_state, check_storage_lint
        state = build_project_state(project_dir)
        findings = check_storage_lint(state)
        mismatch_ids = [f.id for f in findings if "done-status-mismatch" in f.id and "ISSUE-234" in f.id]
        assert mismatch_ids == [], (
            f"Expected no done-status-mismatch for ISSUE-234, got: {mismatch_ids}"
        )


# ---------------------------------------------------------------------------
# Scenario: Audit log entries are JSONL format
# ---------------------------------------------------------------------------

class TestAuditLogFormat:
    def test_audit_log_is_valid_jsonl(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-240-test.md", "new", "ISSUE-240")

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        log = _audit_log_path(project_dir)
        assert log.exists(), f"Audit log not created at {log}"

        lines = [ln.strip() for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) >= 1

        entry = json.loads(lines[-1])
        for key in ("ts", "actor", "entity", "file", "old", "new"):
            assert key in entry, f"Audit entry missing key '{key}': {entry}"

    def test_audit_entry_has_correct_values(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-240-test.md", "new", "ISSUE-240")

        write_status(str(path), "active", "go", project_dir=str(project_dir))

        entries = _read_audit_entries(project_dir)
        entry = next(e for e in entries if e.get("entity") == "ISSUE-240")
        assert entry["actor"] == "go"
        assert entry["old"] == "new"
        assert entry["new"] == "active"
        assert "ISSUE-240" in entry["file"]


# ---------------------------------------------------------------------------
# Scenario: Audit log is append-only across multiple writes
# ---------------------------------------------------------------------------

class TestAuditLogAppend:
    def test_two_writes_create_two_entries(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-241-test.md", "new", "ISSUE-241")

        write_status(str(path), "ready", "triage", project_dir=str(project_dir))
        write_status(str(path), "active", "go", project_dir=str(project_dir))

        entries = _read_audit_entries(project_dir)
        issue_entries = [e for e in entries if e.get("entity") == "ISSUE-241"]
        assert len(issue_entries) == 2

    def test_first_entry_shows_new_to_ready(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-241-test.md", "new", "ISSUE-241")

        write_status(str(path), "ready", "triage", project_dir=str(project_dir))
        write_status(str(path), "active", "go", project_dir=str(project_dir))

        entries = _read_audit_entries(project_dir)
        issue_entries = [e for e in entries if e.get("entity") == "ISSUE-241"]
        first = issue_entries[0]
        assert first["old"] == "new"
        assert first["new"] == "ready"

    def test_second_entry_shows_ready_to_active(self, tmp_path):
        project_dir = _setup_project_dir(tmp_path)
        path = _make_issue(project_dir, "backlog/ISSUE-241-test.md", "new", "ISSUE-241")

        write_status(str(path), "ready", "triage", project_dir=str(project_dir))
        write_status(str(path), "active", "go", project_dir=str(project_dir))

        entries = _read_audit_entries(project_dir)
        issue_entries = [e for e in entries if e.get("entity") == "ISSUE-241"]
        second = issue_entries[1]
        assert second["old"] == "ready"
        assert second["new"] == "active"


# ---------------------------------------------------------------------------
# Scenario: Milestone skill maps vocabulary before calling status.py
# ---------------------------------------------------------------------------

class TestMilestoneVocabularyMapping:
    def test_status_py_receives_done_not_achieved(self, tmp_path):
        """
        The milestone skill must map 'achieved' → 'done' before calling write_status.
        status.py must reject 'achieved' directly (it is not canonical).
        This test verifies the invariant from status.py's side.
        """
        project_dir = _setup_project_dir(tmp_path)
        path = project_dir / "roadmap" / "milestones" / "MS-099-test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        _frontmatter_file(path, {
            "id": "MS-099", "title": "Milestone test", "status": "active",
            "type": "milestone", "created": "2026-05-22",
        })

        # "achieved" is not canonical — status.py must reject it
        with pytest.raises((ValueError, RuntimeError)):
            write_status(str(path), "achieved", "milestone-skill", project_dir=str(project_dir))


# ---------------------------------------------------------------------------
# Scenario: Existing milestones with legacy vocabulary are backfilled
# ---------------------------------------------------------------------------

class TestMilestoneBackfill:
    """
    The backfill migration maps legacy milestone vocabulary to canonical statuses.
    These tests verify the mapping contract: status.py must accept the canonical
    target values and reject the legacy source values.
    """

    @pytest.mark.parametrize("legacy,canonical", [
        ("proposed", "new"),
        ("achieved", "done"),
        ("dropped", "declined"),
    ])
    def test_legacy_status_is_not_canonical(self, legacy, canonical):
        assert validate(legacy) is False, f"'{legacy}' should not be canonical"

    @pytest.mark.parametrize("canonical", ["new", "done", "declined", "active"])
    def test_canonical_target_is_accepted(self, canonical):
        assert validate(canonical) is True, f"'{canonical}' should be canonical"


# ---------------------------------------------------------------------------
# derived_status() tests (ISSUE-184)
# ---------------------------------------------------------------------------

class TestDerivedStatus:

    def test_empty_list_returns_new(self):
        assert derived_status([]) == "new"

    def test_all_terminal_returns_done(self):
        assert derived_status(["done", "done", "done"]) == "done"

    def test_mixed_terminal_returns_done(self):
        assert derived_status(["done", "abandoned", "declined", "superseded"]) == "done"

    def test_single_active(self):
        assert derived_status(["active"]) == "active"

    def test_single_new(self):
        assert derived_status(["new"]) == "new"

    @pytest.mark.parametrize("higher,lower", [
        ("blocked", "active"),
        ("on-hold", "active"),
        ("active", "ready"),
        ("in-review", "ready"),
        ("ready", "new"),
        ("new", "deferred"),
    ])
    def test_precedence_higher_wins(self, higher, lower):
        assert derived_status([higher, lower]) == higher

    def test_blocked_beats_everything(self):
        others = ["on-hold", "active", "in-review", "ready", "new", "deferred"]
        assert derived_status(["blocked"] + others) == "blocked"

    def test_terminal_children_ignored_when_non_terminal_present(self):
        assert derived_status(["done", "done", "active"]) == "active"

    def test_terminal_plus_new(self):
        assert derived_status(["done", "new"]) == "new"

    def test_deferred_is_lowest_precedence(self):
        assert derived_status(["deferred"]) == "deferred"

    def test_terminal_plus_non_active_non_terminal(self):
        assert derived_status(["done", "in-review"]) == "in-review"

    def test_terminal_plus_deferred(self):
        assert derived_status(["done", "abandoned", "deferred"]) == "deferred"

    def test_invalid_statuses_filtered_out(self):
        assert derived_status(["bogus", "nonsense"]) == "done"

    def test_invalid_mixed_with_valid(self):
        assert derived_status(["bogus", "active"]) == "active"

    def test_precedence_tuple_matches_expected_order(self):
        assert STATUS_PRECEDENCE == (
            "blocked", "on-hold", "active", "in-review", "ready", "new", "deferred",
        )

    def test_all_non_terminal_statuses_appear_in_precedence(self):
        non_terminal = CANONICAL_STATUSES - TERMINAL_STATUSES
        assert non_terminal == set(STATUS_PRECEDENCE)
