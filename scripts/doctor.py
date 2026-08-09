#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SweetClaude doctor — diagnostic scan and repair engine.

Deterministic engine with no user interaction. The skill layer
(skills/doctor/SKILL.md) owns all UX: report rendering, menus,
prompted fixes, safety branch offers. This script owns: scan,
auto-fix, archive, persist, suppression, dry-run simulation.

All data crosses the skill/script boundary as JSON.

CLI subcommands:
  scan              --project-dir DIR
  create-archive    --project-dir DIR
  auto-fix          --project-dir DIR --archive-dir DIR  (stdin: findings)
  post-fix-rescan   --project-dir DIR --categories C1,C2 (stdin: original findings)
  record-action     --archive-dir DIR                    (stdin: action JSON)
  dry-run           --project-dir DIR                    (stdin: findings)
  persist           --project-dir DIR --archive-dir DIR [--menu-preference VAL]
  prune-archives    --project-dir DIR

All commands emit JSON on stdout. Errors emit on stderr; exit 1 on failure.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Callable

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip install pyyaml")

from schema import (
    REQUIRED_FIELDS,
    VALID_TYPES,
    normalize_milestone,
    normalize_status,
    validate_frontmatter,
)
from maintenance.capability_manifest import capability_config, project_shape_config
from status import CANONICAL_STATUSES, TERMINAL_STATUSES, derived_status


_SCRIPTS_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    id: str
    category: str
    severity: str           # "error" | "warning" | "info"
    summary: str            # user-facing, plain English
    detail: str             # technical, paths + values
    file_paths: list[str]
    fix_type: str           # "auto" | "prompted" | "report-only"
    fix_recipe: dict
    previously_suppressed: bool = False


@dataclass
class RecipeResult:
    finding_id: str
    before_hash: str
    after_hash: str | None
    backup_path: Path | None
    success: bool
    error: str | None = None


@dataclass
class ProjectState:
    project_dir: Path
    sweetclaude_yaml: dict | None
    artifact_privacy: dict | None
    session_state: dict | None
    product_base: Path
    backlog_files: list[Path]
    roadmap_files: list[Path]
    hook_files: list[Path]
    hook_manifest: dict | None
    hooks_json: dict | None
    settings_global: dict | None
    settings_local: dict | None
    claude_md_project: str | None
    claude_md_global: str | None
    rules_files: dict[str, str]
    skills_yaml: dict | None
    installed_version: str | None
    migration_runner_path: Path | None
    suppressions: list[dict] = field(default_factory=list)


class DependencyMissing(Exception):
    pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_DATETIME_FIELDS = frozenset({
    "created", "updated", "completed", "closed_date",
})

RUN_SCRIPT_ALLOWLIST = {
    "cache.py",
    "generate-session-state.sh",
    "generate-skills-state.py",
    "runner.py",
}

# Actions execute_recipe can actually perform. Any finding presented as
# auto/prompted MUST use one of these (or "prompt", which is presented for
# approval rather than executed). Enforced at runtime by
# _enforce_executable_contract so doctor can never offer a fix it cannot run.
EXECUTOR_SUPPORTED_ACTIONS = frozenset({
    "run_script",
    "rebuild_cache",
    "create_dir",
    "delete_file",
    "write_field",
    "write_frontmatter_field",
    "prompt",
    "sync_parent_status",
    "convert_to_yaml",
    "config_conflict",
    "yaml_repair",
    "hook_restore",
    "file_move",
    "renumber_duplicate",
    "resolve_orphans",
})

# Manual guidance for known-unsupported actions, surfaced when an auto/prompted
# finding is downgraded. Keeps the no-data-loss path actionable instead of
# leaving a dangling, unrunnable fix.
_UNSUPPORTED_ACTION_GUIDANCE = {
}


RESOLUTION_AUTO = "auto-fixable"
RESOLUTION_GUIDED = "guided-manual"
RESOLUTION_ACCEPTED = "accepted-no-action"
RESOLUTION_FALLBACK = "terminal-fallback"


def classify_resolution(finding: Finding) -> str:
    """Map a finding to its resolution path. Total by construction — every
    finding gets a class, worst case the terminal fallback. Nothing dangles.

    Runs AFTER _enforce_executable_contract, so any auto/prompted finding here
    has an executable action.
    """
    action = (finding.fix_recipe or {}).get("action", "")
    if finding.fix_type == "auto" and action in EXECUTOR_SUPPORTED_ACTIONS:
        return RESOLUTION_AUTO
    if finding.fix_type == "prompted":
        return RESOLUTION_GUIDED
    if finding.fix_type == "report-only":
        if finding.category == "compatibility_mode" or finding.severity == "info":
            return RESOLUTION_ACCEPTED
        if _report_only_has_guidance(finding):
            return RESOLUTION_GUIDED
        return RESOLUTION_FALLBACK
    return RESOLUTION_FALLBACK


_GUIDANCE_MARKERS = ("executable-contract:", "Guidance:", "guidance:", "Resolve", "python3", "run ")


def _report_only_has_guidance(finding: Finding) -> bool:
    return any(m in (finding.detail or "") for m in _GUIDANCE_MARKERS)


def _trigger_out_of_chain(state: "ProjectState | None") -> bool:
    """True if the migration runner reports a schema version OUTSIDE the
    supported migration chain (any FINDING|...|chain=broken).

    Source primitive: runner.py --report-drift-for-skill, which emits
    DRIFT_COUNT=N then FINDING|<key>|v<from>-><to>|chain=<ok|broken>. Degrades
    gracefully to False if the runner is absent or errors (no crash)."""
    if state is None or not getattr(state, "migration_runner_path", None):
        return False
    try:
        r = subprocess.run(
            [sys.executable, str(state.migration_runner_path),
             "--report-drift-for-skill", "--project-dir", str(state.project_dir)],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    if r.returncode != 0:
        return False
    for line in r.stdout.splitlines():
        if line.startswith("FINDING|") and line.rstrip().endswith("chain=broken"):
            return True
    return False


def _trigger_uncorrectable_after_repair(state: "ProjectState | None") -> bool:
    """True if the core sweetclaude.yaml has an unrecoverable parse error — the
    best available signal that no state-file repair can fix the project.

    Source primitive: the same YAML parse-detection check_state_integrity uses
    (sweetclaude.yaml present on disk but state.sweetclaude_yaml is None because
    it failed to parse). Degrades gracefully to False if the file is absent."""
    if state is None:
        return False
    sc_yaml_path = state.project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not sc_yaml_path.exists() or state.sweetclaude_yaml is not None:
        return False
    try:
        yaml.safe_load(sc_yaml_path.read_text())
    except yaml.YAMLError:
        return True
    except OSError:
        return False
    return False


def _trigger_recovery_looped(state: "ProjectState | None") -> bool:
    """True if recover_project's recovery state signals a stopped/looped
    recovery. We READ the signal recovery already computes — we do not
    re-derive it.

    Source primitive: recover_project writes execution-manifest.json under
    .sweetclaude/state/recovery-runs/<run>/ with status="stopped" and
    repair_loop.stop=True when should_stop_repair_loop fires. Degrades
    gracefully to False if no recovery run exists or a manifest is unreadable."""
    if state is None:
        return False
    runs_dir = state.project_dir / ".sweetclaude" / "state" / "recovery-runs"
    if not runs_dir.is_dir():
        return False
    for run_dir in runs_dir.iterdir():
        manifest_path = run_dir / "execution-manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, dict):
            continue
        repair_loop = manifest.get("repair_loop")
        if isinstance(repair_loop, dict) and repair_loop.get("stop") is True:
            return True
        if manifest.get("status") == "stopped":
            return True
    return False


def _build_terminal_fallback(
    maintenance_route: dict,
    state: "ProjectState | None" = None,
    findings: "list[Finding] | None" = None,
) -> dict:
    """The guaranteed exits when nothing else resolves a finding.

    Re-adopt is the universal no-data-loss backstop: it works even when a layout
    has no validated migrator. Purge is the clean-break last resort. Both
    full-migration and re-adopt snapshot first; purge snapshots first too as a
    safety net even though it does not preserve data.

    The `triggers` dict tells the SKILL WHEN to surface the Tier-4 menu. The
    three script-computed triggers are SAFE on a healthy project (all False) and
    degrade gracefully when the runner/recovery state is absent. `user_requested`
    is never script-computed — it is a flag the skill sets on explicit user
    request (default False) and does NOT feed `any`.
    """
    migration_available = maintenance_route.get("status") == "supported-migration-available"

    out_of_chain = _trigger_out_of_chain(state)
    uncorrectable_after_repair = _trigger_uncorrectable_after_repair(state)
    recovery_looped = _trigger_recovery_looped(state)

    triggers = {
        "out_of_chain": out_of_chain,
        "uncorrectable_after_repair": uncorrectable_after_repair,
        "recovery_looped": recovery_looped,
        # Skill-set only — never script-computed. The skill flips this on an
        # explicit user request to surface Tier-4. Excluded from `any`.
        "user_requested": False,
        "any": bool(out_of_chain or uncorrectable_after_repair or recovery_looped),
    }

    return {
        "always_available": True,
        "triggers": triggers,
        "options": [
            {
                "id": "full-migration",
                "label": "Full migration to the current taxonomy",
                "available": migration_available,
                "blocked_reason": (
                    None if migration_available
                    else "No validated migrator for this layout; use re-adopt."
                ),
                "no_data_loss": True,
                "snapshot_first": True,
                "capability": "migrate",
            },
            {
                "id": "re-adopt",
                "label": "Re-adopt the project (archive existing state, re-onboard, port content)",
                "available": True,
                "no_data_loss": True,
                "snapshot_first": True,
                # V8 / plan §8.4: re_adopt.py archives .sweetclaude/ then hands
                # to sweetclaude:init as the re-onboard entry point. There is NO
                # sweetclaude:adopt skill.
                "capability": "init",
                "executable": "scripts/recovery/re_adopt.py",
                "plan_first": "recovery.re_adopt.plan_re_adopt",
                "reversible": "recovery.re_adopt.reverse_re_adopt",
            },
            {
                "id": "purge",
                "label": "Remove SweetClaude entirely (clean break — no legacy archive)",
                "available": True,
                "no_data_loss": False,
                "snapshot_first": True,
                "capability": "purge",
            },
        ],
    }


def _classify_all(
    findings: list[Finding],
    maintenance_route: dict,
    state: "ProjectState | None" = None,
) -> tuple[dict, dict]:
    """Return (resolution_summary, per_finding_class). Totality guarantee:
    every finding maps to a class; if any is unresolved, the terminal fallback
    is present."""
    per_id: dict[str, str] = {}
    by_class: dict[str, int] = {}
    for f in findings:
        cls = classify_resolution(f)
        per_id[f.id] = cls
        by_class[cls] = by_class.get(cls, 0) + 1
    summary = {
        "total": len(findings),
        "by_class": by_class,
        "unresolved_count": by_class.get(RESOLUTION_FALLBACK, 0),
        "all_findings_routed": True,  # true by construction of classify_resolution
        "terminal_fallback": _build_terminal_fallback(
            maintenance_route, state=state, findings=findings),
    }
    return summary, per_id


def _enforce_executable_contract(findings: list[Finding]) -> tuple[list[Finding], dict]:
    """Downgrade any auto/prompted finding whose action the executor cannot run.

    This is the structural guarantee that doctor never presents a fix it cannot
    perform (the syncog sync_parent_status class). Unsupported actions become
    report-only with explicit manual guidance, rather than a dangling
    'auto' fix that silently fails.
    """
    adjusted: list[Finding] = []
    downgraded: list[str] = []
    for f in findings:
        action = (f.fix_recipe or {}).get("action", "")
        if f.fix_type in ("auto", "prompted") and action not in EXECUTOR_SUPPORTED_ACTIONS:
            guidance = _UNSUPPORTED_ACTION_GUIDANCE.get(
                action,
                f"Doctor cannot auto-apply action '{action}'. Resolve manually; "
                "no automatic fix is available for this finding.",
            )
            downgraded.append(f.id)
            adjusted.append(replace(
                f,
                fix_type="report-only",
                detail=f"{f.detail} | executable-contract: {guidance}",
                fix_recipe={},
            ))
        else:
            adjusted.append(f)
    return adjusted, {"downgraded_count": len(downgraded), "downgraded_ids": downgraded}


def _script_has_cli_entrypoint(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text()
    except OSError:
        return False
    return "__name__" in text and "__main__" in text


# ---------------------------------------------------------------------------
# Frontmatter helper
# ---------------------------------------------------------------------------

def _read_frontmatter(path: Path) -> dict | None:
    try:
        raw = path.read_text()
    except OSError:
        return None
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                if isinstance(fm, dict):
                    return fm
            except yaml.YAMLError:
                pass
    try:
        from parse_utils import parse_bold_metadata
        return parse_bold_metadata(raw)
    except ImportError:
        return None


def _read_frontmatter_raw(path: Path) -> tuple[dict | None, str | None]:
    """Return (parsed_frontmatter, error_description)."""
    try:
        raw = path.read_text()
    except OSError:
        return None, "file unreadable"
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                return fm, None
            except yaml.YAMLError as e:
                return None, f"YAML parse error: {e}"
    try:
        from parse_utils import parse_bold_metadata
        fm = parse_bold_metadata(raw)
        if fm is not None:
            return fm, None
    except ImportError:
        pass
    return None, "no frontmatter delimiter"


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def check_state_integrity(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    sc_yaml_path = state.project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"

    if sc_yaml_path.exists() and state.sweetclaude_yaml is None:
        try:
            yaml.safe_load(sc_yaml_path.read_text())
        except yaml.YAMLError as e:
            line_info = ""
            if hasattr(e, "problem_mark") and e.problem_mark:
                line_info = f" at line {e.problem_mark.line + 1}"
            findings.append(Finding(
                id="state-integrity:yaml-parse:sweetclaude.yaml",
                category="state_integrity",
                severity="error",
                summary=f"Your main config file has a syntax error{line_info}",
                detail=f"sweetclaude.yaml YAML parse failure: {e}",
                file_paths=[str(sc_yaml_path)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "yaml_repair",
                            "file": str(sc_yaml_path)},
            ))

    ss_path = state.project_dir / ".sweetclaude" / "state" / "session-state.yaml"
    if not ss_path.exists():
        findings.append(Finding(
            id="state-integrity:missing:session-state.yaml",
            category="state_integrity",
            severity="warning",
            summary="Session state file is missing — some skills may not work correctly",
            detail=f"Expected {ss_path}",
            file_paths=[str(ss_path)],
            fix_type="auto",
            fix_recipe={"action": "run_script",
                        "cmd": ["bash", str(Path.home() / ".claude" / "hooks" / "sweetclaude" / "generate-session-state.sh")],
                        "args": [],
                        "regenerates": [".sweetclaude/state/session-state.yaml"]},
        ))

    if state.sweetclaude_yaml:
        schema_v = state.sweetclaude_yaml.get("phase_schema_version")
        if schema_v is not None and schema_v != 2:
            if state.migration_runner_path:
                findings.append(Finding(
                    id="state-integrity:schema-version:sweetclaude.yaml",
                    category="state_integrity",
                    severity="warning",
                    summary="Config file is on an old schema version",
                    detail=f"phase_schema_version={schema_v}, expected 2",
                    file_paths=[str(sc_yaml_path)],
                    fix_type="auto",
                    fix_recipe={"action": "run_script",
                                "cmd": [sys.executable, str(state.migration_runner_path),
                                        "--project-dir", str(state.project_dir),
                                        "--file", "sweetclaude.yaml"],
                                "args": [],
                                "regenerates": [str(sc_yaml_path)]},
                ))
            else:
                findings.append(Finding(
                    id="state-integrity:schema-version:sweetclaude.yaml",
                    category="state_integrity",
                    severity="warning",
                    summary="Config file is on an old schema version",
                    detail=f"phase_schema_version={schema_v}, expected 2",
                    file_paths=[str(sc_yaml_path)],
                    fix_type="report-only",
                    fix_recipe={},
                ))

        fw = state.sweetclaude_yaml.get("framework", {})
        stored_version = fw.get("installed_version")
        if stored_version and state.installed_version and stored_version != state.installed_version:
            findings.append(Finding(
                id="state-integrity:version-drift:installed_version",
                category="state_integrity",
                severity="warning",
                summary="Installed version doesn't match what's recorded in your config",
                detail=f"sweetclaude.yaml says {stored_version}, installed_plugins.json says {state.installed_version}",
                file_paths=[str(sc_yaml_path)],
                fix_type="auto",
                fix_recipe={"action": "write_field",
                            "file": str(sc_yaml_path),
                            "key": "framework",
                            "value": {**fw, "installed_version": state.installed_version}},
            ))

    if state.artifact_privacy and state.session_state:
        auth_base = (
            (state.artifact_privacy.get("categories") or {})
            .get("product", {})
            .get("base_path", "")
        ).rstrip("/")
        snap_base = (
            (state.session_state.get("paths") or {})
            .get("product_base", "")
        ).rstrip("/")
        if auth_base and snap_base and auth_base != snap_base:
            findings.append(Finding(
                id="state-integrity:product-base-drift:session-state",
                category="state_integrity",
                severity="warning",
                summary="Product base path is out of sync between config files",
                detail=f"artifact-privacy.yaml says {auth_base}, session-state.yaml says {snap_base}",
                file_paths=[
                    str(state.project_dir / ".sweetclaude" / "artifact-privacy.yaml"),
                    str(state.project_dir / ".sweetclaude" / "state" / "session-state.yaml"),
                ],
                fix_type="auto",
                fix_recipe={"action": "run_script",
                            "cmd": ["bash", str(Path.home() / ".claude" / "hooks" / "sweetclaude" / "generate-session-state.sh")],
                            "args": [],
                            "regenerates": [".sweetclaude/state/session-state.yaml"]},
            ))

    return findings


def check_hook_health(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []

    if state.hooks_json is None:
        hooks_json_path = Path.home() / ".claude" / "hooks" / "sweetclaude" / "hooks.json"
        findings.append(Finding(
            id="hook-health:missing:hooks.json",
            category="hook_health",
            severity="error",
            summary="SweetClaude hooks configuration is missing",
            detail=f"Expected {hooks_json_path}",
            file_paths=[str(hooks_json_path)],
            fix_type="prompted",
            fix_recipe={"action": "prompt", "type": "hook_restore",
                        "hook": "hooks.json", "sources": ["backup", "repo"]},
        ))

    for hf in state.hook_files:
        try:
            result = subprocess.run(
                ["bash", "-n", str(hf)],
                capture_output=True, timeout=5,
            )
            if result.returncode != 0:
                findings.append(Finding(
                    id=f"hook-health:syntax-error:{hf.name}",
                    category="hook_health",
                    severity="error",
                    summary=f"Hook script {hf.name} has a syntax error",
                    detail=f"bash -n failed: {result.stderr.decode(errors='replace')[:200]}",
                    file_paths=[str(hf)],
                    fix_type="prompted",
                    fix_recipe={"action": "prompt", "type": "hook_restore",
                                "hook": hf.name, "sources": ["backup", "repo"]},
                ))
        except (subprocess.TimeoutExpired, OSError):
            pass

    # A hook the manifest declares but that is absent on disk cannot fire.
    # Consult the loaded manifest (hooks-manifest.json) for expected scripts and
    # compare against what is present, so a missing hook is detectable AND
    # fixable end-to-end via the hook_restore prompt.
    if state.hook_manifest:
        hooks_dir = Path.home() / ".claude" / "hooks" / "sweetclaude"
        present_names = {hf.name for hf in state.hook_files}
        for entry in state.hook_manifest.get("hooks", []):
            name = entry.get("file") if isinstance(entry, dict) else None
            if not name:
                continue
            if name in present_names:
                continue
            findings.append(Finding(
                id=f"hook-health:missing-hook:{name}",
                category="hook_health",
                severity="error",
                summary=f"Hook script {name} is declared in the manifest but missing",
                detail=f"Expected {hooks_dir / name} (declared in hooks-manifest.json)",
                file_paths=[str(hooks_dir / name)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "hook_restore",
                            "hook": name, "sources": ["backup", "repo"]},
            ))

    rules_dir = Path.home() / ".claude" / "rules" / "sweetclaude"
    expected_rules = ["interaction-model.md", "phase-gates.md", "tdd-levels.md"]
    for rf in expected_rules:
        if f"sweetclaude/{rf}" not in state.rules_files:
            findings.append(Finding(
                id=f"hook-health:missing-rule:{rf}",
                category="hook_health",
                severity="warning",
                summary=f"SweetClaude rules file {rf} is missing",
                detail=f"Expected at {rules_dir / rf}",
                file_paths=[str(rules_dir / rf)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "hook_restore",
                            "hook": rf, "sources": ["backup", "repo"]},
            ))

    return findings


_VOLATILE_FRONTMATTER_KEYS = ("created", "updated", "last_updated", "modified")


def _content_sans_volatile(path: Path):
    """Return (frontmatter_without_volatile_keys, body) for duplicate comparison,
    or None if unreadable. Volatile keys (e.g. created) are dropped so two copies
    that differ only by a timestamp still compare equal."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ({}, text)
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        return None
    if isinstance(fm, dict):
        for key in _VOLATILE_FRONTMATTER_KEYS:
            fm.pop(key, None)
    return (fm, parts[2])


def _duplicate_files_identical(file_a: Path, file_b: Path) -> bool:
    """True if two colliding files are the same item once volatile frontmatter is
    ignored. Unreadable/ambiguous -> False (treat as divergent, keeping the safe
    renumber offer)."""
    a = _content_sans_volatile(file_a)
    b = _content_sans_volatile(file_b)
    if a is None or b is None:
        return False
    return a == b


def check_storage_lint(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    backlog_dir = state.product_base / "backlog"
    roadmap_dir = state.product_base / "roadmap"

    if backlog_dir.is_dir() and roadmap_dir.is_dir():
        backlog_files: dict[str, Path] = {}
        for p in backlog_dir.rglob("*.md"):
            if p.name in ("INDEX.md", "MIGRATION-MAP.md"):
                continue
            fm = _read_frontmatter(p)
            if fm and fm.get("id"):
                backlog_files.setdefault(str(fm["id"]), p)
        roadmap_files: dict[str, Path] = {}
        for p in roadmap_dir.rglob("*.md"):
            fm = _read_frontmatter(p)
            if fm and fm.get("id"):
                roadmap_files.setdefault(str(fm["id"]), p)
        all_known_ids = set(backlog_files) | set(roadmap_files)
        for dup_id in sorted(set(backlog_files) & set(roadmap_files)):
            file_a = backlog_files[dup_id]
            file_b = roadmap_files[dup_id]
            proposed = _propose_next_id(dup_id, all_known_ids)
            label_a = str(file_a.parent.relative_to(state.product_base))
            label_b = str(file_b.parent.relative_to(state.product_base))
            # Identical copies (same item copied between folders) must be
            # de-duplicated by dropping one, not renumbered — renumbering would
            # mint a phantom second item. Divergent files are genuinely distinct,
            # so they keep the renumber offer.
            if _duplicate_files_identical(file_a, file_b):
                fix_recipe = {
                    "action": "prompt",
                    "type": "resolve_identical_duplicate",
                    "duplicate_id": dup_id,
                    "files": [str(file_a), str(file_b)],
                    "labels": [label_a, label_b],
                    # Recommend keeping the backlog copy (the status-appropriate
                    # home for an unscheduled item) and removing the roadmap copy.
                    "recommended_keep": str(file_a),
                    "recommended_remove": str(file_b),
                }
            else:
                fix_recipe = {
                    "action": "prompt",
                    "type": "renumber_duplicate",
                    "duplicate_id": dup_id,
                    "files": [str(file_a), str(file_b)],
                    "labels": [label_a, label_b],
                    "proposed_new_id": proposed,
                }
            findings.append(Finding(
                id=f"storage-lint:cross-location-duplicate-id:{dup_id}",
                category="storage_lint",
                severity="error",
                summary=f"Item {dup_id} exists in both backlog and roadmap",
                detail=f"ID {dup_id} found in both {file_a} and {file_b}",
                file_paths=[str(file_a), str(file_b)],
                fix_type="prompted",
                fix_recipe=fix_recipe,
            ))

    if backlog_dir.is_dir():
        max_seen = 0
        for p in backlog_dir.rglob("*.md"):
            m = re.match(r"^ISSUE-(\d+)-", p.name)
            if m:
                max_seen = max(max_seen, int(m.group(1)))

        cache_script = _SCRIPTS_DIR / "cache.py"
        if not cache_script.exists():
            pass
        else:
            try:
                r = subprocess.run(
                    [sys.executable, str(cache_script), "--project-dir",
                     str(state.project_dir), "--query", "next-id", "--prefix", "ISSUE"],
                    capture_output=True, text=True, timeout=10,
                )
                cache_data = json.loads(r.stdout)
                next_id = cache_data.get("next_id", "")
                id_match = re.search(r"(\d+)", next_id)
                cache_max = int(id_match.group(1)) - 1 if id_match else 0
            except Exception:
                cache_max = max_seen

            if max_seen > cache_max:
                findings.append(Finding(
                    id="storage-lint:counter-drift:issue",
                    category="storage_lint",
                    severity="warning",
                    summary="Your cache is out of sync with your files",
                    detail=f"counter-drift: cache_max={cache_max}, file_max={max_seen}",
                    file_paths=[],
                    fix_type="auto",
                    fix_recipe={"action": "rebuild_cache"},
                ))

        sc_version = ""
        if state.sweetclaude_yaml:
            sc_version = (
                state.sweetclaude_yaml.get("framework", {})
                .get("installed_version", "")
            )
        v3_files = list(backlog_dir.glob("BL-*.md"))
        if v3_files and sc_version.startswith("4."):
            findings.append(Finding(
                id="storage-lint:v3-files-present:backlog",
                category="storage_lint",
                severity="warning",
                summary=f"{len(v3_files)} old-format files still need migrating",
                detail=f"v3-files-present: {len(v3_files)} BL-NNN files in {backlog_dir}",
                file_paths=[str(p) for p in v3_files[:5]],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "migration",
                            "script": "migrate-v3-to-v4.py", "args": []},
            ))

        done_dir = backlog_dir / "done"
        if done_dir.is_dir():
            for p in done_dir.glob("*.md"):
                fm = _read_frontmatter(p)
                if fm and fm.get("status") not in ("done", "abandoned"):
                    findings.append(Finding(
                        id=f"storage-lint:done-status-mismatch:{p.name}",
                        category="storage_lint",
                        severity="warning",
                        summary=f"{p.name} is in the done folder but isn't marked as done",
                        detail=f"done-status-mismatch: {p.name} in done/ has status={fm.get('status')}",
                        file_paths=[str(p)],
                        fix_type="prompted",
                        fix_recipe={"action": "prompt", "type": "file_move",
                                    "src": str(p), "dest": str(backlog_dir / p.name)},
                    ))

        for p in backlog_dir.rglob("ISSUE-*.md"):
            if "done" in p.parts or "archived" in p.parts:
                continue
            fm = _read_frontmatter(p)
            if fm and fm.get("status") in ("done", "abandoned"):
                findings.append(Finding(
                    id=f"storage-lint:done-status-mismatch:{p.name}",
                    category="storage_lint",
                    severity="warning",
                    summary=f"{p.name} is marked done but isn't in the done folder",
                    detail=f"done-status-mismatch: {p.name} has status={fm.get('status')} but not in done/",
                    file_paths=[str(p)],
                    fix_type="prompted",
                    fix_recipe={"action": "prompt", "type": "file_move",
                                "src": str(p),
                                "dest": str(backlog_dir / "done" / p.name)},
                ))

    if roadmap_dir.is_dir():
        issues_dir = roadmap_dir / "issues"
        if issues_dir.is_dir():
            done_dir = issues_dir / "done"
            for p in issues_dir.rglob("ISSUE-*.md"):
                if "done" in p.parts:
                    continue
                fm = _read_frontmatter(p)
                if fm and fm.get("status") in ("done", "abandoned"):
                    findings.append(Finding(
                        id=f"storage-lint:done-status-mismatch:{p.name}",
                        category="storage_lint",
                        severity="warning",
                        summary=f"{p.name} is marked done but isn't in the done folder",
                        detail=f"done-status-mismatch: {p.name} has status={fm.get('status')} but not in done/",
                        file_paths=[str(p)],
                        fix_type="prompted",
                        fix_recipe={"action": "prompt", "type": "file_move",
                                    "src": str(p),
                                    "dest": str((done_dir if done_dir.is_dir() else issues_dir / "done") / p.name)},
                    ))

        epics_dir = roadmap_dir / "epics"
        if epics_dir.is_dir():
            for p in epics_dir.glob("*.md"):
                if p.parent.name == "done":
                    continue
                fm = _read_frontmatter(p)
                if not fm or fm.get("type") != "epic":
                    continue
                if fm.get("status") in ("done", "abandoned"):
                    continue
                if not fm.get("completion_criteria"):
                    findings.append(Finding(
                        id=f"storage-lint:epic-missing-criteria:{fm.get('id', p.stem)}",
                        category="storage_lint",
                        severity="info",
                        summary=f"Epic {fm.get('id', p.stem)} has no completion criteria defined",
                        detail=f"epic-missing-criteria: {p.name} — cache will render Criteria: 0/0",
                        file_paths=[str(p)],
                        fix_type="report-only",
                        fix_recipe={},
                    ))

    return findings


def check_migration_currency(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []

    if not state.migration_runner_path:
        raise DependencyMissing("migration runner not found — cannot check migration currency")

    drift_marker = state.project_dir / ".sweetclaude" / "state" / "pending-drift-decision.yaml"
    if drift_marker.exists():
        findings.append(Finding(
            id="migration-currency:stale-drift-marker:pending-drift-decision.yaml",
            category="migration_currency",
            severity="info",
            summary="Stale drift marker left over from a previous session",
            detail=f"pending-drift-decision.yaml exists at {drift_marker}",
            file_paths=[str(drift_marker)],
            fix_type="auto",
            fix_recipe={"action": "delete_file", "file": str(drift_marker)},
        ))

    if state.migration_runner_path:
        # C3.5b: --scan-drift prints HUMAN PROSE, not JSON — json.loads()'ing it
        # always raised JSONDecodeError, which was swallowed, so a schema-drift
        # finding could never be produced. The machine-parseable mode is
        # --report-drift-for-skill, which emits DRIFT_COUNT=N then
        # FINDING|<file_key>|v<from>-><to>|chain=<ok|broken> (and MISSING|<file_key>
        # for absent files). Parse that line format, reusing the P2.1 pattern from
        # _trigger_out_of_chain. Degrades gracefully on absent/erroring runner.
        try:
            r = subprocess.run(
                [sys.executable, str(state.migration_runner_path),
                 "--report-drift-for-skill", "--project-dir", str(state.project_dir)],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    line = line.strip()
                    chain = ""
                    if line.startswith("FINDING|"):
                        parts = line.split("|")
                        file_key = parts[1] if len(parts) > 1 else "unknown"
                        version = parts[2] if len(parts) > 2 else ""
                        chain = parts[3] if len(parts) > 3 else ""
                        detail = f"Schema drift: {file_key} {version}".strip()
                        if chain:
                            detail = f"{detail} ({chain})"
                    elif line.startswith("MISSING|"):
                        parts = line.split("|")
                        file_key = parts[1] if len(parts) > 1 else "unknown"
                        detail = f"Schema drift: {file_key} is missing and cannot be migrated"
                    else:
                        continue
                    chain_ok = chain.endswith("ok") if chain else False
                    if chain_ok and not line.startswith("MISSING|"):
                        runner_path = str(state.migration_runner_path)
                        state_file = str(state.project_dir / ".sweetclaude" / "state" / file_key)
                        findings.append(Finding(
                            id=f"migration-currency:schema-drift:{file_key}",
                            category="migration_currency",
                            severity="warning",
                            summary="A state file needs to be upgraded to the current schema",
                            detail=detail,
                            file_paths=[file_key],
                            fix_type="auto",
                            fix_recipe={"action": "run_script",
                                        "cmd": [sys.executable, runner_path,
                                                "--project-dir", str(state.project_dir),
                                                "--file", file_key],
                                        "args": [],
                                        "regenerates": [state_file]},
                        ))
                    else:
                        findings.append(Finding(
                            id=f"migration-currency:schema-drift:{file_key}",
                            category="migration_currency",
                            severity="warning",
                            summary="A state file needs to be upgraded to the current schema",
                            detail=detail,
                            file_paths=[file_key],
                            fix_type="report-only",
                            fix_recipe={},
                        ))
        except (subprocess.TimeoutExpired, OSError):
            pass

    backlog_dir = state.product_base / "backlog"
    if backlog_dir.is_dir():
        taxonomy_script = _SCRIPTS_DIR / "migrate" / "migrate_taxonomy.py"
        taxonomy_migration_runnable = _script_has_cli_entrypoint(taxonomy_script)
        old_prefixes = {"STORY-", "BUG-", "DEBT-", "CHORE-"}
        old_files = []
        for p in backlog_dir.rglob("*.md"):
            if any(p.name.startswith(pfx) for pfx in old_prefixes):
                old_files.append(p)
        if old_files:
            if taxonomy_migration_runnable:
                fix_type = "prompted"
                fix_recipe = {"action": "prompt", "type": "migration",
                              "script": "migrate_taxonomy.py", "args": []}
                summary = f"{len(old_files)} files still use old naming conventions"
            else:
                fix_type = "report-only"
                fix_recipe = {}
                summary = (
                    f"{len(old_files)} files still use old naming conventions, "
                    "but taxonomy migration is not currently executable"
                )
            findings.append(Finding(
                id="migration-currency:taxonomy-drift:old-prefixes",
                category="migration_currency",
                severity="warning",
                summary=summary,
                detail=f"taxonomy-drift: found {', '.join(p.name for p in old_files[:5])}",
                file_paths=[str(p) for p in old_files[:5]],
                fix_type=fix_type,
                fix_recipe=fix_recipe,
            ))

    orphan_script = _SCRIPTS_DIR / "migrate" / "migrate-v3-to-v4.py"
    if orphan_script.exists():
        try:
            r = subprocess.run(
                [sys.executable, str(orphan_script),
                 "scan-orphans", "--project-dir", str(state.project_dir)],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                orphan_data = json.loads(r.stdout)
                orphans = orphan_data.get("findings", [])
                for o in orphans:
                    rel = o.get("file", "")
                    if not rel:
                        continue
                    findings.append(Finding(
                        id=f"migration-currency:orphan:{Path(rel).name}",
                        category="migration_currency",
                        severity="warning",
                        summary=f"Orphaned work item file: {rel}",
                        detail=(
                            f"orphan: {rel} was not migrated; resolve via "
                            "acknowledge, archive, or reonboard"
                        ),
                        file_paths=[rel],
                        fix_type="prompted",
                        fix_recipe={"action": "prompt", "type": "resolve_orphans",
                                    "file": rel},
                    ))
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            pass

    return findings


def check_config_compat(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []

    home_claude = Path.home() / ".claude"

    # Logical source name -> real filesystem path, so config_conflict adopt can
    # perform a targeted edit through the executor (the logical names like
    # "~/.claude/settings.json" do not resolve under project_dir).
    _text_sources: list[tuple[str, str, str]] = []
    if state.claude_md_project:
        _text_sources.append(
            ("CLAUDE.md", state.claude_md_project, str(state.project_dir / "CLAUDE.md")))
    if state.claude_md_global:
        _text_sources.append(
            ("~/.claude/CLAUDE.md", state.claude_md_global, str(home_claude / "CLAUDE.md")))
    for name, content in state.rules_files.items():
        _text_sources.append(
            (f"rules/{name}", content, str(home_claude / "rules" / name)))

    _settings_sources: list[tuple[str, dict, str]] = []
    if state.settings_global:
        _settings_sources.append(
            ("~/.claude/settings.json", state.settings_global, str(home_claude / "settings.json")))
    if state.settings_local:
        _settings_sources.append(
            (".claude/settings.local.json", state.settings_local,
             str(state.project_dir / ".claude" / "settings.local.json")))

    for sname, sdata, spath in _settings_sources:
        allowed = sdata.get("allowedTools")
        if allowed is not None:
            for tool in ("Agent", "Bash", "Write"):
                if tool not in allowed:
                    findings.append(Finding(
                        id=f"config-compat:F1:{sname}:{tool}",
                        category="config_compat",
                        severity="error",
                        summary=f"Settings block SweetClaude from using {tool}",
                        detail=f"F1: allowedTools in {sname} excludes {tool}",
                        file_paths=[sname],
                        fix_type="prompted",
                        fix_recipe={"action": "prompt", "type": "config_conflict",
                                    "file": sname, "path": spath, "line": 0,
                                    "conflict": "F1", "tool": tool,
                                    "options": ["adopt", "keep", "both"]},
                    ))

        for hook_list in (sdata.get("hooks") or {}).values():
            if not isinstance(hook_list, list):
                continue
            for entry in hook_list:
                for h in entry.get("hooks", []):
                    cmd = h.get("command", "")
                    matcher = str(entry.get("matcher", ""))
                    if ("test" in matcher.lower() or "spec" in matcher.lower()):
                        if "sweetclaude" not in cmd and "${CLAUDE_PLUGIN_ROOT}" not in cmd:
                            findings.append(Finding(
                                id=f"config-compat:F2:{sname}",
                                category="config_compat",
                                severity="error",
                                summary="A non-SweetClaude hook intercepts test file writes",
                                detail=f"F2: PostToolUse hook in {sname} targets test/spec files with external command",
                                file_paths=[sname],
                                fix_type="prompted",
                                fix_recipe={"action": "prompt", "type": "config_conflict",
                                            "file": sname, "path": spath, "line": 0,
                                            "conflict": "F2", "hook_command": cmd,
                                            "matcher": matcher,
                                            "options": ["adopt", "keep", "both"]},
                            ))
                    test_runners = ["npm test", "pytest", "cargo test", "jest ", "vitest", "go test"]
                    for runner in test_runners:
                        if runner in cmd:
                            findings.append(Finding(
                                id=f"config-compat:F3:{sname}:{runner.strip()}",
                                category="config_compat",
                                severity="error",
                                summary="A hook runs the test suite directly — it'll run twice on every edit",
                                detail=f"F3: PostToolUse command in {sname} contains '{runner.strip()}'",
                                file_paths=[sname],
                                fix_type="prompted",
                                fix_recipe={"action": "prompt", "type": "config_conflict",
                                            "file": sname, "path": spath, "line": 0,
                                            "conflict": "F3", "hook_command": cmd,
                                            "matcher": matcher,
                                            "options": ["adopt", "keep", "both"]},
                            ))
                            break

    f4_patterns = [r"--no-verify", r"skip hooks", r"bypass hooks", r"skipHooks"]
    w1_patterns = [r"estimate", r"how long will", r"days to complete",
                   r"weeks to complete", r"sprint velocity", r"story points"]
    w2_patterns = [r"always add comments", r"comment every", r"document all methods",
                   r"add docstrings", r"comment all functions"]
    w3_patterns = [r"skip tests", r"tests optional", r"no TDD",
                   r"don't write tests", r"tests are not required"]
    w4_patterns = [r"proceed without asking", r"don't ask for approval",
                   r"skip confirmation"]
    i1_patterns = [r"never ask if ready to move", r"don't push for advancement",
                   r"user decides when phase is done"]
    i2_patterns = [r"propose don't ask", r"give recommendation with reasoning",
                   r"propose not ask"]

    _negation_re = re.compile(r"\b(?:never|don't|do not|avoid|no)\b")

    def _is_negated(text_lower: str, match_start: int) -> bool:
        line_start = text_lower.rfind("\n", 0, match_start) + 1
        window_start = line_start
        for term in ".!?;:":
            pos = text_lower.rfind(term, line_start, match_start)
            if pos + 1 > window_start:
                window_start = pos + 1
        return _negation_re.search(text_lower, window_start, match_start) is not None

    def _scan_text(code: str, patterns: list[str], source: str) -> list[str]:
        matched = []
        lower = source.lower()
        if "rules/sweetclaude/" in lower or "rules\\sweetclaude\\" in lower:
            return []
        text_lower = code.lower()
        for pat in patterns:
            pat_lower = pat.lower()
            for m in re.finditer(re.escape(pat_lower), text_lower):
                if not _is_negated(text_lower, m.start()):
                    matched.append(pat)
                    break
        return matched

    for src_name, src_content, src_path in _text_sources:
        for pat in _scan_text("", f4_patterns, src_name):
            pass
        hits = _scan_text(src_content, f4_patterns, src_name)
        for h in hits:
            fid = f"config-compat:F4:{src_name}:{hashlib.md5(h.encode()).hexdigest()[:8]}"
            findings.append(Finding(
                id=fid, category="config_compat", severity="error",
                summary="Instructions to skip hooks will break SweetClaude's safety checks",
                detail=f"F4: '{h}' found in {src_name}",
                file_paths=[src_name], fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "config_conflict",
                            "file": src_name, "path": src_path, "line": 0,
                            "conflict": "F4", "pattern": h,
                            "options": ["adopt", "keep", "both"]},
            ))

        for pat_group, code, sev, msg in [
            (w1_patterns, "W1", "warning", "Time-estimate instructions conflict with SweetClaude's no-estimates rule"),
            (w2_patterns, "W2", "warning", "Comment-everywhere instructions conflict with SweetClaude's no-comments default"),
            (w3_patterns, "W3", "warning", "Skip-tests instructions conflict with TDD enforcement"),
            (w4_patterns, "W4", "warning", "Skip-confirmation instructions conflict with deference levels"),
            (i1_patterns, "I1", "info", "Duplicate phase-dwelling rule — already covered by SweetClaude"),
            (i2_patterns, "I2", "info", "Duplicate proposal-mode rule — already covered by SweetClaude"),
        ]:
            hits = _scan_text(src_content, pat_group, src_name)
            for h in hits:
                fid = f"config-compat:{code}:{src_name}:{hashlib.md5(h.encode()).hexdigest()[:8]}"
                findings.append(Finding(
                    id=fid, category="config_compat", severity=sev,
                    summary=msg, detail=f"{code}: '{h}' found in {src_name}",
                    file_paths=[src_name],
                    fix_type="prompted" if sev != "info" else "report-only",
                    fix_recipe={"action": "prompt", "type": "config_conflict",
                                "file": src_name, "path": src_path, "line": 0,
                                "conflict": code, "pattern": h,
                                "options": ["adopt", "keep", "both"]}
                    if sev != "info" else {},
                ))

    return findings


# Genuinely-invalid legacy item-type aliases mapped to their current-taxonomy
# canonical target in schema.VALID_TYPES. `story` and `release` are valid item
# types in VALID_TYPES and therefore need no remap (they produce no finding).
_LEGACY_TYPE_ALIASES: dict[str, str] = {
    "bug": "bug-fix",
    "debt": "tech-debt",
    "chore": "tech-debt",
    "feature": "net-new-feature",
}


def _violation_to_finding(violation: str, p: Path, fm: dict) -> Finding | None:
    """Convert a validate_frontmatter() violation string into a Finding."""
    item_type = str(fm.get("type", ""))

    if violation.startswith("missing required field: "):
        field_name = violation.split("missing required field: ", 1)[1]
        if field_name == "id":
            return Finding(
                id=f"file-diagnostics:missing-field-id:{p.name}",
                category="file_diagnostics",
                severity="warning",
                summary=f"{p.name} has no ID in its frontmatter",
                detail=f"missing-field:id in {p}",
                file_paths=[str(p)],
                fix_type="report-only",
                fix_recipe={},
            )
        if field_name == "title":
            return Finding(
                id=f"file-diagnostics:missing-field-title:{p.name}",
                category="file_diagnostics",
                severity="warning",
                summary=f"{p.name} has no title in its frontmatter",
                detail=f"missing-field:title in {p}",
                file_paths=[str(p)],
                fix_type="report-only",
                fix_recipe={},
            )
        if field_name == "type":
            return Finding(
                id=f"file-diagnostics:missing-field-type:{p.name}",
                category="file_diagnostics",
                severity="warning",
                summary=f"{p.name} has no type set",
                detail=f"missing-field:type in {p}",
                file_paths=[str(p)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "choose_value",
                            "file": str(p), "field": "type",
                            "options": sorted(VALID_TYPES)},
            )
        if field_name == "status":
            return Finding(
                id=f"file-diagnostics:missing-field-status:{p.name}",
                category="file_diagnostics",
                severity="warning",
                summary=f"{p.name} has no status set",
                detail=f"missing-field:status in {p}",
                file_paths=[str(p)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "choose_value",
                            "file": str(p), "field": "status",
                            "options": sorted(CANONICAL_STATUSES)},
            )
        if field_name == "created":
            now_utc = datetime.datetime.now(
                datetime.timezone.utc,
            ).isoformat(timespec="seconds")
            return Finding(
                id=f"file-diagnostics:missing-field-created:{p.name}",
                category="file_diagnostics",
                severity="warning",
                summary=f"{p.name} has no created date",
                detail=f"missing-field:created in {p}",
                file_paths=[str(p)],
                fix_type="auto",
                fix_recipe={"action": "write_frontmatter_field",
                            "file": str(p), "key": "created",
                            "value": now_utc},
            )
        return None

    if violation.startswith("missing required field for type"):
        field_name = violation.rsplit(": ", 1)[1]
        return Finding(
            id=f"file-diagnostics:missing-type-field-{field_name}:{p.name}",
            category="file_diagnostics",
            severity="warning",
            summary=f"{p.name} ({item_type}) is missing required field: {field_name}",
            detail=f"missing-type-field:{field_name} for type={item_type} in {p}",
            file_paths=[str(p)],
            fix_type="prompted",
            fix_recipe={"action": "prompt", "type": "provide_value",
                        "file": str(p), "field": field_name,
                        "entity_type": item_type},
        )

    if violation.startswith("invalid "):
        parts = violation.split(": ", 1)
        field_name = parts[0].replace("invalid ", "")
        bad_value = parts[1] if len(parts) > 1 else "?"
        if field_name == "status":
            return Finding(
                id=f"file-diagnostics:unknown-status:{p.name}",
                category="file_diagnostics",
                severity="warning",
                summary=f"{p.name} has an unrecognized status: {bad_value}",
                detail=f"unknown-status:{bad_value} in {p}",
                file_paths=[str(p)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "choose_value",
                            "file": str(p), "field": "status",
                            "options": sorted(CANONICAL_STATUSES)},
            )
        if field_name == "type":
            return Finding(
                id=f"file-diagnostics:unknown-type:{p.name}",
                category="file_diagnostics",
                severity="warning",
                summary=f"{p.name} has an unrecognized type: {bad_value}",
                detail=f"unknown-type:{bad_value} in {p}",
                file_paths=[str(p)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "choose_value",
                            "file": str(p), "field": "type",
                            "options": sorted(VALID_TYPES)},
            )
        return Finding(
            id=f"file-diagnostics:invalid-{field_name}:{p.name}",
            category="file_diagnostics",
            severity="warning",
            summary=f"{p.name} has an invalid {field_name}: {bad_value}",
            detail=f"invalid-{field_name}:{bad_value} in {p}",
            file_paths=[str(p)],
            fix_type="report-only",
            fix_recipe={},
        )

    return None


def _propose_next_id(old_id: str, known_ids: set[str]) -> str | None:
    """Propose the next-available id of old_id's prefix family (PREFIX-<max+1>).

    Scans known_ids for the highest numeric suffix sharing old_id's prefix and
    returns PREFIX-(max+1). Returns None if old_id has no PREFIX-N shape. Used
    by the duplicate-id finding so the renumber prompt can offer a concrete new
    id without the renamer having to invent one.
    """
    m = re.match(r"^([A-Za-z]+)-(\d+)$", old_id)
    if not m:
        return None
    prefix = m.group(1)
    max_n = 0
    width = len(m.group(2))
    for kid in known_ids:
        km = re.match(r"^([A-Za-z]+)-(\d+)$", kid)
        if km and km.group(1) == prefix:
            max_n = max(max_n, int(km.group(2)))
            width = max(width, len(km.group(2)))
    return f"{prefix}-{max_n + 1:0{width}d}"


def check_file_diagnostics(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    seen_ids: dict[str, Path] = {}

    dirs_to_scan = []
    backlog_dir = state.product_base / "backlog"
    roadmap_dir = state.product_base / "roadmap"
    if backlog_dir.is_dir():
        dirs_to_scan.append(backlog_dir)
    if roadmap_dir.is_dir():
        dirs_to_scan.append(roadmap_dir)

    # Pre-pass: collect every id across the scanned dirs so a duplicate-id
    # finding can propose the next-available id of that prefix family. The
    # inline detection loop below cannot see ids that sort after the duplicate,
    # so the proposal must come from a full sweep.
    all_known_ids: set[str] = set()
    for scan_dir in dirs_to_scan:
        for p in scan_dir.rglob("*.md"):
            if p.name in ("INDEX.md", "MIGRATION-MAP.md") or \
               p.name.endswith("-INDEX.md") or "archived" in p.parts:
                continue
            fm, _err = _read_frontmatter_raw(p)
            if fm and fm.get("id"):
                all_known_ids.add(str(fm["id"]))

    for scan_dir in dirs_to_scan:
        for p in scan_dir.rglob("*.md"):
            if p.name in ("INDEX.md", "MIGRATION-MAP.md") or \
               p.name.endswith("-INDEX.md"):
                continue
            if "archived" in p.parts:
                continue

            fm, err = _read_frontmatter_raw(p)
            if err and "no frontmatter" in err:
                findings.append(Finding(
                    id=f"file-diagnostics:no-frontmatter:{p.name}",
                    category="file_diagnostics",
                    severity="error",
                    summary=f"{p.name} has no frontmatter — SweetClaude can't read it",
                    detail=f"no-frontmatter-delimiter: {p}",
                    file_paths=[str(p)],
                    fix_type="report-only",
                    fix_recipe={},
                ))
                continue
            if err and "YAML parse" in err:
                findings.append(Finding(
                    id=f"file-diagnostics:parse-error:{p.name}",
                    category="file_diagnostics",
                    severity="error",
                    summary=f"{p.name} has broken frontmatter",
                    detail=f"frontmatter-parse-error: {err}",
                    file_paths=[str(p)],
                    fix_type="report-only",
                    fix_recipe={},
                ))
                continue
            if fm is None:
                continue

            item_id = fm.get("id")
            if item_id:
                if item_id in seen_ids:
                    first = seen_ids[item_id]
                    file_a, file_b = str(first), str(p)
                    proposed = _propose_next_id(item_id, all_known_ids)
                    # Identical copies -> drop one (delete via executor, reversible);
                    # divergent copies -> renumber one to a fresh id.
                    if _duplicate_files_identical(Path(file_a), Path(file_b)):
                        recipe = {
                            "action": "prompt",
                            "type": "resolve_identical_duplicate",
                            "duplicate_id": item_id,
                            "files": [file_a, file_b],
                            "labels": [Path(file_a).parent.name, Path(file_b).parent.name],
                            "recommended_keep": file_a,
                            "recommended_remove": file_b,
                        }
                    else:
                        recipe = {
                            "action": "prompt",
                            "type": "renumber_duplicate",
                            "duplicate_id": item_id,
                            "files": [file_a, file_b],
                            "labels": [
                                Path(file_a).parent.name,
                                Path(file_b).parent.name,
                            ],
                            "proposed_new_id": proposed,
                        }
                    findings.append(Finding(
                        id=f"file-diagnostics:duplicate-id:{item_id}",
                        category="file_diagnostics",
                        severity="error",
                        summary=f"ID {item_id} is used by multiple files",
                        detail=f"duplicate-id: {item_id} in {file_b} and {file_a}",
                        file_paths=[file_a, file_b],
                        fix_type="prompted",
                        fix_recipe=recipe,
                    ))
                else:
                    seen_ids[item_id] = p

            if not fm:
                for field_name in REQUIRED_FIELDS["_all"]:
                    finding = _violation_to_finding(
                        f"missing required field: {field_name}", p, {},
                    )
                    if finding:
                        findings.append(finding)
                continue

            fm_normalized = dict(fm)
            raw_status = fm_normalized.get("status")
            if raw_status and isinstance(raw_status, str):
                fm_normalized["status"] = normalize_status(raw_status).lower()
            raw_type = str(fm.get("type", ""))
            if raw_type:
                fm_normalized["type"] = raw_type.lower()

            violations = validate_frontmatter(fm_normalized)
            for v in violations:
                if v.startswith("invalid type:"):
                    canonical = _LEGACY_TYPE_ALIASES.get(raw_type.lower())
                    if canonical:
                        # A legacy item-type alias with a known canonical target:
                        # emit a remap finding instead of the generic
                        # unknown-type one. A type change is semantically
                        # significant, so present it as a prompted choose_value
                        # seeded so the recommended value is the canonical
                        # target. The skill applies the chosen value through the
                        # executor's write_frontmatter_field backup pipeline.
                        findings.append(Finding(
                            id=f"file-diagnostics:legacy-type-alias:{p.name}",
                            category="file_diagnostics",
                            severity="warning",
                            summary=(
                                f"{p.name} uses legacy type '{raw_type}' "
                                f"— remap to '{canonical}'"
                            ),
                            detail=(
                                f"legacy-type-alias:{raw_type}->{canonical} in {p}"
                            ),
                            file_paths=[str(p)],
                            fix_type="prompted",
                            fix_recipe={"action": "prompt", "type": "choose_value",
                                        "file": str(p), "field": "type",
                                        "recommended": canonical,
                                        "options": sorted(VALID_TYPES)},
                        ))
                        continue
                finding = _violation_to_finding(v, p, fm)
                if finding:
                    if finding.id.endswith(":missing-field-id:" + p.name) and item_id:
                        continue
                    findings.append(finding)

            for dt_field in _DATETIME_FIELDS:
                val = fm.get(dt_field)
                if val is not None and isinstance(val, (str, datetime.date)):
                    val_str = val.isoformat() if isinstance(val, datetime.date) else str(val)
                    if _DATE_ONLY_RE.match(val_str):
                        findings.append(Finding(
                            id=f"file-diagnostics:date-only-{dt_field}:{p.name}",
                            category="file_diagnostics",
                            severity="warning",
                            summary=f"{p.name} has date-only {dt_field} — needs full datetime with timezone",
                            detail=f"date-only:{dt_field}={val_str} in {p}",
                            file_paths=[str(p)],
                            fix_type="auto",
                            fix_recipe={"action": "write_frontmatter_field",
                                        "file": str(p), "key": dt_field,
                                        "value": f"{val_str}T00:00:00+00:00"},
                        ))

    return findings


def check_onboarding_state(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    skills_path = state.project_dir / ".sweetclaude" / "state" / "skills.yaml"

    # No missing-skills.yaml finding. v4 onboarding never writes this file —
    # the six data-owning skills create it the first time one of them is used,
    # the same lazy lifecycle as phase.yaml, which is deliberately not flagged
    # either. Reporting it made every correctly configured project carry a
    # permanent finding, and noise in a diagnostic is how real findings get
    # skimmed past (ISSUE-284).
    if state.skills_yaml:
        schema = state.skills_yaml.get("schema_version")
        if schema is not None and schema < 2:
            if state.migration_runner_path:
                findings.append(Finding(
                    id="onboarding-state:schema-v1:skills.yaml",
                    category="onboarding_state",
                    severity="warning",
                    summary="Skills file needs upgrading to the current format",
                    detail=f"skills.yaml schema_version={schema}, expected >=2",
                    file_paths=[str(skills_path)],
                    fix_type="auto",
                    fix_recipe={"action": "run_script",
                                "cmd": [sys.executable, str(state.migration_runner_path),
                                        "--project-dir", str(state.project_dir),
                                        "--file", "skills.yaml"],
                                "args": [],
                                "regenerates": [str(skills_path)]},
                ))
            else:
                findings.append(Finding(
                    id="onboarding-state:schema-v1:skills.yaml",
                    category="onboarding_state",
                    severity="warning",
                    summary="Skills file needs upgrading to the current format",
                    detail=f"skills.yaml schema_version={schema}, expected >=2",
                    file_paths=[str(skills_path)],
                    fix_type="report-only",
                    fix_recipe={},
                ))

    return findings


def check_env_wiring(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []

    plans_dir = state.project_dir / ".sweetclaude" / "plans"
    if not plans_dir.is_dir():
        findings.append(Finding(
            id="env-wiring:missing:plans-directory",
            category="env_wiring",
            severity="info",
            summary="Plans directory hasn't been created yet",
            detail=f"Expected {plans_dir}",
            file_paths=[str(plans_dir)],
            fix_type="auto",
            fix_recipe={"action": "create_dir", "path": str(plans_dir)},
        ))

    for sname, sdata in [
        ("settings_global", state.settings_global),
        ("settings_local", state.settings_local),
    ]:
        if sdata is not None:
            plans_setting = sdata.get("plansDirectory")
            if plans_setting is None:
                settings_path = (
                    Path.home() / ".claude" / "settings.json"
                    if sname == "settings_global"
                    else state.project_dir / ".claude" / "settings.local.json"
                )
                findings.append(Finding(
                    id=f"env-wiring:plans-directory-unset:{sname}",
                    category="env_wiring",
                    severity="warning",
                    summary="Plans directory isn't configured in settings",
                    detail=f"plansDirectory not set in {settings_path}",
                    file_paths=[str(settings_path)],
                    fix_type="auto",
                    fix_recipe={"action": "write_field",
                                "file": str(settings_path),
                                "key": "plansDirectory",
                                "value": ".sweetclaude/plans"},
                ))
            break

    if state.claude_md_project:
        if "sweetclaude" not in state.claude_md_project.lower():
            findings.append(Finding(
                id="env-wiring:claude-md-missing-section:CLAUDE.md",
                category="env_wiring",
                severity="warning",
                summary="CLAUDE.md doesn't mention SweetClaude",
                detail="No SweetClaude section found in project CLAUDE.md",
                file_paths=[str(state.project_dir / "CLAUDE.md")],
                fix_type="report-only",
                fix_recipe={},
            ))

    return findings


def check_derived_status(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    roadmap_dir = state.product_base / "roadmap"
    backlog_dir = state.product_base / "backlog"
    if not roadmap_dir.is_dir():
        return findings

    all_items: dict[str, dict] = {}
    all_paths: dict[str, Path] = {}
    children_of: dict[str, set[str]] = {}

    scan_dirs = [roadmap_dir]
    if backlog_dir.is_dir():
        scan_dirs.append(backlog_dir)
    for extra in ("epics", "sprints", "themes", "milestones", "pitches", "cycles"):
        d = state.product_base / extra
        if d.is_dir():
            scan_dirs.append(d)

    for scan_dir in scan_dirs:
        for p in scan_dir.rglob("*.md"):
            if p.name in ("INDEX.md", "MIGRATION-MAP.md") or p.name.endswith("-INDEX.md"):
                continue
            fm = _read_frontmatter(p)
            if not fm or not fm.get("id"):
                continue
            item_id = fm["id"]
            raw_status = normalize_status(str(fm.get("status", "")))
            fm["_normalized_status"] = raw_status
            all_items[item_id] = fm
            all_paths[item_id] = p

            epic_ref = fm.get("epic")
            if epic_ref and isinstance(epic_ref, str):
                children_of.setdefault(epic_ref, set()).add(item_id)

            ms_ref = fm.get("milestone")
            if ms_ref and isinstance(ms_ref, str) and fm.get("type") == "epic":
                ms_id = normalize_milestone(ms_ref)
                if ms_id:
                    children_of.setdefault(ms_id, set()).add(item_id)

    _OVERRIDE_REASON_FIELDS = {
        "blocked": ("blocked_reason", "reason"),
        "on-hold": ("hold_reason", "on_hold_reason", "reason"),
    }

    computed_derived: dict[str, str] = {}
    for parent_id, child_ids in children_of.items():
        parent = all_items.get(parent_id)
        if not parent or parent.get("type") != "epic":
            continue
        child_statuses = []
        for cid in child_ids:
            child = all_items.get(cid)
            if child:
                cs = child.get("_normalized_status", "")
                if cs:
                    child_statuses.append(cs)
        if child_statuses:
            computed_derived[parent_id] = derived_status(child_statuses)

    for parent_id, child_ids in children_of.items():
        parent = all_items.get(parent_id)
        if not parent:
            continue
        parent_type = parent.get("type", "")
        if parent_type not in ("epic", "milestone"):
            continue

        stored = parent.get("_normalized_status", "")
        if not stored or stored not in CANONICAL_STATUSES:
            continue

        child_statuses = []
        for cid in child_ids:
            if parent_type == "milestone" and cid in computed_derived:
                child_statuses.append(computed_derived[cid])
            else:
                child = all_items.get(cid)
                if child:
                    cs = child.get("_normalized_status", "")
                    if cs:
                        child_statuses.append(cs)

        if not child_statuses:
            continue

        derived = derived_status(child_statuses)
        computed_derived[parent_id] = derived

        if stored == derived:
            continue

        reason_fields = _OVERRIDE_REASON_FIELDS.get(stored)
        if reason_fields and any(parent.get(f) for f in reason_fields):
            continue

        parent_path = all_paths[parent_id]
        parent_source = parent.get("source", "auto")

        if parent_source == "manual":
            findings.append(Finding(
                id=f"derived-status:manual-override:{parent_id}",
                category="derived_status",
                severity="info",
                summary=(
                    f"{parent_id} status is {stored!r} (manual override); "
                    f"children suggest {derived!r}"
                ),
                detail=(
                    f"derived-status-override: {parent_id} (type={parent_type}) "
                    f"stored={stored}, derived={derived}, source=manual, "
                    f"children={sorted(child_ids)}"
                ),
                file_paths=[str(parent_path)],
                fix_type="report-only",
                fix_recipe={},
            ))
        else:
            findings.append(Finding(
                id=f"derived-status:stale-auto:{parent_id}",
                category="derived_status",
                severity="warning",
                summary=(
                    f"{parent_id} status is {stored!r} but children suggest {derived!r} "
                    f"(source=auto, should auto-sync)"
                ),
                detail=(
                    f"derived-status-stale: {parent_id} (type={parent_type}) "
                    f"stored={stored}, derived={derived}, source=auto, "
                    f"children={sorted(child_ids)}"
                ),
                file_paths=[str(parent_path)],
                fix_type="auto",
                fix_recipe={"action": "sync_parent_status", "file": str(parent_path),
                            "parent_id": parent_id, "parent_type": parent_type},
            ))

    return findings


def check_structure_anomalies(state: ProjectState) -> list[Finding]:
    """Flag symlinks where SweetClaude expects real directories.

    A symlink in the artifact tree is unusual and is often LOAD-BEARING — e.g.
    a bridge between a scanner that hardcodes `.sweetclaude/product/` and an
    artifact base relocated elsewhere via artifact-privacy. Doctor must never
    treat such a path's contents as duplicates/orphans, and must never offer to
    delete it: walking a symlink shows files identical to its target, which
    looks exactly like "duplicate dead weight" but is the opposite of safe to
    remove. This check stops and explains; resolution is left to a human.
    """
    findings: list[Finding] = []
    sc = state.project_dir / ".sweetclaude"
    candidates = [
        sc / "product",
        sc / "stories",
        state.product_base,
        state.product_base / "backlog",
        state.product_base / "roadmap",
        state.product_base / "stories",
        state.product_base / "milestones",
        state.product_base / "epics",
    ]
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            is_link = path.is_symlink()
        except OSError:
            continue
        if not is_link:
            continue
        try:
            target = os.readlink(path)
        except OSError:
            target = "<unreadable>"
        try:
            rel = path.relative_to(state.project_dir)
        except ValueError:
            rel = path
        findings.append(Finding(
            id=f"structure-anomaly:unexpected-symlink:{rel}",
            category="structure_anomalies",
            severity="warning",
            summary=(
                f"{rel} is a symlink, not a real directory — unusual and "
                "possibly load-bearing; doctor will not auto-change it"
            ),
            detail=(
                f"unexpected-symlink: {rel} -> {target}. SweetClaude expects a "
                "real directory here. A symlink is commonly a bridge (for "
                "example, the dashboard cache scanner hardcodes "
                ".sweetclaude/product/ while artifact-privacy relocates the "
                "product base elsewhere). Its contents will mirror the target "
                "exactly — that resemblance is the SIGNATURE OF A SYMLINK, not "
                "duplicate dead weight. Doctor will NOT treat it as a duplicate "
                "or orphan and will NOT remove it. Guidance: determine what the "
                "symlink bridges before changing anything. If it connects a "
                "hardcoded scanner path to a relocated base, deleting it blinds "
                "the cache/dashboard with no data loss but with broken views. "
                "Resolve by aligning the scanner and base_path, then remove the "
                "bridge deliberately — or keep it. No automatic action is safe."
            ),
            file_paths=[str(path)],
            fix_type="report-only",
            fix_recipe={},
        ))
    return findings


def _semver_tuple(v: object) -> tuple[int, int, int] | None:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", str(v or ""))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def check_version_currency(state: ProjectState) -> list[Finding]:
    """Advise updating when the framework is behind latest and findings exist.

    Doctor's own checks and recovery improve between releases — a stale doctor
    can surface findings a newer one already resolves (the syncog 4.1.2-beta
    case dumped 639 raw findings that 4.1.6+ collapses). When behind latest,
    say so first: update may resolve some findings before acting on them.
    """
    fw = (state.sweetclaude_yaml or {}).get("framework", {}) or {}
    installed = fw.get("installed_version")
    available = (fw.get("update") or {}).get("available")
    it, at = _semver_tuple(installed), _semver_tuple(available)
    if not (it and at and at > it):
        return []
    return [Finding(
        id="version-currency:behind-latest",
        category="version_currency",
        severity="warning",
        summary=(
            f"Doctor is running an older SweetClaude ({installed}); "
            f"{available} is available"
        ),
        detail=(
            f"version-currency: installed={installed}, available={available}. "
            "Doctor's checks and recovery improve between releases, so some "
            "findings here may already be resolved in the newer version. "
            "Guidance: update first — run /sweetclaude:update (beta: update the "
            "plugin package and restart, then /sweetclaude:update) — then re-run "
            "doctor before acting on other findings."
        ),
        file_paths=[],
        fix_type="report-only",
        fix_recipe={},
    )]


def check_work_item_artifacts(state: ProjectState) -> list[Finding]:
    """Validate work-item artifact directories when the feature is active."""
    findings: list[Finding] = []
    features = (state.sweetclaude_yaml or {}).get("features", {})
    wia = features.get("work_item_artifacts")
    if not isinstance(wia, dict) or wia.get("status") != "active":
        return []

    work_dir = state.project_dir / ".sweetclaude" / "work"
    if not work_dir.is_dir():
        findings.append(Finding(
            id="work-item-artifacts:missing-dir",
            category="work_item_artifacts",
            severity="warning",
            summary="Work-item artifacts feature is active but .sweetclaude/work/ does not exist",
            detail="The feature is enabled but no work directory has been created. Run /sweetclaude:work-item-artifacts to set it up.",
            file_paths=[],
            fix_type="report-only",
            fix_recipe={},
        ))
        return findings

    broken_links = []
    missing_manifests = []
    for entry in sorted(work_dir.iterdir()):
        if not entry.is_dir():
            continue
        manifest = entry / "manifest.yaml"
        if not manifest.exists():
            missing_manifests.append(str(entry.relative_to(state.project_dir)))
        for root, _, files in os.walk(entry):
            for f in files:
                fpath = Path(root) / f
                if fpath.is_symlink() and not fpath.exists():
                    broken_links.append(str(fpath.relative_to(state.project_dir)))

    if missing_manifests:
        findings.append(Finding(
            id="work-item-artifacts:missing-manifest",
            category="work_item_artifacts",
            severity="warning",
            summary=f"{len(missing_manifests)} work-item director{'ies' if len(missing_manifests) != 1 else 'y'} missing manifest.yaml",
            detail=f"Directories without manifest.yaml: {', '.join(missing_manifests)}",
            file_paths=missing_manifests,
            fix_type="report-only",
            fix_recipe={},
        ))
    if broken_links:
        findings.append(Finding(
            id="work-item-artifacts:broken-links",
            category="work_item_artifacts",
            severity="warning",
            summary=f"{len(broken_links)} broken symlink{'s' if len(broken_links) != 1 else ''} in work-item directories",
            detail=f"Broken symlinks: {', '.join(broken_links[:10])}{'...' if len(broken_links) > 10 else ''}",
            file_paths=broken_links[:10],
            fix_type="report-only",
            fix_recipe={},
        ))
    return findings


def check_epic_completion_criteria(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    roadmap_dir = state.product_base / "roadmap"
    if not roadmap_dir.is_dir():
        return findings

    for p in roadmap_dir.rglob("*.md"):
        if p.name in ("INDEX.md", "MIGRATION-MAP.md") or p.name.endswith("-INDEX.md"):
            continue
        fm = _read_frontmatter(p)
        if not fm or fm.get("type") != "epic":
            continue

        criteria = fm.get("completion_criteria")
        if not criteria or not isinstance(criteria, list):
            continue

        has_old_format = any(isinstance(c, str) for c in criteria)
        if not has_old_format:
            continue

        done_list = fm.get("completion_criteria_done", []) or []
        done_set = set(done_list) if done_list else set()

        new_criteria = []
        for i, crit in enumerate(criteria):
            if isinstance(crit, dict):
                new_criteria.append(crit)
            else:
                crit_str = str(crit)
                new_criteria.append({
                    "id": f"cc-{i + 1}",
                    "description": crit_str,
                    "done": crit_str in done_set,
                })

        epic_id = fm.get("id", p.stem)
        findings.append(Finding(
            id=f"epic-completion-criteria:old-format:{epic_id}",
            category="epic_completion_criteria",
            severity="warning",
            summary=(
                f"{epic_id} uses old-format completion criteria "
                f"(strings + completion_criteria_done)"
            ),
            detail=(
                f"Epic {epic_id} at {p} has {len(criteria)} criteria in "
                f"string format. Migrating to dict format with "
                f"{len(done_set)} marked done."
            ),
            file_paths=[str(p)],
            fix_type="auto",
            fix_recipe={
                "action": "write_frontmatter_field",
                "file": str(p),
                "key": "completion_criteria",
                "value": new_criteria,
                "remove_keys": ["completion_criteria_done"],
            },
        ))

    return findings


def check_format_consistency(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    scan_dirs = [
        state.product_base / "backlog",
        state.product_base / "roadmap",
        state.product_base / "epics",
        state.product_base / "sprints",
        state.product_base / "themes",
        state.product_base / "milestones",
        state.product_base / "pitches",
        state.product_base / "cycles",
    ]
    try:
        from parse_utils import detect_format, is_backup_artifact
    except ImportError:
        return findings

    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for p in scan_dir.rglob("*.md"):
            if p.name in ("INDEX.md", "MIGRATION-MAP.md") or p.name.endswith("-INDEX.md"):
                continue
            if is_backup_artifact(p.name):
                continue
            try:
                content = p.read_text()
            except OSError:
                continue
            fmt = detect_format(content)
            if fmt == "bold":
                findings.append(Finding(
                    id=f"format-consistency:bold:{p.name}",
                    category="format_consistency",
                    severity="warning",
                    summary=f"{p.name} uses Bold Key-Value format instead of YAML frontmatter",
                    detail=f"File at {p} uses the legacy Bold format (**Key:** Value). "
                           f"Convert to YAML frontmatter for full cache/propagation support.",
                    file_paths=[str(p)],
                    fix_type="auto",
                    fix_recipe={"action": "convert_to_yaml", "file": str(p)},
                ))
    return findings


def check_orphaned_index(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    idx_path = state.project_dir / ".sweetclaude" / "state" / "project-index.json"
    if idx_path.is_file():
        findings.append(Finding(
            id="orphaned-index:project-index-json",
            category="orphaned_index",
            severity="warning",
            summary="Orphaned project-index.json found — SQLite cache is now authoritative",
            detail=f"{idx_path} is no longer used. The SQLite cache at "
                   f".sweetclaude/cache/roadmap.db is the single query store. "
                   f"This file can be safely deleted.",
            file_paths=[str(idx_path)],
            fix_type="auto",
            fix_recipe={"action": "delete_file", "file": str(idx_path)},
        ))
    return findings


CHECKS: dict[str, Callable[[ProjectState], list[Finding]]] = {
    "state_integrity":    check_state_integrity,
    "hook_health":        check_hook_health,
    "version_currency":   check_version_currency,
    "structure_anomalies": check_structure_anomalies,
    "storage_lint":       check_storage_lint,
    "migration_currency": check_migration_currency,
    "config_compat":      check_config_compat,
    "file_diagnostics":   check_file_diagnostics,
    "onboarding_state":   check_onboarding_state,
    "env_wiring":         check_env_wiring,
    "derived_status":     check_derived_status,
    "work_item_artifacts": check_work_item_artifacts,
    "epic_completion_criteria": check_epic_completion_criteria,
    "format_consistency": check_format_consistency,
    "orphaned_index":     check_orphaned_index,
}


# ---------------------------------------------------------------------------
# Project state builder
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        text = path.read_text()
        return yaml.safe_load(text) or {}
    except yaml.YAMLError:
        try:
            if not path.read_text().replace("---", "").strip():
                return {}
        except OSError:
            pass
        return None
    except OSError:
        return None


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text()
    except OSError:
        return None


def _resolve_product_base(project_dir: Path, artifact_privacy: dict | None) -> Path:
    if artifact_privacy:
        base = (
            (artifact_privacy.get("categories") or {})
            .get("product", {})
            .get("base_path", "")
        )
        if base:
            base = base.rstrip("/")
            p = Path(base)
            if p.is_absolute():
                return p
            return project_dir / base
    return project_dir / ".sweetclaude" / "product"


def _resolve_installed_version() -> str | None:
    plugins_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    data = _read_json(plugins_path)
    if not data:
        return None
    candidates = []
    for _key, entries in (data.get("plugins") or {}).items():
        if "sweetclaude" in _key.lower() and entries:
            candidates.append(entries[0])
    if not candidates:
        return None
    candidates.sort(key=lambda e: e.get("lastUpdated", ""), reverse=True)
    return candidates[0].get("version")


def _find_migration_runner(project_dir: Path) -> Path | None:
    candidate = _SCRIPTS_DIR / "migrations" / "runner.py"
    return candidate if candidate.exists() else None


def build_project_state(project_dir: Path) -> ProjectState:
    sc = project_dir / ".sweetclaude"
    state_dir = sc / "state"

    sweetclaude_yaml = _read_yaml(state_dir / "sweetclaude.yaml")
    artifact_privacy = _read_yaml(sc / "artifact-privacy.yaml")
    product_base = _resolve_product_base(project_dir, artifact_privacy)

    home_claude = Path.home() / ".claude"

    rules_dir = home_claude / "rules" / "sweetclaude"
    rules_files = {}
    if rules_dir.is_dir():
        for f in rules_dir.iterdir():
            if f.suffix == ".md":
                content = _read_text(f)
                if content is not None:
                    rules_files[f"sweetclaude/{f.name}"] = content

    backlog_dir = product_base / "backlog"
    roadmap_dir = product_base / "roadmap"

    return ProjectState(
        project_dir=project_dir,
        sweetclaude_yaml=sweetclaude_yaml,
        artifact_privacy=artifact_privacy,
        session_state=_read_yaml(state_dir / "session-state.yaml"),
        product_base=product_base,
        backlog_files=sorted(backlog_dir.glob("*.md")) if backlog_dir.is_dir() else [],
        roadmap_files=(
            sorted(roadmap_dir.rglob("*.md")) if roadmap_dir.is_dir() else []
        ),
        hook_files=(
            sorted((home_claude / "hooks" / "sweetclaude").glob("*.sh"))
            if (home_claude / "hooks" / "sweetclaude").is_dir()
            else []
        ),
        hook_manifest=_read_json(home_claude / "hooks" / "sweetclaude" / "hooks-manifest.json"),
        hooks_json=_read_json(home_claude / "hooks" / "sweetclaude" / "hooks.json"),
        settings_global=_read_json(home_claude / "settings.json"),
        settings_local=_read_json(project_dir / ".claude" / "settings.local.json"),
        claude_md_project=_read_text(project_dir / "CLAUDE.md"),
        claude_md_global=_read_text(home_claude / "CLAUDE.md"),
        rules_files=rules_files,
        skills_yaml=_read_yaml(state_dir / "skills.yaml"),
        installed_version=_resolve_installed_version(),
        migration_runner_path=_find_migration_runner(project_dir),
        suppressions=_read_json(state_dir / "doctor-suppressions.json") or [],
    )


def build_state_summary(state: ProjectState) -> dict:
    return {
        "installed_version": state.installed_version,
        "product_base": str(state.product_base),
        "backlog_count": len(state.backlog_files),
        "roadmap_count": len(state.roadmap_files),
        "hook_count": len(state.hook_files),
        "has_sweetclaude_yaml": state.sweetclaude_yaml is not None,
        "has_session_state": state.session_state is not None,
        "suppression_count": len(state.suppressions),
    }


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------

def _suppressions_path(project_dir: Path) -> Path:
    return project_dir / ".sweetclaude" / "state" / "doctor-suppressions.json"


def load_suppressions(project_dir: Path) -> list[dict]:
    data = _read_json(_suppressions_path(project_dir))
    return data if isinstance(data, list) else []


def save_suppressions(project_dir: Path, entries: list[dict]) -> None:
    path = _suppressions_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2))
    os.replace(tmp, path)


def compute_resolved_suppressions(
    project_dir: Path, current_finding_ids: set[str]
) -> set[str]:
    """Read-only: which suppression entries are stale (their finding resolved).

    Used during the read-only scan phase to flag previously_suppressed findings
    and populate suppressions_resolved WITHOUT mutating the ledger. The actual
    prune is deferred to the execute phase (``prune_resolved_suppressions``),
    where it is backed up through the archive — keeping scan strictly read-only
    (P4) and every mutation on the executor backup pipeline (P2).
    """
    entries = load_suppressions(project_dir)
    return {
        e["finding_id"]
        for e in entries
        if e.get("finding_id") and e["finding_id"] not in current_finding_ids
    }


def prune_resolved_suppressions(
    project_dir: Path, archive_path: Path, current_finding_ids: set[str]
) -> set[str]:
    """Execute-phase prune of stale suppression entries, backed up via the archive.

    Computes the same resolved set as ``compute_resolved_suppressions``; if any
    entries are stale, backs up the ledger through ``_record_mutation``
    (before-image + diff, ``restore``-reversible) before writing the pruned
    file. This is the executor-routed mutation that replaces the former
    scan-time write, satisfying the "every mutation goes through the backup
    pipeline" invariant (P2) while leaving scan read-only (P4).
    """
    entries = load_suppressions(project_dir)
    if not entries:
        return set()
    resolved = {
        e["finding_id"]
        for e in entries
        if e.get("finding_id") and e["finding_id"] not in current_finding_ids
    }
    if not resolved:
        return set()
    # Keep everything NOT in the resolved set — so entries lacking a finding_id
    # (hand-written/legacy) survive rather than being collateral-dropped by a
    # membership test against current findings.
    remaining = [e for e in entries if e.get("finding_id") not in resolved]
    path = _suppressions_path(project_dir)
    before = path.read_bytes() if path.exists() else b""
    after = json.dumps(remaining, indent=2).encode()
    _record_mutation(archive_path, path, before, after)
    save_suppressions(project_dir, remaining)
    return resolved


def _validate_finding_id(finding_id: object) -> str | None:
    """Return an error message if *finding_id* is not a safe single-line id,
    else None.

    Guards the only sanctioned writer of doctor-suppressions.json against
    malformed input — e.g. a newline-joined blob of many ids passed as one
    argument, which would otherwise be stored verbatim and corrupt the file.
    """
    if not isinstance(finding_id, str):
        return "finding_id must be a string"
    if finding_id == "":
        return "finding_id is empty"
    if finding_id != finding_id.strip():
        return "finding_id has leading or trailing whitespace"
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in finding_id):
        return (
            "finding_id contains control characters; pass one id per call "
            "(newlines/tabs are not allowed)"
        )
    return None


def suppress_finding(
    project_dir: Path, finding_id: str, reason: str | None = None
) -> dict:
    """Append a suppression entry through save_suppressions.

    Idempotent: an already-suppressed finding_id is not duplicated and its
    existing entry is preserved. This is the script-owned path that replaces
    the former skill-side inline write to doctor-suppressions.json (S3).
    """
    error = _validate_finding_id(finding_id)
    if error:
        return {"suppressed": False, "finding_id": finding_id, "error": error}
    entries = load_suppressions(project_dir)
    already = any(e.get("finding_id") == finding_id for e in entries)
    if not already:
        entry = {"finding_id": finding_id, "suppressed_at": _now_iso()}
        if reason:
            entry["reason"] = reason
        entries.append(entry)
        save_suppressions(project_dir, entries)
    return {
        "suppressed": True,
        "finding_id": finding_id,
        "already_suppressed": already,
        "count": len(entries),
    }


def unsuppress_finding(
    project_dir: Path,
    finding_id: str | None = None,
    *,
    prune_malformed: bool = False,
) -> dict:
    """Remove suppression entries through the same load/save owner as suppress.

    Idempotent: removing an absent id is a no-op success. With
    ``prune_malformed`` also drops any entry whose finding_id is missing or
    fails ``_validate_finding_id`` — a one-command recovery from a ledger that
    was corrupted before validation existed.
    """
    entries = load_suppressions(project_dir)
    removed: list[dict] = []
    remaining: list[dict] = []
    for entry in entries:
        fid = entry.get("finding_id")
        drop = (finding_id is not None and fid == finding_id) or (
            prune_malformed and (fid is None or _validate_finding_id(fid) is not None)
        )
        (removed if drop else remaining).append(entry)
    if removed:
        save_suppressions(project_dir, remaining)
    return {
        "unsuppressed": True,
        "finding_id": finding_id,
        "prune_malformed": prune_malformed,
        "removed_count": len(removed),
        "count": len(remaining),
    }


# ---------------------------------------------------------------------------
# Migration recommendations
# ---------------------------------------------------------------------------

_OLD_PREFIXES = frozenset({"STORY-", "BUG-", "DEBT-", "CHORE-", "BL-"})


def _build_migration_recommendations(
    findings: list[Finding], state: ProjectState, maintenance_route: dict,
) -> list[dict]:
    if maintenance_route.get("status") != "supported-migration-available":
        return []
    allowed_capability = (maintenance_route.get("primary_action") or {}).get("capability_id")
    # S7: also handle typed-legacy migration capability
    if allowed_capability not in ("migrate.flat_bl_to_issue", "migrate.typed_legacy_backlog"):
        return []
    if allowed_capability == "migrate.typed_legacy_backlog":
        return [{
            "script": "migrate_taxonomy.py",
            "finding_id": "typed-legacy-migration",
            "summary": "Typed legacy backlog can be migrated to ISSUE-NNN taxonomy",
            "estimated_resolvable": 1,
            "total_findings": max(1, len(findings)),
            "pct": 100,
            "capability_id": "migrate.typed_legacy_backlog",
        }]

    recs: list[dict] = []

    migration_findings = [
        f for f in findings
        if f.category == "migration_currency"
        and f.fix_type == "prompted"
        and getattr(f, "fix_recipe", {}).get("type") == "migration"
    ]
    for mf in migration_findings:
        recipe = mf.fix_recipe or {}
        script = recipe.get("script", "")

        affected_count = 0
        if script == "migrate_taxonomy.py":
            for f in findings:
                fps = f.file_paths or []
                if fps and any(
                    fps[0].split("/")[-1].startswith(pfx) for pfx in _OLD_PREFIXES
                ):
                    affected_count += 1
            if affected_count == 0:
                detail = mf.detail or ""
                try:
                    affected_count = int(
                        "".join(c for c in mf.summary.split()[0] if c.isdigit())
                    )
                except (ValueError, IndexError):
                    affected_count = 0

        elif script in ("migrate-v3-to-v4.py", "runner.py"):
            affected_count = sum(
                1 for f in findings
                if f.category in ("storage_lint", "file_diagnostics", "migration_currency")
                and getattr(f, "fix_recipe", {}).get("type") == "migration"
                and getattr(f, "fix_recipe", {}).get("script") == script
            )

        total = len(findings)
        resolvable = max(affected_count, 1)

        recs.append({
            "script": script,
            "finding_id": mf.id,
            "summary": mf.summary,
            "estimated_resolvable": resolvable,
            "total_findings": total,
            "pct": round(resolvable / total * 100) if total else 0,
        })

    return recs


# ---------------------------------------------------------------------------
# Maintenance routing
# ---------------------------------------------------------------------------

def _migration_preflight(project_dir: Path) -> dict | None:
    script = _SCRIPTS_DIR / "migrate" / "migrate-v3-to-v4.py"
    if not script.exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(script), "preflight", "--project-dir", str(project_dir)],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return {
            "status": "error",
            "migrate_allowed": False,
            "error": result.stderr.strip() or result.stdout.strip(),
        }
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "migrate_allowed": False,
            "error": "migration preflight returned invalid JSON",
        }
    return data if isinstance(data, dict) else None


def _capability_action(capability_id: str, action_id: str, label: str) -> dict:
    capability = capability_config(capability_id)
    action = {
        "id": action_id,
        "label": label,
        "capability_id": capability_id,
        "requires_approval": bool(capability.get("requires_approval", False)),
        "mutates_project": bool(capability.get("mutates_project", False)),
        "supported_project_shapes": list(capability.get("supports_project_shapes") or []),
    }
    if capability.get("delegate_skill"):
        action["delegate_skill"] = capability["delegate_skill"]
    if capability.get("verification_commands"):
        action["verification_commands"] = list(capability["verification_commands"])
    if capability.get("safety_contract"):
        action["safety_contract"] = list(capability["safety_contract"])
    return action


def _blocked_capabilities(project_shape: str) -> list[dict]:
    shape = project_shape_config(project_shape)
    blocked: list[dict] = []
    for capability_id in shape.get("blocked_capabilities") or []:
        capability = capability_config(capability_id)
        blocked.append({
            "capability_id": capability_id,
            "supported": bool(capability.get("supported", True)),
            "block_reason": capability.get("block_reason", ""),
            "supported_project_shapes": list(capability.get("supports_project_shapes") or []),
        })
    return blocked


def build_maintenance_route(state: ProjectState) -> dict:
    """Classify the maintenance UX path Doctor should present.

    Doctor remains the front door. The returned route names internal skills as
    delegated capabilities, but labels are user-facing actions.
    """
    try:
        from recovery.recover_project import guard_project
        guard = guard_project(state.project_dir)
    except Exception as exc:
        return {
            "status": "manual-review",
            "doctor_front_door": True,
            "message": f"Maintenance guard failed: {exc}",
            "primary_action": None,
            "secondary_actions": [],
            "guard": {"status": "guard-error"},
        }

    status = guard.get("status")
    project_shape = str(guard.get("project_shape", "") or "")
    shape_config = project_shape_config(project_shape) if project_shape else {}
    route: dict = {
        "status": "no-maintenance-action",
        "doctor_front_door": True,
        "message": guard.get("message", ""),
        "project_shape": project_shape,
        "blocked_capabilities": _blocked_capabilities(project_shape) if project_shape else [],
        "primary_action": None,
        "secondary_actions": [],
        "guard": guard,
    }

    if status == "run-recover":
        route.update({
            "status": "recovery-available",
            "message": (
                "Doctor found a recoverable SweetClaude maintenance state. "
                "Run safe recovery from Doctor; recovery will diagnose, plan, "
                "snapshot, request approval, verify, and keep rollback data."
            ),
            "primary_action": _capability_action(
                str(shape_config.get("recovery_capability", "recover.stabilize_without_migration")),
                "run-safe-recovery",
                "Run safe recovery",
            ),
            "secondary_actions": [
                {
                    "id": "continue-without-maintenance",
                    "label": "Continue without maintenance",
                    "mutates_project": False,
                },
            ],
        })
        return route

    if status == "graduation-available":
        route.update({
            "status": "graduation-available",
            "message": (
                "This project is v4-compliant and can graduate from compatibility "
                "mode. Graduating clears the compatibility lock and marks "
                "migration complete."
            ),
            "primary_action": _capability_action(
                str(shape_config.get("graduation_capability", "recover.graduate_from_compatibility")),
                "graduate-from-compatibility",
                "Graduate from compatibility mode",
            ),
            "secondary_actions": [
                {
                    "id": "continue-compatibility-mode",
                    "label": "Stay in compatibility mode",
                    "mutates_project": False,
                },
            ],
        })
        return route

    if status == "graduation-blocked":
        blockers = list(guard.get("graduation_blockers") or [])
        blocker_lines = "; ".join(
            f"{b.get('code')}: {b.get('detail')}" for b in blockers
        )
        route.update({
            "status": "graduation-blocked",
            "graduation_blockers": blockers,
            "message": (
                "This project could graduate from compatibility mode, but "
                f"validation blockers must be fixed first — {blocker_lines}. "
                "Each blocker carries its resolution; fixes are archived and "
                "reversible."
            ),
            "primary_action": _capability_action(
                str(shape_config.get("blocker_fix_capability", "doctor.fix_graduation_blockers")),
                "fix-graduation-blockers",
                "Fix graduation blockers, then graduate",
            ),
            "secondary_actions": [
                {
                    "id": "continue-compatibility-mode",
                    "label": "Stay in compatibility mode",
                    "mutates_project": False,
                },
            ],
        })
        return route

    if status == "supported-migration-available":
        # S7: typed-legacy projects now route here directly (not through migration-may-be-needed)
        capability_id = str(shape_config.get("migration_capability", "migrate.typed_legacy_backlog"))
        route.update({
            "status": "supported-migration-available",
            "message": (
                "Doctor found a typed legacy backlog layout. "
                "Run /sweetclaude:migrate to migrate to the unified ISSUE-NNN taxonomy."
            ),
            "primary_action": _capability_action(
                capability_id,
                "start-typed-legacy-migration",
                "Migrate typed legacy backlog",
            ),
            "secondary_actions": [
                {
                    "id": "continue-without-migration",
                    "label": "Continue without migration",
                    "mutates_project": False,
                },
            ],
        })
        return route

    if status == "compatibility-mode":
        route.update({
            "status": "compatibility-mode",
            "message": (
                "Doctor found an accepted legacy taxonomy layout. No repair is "
                "needed right now; continue safely in compatibility mode. "
                "Migration remains blocked until a layout-specific plan exists."
            ),
            "primary_action": _capability_action(
                str(shape_config.get("doctor_capability", "doctor.compatibility_mode")),
                "continue-compatibility-mode",
                "Continue in compatibility mode",
            ),
        })
        return route

    if status == "migration-may-be-needed":
        preflight = _migration_preflight(state.project_dir)
        route["migration_preflight"] = preflight
        capability_id = str(shape_config.get("migration_capability", ""))
        capability = capability_config(capability_id) if capability_id else {}
        capability_shapes = list(capability.get("supports_project_shapes") or [])
        route["capability_check"] = {
            "capability_id": capability_id,
            "project_shape": project_shape,
            "supported_project_shapes": capability_shapes,
            "supported": bool(capability_id and project_shape in capability_shapes),
            "preflight_required": bool(capability.get("preflight_required", False)),
        }
        if (
            route["capability_check"]["supported"]
            and preflight
            and preflight.get("migrate_allowed")
        ):
            route.update({
                "status": "supported-migration-available",
                "message": (
                    "Doctor found a supported flat BL-NNN migration candidate. "
                    "Start the migration flow from Doctor; migration will run "
                    "its own preflight and safety steps before conversion."
                ),
                "primary_action": _capability_action(
                    capability_id,
                    "start-supported-migration",
                    "Start supported migration",
                ),
                "secondary_actions": [
                    {
                        "id": "continue-without-migration",
                        "label": "Continue without migration",
                        "mutates_project": False,
                    },
                ],
            })
        else:
            route.update({
                "status": "migration-blocked",
                "message": (
                    "Doctor found old-format work items, but the available "
                    "migration capability did not prove this layout is safe. "
                    "No files were changed."
                ),
                "primary_action": {
                    "id": "continue-without-migration",
                    "label": "Continue without migration",
                    "mutates_project": False,
                },
            })
        return route

    if status in {"manual-review", "missing-product-base", "guard-unavailable"}:
        route.update({
            "status": "manual-review",
            "primary_action": _capability_action(
                str(shape_config.get("doctor_capability", "doctor.manual_review")),
                "manual-review",
                "Manual review",
            ),
        })
        return route

    return route


def _legacy_value_from_summary(summary: str, label: str) -> str:
    marker = f"invalid {label}: "
    if marker not in summary:
        return ""
    value = summary.split(marker, 1)[1].strip()
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        value = value[1:-1]
    return value


def _legacy_taxonomy_kind(finding: Finding) -> str | None:
    """Return a compatibility-collapse kind for accepted legacy-taxonomy noise.

    Post-WI-017, old-prefix work items route to migration (typed_legacy_backlog),
    not compatibility-mode, so old-prefix-taxonomy-drift and legacy-work-item-id
    findings can no longer co-occur with compatibility mode. Only legacy
    frontmatter references (milestone/source) remain collapsible here.
    """
    if finding.category != "file_diagnostics":
        return None

    if finding.id.startswith("file-diagnostics:invalid-milestone:"):
        bad_milestone = _legacy_value_from_summary(finding.summary, "milestone")
        if bad_milestone:
            return "legacy-milestone-reference"

    if finding.id.startswith("file-diagnostics:invalid-source:"):
        return "legacy-source-reference"

    return None


def _apply_compatibility_mode_policy(
    findings: list[Finding], maintenance_route: dict,
) -> tuple[list[Finding], dict]:
    """Collapse accepted legacy taxonomy noise after guard-approved recovery.

    This does not suppress real integrity issues such as duplicate IDs,
    frontmatter parse errors, missing frontmatter, date fixes, or prompted
    config/status fixes. It only prevents accepted compatibility-mode taxonomy
    artifacts from dominating Doctor's report.
    """
    if maintenance_route.get("status") != "compatibility-mode":
        return findings, {"applied": False, "collapsed_count": 0}

    visible: list[Finding] = []
    collapsed_by_kind: dict[str, int] = {}

    for finding in findings:
        kind = _legacy_taxonomy_kind(finding)
        if kind:
            collapsed_by_kind[kind] = collapsed_by_kind.get(kind, 0) + 1
            continue
        visible.append(finding)

    collapsed_count = sum(collapsed_by_kind.values())
    if collapsed_count:
        visible.insert(0, Finding(
            id="compatibility-mode:accepted-legacy-taxonomy",
            category="compatibility_mode",
            severity="info",
            summary=(
                f"{collapsed_count} accepted legacy taxonomy findings were "
                "collapsed because compatibility mode is active"
            ),
            detail=(
                "compatibility-mode: accepted legacy taxonomy findings "
                f"collapsed by kind: {collapsed_by_kind}"
            ),
            file_paths=[],
            fix_type="report-only",
            fix_recipe={
                "action": "compatibility_summary",
                "collapsed_count": collapsed_count,
                "collapsed_by_kind": collapsed_by_kind,
            },
        ))

    # No exit prompt is surfaced here. The compatibility_exited flag write was
    # a no-op exit: the guard never read it for status, so the prompt re-offered
    # itself forever while changing nothing the user could see. The only real
    # exit from compatibility mode is graduation, which the guard routes via
    # graduation-available / graduation-blocked.

    return visible, {
        "applied": True,
        "collapsed_count": collapsed_count,
        "collapsed_by_kind": collapsed_by_kind,
    }


def _apply_manifest_migration_policy(
    findings: list[Finding], maintenance_route: dict,
) -> tuple[list[Finding], dict]:
    """Keep legacy migration checks report-only unless the manifest route allows them."""
    allowed = maintenance_route.get("status") == "supported-migration-available"
    allowed_capability = (
        (maintenance_route.get("primary_action") or {}).get("capability_id")
        if allowed
        else None
    )
    taxonomy_script = _SCRIPTS_DIR / "migrate" / "migrate_taxonomy.py"
    taxonomy_runnable = _script_has_cli_entrypoint(taxonomy_script)
    visible: list[Finding] = []
    blocked_count = 0
    for finding in findings:
        recipe = finding.fix_recipe or {}
        if recipe.get("type") != "migration":
            visible.append(finding)
            continue
        if (
            allowed_capability == "migrate.flat_bl_to_issue"
            and recipe.get("script") == "migrate-v3-to-v4.py"
        ):
            visible.append(finding)
            continue
        # T3b (plan §8.2, LOCKED): taxonomy migration now has a runnable CLI and
        # routes through sweetclaude:migrate, which owns its own preflight/safety
        # flow — the same delegation contract as the v3-to-v4 path. So it is no
        # longer manifest-blocked; let the runnable prompted finding through.
        if recipe.get("script") == "migrate_taxonomy.py" and taxonomy_runnable:
            visible.append(finding)
            continue
        blocked_count += 1
        visible.append(Finding(
            id=finding.id,
            category=finding.category,
            severity=finding.severity,
            summary=finding.summary,
            detail=(
                f"{finding.detail}\n\nManifest migration policy: prompted migration "
                f"is blocked for maintenance_route={maintenance_route.get('status')}."
            ),
            file_paths=finding.file_paths,
            fix_type="report-only",
            fix_recipe={
                "action": "capability_blocked",
                "type": "capability_blocked_migration",
                "route_status": maintenance_route.get("status"),
                "project_shape": maintenance_route.get("project_shape"),
            },
            previously_suppressed=finding.previously_suppressed,
        ))
    return visible, {
        "applied": True,
        "blocked_prompt_count": blocked_count,
        "allowed_capability": allowed_capability,
    }


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def _dedup_duplicate_id_findings(findings: list[Finding]) -> list[Finding]:
    """F5.1.4: a cross-location duplicate supersedes the same-directory/file
    duplicate-id finding for the same id.

    When one id is duplicated across backlog and roadmap, storage-lint emits
    `storage-lint:cross-location-duplicate-id:<id>` AND file-diagnostics emits
    `file-diagnostics:duplicate-id:<id>` for the same id. The cross-location
    finding is the more specific, actionable one, so drop the same-directory
    duplicate-id for that id. Same-directory-only duplicates (no cross-location
    counterpart) and all other findings are untouched.
    """
    cross_location_ids: set[str] = set()
    for f in findings:
        prefix = "storage-lint:cross-location-duplicate-id:"
        if f.id.startswith(prefix):
            cross_location_ids.add(f.id[len(prefix):])

    if not cross_location_ids:
        return findings

    deduped: list[Finding] = []
    for f in findings:
        prefix = "file-diagnostics:duplicate-id:"
        if f.id.startswith(prefix) and f.id[len(prefix):] in cross_location_ids:
            continue
        deduped.append(f)
    return deduped


def _scan(
    project_state: ProjectState,
    categories: list[str] | None = None,
) -> dict:
    if categories:
        invalid = set(categories) - set(CHECKS.keys())
        if invalid:
            raise ValueError(
                f"Unknown categories: {sorted(invalid)}. "
                f"Valid: {sorted(CHECKS.keys())}"
            )
        checks_to_run = {k: v for k, v in CHECKS.items() if k in categories}
    else:
        checks_to_run = CHECKS

    skipped: list[dict] = []
    all_findings: list[Finding] = []

    for name, fn in checks_to_run.items():
        try:
            all_findings.extend(fn(project_state))
        except DependencyMissing as e:
            skipped.append({"category": name, "reason": str(e)})

    all_finding_ids = {f.id for f in all_findings}
    suppressed_ids = {s.get("finding_id") for s in project_state.suppressions if s.get("finding_id")}

    if not categories:
        resolved_ids = compute_resolved_suppressions(
            project_state.project_dir, all_finding_ids
        )
    else:
        resolved_ids: set[str] = set()

    for f in all_findings:
        if f.id in resolved_ids:
            f.previously_suppressed = True

    maintenance_route = build_maintenance_route(project_state)
    active = [f for f in all_findings if f.id not in suppressed_ids]
    active, executable_contract = _enforce_executable_contract(active)
    active, compatibility_adjustments = _apply_compatibility_mode_policy(
        active, maintenance_route,
    )
    active, manifest_migration_policy = _apply_manifest_migration_policy(
        active, maintenance_route,
    )
    active = _dedup_duplicate_id_findings(active)
    migration_recs = _build_migration_recommendations(
        active, project_state, maintenance_route,
    )

    resolution_summary, _resolution_by_id = _classify_all(
        active, maintenance_route, state=project_state)
    finding_dicts = []
    for f in active:
        d = asdict(f)
        d["resolution_class"] = _resolution_by_id[f.id]
        finding_dicts.append(d)

    result = {
        "findings": finding_dicts,
        "resolution_summary": resolution_summary,
        "skipped_categories": skipped,
        "suppressions_resolved": sorted(resolved_ids),
        "project_state_summary": build_state_summary(project_state),
        "migration_recommendations": migration_recs,
        "maintenance_route": maintenance_route,
        "compatibility_adjustments": compatibility_adjustments,
        "manifest_migration_policy": manifest_migration_policy,
        "executable_contract": executable_contract,
    }
    if categories:
        result["scanned_categories"] = sorted(checks_to_run.keys())
    return result


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sanitize_path(p: str) -> str:
    h = hashlib.md5(p.encode()).hexdigest()[:8]
    name = p.replace("/", "__").replace("\\", "__")
    return f"{name}__{h}"


def _hash_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def create_archive(project_dir: Path) -> Path:
    ts = _now_iso()
    archive = project_dir / ".sweetclaude" / "state" / "doctor-runs" / ts
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "before").mkdir(exist_ok=True)
    (archive / "diffs").mkdir(exist_ok=True)
    return archive


def backup_content(archive_path: Path, file_path: Path, content: bytes) -> str:
    h = _hash_bytes(content)
    dest = archive_path / "before" / _sanitize_path(str(file_path))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return h


def write_diff(
    archive_path: Path, file_path: Path, original: bytes, modified: bytes
) -> None:
    orig_lines = original.decode("utf-8", errors="replace").splitlines(keepends=True)
    mod_lines = modified.decode("utf-8", errors="replace").splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines, mod_lines,
        fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
    )
    diff_text = "".join(diff)
    if diff_text:
        dest = archive_path / "diffs" / (_sanitize_path(str(file_path)) + ".diff")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(diff_text)


def _record_mutation(
    archive_path: Path, file_path: Path, before: bytes, after: bytes
) -> RecipeResult:
    """Record a file mutation through the archive pipeline.

    Backs up the original content to before/, writes a unified diff to diffs/,
    and returns a RecipeResult with real before/after hashes. The caller
    performs the actual write (or delete); routing every mutation through this
    helper guarantees it is backed up and diffed so it can be reversed by
    ``restore``. This is the single backup/diff contract the executor relies on.
    """
    before_hash = backup_content(archive_path, file_path, before)
    write_diff(archive_path, file_path, before, after)
    return RecipeResult(
        "", before_hash, _hash_bytes(after),
        archive_path / "before" / _sanitize_path(str(file_path)), True,
    )


def _record_subprocess_mutations(
    archive_path: Path, recipe: dict, targets: list[Path],
    before_map: dict[Path, bytes],
) -> RecipeResult:
    """Back up + diff the file(s) a subprocess action regenerated.

    run_script and rebuild_cache run an external script that rewrites derived/
    cache state. The caller captures each target's bytes BEFORE running and
    passes them here. For every target whose content actually changed, this
    routes the (before, after) pair through ``_record_mutation`` so a before/
    image and a unified diff are recorded — making the subprocess output
    reversible by ``restore`` exactly like an in-process file mutation.

    The first changed target is threaded onto ``recipe["file"]`` so the
    ``auto_fix`` action entry keys ``restore`` to it; any additional changed
    targets are threaded onto ``recipe["extra_files"]`` so ``auto_fix`` can emit
    one extra action entry per file. If nothing changed, the result reports a
    no-op (before == after) with no backup. If no targets were declared, the
    result is honestly reversible:false (backup_path is None).
    """
    changed: list[tuple[Path, bytes, bytes]] = []
    for tp in targets:
        before = before_map.get(tp, b"")
        after = tp.read_bytes() if tp.exists() else b""
        if before != after:
            changed.append((tp, before, after))

    if not changed:
        # No declared target changed (or none declared): no authored before-
        # image. Report a no-op success; restore reports reversible:false.
        return RecipeResult("", "", None, None, True)

    primary_path, primary_before, primary_after = changed[0]
    primary = _record_mutation(archive_path, primary_path, primary_before, primary_after)
    recipe["file"] = str(primary_path)

    extra: list[str] = []
    for tp, before, after in changed[1:]:
        _record_mutation(archive_path, tp, before, after)
        extra.append(str(tp))
    if extra:
        recipe["extra_files"] = extra

    return primary


def write_manifest(archive_path: Path, manifest: dict) -> None:
    path = archive_path / "manifest.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2, default=str))
    os.replace(tmp, path)


def prune_archives(project_dir: Path, max_age_days: int = 30, keep_min: int = 5) -> list[str]:
    runs_dir = project_dir / ".sweetclaude" / "state" / "doctor-runs"
    if not runs_dir.is_dir():
        return []
    dirs = sorted(runs_dir.iterdir(), reverse=True)
    if len(dirs) <= keep_min:
        return []

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_age_days)
    pruned = []
    for d in dirs[keep_min:]:
        try:
            ts = datetime.datetime.strptime(d.name, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=datetime.timezone.utc
            )
            if ts < cutoff:
                shutil.rmtree(d)
                pruned.append(d.name)
        except (ValueError, OSError):
            continue
    return pruned


# ---------------------------------------------------------------------------
# Recipe execution (sole file-mutation entry point)
# ---------------------------------------------------------------------------

def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    try:
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _resolve_within(path: Path, *roots: Path) -> bool:
    """True if ``path`` (resolved) lies within any of ``roots`` (resolved).

    Containment guard for executor/restore writes. Doctor may only touch the
    project tree or the user's ``~/.claude`` SweetClaude install — never anywhere
    else. Blocks path traversal (``../``) and absolute escapes in recipe- or
    archive-supplied paths from reaching ``shutil.move``/``_atomic_write``/
    ``unlink``. Symlinks are resolved, so a symlinked escape is also caught.
    """
    try:
        rp = path.resolve()
    except (OSError, RuntimeError):
        return False
    for root in roots:
        try:
            rp.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _apply_transform(content: bytes, recipe: dict, project_dir: Path) -> bytes:
    action = recipe["action"]

    if action == "write_field":
        text = content.decode("utf-8")
        data = yaml.safe_load(text) or {}
        # key_path supports nested writes (e.g. recovery.taxonomy.compatibility
        # _exited) so exit_compatibility_mode can REUSE write_field rather than
        # add a new transform (V7 tripwire). A flat `key` keeps the top-level
        # behavior unchanged.
        key_path = recipe.get("key_path")
        if key_path:
            node = data
            for k in key_path[:-1]:
                child = node.get(k)
                if not isinstance(child, dict):
                    child = {}
                    node[k] = child
                node = child
            node[key_path[-1]] = recipe["value"]
        else:
            data[recipe["key"]] = recipe["value"]
        return yaml.safe_dump(data, default_flow_style=False).encode("utf-8")

    if action == "write_frontmatter_field":
        text = content.decode("utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError("No frontmatter delimiters found")
        fm_data = yaml.safe_load(parts[1]) or {}
        fm_data[recipe["key"]] = recipe["value"]
        for rk in recipe.get("remove_keys", []):
            fm_data.pop(rk, None)
        new_fm = yaml.safe_dump(fm_data, default_flow_style=False)
        return f"---\n{new_fm}---{parts[2]}".encode("utf-8")

    if action == "delete_file":
        return b""

    if action == "create_dir":
        return b""

    if action == "rebuild_cache":
        return content

    if action == "run_script":
        return content

    if action in ("sync_parent_status", "convert_to_yaml"):
        return content

    raise ValueError(f"Unknown recipe action: {action}")


def _check_precondition(recipe: dict, content: bytes, file_path: Path) -> bool:
    """Return True if the fix is already applied (skip)."""
    action = recipe["action"]

    if action == "write_field":
        try:
            data = yaml.safe_load(content.decode("utf-8")) or {}
            key_path = recipe.get("key_path")
            if key_path:
                node = data
                for k in key_path[:-1]:
                    node = node.get(k) if isinstance(node, dict) else None
                    if not isinstance(node, dict):
                        return False
                return node.get(key_path[-1]) == recipe["value"]
            return data.get(recipe["key"]) == recipe["value"]
        except (yaml.YAMLError, UnicodeDecodeError):
            return False

    if action == "write_frontmatter_field":
        try:
            text = content.decode("utf-8")
            parts = text.split("---", 2)
            if len(parts) < 3:
                return False
            fm_data = yaml.safe_load(parts[1]) or {}
            if fm_data.get(recipe["key"]) != recipe["value"]:
                return False
            for rk in recipe.get("remove_keys", []):
                if rk in fm_data:
                    return False
            return True
        except (yaml.YAMLError, UnicodeDecodeError):
            return False

    if action == "delete_file":
        return not file_path.exists()

    if action == "create_dir":
        target = Path(recipe["path"])
        return target.is_dir()

    return False


def _yaml_frontmatter_reparses(text: str) -> dict | None:
    """Return the parsed mapping iff ``text`` is valid SweetClaude frontmatter.

    Valid means: opens with a ``---`` line, has a closing ``---``, and the
    region between them parses to a YAML mapping. Returns the mapping, or None
    if any of those does not hold. This is the post-repair validation gate.
    """
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if fm is None:
        return {}
    return fm if isinstance(fm, dict) else None


def _yaml_repair_auto(before: bytes) -> bytes:
    """Deterministically repair unambiguous frontmatter-DELIMITER breakage.

    Scope is intentionally narrow — delimiter placement only, never quoting,
    indentation, or value rewriting. Two unambiguous forms are repaired:

    1. Missing closing ``---``: the file opens with a ``---`` line, then a run
       of lines that parse as a YAML mapping, then markdown body. We find the
       largest leading run of post-delimiter lines that parses as a mapping and
       insert a closing ``---`` immediately after it.
    2. Missing opening ``---``: the file begins with a YAML mapping, then a
       ``---`` line, then body. We prepend an opening ``---``.

    AMBIGUITY GUARD: a repair is accepted only if the reconstructed text
    re-parses as valid frontmatter (``_yaml_frontmatter_reparses``) AND the
    re-parsed mapping equals the mapping we isolated. If we cannot isolate a
    clean mapping, or the reconstruction does not re-parse to the same fields,
    we DO NOT guess — we raise ValueError so the executor signals manual-edit.
    The caller treats any raise here as "not safely repairable".
    """
    text = before.decode("utf-8", errors="strict")
    lines = text.splitlines(keepends=True)

    def _strip_delims(seq: list[str]) -> str:
        return "".join(seq)

    # Already valid frontmatter: nothing to repair (idempotent / defensive).
    if _yaml_frontmatter_reparses(text) is not None:
        return before

    # --- Form 1: opening delimiter present, closing delimiter missing -------
    if lines and lines[0].rstrip("\r\n") == "---":
        # The body boundary must be STRUCTURALLY unambiguous — we do not search
        # for a split point that makes YAML happy (that is guessing). The body
        # of a SweetClaude markdown file begins at the first blank line or the
        # first markdown construct (a line starting with '#'). Everything from
        # the opening delimiter to that boundary must parse, as a whole, into a
        # YAML mapping. If it does not, the breakage is inside the frontmatter
        # itself (quoting/indentation) — not a delimiter problem — so refuse.
        body_start = None
        for i in range(1, len(lines)):
            stripped = lines[i].rstrip("\r\n")
            if stripped == "" or stripped.lstrip().startswith("#"):
                body_start = i
                break
        if body_start is None:
            body_start = len(lines)
        region = _strip_delims(lines[1:body_start])
        if not region.strip():
            raise ValueError(
                "auto repair: no frontmatter content before the body boundary"
            )
        try:
            isolated = yaml.safe_load(region)
        except yaml.YAMLError:
            isolated = None
        if not isinstance(isolated, dict) or not isolated:
            raise ValueError(
                "auto repair: frontmatter is not unambiguously recoverable "
                "(content before the body boundary is not a clean YAML mapping)"
            )
        head = lines[:body_start]
        tail = lines[body_start:]
        if head and not head[-1].endswith("\n"):
            head[-1] = head[-1] + "\n"
        rebuilt = "".join(head) + "---\n" + "".join(tail)
        reparsed = _yaml_frontmatter_reparses(rebuilt)
        if reparsed is None or reparsed != isolated:
            raise ValueError(
                "auto repair: reconstructed frontmatter did not re-parse to the "
                "same fields — refusing to guess"
            )
        return rebuilt.encode("utf-8")

    # --- Form 2: opening delimiter missing, closing delimiter present -------
    delim_idx = None
    for idx, ln in enumerate(lines):
        if ln.rstrip("\r\n") == "---":
            delim_idx = idx
            break
    if delim_idx is not None and delim_idx > 0:
        region = _strip_delims(lines[:delim_idx])
        try:
            parsed = yaml.safe_load(region)
        except yaml.YAMLError:
            parsed = None
        if isinstance(parsed, dict) and parsed:
            rebuilt = "---\n" + text
            reparsed = _yaml_frontmatter_reparses(rebuilt)
            if reparsed is not None and reparsed == parsed:
                return rebuilt.encode("utf-8")

    raise ValueError(
        "auto repair: not an unambiguous delimiter break — manual edit needed"
    )


def _config_conflict_adopt(before: bytes, recipe: dict) -> bytes:
    """Apply SweetClaude's rule for a config_conflict (the ``adopt`` choice).

    Two targeted mechanisms, derived from how check_config_compat detected the
    conflict (NOT a general config editor — the recipe names the exact target):

    - Settings conflicts (F1-F3): edit settings.json structurally. F1 adds the
      excluded ``tool`` back to allowedTools; F2/F3 remove the conflicting hook
      entry (matched by its command, optionally narrowed by matcher).
    - Text conflicts (F4, W1-W4, I1, I2): remove the line(s) of the source file
      that contain the matched ``pattern`` (case-insensitive substring).
    """
    tool = recipe.get("tool")
    hook_command = recipe.get("hook_command")

    if tool is not None or hook_command is not None:
        data = json.loads(before.decode("utf-8"))
        if tool is not None:
            allowed = data.get("allowedTools")
            if isinstance(allowed, list) and tool not in allowed:
                allowed.append(tool)
        elif hook_command is not None:
            matcher = recipe.get("matcher")
            for hook_list in (data.get("hooks") or {}).values():
                if not isinstance(hook_list, list):
                    continue
                kept = []
                for entry in hook_list:
                    cmds = [h.get("command", "") for h in entry.get("hooks", [])]
                    matches_cmd = hook_command in cmds
                    matches_matcher = (
                        matcher is None or str(entry.get("matcher", "")) == matcher
                    )
                    if matches_cmd and matches_matcher:
                        continue
                    kept.append(entry)
                hook_list[:] = kept
        return json.dumps(data, indent=2).encode("utf-8")

    pattern = recipe.get("pattern")
    if not pattern:
        raise ValueError("config_conflict adopt: no target (tool/hook_command/pattern)")
    text = before.decode("utf-8")
    pat_lower = pattern.lower()
    kept_lines = [ln for ln in text.splitlines(keepends=True)
                  if pat_lower not in ln.lower()]
    return "".join(kept_lines).encode("utf-8")


def _resolve_hook_restore_paths(recipe: dict) -> tuple[Path, Path]:
    """Map a hook_restore target name to its real plugin SOURCE and installed DEST.

      - rules ``*.md``              : {plugin}/rules/{name} -> ~/.claude/rules/sweetclaude/{name}
      - hook script ``*.sh`` / json : {plugin}/hooks/{name} -> ~/.claude/hooks/sweetclaude/{name}

    An explicit ``source``/``dest`` on the recipe overrides the derivation.
    """
    name = recipe.get("hook", "")
    if not name:
        raise ValueError("hook_restore: no hook/target name in recipe")

    explicit_source = recipe.get("source")
    explicit_dest = recipe.get("dest")
    if explicit_source and explicit_dest:
        return Path(explicit_source), Path(explicit_dest)

    plugin_dir = Path(recipe.get("plugin_dir", ""))
    home_claude = Path.home() / ".claude"

    if name.endswith(".md"):
        source = plugin_dir / "rules" / name
        dest = home_claude / "rules" / "sweetclaude" / name
    else:
        source = plugin_dir / "hooks" / name
        dest = home_claude / "hooks" / "sweetclaude" / name
    return source, dest


def execute_recipe(
    project_dir: Path, recipe: dict, archive_path: Path
) -> RecipeResult:
    action = recipe["action"]

    if action == "sync_parent_status":
        parent_file = recipe.get("file", "")
        parent_path = Path(parent_file)
        if not parent_path.is_absolute():
            parent_path = project_dir / parent_path
        if not parent_path.exists():
            return RecipeResult("", "", None, None, False, f"Parent file not found: {parent_path}")
        try:
            from cache import get_conn, rebuild as _rebuild
            _rebuild(str(project_dir))
            parent_id = recipe.get("parent_id", "")
            parent_type = recipe.get("parent_type", "epic")
            conn = get_conn(str(project_dir))
            if parent_type == "epic":
                rows = conn.execute(
                    "SELECT status FROM items WHERE epic=? AND type NOT IN ('epic', 'milestone')",
                    (parent_id,),
                ).fetchall()
            elif parent_type == "milestone":
                rows = conn.execute(
                    "SELECT status FROM items WHERE type='epic' AND milestone=?",
                    (parent_id,),
                ).fetchall()
            else:
                rows = []
            conn.close()
            child_statuses = [r["status"] for r in rows]
            before = parent_path.read_bytes()
            from status import sync_parent_status as _sync
            changed = _sync(str(parent_path), child_statuses, "doctor-auto-fix", project_dir=str(project_dir))
            if not changed:
                h = _hash_bytes(before)
                return RecipeResult("", h, h, None, True, "already in sync")
            after = parent_path.read_bytes()
            return _record_mutation(archive_path, parent_path, before, after)
        except Exception as e:
            return RecipeResult("", "", None, None, False, str(e))

    if action == "convert_to_yaml":
        target_file = recipe.get("file", "")
        target_path = Path(target_file)
        if not target_path.is_absolute():
            target_path = project_dir / target_path
        if not target_path.exists():
            return RecipeResult("", "", None, None, False, f"File not found: {target_path}")
        try:
            before = target_path.read_bytes()
            from format_converter import convert_file
            result = convert_file(target_path, dry_run=False, backup=False)
            if result["action"] == "converted":
                after = target_path.read_bytes()
                return _record_mutation(archive_path, target_path, before, after)
            h = _hash_bytes(before)
            return RecipeResult("", h, h, None, False)
        except Exception as e:
            return RecipeResult("", "", None, None, False, str(e))

    if action == "config_conflict":
        choice = recipe.get("choice", "")
        # keep = leave SweetClaude's rule aside; both = keep both rules.
        # Neither mutates the file: no-op success, no backup.
        if choice != "adopt":
            return RecipeResult("", "", None, None, True, f"no-op ({choice or 'no choice'})")
        # adopt = apply SweetClaude's rule: a targeted edit of the offending
        # file. The recipe carries an explicit real path because the logical
        # source names ("~/.claude/settings.json") do not resolve under
        # project_dir.
        target_path = Path(recipe.get("path") or recipe.get("file", ""))
        if not target_path.is_absolute():
            target_path = project_dir / target_path
        if not target_path.exists():
            return RecipeResult("", "", None, None, False, f"File not found: {target_path}")
        try:
            before = target_path.read_bytes()
            after = _config_conflict_adopt(before, recipe)
            if after == before:
                h = _hash_bytes(before)
                return RecipeResult("", h, h, None, True, "already resolved")
            _atomic_write(target_path, after)
            return _record_mutation(archive_path, target_path, before, after)
        except Exception as e:
            return RecipeResult("", "", None, None, False, str(e))

    if action == "yaml_repair":
        choice = recipe.get("choice", "")
        target_path = Path(recipe.get("path") or recipe.get("file", ""))
        if not target_path.is_absolute():
            target_path = project_dir / target_path

        # manual = the skill shows the file for hand-editing. No-op success,
        # no backup (nothing changed).
        if choice == "manual":
            return RecipeResult("", "", None, None, True, "no-op (manual)")

        # restore = revert to a prior run's archived before-image. Delegate to
        # the existing restore path against this run's archive.
        if choice == "restore":
            res = restore(project_dir, archive_path, file=str(target_path))
            if res["restored"]:
                return RecipeResult("", "", None, None, True, f"restored {res['restored']}")
            return RecipeResult(
                "", "", None, None, False,
                "no archived before-image to restore from — choose manual edit",
            )

        # auto = deterministic delimiter repair, routed through _record_mutation
        # so it is backed up, diffed, and reversible. The repair refuses to
        # guess on ambiguous content (raises -> success=False, manual signal).
        if choice == "auto":
            if not target_path.exists():
                return RecipeResult("", "", None, None, False, f"File not found: {target_path}")
            try:
                before = target_path.read_bytes()
                after = _yaml_repair_auto(before)
            except Exception as e:
                # Ambiguous / unrecoverable: do not mutate, signal manual edit.
                return RecipeResult("", "", None, None, False, str(e))
            if after == before:
                h = _hash_bytes(before)
                return RecipeResult("", h, h, None, True, "already valid")
            _atomic_write(target_path, after)
            return _record_mutation(archive_path, target_path, before, after)

        return RecipeResult("", "", None, None, False, f"unknown yaml_repair choice: {choice!r}")

    if action == "hook_restore":
        # Restore a SweetClaude hook script, hooks config, or rules file from
        # the plugin source to its ~/.claude destination. Resolves the correct
        # per-kind source/dest (the old skill-side cp used the wrong path), and
        # routes any overwrite through _record_mutation so a clobbered dest is
        # backed up, diffed, and reversible via `restore` — important because
        # these ~/.claude files live outside the project git safety branch.
        try:
            source, dest = _resolve_hook_restore_paths(recipe)
        except Exception as e:
            return RecipeResult("", "", None, None, False, str(e))
        if not source.is_file():
            return RecipeResult(
                "", "", None, None, False,
                f"hook_restore source not found: {source}",
            )
        try:
            after = source.read_bytes()
        except OSError as e:
            return RecipeResult("", "", None, None, False, str(e))
        before = dest.read_bytes() if dest.is_file() else b""
        # Thread the resolved dest back onto the recipe so the auto_fix recorder
        # logs the real mutated path (it reads recipe["file"]); restore keys on
        # that path to find this run's before-image.
        recipe["file"] = str(dest)
        if before == after:
            h = _hash_bytes(before)
            return RecipeResult("", h, h, None, True, "already up to date")
        _atomic_write(dest, after)
        return _record_mutation(archive_path, dest, before, after)

    if action == "file_move":
        # Relocate a misfiled artifact (src -> dest). Emitted by storage-lint
        # for done-status items in the wrong folder. A move does NOT fit the
        # content-revert restore model: backing up src and writing it back to
        # src would leave BOTH src and dest. So the move is recorded as a move —
        # the recorded file_path is src (its before-image is src's content) and
        # a `moved_to` marker carries the dest — and `restore` REVERSES it
        # (delete dest, recreate src from its before-image) rather than
        # content-reverting.
        src = Path(recipe.get("src", ""))
        if not src.is_absolute():
            src = project_dir / src
        dest = Path(recipe.get("dest", ""))
        if not dest.is_absolute():
            dest = project_dir / dest
        if not (_resolve_within(src, project_dir) and _resolve_within(dest, project_dir)):
            return RecipeResult("", "", None, None, False,
                                f"file_move path outside project: src={src} dest={dest}")
        if not src.is_file():
            return RecipeResult("", "", None, None, False, f"file_move source not found: {src}")
        try:
            before = src.read_bytes()
            # Back up src's content (keyed to src) and diff src -> empty so the
            # move is reversible through the same archive contract.
            recorded = _record_mutation(archive_path, src, before, b"")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
        except Exception as e:
            return RecipeResult("", "", None, None, False, str(e))
        # Thread the real moved paths back onto the recipe so the auto_fix
        # recorder logs file_path=src (restore keys its before-image on that)
        # and moved_to=dest (restore reverses the move using it).
        recipe["file"] = str(src)
        recipe["moved_to"] = str(dest)
        return RecipeResult("", recorded.before_hash, recorded.after_hash,
                            recorded.backup_path, True)

    if action == "renumber_duplicate":
        # Resolve a duplicate id: rewrite the chosen file's `id` frontmatter to
        # new_id AND rename OLD-ID*.md -> NEW-ID*.md so the filename matches.
        # This is a content edit + rename, so — like file_move — it does NOT fit
        # the content-revert restore model: the file's path changes, so writing
        # the before-image back to the new path would leave BOTH names. It is
        # recorded move-aware: the before-image is keyed to the ORIGINAL path
        # (and holds the OLD id), and a `moved_to` marker carries the renamed
        # path. `restore` then reverses BOTH — delete the renamed file, recreate
        # the original path from its before-image (which restores the old id).
        target = Path(recipe.get("file", ""))
        if not target.is_absolute():
            target = project_dir / target
        if not _resolve_within(target, project_dir):
            return RecipeResult("", "", None, None, False,
                                f"renumber_duplicate path outside project: {target}")
        old_id = recipe.get("old_id", "")
        new_id = recipe.get("new_id", "")
        if not old_id or not new_id:
            return RecipeResult("", "", None, None, False,
                                "renumber_duplicate requires old_id and new_id")
        if old_id == new_id:
            return RecipeResult("", "", None, None, False,
                                f"new_id must differ from old_id: {old_id}")
        if not target.is_file():
            return RecipeResult("", "", None, None, False,
                                f"renumber_duplicate file not found: {target}")
        try:
            before = target.read_bytes()
            text = before.decode("utf-8")
            parts = text.split("---", 2)
            if len(parts) < 3:
                return RecipeResult("", "", None, None, False,
                                    "No frontmatter delimiters found")
            fm_data = yaml.safe_load(parts[1]) or {}
            fm_data["id"] = new_id
            new_fm = yaml.safe_dump(fm_data, default_flow_style=False)
            after_content = f"---\n{new_fm}---{parts[2]}".encode("utf-8")
            # Determine the renamed path: swap old_id's PREFIX-N for new_id's in
            # the filename. If the filename carries no id (no swap), keep it.
            final_path = target
            if old_id in target.name:
                final_path = target.parent / target.name.replace(old_id, new_id, 1)
            # Back up the ORIGINAL content keyed to the original path, and diff
            # original -> empty so the rename+rewrite is reversible through the
            # same archive contract file_move uses.
            recorded = _record_mutation(archive_path, target, before, b"")
            _atomic_write(final_path, after_content)
            if final_path != target:
                target.unlink()
        except Exception as e:
            return RecipeResult("", "", None, None, False, str(e))
        # Thread the real paths back onto the recipe so the auto_fix recorder
        # logs file_path=original (restore keys its before-image on that) and
        # moved_to=renamed (restore reverses the rename using it). When the
        # filename did not change, moved_to == file and restore degrades to a
        # plain content revert (which still restores the old id).
        recipe["file"] = str(target)
        recipe["moved_to"] = str(final_path)
        return RecipeResult("", recorded.before_hash, _hash_bytes(after_content),
                            recorded.backup_path, True)

    if action == "resolve_orphans":
        # Resolve one orphaned work item file through the v3->v4 migration
        # script, routing the mutation through the archive pipeline so it is
        # reversible by restore. The script's filename is hyphenated (not
        # importable), so — like the scan in check_migration_currency — it is
        # invoked via subprocess.
        #   - acknowledge: appends the path to the orphan registry (registry is
        #     the mutated file; before = b"" when absent, restore reverts it).
        #   - archive: moves the file into product archive/orphans; recorded
        #     move-aware like file_move (before-image keyed to src, moved_to =
        #     dest) so restore reverses the move.
        #   - reonboard: copies the orphan to a new ISSUE file, source stays;
        #     recorded with moved_to = the created file so restore deletes it
        #     and rewrites the unchanged source.
        orphan_action = recipe.get("orphan_action", "")
        src = Path(recipe.get("path", ""))
        if not src.is_absolute():
            src = project_dir / src
        subcmd = {
            "acknowledge": "acknowledge-orphans",
            "archive": "archive-orphans",
            "reonboard": "reonboard-orphans",
        }.get(orphan_action)
        if subcmd is None:
            return RecipeResult("", "", None, None, False,
                                f"resolve_orphans: unknown orphan_action "
                                f"'{orphan_action}' (expected acknowledge, "
                                f"archive, or reonboard)")
        if not _resolve_within(src, project_dir):
            return RecipeResult("", "", None, None, False,
                                f"resolve_orphans path outside project: {src}")
        if not src.is_file():
            return RecipeResult("", "", None, None, False,
                                f"resolve_orphans source not found: {src}")
        orphan_script = _SCRIPTS_DIR / "migrate" / "migrate-v3-to-v4.py"
        if not orphan_script.exists():
            return RecipeResult("", "", None, None, False,
                                f"migration script not found: {orphan_script}")
        rel = str(src.relative_to(project_dir))
        registry = project_dir / ".sweetclaude" / "state" / "orphan-registry.yaml"
        key_path = registry if orphan_action == "acknowledge" else src
        before = key_path.read_bytes() if key_path.exists() else b""
        try:
            r = subprocess.run(
                [sys.executable, str(orphan_script), subcmd,
                 "--project-dir", str(project_dir),
                 "--paths", json.dumps([rel])],
                capture_output=True, text=True, timeout=30,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            return RecipeResult("", "", None, None, False, str(e))
        if r.returncode != 0:
            return RecipeResult("", "", None, None, False,
                                r.stderr or f"{subcmd} exited {r.returncode}")
        try:
            out = json.loads(r.stdout)
        except json.JSONDecodeError:
            return RecipeResult("", "", None, None, False,
                                f"unparseable {subcmd} output: "
                                f"{r.stderr or r.stdout}")
        if orphan_action == "acknowledge":
            after = registry.read_bytes() if registry.exists() else b""
            recipe["file"] = str(registry)
            return _record_mutation(archive_path, registry, before, after)
        if orphan_action == "archive":
            archived = out.get("archived") or []
            if not archived:
                return RecipeResult("", "", None, None, False,
                                    f"archive-orphans did not archive {rel}")
            dest = Path(archived[0].get("dest", ""))
            if not dest.is_absolute():
                dest = project_dir / dest
            recorded = _record_mutation(archive_path, src, before, b"")
            recipe["file"] = str(src)
            recipe["moved_to"] = str(dest)
            return RecipeResult("", recorded.before_hash, recorded.after_hash,
                                recorded.backup_path, True)
        reonboarded = out.get("reonboarded") or []
        if not reonboarded:
            return RecipeResult("", "", None, None, False,
                                f"reonboard-orphans did not reonboard {rel}")
        dest = Path(reonboarded[0].get("dest", ""))
        if not dest.is_absolute():
            dest = project_dir / dest
        recorded = _record_mutation(archive_path, src, before, before)
        recipe["file"] = str(src)
        recipe["moved_to"] = str(dest)
        return RecipeResult("", recorded.before_hash, recorded.after_hash,
                            recorded.backup_path, True)

    if action == "run_script":
        cmd = recipe.get("cmd", [])
        if len(cmd) < 2:
            raise ValueError("run_script recipe must have cmd with >= 2 elements")
        script_name = Path(cmd[1]).name
        if script_name not in RUN_SCRIPT_ALLOWLIST:
            raise ValueError(
                f"Script '{script_name}' not in allowlist: {RUN_SCRIPT_ALLOWLIST}"
            )
        # The allowlist matches only the basename, so it alone would pass a
        # traversal path like "../../evil/cache.py". Require the resolved script
        # to live in a trusted root — the framework scripts dir, ~/.claude (where
        # the real hook scripts live), or the project tree doctor operates on — so
        # a crafted cmd[1] cannot escape to run an arbitrary file (e.g. /etc,
        # ~/.ssh, /tmp) under an allowlisted name.
        if not _resolve_within(
            Path(cmd[1]), _SCRIPTS_DIR, Path.home() / ".claude", project_dir
        ):
            raise ValueError(f"run_script path outside trusted roots: {cmd[1]}")
        # `regenerates` names the file(s) the script rewrites. Capture their
        # bytes BEFORE running so each changed target is routed through
        # _record_mutation (before/ image + diff) and is reversible by restore.
        # Absent/empty: fall back to fire-and-forget, honestly reversible:false.
        targets: list[Path] = []
        before_map: dict[Path, bytes] = {}
        for rel in (recipe.get("regenerates") or []):
            tp = Path(rel)
            if not tp.is_absolute():
                tp = project_dir / tp
            targets.append(tp)
            before_map[tp] = tp.read_bytes() if tp.exists() else b""
        result = subprocess.run(
            cmd + recipe.get("args", []),
            cwd=project_dir, capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            return RecipeResult(
                finding_id="", before_hash="", after_hash=None,
                backup_path=None, success=False, error=result.stderr.decode(),
            )
        return _record_subprocess_mutations(archive_path, recipe, targets, before_map)

    if action == "rebuild_cache":
        cache_script = _SCRIPTS_DIR / "cache.py"
        if not cache_script.exists():
            raise DependencyMissing("cache.py not found")
        # Capture the cache file's bytes before the rebuild so it is backed up,
        # diffed, and reverted byte-identically by restore. A missing cache
        # pre-rebuild is a create (before = b""): restore reverts to empty.
        cache_path = project_dir / ".sweetclaude" / "cache" / "roadmap.db"
        before = cache_path.read_bytes() if cache_path.exists() else b""
        result = subprocess.run(
            [sys.executable, str(cache_script), "--project-dir", str(project_dir), "--rebuild"],
            cwd=project_dir, capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            return RecipeResult(
                finding_id="", before_hash="", after_hash=None,
                backup_path=None, success=False, error=result.stderr.decode(),
            )
        return _record_subprocess_mutations(
            archive_path, recipe, [cache_path], {cache_path: before})

    if action == "create_dir":
        target = Path(recipe["path"])
        if not target.is_absolute():
            target = project_dir / target
        if _check_precondition(recipe, b"", target):
            h = _hash_bytes(b"")
            return RecipeResult("", h, h, None, True)
        target.mkdir(parents=True, exist_ok=True)
        return RecipeResult("", _hash_bytes(b""), _hash_bytes(b"created"), None, True)

    file_key = recipe.get("file", "")
    file_path = Path(file_key)
    if not file_path.is_absolute():
        file_path = project_dir / file_path

    content = file_path.read_bytes() if file_path.exists() else b""

    if _check_precondition(recipe, content, file_path):
        h = _hash_bytes(content)
        return RecipeResult("", h, h, None, True)

    if action == "delete_file":
        if file_path.exists():
            file_path.unlink()
        return _record_mutation(archive_path, file_path, content, b"")

    new_content = _apply_transform(content, recipe, project_dir)
    _atomic_write(file_path, new_content)
    return _record_mutation(archive_path, file_path, content, new_content)


# ---------------------------------------------------------------------------
# Auto-fix pipeline
# ---------------------------------------------------------------------------

def auto_fix(
    project_dir: Path, findings: list[dict], archive_path: Path,
    include_prompted: bool = False,
) -> dict:
    actions: list[dict] = []
    fixed_categories: set[str] = set()
    allowed_types = {"auto"}
    if include_prompted:
        allowed_types.add("prompted")

    for f in findings:
        if f.get("fix_type") not in allowed_types:
            continue
        recipe = f.get("fix_recipe", {})
        if recipe.get("action") == "prompt":
            continue
        recipe = f.get("fix_recipe", {})
        try:
            result = execute_recipe(project_dir, recipe, archive_path)
            result.finding_id = f["id"]
            if result.before_hash != result.after_hash:
                fixed_categories.add(f["category"])
            entry = {
                "action": "auto-fix",
                "finding_id": f["id"],
                "category": f["category"],
                "description": f["summary"],
                "file_path": recipe.get("file", ""),
                "before_hash": result.before_hash,
                "after_hash": result.after_hash,
                "timestamp": _now_iso(),
            }
            # file_move threads a moved_to marker onto the recipe; carry it into
            # the recorded action so `restore` can reverse the move (delete the
            # dest, recreate src from its before-image) instead of content-
            # reverting it. Plain actions never set this.
            if recipe.get("moved_to"):
                entry["moved_to"] = recipe["moved_to"]
            actions.append(entry)
            # Subprocess actions (run_script/rebuild_cache) may regenerate more
            # than one file. The primary changed target is recorded above via
            # recipe["file"]; each additional changed target is threaded onto
            # recipe["extra_files"] by _record_subprocess_mutations. Emit one
            # extra action entry per file so `restore` reverses every backed-up
            # target, not just the first.
            for extra_file in recipe.get("extra_files", []):
                actions.append({
                    "action": "auto-fix",
                    "finding_id": f["id"],
                    "category": f["category"],
                    "description": f["summary"],
                    "file_path": extra_file,
                    "before_hash": "",
                    "after_hash": None,
                    "timestamp": _now_iso(),
                })
        except Exception as e:
            actions.append({
                "action": "auto-fix-failed",
                "finding_id": f["id"],
                "category": f["category"],
                "description": f["summary"],
                "error": str(e),
                "timestamp": _now_iso(),
            })

    actions_path = archive_path / "actions.json"
    tmp = actions_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(actions, indent=2, default=str))
    os.replace(tmp, actions_path)

    return {
        "actions": actions,
        "post_fix_categories": sorted(fixed_categories),
    }


# ---------------------------------------------------------------------------
# Restore — reverse mutations from a run archive's before/ images
# ---------------------------------------------------------------------------

def restore(
    project_dir: Path, archive_path: Path,
    file: str | None = None, restore_all: bool = False,
) -> dict:
    """Reconstruct files from a doctor run's archived before/ images.

    The inverse of ``_record_mutation``: reads the run's recorded actions
    (manifest.json, falling back to actions.json), and for the requested
    target(s) writes the archived before-image back over the live file. A
    single file (``file=``) or the whole run (``restore_all=True``) can be
    restored. Actions with no archived before-image (e.g. cache/derived
    ``reversible:false`` mutations) are reported as skipped rather than failing.
    """
    project_dir = Path(project_dir)
    archive_path = Path(archive_path)

    actions: list[dict] = []
    manifest = archive_path / "manifest.json"
    actions_file = archive_path / "actions.json"
    if manifest.exists():
        try:
            actions = json.loads(manifest.read_text()).get("actions", [])
        except (json.JSONDecodeError, OSError):
            actions = []
    if not actions and actions_file.exists():
        try:
            actions = json.loads(actions_file.read_text())
        except (json.JSONDecodeError, OSError):
            actions = []

    target = None
    if file is not None:
        target = Path(file)
        if not target.is_absolute():
            target = project_dir / target

    restored: list[str] = []
    skipped: list[dict] = []
    seen: set[str] = set()
    for a in actions:
        fp = a.get("file_path", "")
        if not fp:
            continue
        resolved = Path(fp)
        if not resolved.is_absolute():
            resolved = project_dir / resolved
        if target is not None:
            if resolved != target:
                continue
        elif not restore_all:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        # Containment: restore only writes inside the project tree or the user's
        # ~/.claude install (hook_restore legitimately targets the latter). A
        # crafted archive with file_path/moved_to escaping those roots is refused
        # rather than allowed to delete/overwrite an arbitrary path.
        roots = (project_dir, Path.home() / ".claude")
        moved_to = a.get("moved_to", "")
        dest = None
        if moved_to:
            dest = Path(moved_to)
            if not dest.is_absolute():
                dest = project_dir / dest
        if not _resolve_within(resolved, *roots) or (
            dest is not None and not _resolve_within(dest, *roots)
        ):
            skipped.append({"file": str(resolved), "reason": "outside allowed roots"})
            continue
        backup = archive_path / "before" / _sanitize_path(str(resolved))
        if backup.exists():
            data = backup.read_bytes()
            # Move-aware rollback: a file_move action records file_path=src (its
            # before-image is src's content) plus a moved_to=dest marker. A move
            # cannot be content-reverted — rewriting src alone would leave BOTH
            # src and dest. Reverse it: remove dest first, then recreate src
            # from its before-image. Plain (non-move) actions have no marker and
            # keep the existing content-revert behavior.
            if dest is not None and dest.exists():
                dest.unlink()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(resolved, data)
            restored.append(str(resolved))
        else:
            skipped.append({
                "file": str(resolved),
                "reason": "no archived before-image (reversible:false)",
            })

    return {"restored": restored, "skipped": skipped}


# ---------------------------------------------------------------------------
# Post-fix rescan
# ---------------------------------------------------------------------------

def post_fix_rescan(
    project_dir: Path, categories: list[str], original_finding_ids: set[str]
) -> dict:
    state = build_project_state(project_dir)
    new_findings: list[Finding] = []
    for cat in categories:
        fn = CHECKS.get(cat)
        if fn:
            try:
                new_findings.extend(fn(state))
            except DependencyMissing:
                pass
    genuinely_new = [f for f in new_findings if f.id not in original_finding_ids]
    return {"findings": [asdict(f) for f in genuinely_new]}


# ---------------------------------------------------------------------------
# Dry-run simulation
# ---------------------------------------------------------------------------

def dry_run(project_dir: Path, findings: list[dict]) -> dict:
    simulations = []
    for f in findings:
        if f.get("fix_type") == "auto":
            recipe = f.get("fix_recipe", {})
            action = recipe.get("action", "")
            file_key = recipe.get("file", "")
            file_path = (project_dir / file_key) if file_key else None

            if action == "write_field" and file_path and file_path.exists():
                try:
                    content = file_path.read_bytes()
                    new_content = _apply_transform(content, recipe, project_dir)
                    simulations.append({
                        "finding_id": f["id"],
                        "summary": f["summary"],
                        "file": file_key,
                        "before": content.decode("utf-8", errors="replace")[:500],
                        "after": new_content.decode("utf-8", errors="replace")[:500],
                    })
                except Exception:
                    simulations.append({
                        "finding_id": f["id"],
                        "summary": f["summary"],
                        "note": "Actual results may differ — requires real execution",
                    })
            elif action in ("rebuild_cache", "run_script"):
                simulations.append({
                    "finding_id": f["id"],
                    "summary": f["summary"],
                    "note": "Actual results may differ — requires real execution",
                })
            else:
                simulations.append({
                    "finding_id": f["id"],
                    "summary": f["summary"],
                    "file": file_key,
                    "description": f"Will {action}: {file_key}",
                })
        elif f.get("fix_type") == "prompted":
            simulations.append({
                "finding_id": f["id"],
                "summary": f["summary"],
                "note": "Will be presented for your approval",
            })
    return {"simulations": simulations}


# ---------------------------------------------------------------------------
# Record action (prompted-fix tracking)
# ---------------------------------------------------------------------------

def record_action(archive_path: Path, action: dict) -> dict:
    pending = archive_path / "pending-actions.jsonl"
    with open(pending, "a") as fh:
        fh.write(json.dumps(action, default=str) + "\n")
    return {"recorded": True}


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------

def persist(
    project_dir: Path, archive_path: Path,
    menu_preference: str | None = None,
    scan_findings: list[dict] | None = None,
    safety_branch: str | None = None,
) -> dict:
    auto_actions = []
    actions_file = archive_path / "actions.json"
    if actions_file.exists():
        auto_actions = json.loads(actions_file.read_text())

    prompted_actions = []
    pending_file = archive_path / "pending-actions.jsonl"
    if pending_file.exists():
        for line in pending_file.read_text().splitlines():
            line = line.strip()
            if line:
                prompted_actions.append(json.loads(line))

    all_actions = auto_actions + prompted_actions

    errors = sum(1 for a in all_actions if a.get("action") == "auto-fix-failed")
    auto_fixed = sum(1 for a in all_actions if a.get("action") == "auto-fix")
    user_fixed = sum(1 for a in all_actions if a.get("action") == "prompted-fix")
    skipped = sum(1 for a in all_actions if a.get("action") == "skip")
    # Deferred, backed-up suppression prune (P2/P4): scan computes the resolved
    # set read-only; the actual ledger write happens here, in the execute phase,
    # routed through the archive. Only when the current finding set is known
    # (scan_findings passed) — otherwise pruning could clobber live entries.
    # Record it as an action so the before-image is restore-reversible (S6).
    suppressions_pruned: list[str] = []
    if scan_findings is not None:
        current_finding_ids = {f.get("id") for f in scan_findings if f.get("id")}
        suppressions_pruned = sorted(
            prune_resolved_suppressions(project_dir, archive_path, current_finding_ids)
        )
        if suppressions_pruned:
            all_actions.append({
                "action": "suppression-prune",
                "file_path": str(_suppressions_path(project_dir)),
                "pruned": suppressions_pruned,
            })

    scan_findings = scan_findings or []
    severity_counts = {
        "errors": sum(1 for f in scan_findings if f.get("severity") == "error"),
        "warnings": sum(1 for f in scan_findings if f.get("severity") == "warning"),
        "info": sum(1 for f in scan_findings if f.get("severity") == "info"),
        "total_findings": len(scan_findings),
    }

    manifest = {
        "timestamp": _now_iso(),
        "version": _resolve_installed_version() or "unknown",
        "safety_branch": safety_branch,
        "actions": all_actions,
        "suppressions_pruned": suppressions_pruned,
        "post_fix_findings": [],
        "summary": {
            "auto_fixed": auto_fixed,
            "user_fixed": user_fixed,
            "skipped": skipped,
            "failed": errors,
            **severity_counts,
        },
    }
    write_manifest(archive_path, manifest)

    finding_limit = 100
    findings_summary = [
        {"id": f["id"], "severity": f["severity"], "summary": f["summary"]}
        for f in scan_findings[:finding_limit]
    ]

    last_run = {
        "timestamp": manifest["timestamp"],
        "version": manifest["version"],
        "summary": manifest["summary"],
        "findings": findings_summary,
        "findings_total": len(scan_findings),
        "findings_truncated": max(0, len(scan_findings) - len(findings_summary)),
        "menu_preference": menu_preference,
    }
    last_run_path = project_dir / ".sweetclaude" / "state" / "last-doctor-run.json"
    last_run_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = last_run_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(last_run, indent=2))
    os.replace(tmp, last_run_path)

    return {"path": str(last_run_path)}


# ---------------------------------------------------------------------------
# Session-start health check
# ---------------------------------------------------------------------------

def session_check(project_dir: Path) -> dict:
    findings: list[str] = []

    sc_yaml_path = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
    sc_yaml = _read_yaml(sc_yaml_path)

    branch = _git_branch(project_dir)
    active_id = None
    if sc_yaml:
        active_id = (sc_yaml.get("work") or {}).get("active")

    branch_issue = _extract_issue_from_branch(branch) if branch else None

    if active_id:
        active_id = active_id.upper()

    if branch_issue and active_id and branch_issue != active_id:
        findings.append(
            f"Branch implies {branch_issue} but work.active is {active_id}"
        )
    elif branch_issue and not active_id:
        findings.append(
            f"No active work item set — branch implies {branch_issue}"
        )
    elif active_id and not branch_issue and branch:
        findings.append(
            f"work.active is {active_id} but branch {branch!r} has no issue token"
        )

    if active_id:
        fm = _find_item_frontmatter(project_dir, active_id)
        raw_status = fm.get("status", "") if fm else ""
        status_val = raw_status.split("—")[0].split("(")[0].strip() if isinstance(raw_status, str) else ""
        if fm and status_val == "new" and branch:
            findings.append(
                f"{active_id} has status 'new' despite being on an active branch"
            )

    cache_findings = _check_cache_health(project_dir)
    if cache_findings:
        findings.append(cache_findings)

    return {
        "check": "session-start",
        "findings": findings,
        "status": "all clear" if not findings else "issues found",
    }


def _git_branch(project_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(project_dir), capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _extract_issue_from_branch(branch: str) -> str | None:
    m = re.search(r"(ISSUE|EP|MS)-(\d+)", branch, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}"
    return None


def _find_item_frontmatter(project_dir: Path, item_id: str) -> dict | None:
    product_dir = project_dir / ".sweetclaude" / "product"
    if not product_dir.is_dir():
        return None
    pattern = f"{item_id}-*"
    for match in product_dir.rglob(pattern):
        if match.is_file() and match.suffix == ".md":
            return _read_frontmatter(match)
    for match in product_dir.rglob(f"{item_id}.*"):
        if match.is_file() and match.suffix == ".md":
            return _read_frontmatter(match)
    return None


def _check_cache_health(project_dir: Path) -> str | None:
    try:
        scripts_dir = _SCRIPTS_DIR
        if scripts_dir not in [Path(p) for p in sys.path]:
            sys.path.insert(0, str(scripts_dir))
        from cache import rebuild
        result = rebuild(str(project_dir))
        skipped = result.get("skipped", [])
        if skipped:
            return f"Cache rebuild: {result['scanned']} scanned, {result['ingested']} indexed, {len(skipped)} skipped"
    except Exception as e:
        return f"Cache rebuild failed: {e}"
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude doctor — diagnostic scan and repair")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _add(name: str, needs_project: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name)
        if needs_project:
            p.add_argument("--project-dir", required=True, type=Path)
        return p

    p_scan = _add("scan")
    p_scan.add_argument("--category", default=None)

    _add("maintenance-route")

    _add("create-archive")

    p_fix = _add("auto-fix")
    p_fix.add_argument("--archive-dir", required=True, type=Path)
    p_fix.add_argument("--include-prompted", action="store_true", default=False)

    p_rescan = _add("post-fix-rescan")
    p_rescan.add_argument("--categories", required=True)

    p_record = sub.add_parser("record-action")
    p_record.add_argument("--archive-dir", required=True, type=Path)

    p_suppress = _add("suppress")
    p_suppress.add_argument("--finding-id", required=True)
    p_suppress.add_argument("--reason", default=None)

    p_unsuppress = _add("unsuppress")
    p_unsuppress.add_argument("--finding-id", default=None)
    p_unsuppress.add_argument("--prune-malformed", action="store_true", default=False)

    _add("dry-run")

    p_persist = _add("persist")
    p_persist.add_argument("--archive-dir", required=True, type=Path)
    p_persist.add_argument("--menu-preference", default=None)
    p_persist.add_argument("--safety-branch", default=None)

    p_restore = _add("restore")
    p_restore.add_argument("--archive-dir", required=True, type=Path)
    p_restore.add_argument("--file", default=None)
    p_restore.add_argument("--all", action="store_true", default=False)

    _add("prune-archives")
    _add("session-check")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "scan":
            project_dir = args.project_dir.resolve()
            sc_yaml = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
            if not sc_yaml.exists():
                _emit({"error": "not-configured",
                       "message": "SweetClaude not configured for this project"})
                return 0
            state = build_project_state(project_dir)
            cats = [c.strip() for c in args.category.split(",") if c.strip()] if args.category else None
            _emit(_scan(state, categories=cats))

        elif args.cmd == "maintenance-route":
            project_dir = args.project_dir.resolve()
            sc_yaml = project_dir / ".sweetclaude" / "state" / "sweetclaude.yaml"
            if not sc_yaml.exists():
                _emit({"error": "not-configured",
                       "message": "SweetClaude not configured for this project"})
                return 0
            state = build_project_state(project_dir)
            _emit({
                "maintenance_route": build_maintenance_route(state),
                "project_state_summary": build_state_summary(state),
            })

        elif args.cmd == "create-archive":
            archive = create_archive(args.project_dir.resolve())
            _emit({"archive_dir": str(archive)})

        elif args.cmd == "auto-fix":
            findings = json.loads(sys.stdin.read())
            if isinstance(findings, dict):
                findings = findings.get("findings", [])
            result = auto_fix(
                args.project_dir.resolve(), findings, args.archive_dir.resolve(),
                include_prompted=args.include_prompted,
            )
            _emit(result)

        elif args.cmd == "post-fix-rescan":
            original = json.loads(sys.stdin.read())
            if isinstance(original, dict):
                original = original.get("findings", [])
            original_ids = {f["id"] for f in original}
            categories = [c.strip() for c in args.categories.split(",") if c.strip()]
            result = post_fix_rescan(
                args.project_dir.resolve(), categories, original_ids
            )
            _emit(result)

        elif args.cmd == "record-action":
            action = json.loads(sys.stdin.read())
            _emit(record_action(args.archive_dir.resolve(), action))

        elif args.cmd == "suppress":
            result = suppress_finding(
                args.project_dir.resolve(),
                args.finding_id,
                reason=args.reason,
            )
            _emit(result)
            if not result.get("suppressed"):
                return 1

        elif args.cmd == "unsuppress":
            if not args.finding_id and not args.prune_malformed:
                _emit({
                    "unsuppressed": False,
                    "error": "provide --finding-id and/or --prune-malformed",
                })
                return 1
            _emit(unsuppress_finding(
                args.project_dir.resolve(),
                finding_id=args.finding_id,
                prune_malformed=args.prune_malformed,
            ))

        elif args.cmd == "dry-run":
            findings = json.loads(sys.stdin.read())
            if isinstance(findings, dict):
                findings = findings.get("findings", [])
            _emit(dry_run(args.project_dir.resolve(), findings))

        elif args.cmd == "persist":
            stdin_data = sys.stdin.read().strip()
            scan_findings = []
            if stdin_data:
                parsed = json.loads(stdin_data)
                scan_findings = parsed.get("findings", []) if isinstance(parsed, dict) else parsed
            result = persist(
                args.project_dir.resolve(),
                args.archive_dir.resolve(),
                args.menu_preference,
                scan_findings=scan_findings,
                safety_branch=args.safety_branch,
            )
            _emit(result)

        elif args.cmd == "restore":
            _emit(restore(
                args.project_dir.resolve(),
                args.archive_dir.resolve(),
                file=args.file,
                restore_all=args.all,
            ))

        elif args.cmd == "prune-archives":
            pruned = prune_archives(args.project_dir.resolve())
            _emit({"pruned": pruned})

        elif args.cmd == "session-check":
            _emit(session_check(args.project_dir.resolve()))

    except Exception as e:
        print(json.dumps({"error": type(e).__name__, "message": str(e)}), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
