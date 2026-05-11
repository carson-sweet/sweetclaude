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
    steps: list[PlannedStep] = field(default_factory=list)
    missing_handlers: list[str] = field(default_factory=list)


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
        # Migration registry ships with the framework; default to discovering
        # it relative to this runner module.
        repo_root = Path(__file__).resolve().parent.parent.parent
        self.registry_path = (
            Path(registry_path) if registry_path else repo_root / "config" / "migration-registry.yaml"
        )
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
            if base_path:
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
        """Dynamically import a handler module."""
        path = self._handler_module_path(handler_name)
        if not path.exists():
            return None
        spec = importlib.util.spec_from_file_location(
            f"sweetclaude_migration_{handler_name}", path
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write file via temp + os.replace for atomicity."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", dir=str(path.parent), suffix=".tmp", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_name = tmp.name
        os.replace(tmp_name, str(path))

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

            if on_disk is None or on_disk >= target:
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
