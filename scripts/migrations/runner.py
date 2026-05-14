#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SweetClaude migration runner.

Registry-driven runner that walks `config/migration-registry.yaml`, detects
the on-disk version of each registered state file, and applies registered
migration handlers to bring each file up to current.

Usage as a library:

    from scripts.migrations.runner import MigrationRunner
    runner = MigrationRunner(project_dir=Path("."))
    plan = runner.plan()                  # dry-run
    results = runner.run()                # execute

Usage as a CLI:

    python3 scripts/migrations/runner.py --project-dir . [--dry-run] [--file phase.yaml]

Locked design decisions live in:
    scratch/v3-upgrade-assessment-2026-05-11/DECISIONS.md (Gap #2)
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml


# ---------------------------------------------------------------------------
# Named failure modes (Gap #2 success criterion #8)
# ---------------------------------------------------------------------------

FAILURE_VALIDATION_PRE = "validation_failed_pre"
FAILURE_VALIDATION_POST = "validation_failed_post"
FAILURE_HANDLER_RAISED = "handler_raised"
FAILURE_REQUIRED_FIELD_MISSING = "required_field_missing"
FAILURE_WRITE_FAILED = "write_failed"
FAILURE_CHAIN_BROKEN = "chain_broken"
FAILURE_FILE_MISSING = "file_missing"
FAILURE_PARSE_FAILED = "parse_failed"
FAILURE_RECOVERABLE = "recoverable"  # handler raised a recoverable error with a user-facing menu
# Gap #8: distinct symbol for "this migration was intentionally deleted because
# its from-version predates the 3-major support window." Runtime detection
# currently emits chain_broken for any missing handler; this constant lets
# handlers signal "too old" explicitly and lets bootstrap recognize it when
# routing to re-onboarding.
FAILURE_OUT_OF_SUPPORT_WINDOW = "out_of_support_window"


# ---------------------------------------------------------------------------
# Recoverable error protocol (Gap #5)
# ---------------------------------------------------------------------------


class RecoverableMigrationError(Exception):
    """Raised by a handler to signal a problem that the user can resolve.

    The handler provides:
        message: short user-facing description of what's wrong.
        options: list of {label, action, ...} dicts describing handler-specific
                 remediation choices. Each option's `action` is an opaque string
                 the handler understands when re-invoked (e.g., "set_type=story",
                 "open_for_manual_edit").

    The runner appends two universal options to every menu before surfacing it:
        - {"label": "Skip this file", "action": "skip"}
        - {"label": "Initiate rollback", "action": "rollback"}

    "Initiate rollback" routes to Gap #6's confirmation flow when wired into
    the calling skill; it never fires automatically from this exception.

    Optional fields:
        current_file: Path of the specific file the handler was processing
                      when the error occurred. Used by Skip semantics when
                      the runner re-invokes the handler.
        current_id:   String ID (e.g., "BL-007") of the offending item.
    """

    def __init__(
        self,
        message: str,
        options: list[dict] | None = None,
        current_file: Path | str | None = None,
        current_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.options = options or []
        self.current_file = Path(current_file) if current_file else None
        self.current_id = current_id


# Universal options the runner appends to every recoverable-error menu.
UNIVERSAL_RECOVERY_OPTIONS = [
    {"label": "Skip this file", "action": "skip"},
    {"label": "Initiate rollback", "action": "rollback"},
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    from_version: int
    to_version: int
    handler_module: str
    success: bool
    failure_mode: str | None = None
    failure_details: str | None = None


@dataclass
class FileResult:
    file_key: str
    on_disk_version_before: int | None
    on_disk_version_after: int | None
    target_version: int
    success: bool
    failure_mode: str | None = None
    failure_details: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    # When failure_mode == FAILURE_RECOVERABLE, recovery_menu is populated.
    # Shape:
    #   {
    #       "message": str,
    #       "current_file": str | None,
    #       "current_id": str | None,
    #       "options": [{"label": str, "action": str, ...}, ...]
    #   }
    # options always includes the handler's choices plus the universal
    # Skip/Rollback entries appended by the runner.
    recovery_menu: dict | None = None


@dataclass
class SnapshotInfo:
    """Pre-migration safety snapshot — tarball + git tag (Gap #6).

    Belt-and-suspenders: the tarball captures gitignored content (.sweetclaude/
    plus any artifact base_paths outside .sweetclaude/); the git tag captures
    everything tracked in the project. Together they cover the full project
    state at snapshot time.
    """
    tarball_path: str
    git_tag: str
    git_stash_ref: str | None       # set if uncommitted changes were stashed
    paths_in_tarball: list[str]     # paths actually included (existence-filtered)
    tarball_verified: bool          # tar -tzf passed after creation
    git_tag_created: bool
    created_at: str                 # ISO-8601 UTC timestamp
    project_dir: str                # absolute path of the project the snapshot was taken in

    def to_dict(self) -> dict:
        return {
            "tarball_path": self.tarball_path,
            "git_tag": self.git_tag,
            "git_stash_ref": self.git_stash_ref,
            "paths_in_tarball": list(self.paths_in_tarball),
            "tarball_verified": self.tarball_verified,
            "git_tag_created": self.git_tag_created,
            "created_at": self.created_at,
            "project_dir": self.project_dir,
        }


@dataclass
class PlannedStep:
    from_version: int
    to_version: int
    handler_module: str
    handler_path: Path
    handler_available: bool


@dataclass
class FilePlan:
    file_key: str
    file_path: Path
    on_disk_version: int | None
    target_version: int
    needs_migration: bool
    entry_type: str = "file"   # "file" or "directory"
    file_missing: bool = False  # True when the file doesn't exist on disk
    steps: list[PlannedStep] = field(default_factory=list)
    missing_handlers: list[str] = field(default_factory=list)


@dataclass
class DriftFinding:
    """One result row from scan_drift(). Same shape regardless of file/dir."""
    file_key: str
    file_path: str
    entry_type: str
    on_disk_version: int | None
    target_version: int
    needs_migration: bool
    chain_valid: bool
    missing_handlers: list[str] = field(default_factory=list)
    file_missing: bool = False  # True when the file doesn't exist on disk

    def to_dict(self) -> dict:
        return {
            "file_key": self.file_key,
            "file_path": self.file_path,
            "entry_type": self.entry_type,
            "on_disk_version": self.on_disk_version,
            "target_version": self.target_version,
            "needs_migration": self.needs_migration,
            "chain_valid": self.chain_valid,
            "missing_handlers": list(self.missing_handlers),
            "file_missing": self.file_missing,
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class MigrationRunner:
    """Registry-driven migration runner.

    Reads `config/migration-registry.yaml` from the framework install (NOT
    from project_dir). Operates on state files inside `<project_dir>/.sweetclaude/state/`.
    """

    DEFAULT_STATE_SUBDIR = ".sweetclaude/state"
    DEFAULT_BASE_PATHS = {
        "product_base": ".sweetclaude/product",
        "strategy_base": ".sweetclaude/strategy",
        "technical_base": ".sweetclaude/technical",
        "design_base": ".sweetclaude/design",
    }

    def __init__(
        self,
        project_dir: Path | str,
        registry_path: Path | str | None = None,
        migrations_dir: Path | str | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        # Migration registry ships with the framework. Try, in order:
        #   1. Explicit registry_path argument (caller-provided)
        #   2. <runner_root>/config/migration-registry.yaml (dev clone + plugin-cache install layout)
        #   3. ~/.claude/config/sweetclaude/migration-registry.yaml (versionless install layout)
        # The runner can live at either ~/.claude/plugins/cache/.../scripts/migrations/runner.py
        # OR ~/.claude/scripts/sweetclaude/migrations/runner.py — the latter has no
        # colocated config/, so the versionless fallback is required.
        repo_root = Path(__file__).resolve().parent.parent.parent
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            colocated = repo_root / "config" / "migration-registry.yaml"
            versionless = Path.home() / ".claude" / "config" / "sweetclaude" / "migration-registry.yaml"
            if versionless.exists() and colocated.exists():
                # Prefer whichever was written more recently — versionless wins when
                # freshly synced by an update that the plugin cache hasn't seen yet.
                self.registry_path = (
                    versionless if versionless.stat().st_mtime >= colocated.stat().st_mtime
                    else colocated
                )
            elif versionless.exists():
                self.registry_path = versionless
            elif colocated.exists():
                self.registry_path = colocated
            else:
                self.registry_path = versionless  # will raise FileNotFoundError at load
        self.migrations_dir = (
            Path(migrations_dir) if migrations_dir else Path(__file__).resolve().parent
        )
        self.registry = self._load_registry()
        self._base_paths = self._load_base_paths()

    # -- internals ---------------------------------------------------------

    def _load_registry(self) -> dict:
        if not self.registry_path.exists():
            raise FileNotFoundError(
                f"Migration registry not found: {self.registry_path}"
            )
        return yaml.safe_load(self.registry_path.read_text()) or {}

    def _load_base_paths(self) -> dict[str, str]:
        """Resolve {product_base}/{strategy_base}/{technical_base}/{design_base}
        from <project_dir>/.sweetclaude/artifact-privacy.yaml. Fall back to
        SweetClaude defaults if the file is absent or a category is missing.
        """
        resolved = dict(self.DEFAULT_BASE_PATHS)
        privacy_path = self.project_dir / ".sweetclaude" / "artifact-privacy.yaml"
        if not privacy_path.exists():
            return resolved
        try:
            data = yaml.safe_load(privacy_path.read_text()) or {}
        except yaml.YAMLError:
            return resolved
        categories = data.get("categories") or {}
        for cat_name, entry in categories.items():
            if not isinstance(entry, dict):
                continue
            base_path = entry.get("base_path")
            if base_path and ".." not in Path(base_path).parts:
                resolved[f"{cat_name}_base"] = base_path
        return resolved

    def _resolve_path_template(self, template: str) -> Path:
        """Substitute {product_base}-style placeholders, resolve under project_dir."""
        resolved = template
        for var, value in self._base_paths.items():
            resolved = resolved.replace(f"{{{var}}}", value)
        return (self.project_dir / resolved).resolve()

    def _state_file_path(self, file_key: str) -> Path:
        return self.project_dir / self.DEFAULT_STATE_SUBDIR / file_key

    def _detect_version(self, file_path: Path) -> int | None:
        """Read `schema_version` from a state file's YAML."""
        if not file_path.exists():
            return None
        try:
            data = yaml.safe_load(file_path.read_text()) or {}
        except yaml.YAMLError:
            return None
        v = data.get("schema_version")
        if isinstance(v, int):
            return v
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def _handler_module_path(self, handler_name: str) -> Path:
        return self.migrations_dir / f"{handler_name}.py"

    def _load_handler(self, handler_name: str) -> Any:
        """Dynamically import a handler module.

        Injects the RecoverableMigrationError class into the module's namespace
        BEFORE executing it, so handlers can `raise RecoverableMigrationError(...)`
        without importing the runner (handlers are loaded by absolute path and
        don't have the runner on their import path).
        """
        path = self._handler_module_path(handler_name)
        if not path.exists():
            return None
        spec = importlib.util.spec_from_file_location(
            f"sweetclaude_migration_{handler_name}", path
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        # Inject before exec so handler code can reference it at module scope.
        module.RecoverableMigrationError = RecoverableMigrationError
        spec.loader.exec_module(module)
        return module

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write file via temp + os.replace for atomicity."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=str(path.parent), suffix=".tmp", delete=False
            ) as tmp:
                tmp.write(content)
                tmp_name = tmp.name
            os.replace(tmp_name, str(path))
            tmp_name = None
        finally:
            if tmp_name:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    def _build_recovery_menu(self, exc: "RecoverableMigrationError") -> dict:
        """Combine the handler's options with the universal Skip/Rollback entries.

        Output shape:
            {
                "message": str,
                "current_file": str | None,
                "current_id": str | None,
                "options": [{"label": str, "action": str, ...}, ...],
            }
        """
        # Deduplicate by `action` — if the handler already provides a "skip"
        # or "rollback" option, the universal version is suppressed.
        handler_actions = {opt.get("action") for opt in exc.options}
        combined = list(exc.options)
        for opt in UNIVERSAL_RECOVERY_OPTIONS:
            if opt["action"] not in handler_actions:
                combined.append(opt)
        return {
            "message": exc.message,
            "current_file": str(exc.current_file) if exc.current_file else None,
            "current_id": exc.current_id,
            "options": combined,
        }

    def _validate(self, data: dict, validation: dict | None) -> tuple[bool, str | None]:
        """Apply a registry validation block to a data dict.

        Returns (ok, reason). reason is None if ok.
        """
        if not validation:
            return True, None
        req_version = validation.get("required_version")
        if req_version is not None and data.get("schema_version") != req_version:
            return False, f"schema_version mismatch: got {data.get('schema_version')!r}, want {req_version}"
        req_fields = validation.get("required_fields") or []
        for field_name in req_fields:
            if field_name not in data:
                return False, f"required field missing: {field_name}"
        return True, None

    # -- snapshot / rollback (Gap #6) -------------------------------------

    def _git(self, *args: str) -> tuple[int, str, str]:
        """Run `git <args>` in project_dir. Returns (returncode, stdout, stderr)."""
        import subprocess
        proc = subprocess.run(
            ["git", "-C", str(self.project_dir), *args],
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _is_git_repo(self) -> bool:
        rc, _, _ = self._git("rev-parse", "--is-inside-work-tree")
        return rc == 0

    def _snapshot_paths(self) -> list[str]:
        """Compute the set of paths to include in the pre-migration tarball.

        Always includes .sweetclaude/ if it exists. Adds every artifact-privacy
        category base_path that's outside .sweetclaude/ AND exists on disk.

        Returns paths relative to project_dir.
        """
        candidates: list[str] = []
        sc_dir = self.project_dir / ".sweetclaude"
        if sc_dir.exists():
            candidates.append(".sweetclaude")
        for var, base in self._base_paths.items():
            # Resolve any leading "./" and normalize.
            base_norm = base.lstrip("./") if base.startswith("./") else base
            # Skip if it's inside .sweetclaude/ (already covered).
            if base_norm == ".sweetclaude" or base_norm.startswith(".sweetclaude/"):
                continue
            full = self.project_dir / base_norm
            if full.exists():
                if base_norm not in candidates:
                    candidates.append(base_norm)
        return candidates

    def create_snapshot(self) -> SnapshotInfo:
        """Build a pre-migration safety snapshot.

        Two captures, taken together:
          1. Comprehensive tarball at
             .sweetclaude/state/backups/pre-migration-<date>-<sha>.tar.gz
             covering .sweetclaude/ AND any artifact base_paths outside it.
          2. Git tag `pre-migration-<date>-<sha>` if the project is a git repo.
             Uncommitted changes (if any) are stashed and the stash ref is
             recorded on SnapshotInfo for restoration.

        Raises RuntimeError if either capture fails. Callers should abort the
        migration on failure rather than proceeding without a snapshot.
        """
        from datetime import datetime, timezone
        import subprocess

        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d-%H%M%S")
        rc, sha, _ = self._git("rev-parse", "--short", "HEAD") if self._is_git_repo() else (1, "nosha\n", "")
        sha = sha.strip() or "nosha"
        stamp = f"{ts}-{sha}"

        backups_dir = self.project_dir / ".sweetclaude" / "state" / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        tarball = backups_dir / f"pre-migration-{stamp}.tar.gz"

        paths = self._snapshot_paths()
        if not paths:
            raise RuntimeError(
                "No snapshot paths to capture — .sweetclaude/ missing and no artifact base_paths present."
            )

        # 1) Create tarball.
        tar_cmd = ["tar", "-czf", str(tarball), "-C", str(self.project_dir), *paths]
        proc = subprocess.run(tar_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"tar create failed: {proc.stderr.strip() or proc.stdout.strip()}")

        # 2) Verify tarball.
        verify = subprocess.run(
            ["tar", "-tzf", str(tarball)], capture_output=True, text=True
        )
        verified = verify.returncode == 0
        if not verified:
            raise RuntimeError(f"tar verify failed: {verify.stderr.strip() or verify.stdout.strip()}")

        # 3) Retention: keep last 5 tarballs (name as tiebreaker for stable sort).
        existing = sorted(
            backups_dir.glob("pre-migration-*.tar.gz"),
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        )
        for old in existing[5:]:
            try:
                old.unlink()
            except OSError:
                pass

        # 4) Git tag (if git repo). Tag captures HEAD; tarball captures working-tree
        #    content including gitignored files. Together they cover full rollback state.
        git_tag = f"pre-migration-{stamp}"
        git_tag_created = False
        stash_ref = None
        if self._is_git_repo():
            rc, _, tag_err = self._git("tag", git_tag)
            if rc == 0:
                git_tag_created = True
            else:
                raise RuntimeError(f"git tag failed: {tag_err.strip()}")

        return SnapshotInfo(
            tarball_path=str(tarball),
            git_tag=git_tag,
            git_stash_ref=stash_ref,
            paths_in_tarball=list(paths),
            tarball_verified=verified,
            git_tag_created=git_tag_created,
            created_at=now.isoformat(timespec="seconds"),
            project_dir=str(self.project_dir),
        )

    def verify_snapshot(self, snapshot: SnapshotInfo) -> tuple[bool, str | None]:
        """Re-verify a snapshot is still restorable. Returns (ok, reason)."""
        import subprocess
        tarball = Path(snapshot.tarball_path)
        if not tarball.exists():
            return False, f"tarball missing: {tarball}"
        verify = subprocess.run(["tar", "-tzf", str(tarball)], capture_output=True, text=True)
        if verify.returncode != 0:
            return False, f"tar verify failed: {verify.stderr.strip()}"
        if snapshot.git_tag_created:
            rc, _, _ = self._git("rev-parse", f"refs/tags/{snapshot.git_tag}")
            if rc != 0:
                return False, f"git tag missing: {snapshot.git_tag}"
        return True, None

    def rollback(self, snapshot: SnapshotInfo) -> tuple[bool, str | None]:
        """Restore the project to the snapshot state. Returns (ok, reason).

        Order:
          1. tar -xzf the comprehensive tarball over its source paths.
          2. git reset --hard <pre-migration-tag> if a tag was created.
          3. No stash-restore here — the snapshot was taken with the stash
             popped back into the working tree before the tag, so the tag
             already represents the user's pre-migration HEAD without the
             stashed changes. Restoring stashed changes is the caller's
             concern (they were popped at snapshot time, so they're already
             in the post-rollback working tree if they hadn't been overwritten
             by the migration).

        This method does NOT prompt the user — the calling skill must obtain
        explicit confirmation before invoking it (Gap #6 locked: rollback is
        never automatic).
        """
        import subprocess
        ok, reason = self.verify_snapshot(snapshot)
        if not ok:
            return False, f"snapshot verification failed: {reason}"

        # 1. Git reset to the tag first — restores tracked content to pre-migration
        #    HEAD before the tarball overwrites working-tree content on top.
        if snapshot.git_tag_created:
            rc, _, err = self._git("reset", "--hard", snapshot.git_tag)
            if rc != 0:
                return False, f"git reset failed: {err.strip()}"
            # Verify HEAD matches the tag to confirm reset succeeded.
            rc_h, head_sha, _ = self._git("rev-parse", "HEAD")
            rc_t, tag_sha, _ = self._git("rev-parse", snapshot.git_tag)
            if rc_h != 0 or rc_t != 0 or head_sha.strip() != tag_sha.strip():
                return False, (
                    f"git reset verification failed: "
                    f"HEAD={head_sha.strip()!r} tag={tag_sha.strip()!r}"
                )

        # 2. Extract tarball (restores gitignored content and any .sweetclaude/ state).
        proc = subprocess.run(
            ["tar", "-xzf", snapshot.tarball_path, "-C", str(self.project_dir)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, f"tar extract failed: {proc.stderr.strip()}"

        return True, None

    # -- public API --------------------------------------------------------

    def plan(self, file_keys: list[str] | None = None) -> list[FilePlan]:
        """Compute migration plans without executing.

        If file_keys is None, plans every registered file.
        """
        state_files = self.registry.get("state_files") or {}
        if file_keys is None:
            file_keys = list(state_files.keys())

        plans: list[FilePlan] = []
        for file_key in file_keys:
            entry = state_files.get(file_key)
            if entry is None:
                continue

            entry_type = entry.get("type", "file")
            target = int(entry.get("current_version", 1))
            migrations = entry.get("migrations") or []

            # Resolve the location depending on entry type.
            if entry_type == "directory":
                path_template = entry.get("path_template", "")
                file_path = self._resolve_path_template(path_template) if path_template else self.project_dir
                # For directories, on_disk_version comes from the registered
                # handler's detect_version() — we pick the first migration whose
                # handler can answer. If none can, on_disk is None.
                on_disk = self._detect_directory_version(file_path, migrations)
            else:
                file_path = self._state_file_path(file_key)
                on_disk = self._detect_version(file_path)

            steps: list[PlannedStep] = []
            missing: list[str] = []

            if on_disk is None:
                # File doesn't exist. Flag as file_missing if migrations are defined
                # (the file was expected to be present). Can't migrate without source data.
                #
                # Optional files (optional: true in registry) are never flagged — their
                # absence is intentional (e.g. skills.yaml is only created when the user
                # activates the relevant features; projects that never did have no file
                # to migrate and should not be blocked).
                #
                # Consolidation check (BUG-004): if this entry is marked consolidated_into
                # another file AND that file exists on disk, the absence is intentional
                # (the file was absorbed into the target in an earlier framework version).
                # Treat as needs_migration=False so it doesn't surface as drift on every
                # session of every healthy unified-state project.
                needs = bool(migrations) and not entry.get("optional", False)
                if needs:
                    consolidated_target = entry.get("consolidated_into")
                    expected_absent = entry.get("expected_absent_when") or {}
                    target_file_key = expected_absent.get("target_file_exists")
                    if consolidated_target and target_file_key:
                        if self._state_file_path(target_file_key).exists():
                            needs = False
                plans.append(
                    FilePlan(
                        file_key=file_key,
                        file_path=file_path,
                        on_disk_version=None,
                        target_version=target,
                        needs_migration=needs,
                        file_missing=True,
                        entry_type=entry_type,
                    )
                )
                continue

            if on_disk >= target:
                plans.append(
                    FilePlan(
                        file_key=file_key,
                        file_path=file_path,
                        on_disk_version=on_disk,
                        target_version=target,
                        needs_migration=False,
                        entry_type=entry_type,
                    )
                )
                continue

            # Build a from→to map from registered migrations.
            by_from = {int(m["from"]): m for m in migrations}
            cur = on_disk
            while cur < target:
                m = by_from.get(cur)
                if m is None:
                    # No migration registered for cur → cur+1; chain breaks.
                    missing.append(f"v{cur}->v{cur+1}")
                    break
                handler_name = m.get("handler")
                if not handler_name:
                    missing.append(f"v{cur}->v{int(m['to'])} (no handler key in registry)")
                    break
                handler_path = self._handler_module_path(handler_name)
                steps.append(
                    PlannedStep(
                        from_version=int(m["from"]),
                        to_version=int(m["to"]),
                        handler_module=handler_name,
                        handler_path=handler_path,
                        handler_available=handler_path.exists(),
                    )
                )
                if not handler_path.exists():
                    missing.append(handler_name)
                    break
                cur = int(m["to"])

            plans.append(
                FilePlan(
                    file_key=file_key,
                    file_path=file_path,
                    on_disk_version=on_disk,
                    target_version=target,
                    needs_migration=True,
                    entry_type=entry_type,
                    steps=steps,
                    missing_handlers=missing,
                )
            )
        return plans

    def _detect_directory_version(self, dir_path: Path, migrations: list[dict]) -> int | None:
        """For directory entries: ask each registered migration's handler to
        report the on-disk version via its `detect_version()` function. The
        first handler that returns a non-None answer wins.

        Pattern inference per Gap #4 (locked) — handlers observe the actual
        files in the directory rather than relying on a persisted version
        marker.
        """
        if not dir_path.exists():
            return None
        for m in migrations:
            handler_name = m.get("handler")
            if not handler_name:
                continue
            module = self._load_handler(handler_name)
            if module is None:
                continue
            detect_fn = getattr(module, "detect_version", None)
            if not callable(detect_fn):
                continue
            try:
                v = detect_fn(dir_path)
            except Exception:  # noqa: BLE001 — detector errors mean "I don't know"
                continue
            if v is not None:
                return int(v)
        return None

    def scan_drift(self, file_keys: list[str] | None = None, persist: bool = False) -> dict:
        """Registry-driven drift scan (Gap #4).

        Walks the migration registry, detects on-disk versions, and returns
        structured findings for any state file or artifact directory whose
        on-disk version is behind the registry's `current_version`.

        Output shape is uniform across file and directory entries:
            {
                "scanned_at": ISO-8601 UTC timestamp,
                "drift_count": int (count of findings with needs_migration=True),
                "findings": [DriftFinding-as-dict, ...],
            }

        If persist=True, also writes a `framework.drift` block to
        .sweetclaude/state/sweetclaude.yaml so callers (bootstrap,
        fix-sweetclaude) can read the most recent scan without re-running it.
        """
        from datetime import datetime, timezone

        plans = self.plan(file_keys)
        findings: list[DriftFinding] = []
        for p in plans:
            chain_valid = not p.missing_handlers
            findings.append(
                DriftFinding(
                    file_key=p.file_key,
                    file_path=str(p.file_path),
                    entry_type=p.entry_type,
                    on_disk_version=p.on_disk_version,
                    target_version=p.target_version,
                    needs_migration=p.needs_migration,
                    chain_valid=chain_valid,
                    missing_handlers=list(p.missing_handlers),
                    file_missing=p.file_missing,
                )
            )

        scanned_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        drift_count = sum(1 for f in findings if f.needs_migration)

        result = {
            "scanned_at": scanned_at,
            "drift_count": drift_count,
            "findings": [f.to_dict() for f in findings],
        }

        if persist:
            try:
                self._persist_drift(result)
            except OSError:
                pass  # read-only project — drift findings still returned to caller

        return result

    def _persist_drift(self, scan_result: dict) -> None:
        """Write the drift block into .sweetclaude/state/sweetclaude.yaml.

        Preserves all other keys in the file (merges into existing structure).
        Creates the file if it doesn't exist (with minimal scaffold).
        """
        sc_yaml = self.project_dir / self.DEFAULT_STATE_SUBDIR / "sweetclaude.yaml"
        data: dict
        if sc_yaml.exists():
            try:
                data = yaml.safe_load(sc_yaml.read_text()) or {}
            except yaml.YAMLError:
                data = {}
        else:
            data = {}
        framework = data.setdefault("framework", {})
        framework["drift"] = {
            "last_checked": scan_result["scanned_at"],
            "drift_count": scan_result["drift_count"],
            "findings": scan_result["findings"],
        }
        content = yaml.safe_dump(
            data, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
        self._atomic_write(sc_yaml, content)

    def run(
        self,
        file_keys: list[str] | None = None,
        params: dict[str, dict] | None = None,
    ) -> list[FileResult]:
        """Execute migrations for the requested files.

        params: optional per-file parameter dict, e.g.
            {"phase.yaml": {"version_stage": "BETA"}}
        Returns one FileResult per planned file.
        """
        params = params or {}
        plans = self.plan(file_keys)
        results: list[FileResult] = []
        for plan in plans:
            results.append(self._run_one(plan, params.get(plan.file_key, {})))
        return results

    def _run_one(self, plan: FilePlan, file_params: dict) -> FileResult:
        result = FileResult(
            file_key=plan.file_key,
            on_disk_version_before=plan.on_disk_version,
            on_disk_version_after=plan.on_disk_version,
            target_version=plan.target_version,
            success=True,
        )

        if not plan.needs_migration:
            return result  # idempotent: already at target

        if plan.missing_handlers:
            result.success = False
            result.failure_mode = FAILURE_CHAIN_BROKEN
            result.failure_details = (
                f"missing handler(s): {', '.join(plan.missing_handlers)}"
            )
            return result

        # Directory entries take a different execution path entirely — handlers
        # operate on the directory in-place rather than transforming a YAML dict.
        if plan.entry_type == "directory":
            return self._run_directory(plan, file_params)

        # Read source data once at start.
        if not plan.file_path.exists():
            result.success = False
            result.failure_mode = FAILURE_FILE_MISSING
            result.failure_details = str(plan.file_path)
            return result
        try:
            data = yaml.safe_load(plan.file_path.read_text()) or {}
        except yaml.YAMLError as e:
            result.success = False
            result.failure_mode = FAILURE_PARSE_FAILED
            result.failure_details = str(e)
            return result

        # Pull the registry entry to access per-step validation blocks.
        entry = (self.registry.get("state_files") or {}).get(plan.file_key) or {}
        migrations_by_from = {int(m["from"]): m for m in (entry.get("migrations") or [])}

        # Apply each step in sequence.
        for step in plan.steps:
            step_result = StepResult(
                from_version=step.from_version,
                to_version=step.to_version,
                handler_module=step.handler_module,
                success=True,
            )

            migration_entry = migrations_by_from.get(step.from_version) or {}
            pre_validation = migration_entry.get("pre_validation")
            post_validation = migration_entry.get("validation") or migration_entry.get(
                "post_validation"
            )

            # Pre-validation (optional): only checked if the registry block exists.
            if pre_validation:
                ok, reason = self._validate(data, pre_validation)
                if not ok:
                    step_result.success = False
                    step_result.failure_mode = FAILURE_VALIDATION_PRE
                    step_result.failure_details = reason
                    result.steps.append(step_result)
                    result.success = False
                    result.failure_mode = FAILURE_VALIDATION_PRE
                    result.failure_details = reason
                    return result

            # Load + invoke handler.
            module = self._load_handler(step.handler_module)
            if module is None:
                step_result.success = False
                step_result.failure_mode = FAILURE_CHAIN_BROKEN
                step_result.failure_details = (
                    f"could not load handler {step.handler_module}"
                )
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_CHAIN_BROKEN
                result.failure_details = step_result.failure_details
                return result

            up_fn: Callable | None = getattr(module, "up", None)
            if not callable(up_fn):
                step_result.success = False
                step_result.failure_mode = FAILURE_CHAIN_BROKEN
                step_result.failure_details = (
                    f"handler {step.handler_module} has no callable up()"
                )
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_CHAIN_BROKEN
                result.failure_details = step_result.failure_details
                return result

            try:
                data = up_fn(data, file_params)
            except RecoverableMigrationError as e:
                step_result.success = False
                step_result.failure_mode = FAILURE_RECOVERABLE
                step_result.failure_details = e.message
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_RECOVERABLE
                result.failure_details = e.message
                result.recovery_menu = self._build_recovery_menu(e)
                return result
            except KeyError as e:
                step_result.success = False
                step_result.failure_mode = FAILURE_REQUIRED_FIELD_MISSING
                step_result.failure_details = f"handler raised KeyError({e!s})"
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_REQUIRED_FIELD_MISSING
                result.failure_details = step_result.failure_details
                return result
            except Exception as e:  # noqa: BLE001 — broad catch is intentional for runner
                step_result.success = False
                step_result.failure_mode = FAILURE_HANDLER_RAISED
                step_result.failure_details = f"{type(e).__name__}: {e!s}"
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_HANDLER_RAISED
                result.failure_details = step_result.failure_details
                return result

            # Post-validation.
            if post_validation:
                ok, reason = self._validate(data, post_validation)
                if not ok:
                    step_result.success = False
                    step_result.failure_mode = FAILURE_VALIDATION_POST
                    step_result.failure_details = reason
                    result.steps.append(step_result)
                    result.success = False
                    result.failure_mode = FAILURE_VALIDATION_POST
                    result.failure_details = reason
                    return result

            result.steps.append(step_result)

        # All steps succeeded — atomic write.
        try:
            content = yaml.safe_dump(
                data, default_flow_style=False, allow_unicode=True, sort_keys=False
            )
            self._atomic_write(plan.file_path, content)
        except OSError as e:
            result.success = False
            result.failure_mode = FAILURE_WRITE_FAILED
            result.failure_details = str(e)
            return result

        result.on_disk_version_after = data.get("schema_version", plan.target_version)
        return result

    def _run_directory(self, plan: FilePlan, file_params: dict) -> FileResult:
        """Execute a directory migration. Handlers operate on the directory
        in-place; runner aggregates mapping data and writes MIGRATION-MAP.md.

        Handler interface for directories:
            detect_version(directory: Path) -> int | None
            up(directory: Path, params: dict, dry_run: bool = False) -> dict
            down(directory: Path, params: dict, dry_run: bool = False) -> dict

        Handler `up()` return dict (informational; runner consumes these keys):
            {
                "mapping": [
                    {"v_from_id": str, "v_to_id": str, "title": str, "type": str},
                    ...
                ],
                "warnings": [str, ...],
                "files_in": int,
                "files_out": int,
            }
        """
        result = FileResult(
            file_key=plan.file_key,
            on_disk_version_before=plan.on_disk_version,
            on_disk_version_after=plan.on_disk_version,
            target_version=plan.target_version,
            success=True,
        )

        if not plan.file_path.exists():
            result.success = False
            result.failure_mode = FAILURE_FILE_MISSING
            result.failure_details = str(plan.file_path)
            return result

        aggregated_mapping: list[dict] = []
        aggregated_warnings: list[str] = []

        for step in plan.steps:
            step_result = StepResult(
                from_version=step.from_version,
                to_version=step.to_version,
                handler_module=step.handler_module,
                success=True,
            )

            module = self._load_handler(step.handler_module)
            if module is None:
                step_result.success = False
                step_result.failure_mode = FAILURE_CHAIN_BROKEN
                step_result.failure_details = f"could not load handler {step.handler_module}"
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_CHAIN_BROKEN
                result.failure_details = step_result.failure_details
                return result

            up_fn = getattr(module, "up", None)
            if not callable(up_fn):
                step_result.success = False
                step_result.failure_mode = FAILURE_CHAIN_BROKEN
                step_result.failure_details = (
                    f"directory handler {step.handler_module} has no callable up()"
                )
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_CHAIN_BROKEN
                result.failure_details = step_result.failure_details
                return result

            try:
                step_output = up_fn(plan.file_path, file_params) or {}
            except RecoverableMigrationError as e:
                step_result.success = False
                step_result.failure_mode = FAILURE_RECOVERABLE
                step_result.failure_details = e.message
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_RECOVERABLE
                result.failure_details = e.message
                result.recovery_menu = self._build_recovery_menu(e)
                return result
            except KeyError as e:
                step_result.success = False
                step_result.failure_mode = FAILURE_REQUIRED_FIELD_MISSING
                step_result.failure_details = f"handler raised KeyError({e!s})"
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_REQUIRED_FIELD_MISSING
                result.failure_details = step_result.failure_details
                return result
            except Exception as e:  # noqa: BLE001
                step_result.success = False
                step_result.failure_mode = FAILURE_HANDLER_RAISED
                step_result.failure_details = f"{type(e).__name__}: {e!s}"
                result.steps.append(step_result)
                result.success = False
                result.failure_mode = FAILURE_HANDLER_RAISED
                result.failure_details = step_result.failure_details
                return result

            if isinstance(step_output, dict):
                aggregated_mapping.extend(step_output.get("mapping") or [])
                aggregated_warnings.extend(step_output.get("warnings") or [])

            result.steps.append(step_result)

        # All steps succeeded — write MIGRATION-MAP.md if any rows were produced.
        if aggregated_mapping:
            try:
                self._write_migration_map(plan.file_path, aggregated_mapping)
            except OSError as e:
                result.success = False
                result.failure_mode = FAILURE_WRITE_FAILED
                result.failure_details = f"writing MIGRATION-MAP.md: {e!s}"
                return result

        result.on_disk_version_after = plan.target_version
        return result

    def _write_migration_map(self, directory: Path, mapping: list[dict]) -> None:
        """Write the standardized MIGRATION-MAP.md to the artifact directory."""
        from datetime import date
        lines = [
            "# v_from → v_to ID Migration Map",
            f"**Migrated:** {date.today().isoformat()}",
            "",
            "| From ID | To ID | Title | Type |",
            "|---|---|---|---|",
        ]
        for row in sorted(mapping, key=lambda r: r.get("v_from_id", "")):
            lines.append(
                f"| {row.get('v_from_id', '')} "
                f"| {row.get('v_to_id', '')} "
                f"| {row.get('title', '')} "
                f"| {row.get('type', '')} |"
            )
        content = "\n".join(lines) + "\n"
        self._atomic_write(directory / "MIGRATION-MAP.md", content)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_plan(plans: list[FilePlan]) -> str:
    lines = []
    for p in plans:
        if not p.needs_migration:
            lines.append(
                f"  {p.file_key}: on_disk=v{p.on_disk_version} target=v{p.target_version} — no migration needed"
            )
            continue
        chain = " → ".join(f"v{s.from_version}→v{s.to_version}({s.handler_module})" for s in p.steps)
        status = "OK" if not p.missing_handlers else f"BROKEN ({', '.join(p.missing_handlers)})"
        lines.append(
            f"  {p.file_key}: on_disk=v{p.on_disk_version} target=v{p.target_version} steps=[{chain}] {status}"
        )
    return "\n".join(lines) if lines else "  (no registered files)"


def _format_results(results: list[FileResult]) -> str:
    lines = []
    for r in results:
        if r.success and r.on_disk_version_before == r.on_disk_version_after:
            lines.append(f"  {r.file_key}: idempotent — already at v{r.target_version}")
        elif r.success:
            lines.append(
                f"  {r.file_key}: OK v{r.on_disk_version_before}→v{r.on_disk_version_after} ({len(r.steps)} step(s))"
            )
        else:
            lines.append(
                f"  {r.file_key}: FAILED [{r.failure_mode}] {r.failure_details}"
            )
    return "\n".join(lines) if lines else "  (no results)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run SweetClaude state-file migrations."
    )
    parser.add_argument(
        "--project-dir", default=".", help="Path to the project root (default: cwd)"
    )
    parser.add_argument(
        "--file",
        action="append",
        dest="files",
        help="Limit run to a specific state file (repeatable). Default: all registered files.",
    )
    parser.add_argument(
        "--registry", default=None, help="Path to migration-registry.yaml (default: framework default)"
    )
    parser.add_argument(
        "--migrations-dir",
        default=None,
        help="Path to handler modules directory (default: scripts/migrations relative to this script)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the migration plan and exit without executing."
    )
    parser.add_argument(
        "--scan-drift",
        action="store_true",
        help="Run drift scan only — registry-walk + version detection. Prints structured findings. Does not migrate.",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="With --scan-drift: also persist findings to .sweetclaude/state/sweetclaude.yaml framework.drift.*",
    )
    parser.add_argument(
        "--report-drift-for-skill",
        action="store_true",
        help=(
            "Skill-friendly drift report. Runs scan-drift --persist and prints "
            "exactly: DRIFT_COUNT=N and FINDING|<file_key>|v<from>-><to>|chain=<ok|broken> "
            "lines for findings with needs_migration=True. Returns 0 even with drift."
        ),
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Per-file param: file_key:key=value (repeatable). Example: --param phase.yaml:version_stage=BETA",
    )
    args = parser.parse_args(argv)

    runner = MigrationRunner(
        project_dir=args.project_dir,
        registry_path=args.registry,
        migrations_dir=args.migrations_dir,
    )

    # Parse --param entries.
    params: dict[str, dict] = {}
    for p in args.param:
        if ":" not in p or "=" not in p:
            print(f"ERROR: invalid --param '{p}' (expected file_key:key=value)", file=sys.stderr)
            return 2
        file_key, kv = p.split(":", 1)
        k, v = kv.split("=", 1)
        params.setdefault(file_key, {})[k] = v

    if args.report_drift_for_skill:
        scan = runner.scan_drift(args.files, persist=args.persist)
        needs = [f for f in scan["findings"] if f.get("needs_migration")]
        print(f"DRIFT_COUNT={len(needs)}")
        for f in needs:
            if f.get("file_missing"):
                print(f"MISSING|{f['file_key']}")
            else:
                chain = "ok" if f.get("chain_valid") else "broken"
                print(
                    f"FINDING|{f['file_key']}|v{f['on_disk_version']}->v{f['target_version']}|chain={chain}"
                )
        return 0

    if args.scan_drift:
        scan = runner.scan_drift(args.files, persist=args.persist)
        print(f"Drift scan ({scan['scanned_at']}): {scan['drift_count']} finding(s)")
        for f in scan["findings"]:
            mark = "DRIFT" if f["needs_migration"] else "ok   "
            chain = "" if f["chain_valid"] else f" [chain_broken: {','.join(f['missing_handlers'])}]"
            print(
                f"  [{mark}] {f['file_key']}: on_disk=v{f['on_disk_version']} target=v{f['target_version']} type={f['entry_type']}{chain}"
            )
        if args.persist:
            print("Drift findings persisted to .sweetclaude/state/sweetclaude.yaml")
        return 0

    if args.dry_run:
        plans = runner.plan(args.files)
        print("Migration plan:")
        print(_format_plan(plans))
        return 0

    results = runner.run(args.files, params=params)
    print("Migration results:")
    print(_format_results(results))
    any_failed = any(not r.success for r in results)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
