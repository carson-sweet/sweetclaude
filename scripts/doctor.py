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
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip install pyyaml")


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

RUN_SCRIPT_ALLOWLIST = {
    "cache.py",
    "generate-session-state.sh",
}


# ---------------------------------------------------------------------------
# Frontmatter helper
# ---------------------------------------------------------------------------

def _read_frontmatter(path: Path) -> dict | None:
    try:
        raw = path.read_text()
    except OSError:
        return None
    if not raw.startswith("---"):
        return None
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None


def _read_frontmatter_raw(path: Path) -> tuple[dict | None, str | None]:
    """Return (parsed_frontmatter, error_description)."""
    try:
        raw = path.read_text()
    except OSError:
        return None, "file unreadable"
    if not raw.startswith("---"):
        return None, "no frontmatter delimiter"
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None, "no frontmatter delimiter"
    try:
        fm = yaml.safe_load(parts[1]) or {}
        return fm, None
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {e}"


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
                        "cmd": ["bash", str(state.project_dir / "hooks" / "generate-session-state.sh")],
                        "args": []},
        ))

    if state.sweetclaude_yaml:
        schema_v = state.sweetclaude_yaml.get("phase_schema_version")
        if schema_v is not None and schema_v != 2:
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
                            "cmd": ["bash", str(state.project_dir / "hooks" / "generate-session-state.sh")],
                            "args": []},
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
                    detail=f"bash -n failed: {result.stderr.decode()[:200]}",
                    file_paths=[str(hf)],
                    fix_type="prompted",
                    fix_recipe={"action": "prompt", "type": "hook_restore",
                                "hook": hf.name, "sources": ["backup", "repo"]},
                ))
        except (subprocess.TimeoutExpired, OSError):
            pass

    rules_dir = Path.home() / ".claude" / "rules" / "sweetclaude"
    expected_rules = ["interaction-model.md", "phase-gates.md", "tdd-levels.md"]
    for rf in expected_rules:
        if rf not in state.rules_files:
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


def check_storage_lint(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    backlog_dir = state.product_base / "backlog"
    roadmap_dir = state.product_base / "roadmap"

    if backlog_dir.is_dir() and roadmap_dir.is_dir():
        backlog_ids: set[str] = set()
        for p in backlog_dir.rglob("*.md"):
            if p.name in ("INDEX.md", "MIGRATION-MAP.md"):
                continue
            fm = _read_frontmatter(p)
            if fm and fm.get("id"):
                backlog_ids.add(fm["id"])
        roadmap_ids: set[str] = set()
        for p in roadmap_dir.rglob("*.md"):
            fm = _read_frontmatter(p)
            if fm and fm.get("id"):
                roadmap_ids.add(fm["id"])
        for dup_id in sorted(backlog_ids & roadmap_ids):
            findings.append(Finding(
                id=f"storage-lint:cross-location-duplicate-id:{dup_id}",
                category="storage_lint",
                severity="error",
                summary=f"Item {dup_id} exists in both backlog and roadmap",
                detail=f"ID {dup_id} found in both {backlog_dir} and {roadmap_dir}",
                file_paths=[str(backlog_dir), str(roadmap_dir)],
                fix_type="report-only",
                fix_recipe={},
            ))

    if backlog_dir.is_dir():
        max_seen = 0
        for p in backlog_dir.rglob("*.md"):
            m = re.match(r"^ISSUE-(\d+)-", p.name)
            if m:
                max_seen = max(max_seen, int(m.group(1)))

        cache_script = state.project_dir / "scripts" / "cache.py"
        if not cache_script.exists():
            if max_seen > 0:
                raise DependencyMissing("cache.py not found — cannot check counter drift")
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
        try:
            r = subprocess.run(
                [sys.executable, str(state.migration_runner_path),
                 "--scan-drift", "--project-dir", str(state.project_dir)],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                drift_data = json.loads(r.stdout)
                drift_findings = drift_data if isinstance(drift_data, list) else drift_data.get("findings", [])
                for df in drift_findings:
                    findings.append(Finding(
                        id=f"migration-currency:schema-drift:{df.get('file', 'unknown')}",
                        category="migration_currency",
                        severity="warning",
                        summary="A state file needs to be upgraded to the current schema",
                        detail=f"Schema drift: {df.get('message', str(df))}",
                        file_paths=[str(df.get("file", ""))],
                        fix_type="prompted",
                        fix_recipe={"action": "prompt", "type": "migration",
                                    "script": "runner.py", "args": []},
                    ))
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            pass

    backlog_dir = state.product_base / "backlog"
    if backlog_dir.is_dir():
        old_prefixes = {"STORY-", "BUG-", "DEBT-", "CHORE-"}
        old_files = []
        for p in backlog_dir.rglob("*.md"):
            if any(p.name.startswith(pfx) for pfx in old_prefixes):
                old_files.append(p)
        if old_files:
            findings.append(Finding(
                id="migration-currency:taxonomy-drift:old-prefixes",
                category="migration_currency",
                severity="warning",
                summary=f"{len(old_files)} files still use old naming conventions",
                detail=f"taxonomy-drift: found {', '.join(p.name for p in old_files[:5])}",
                file_paths=[str(p) for p in old_files[:5]],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "migration",
                            "script": "migrate_taxonomy.py", "args": []},
            ))

    orphan_script = state.project_dir / "scripts" / "migrate" / "migrate-v3-to-v4.py"
    if orphan_script.exists():
        try:
            r = subprocess.run(
                [sys.executable, str(orphan_script),
                 "scan-orphans", "--project-dir", str(state.project_dir)],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                orphan_data = json.loads(r.stdout)
                orphans = orphan_data.get("orphans", [])
                if orphans:
                    findings.append(Finding(
                        id="migration-currency:orphans:scan",
                        category="migration_currency",
                        severity="warning",
                        summary=f"{len(orphans)} files may have been missed during migration",
                        detail=f"orphan-scan: {', '.join(o.get('file', '') for o in orphans[:5])}",
                        file_paths=[o.get("file", "") for o in orphans[:5]],
                        fix_type="prompted",
                        fix_recipe={"action": "prompt", "type": "migration",
                                    "script": "migrate-v3-to-v4.py", "args": ["scan-orphans"]},
                    ))
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            pass

    return findings


def check_config_compat(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []

    _text_sources: list[tuple[str, str]] = []
    if state.claude_md_project:
        _text_sources.append(("CLAUDE.md", state.claude_md_project))
    if state.claude_md_global:
        _text_sources.append(("~/.claude/CLAUDE.md", state.claude_md_global))
    for name, content in state.rules_files.items():
        _text_sources.append((f"rules/{name}", content))

    _settings_sources: list[tuple[str, dict]] = []
    if state.settings_global:
        _settings_sources.append(("~/.claude/settings.json", state.settings_global))
    if state.settings_local:
        _settings_sources.append((".claude/settings.local.json", state.settings_local))

    for sname, sdata in _settings_sources:
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
                                    "file": sname, "line": 0,
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
                                            "file": sname, "line": 0,
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
                                            "file": sname, "line": 0,
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

    def _scan_text(code: str, patterns: list[str], source: str) -> list[str]:
        matched = []
        lower = source.lower()
        if "rules/sweetclaude/" in lower or "rules\\sweetclaude\\" in lower:
            return []
        text_lower = code.lower()
        for pat in patterns:
            if pat.lower() in text_lower:
                matched.append(pat)
        return matched

    for src_name, src_content in _text_sources:
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
                            "file": src_name, "line": 0,
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
                                "file": src_name, "line": 0,
                                "options": ["adopt", "keep", "both"]}
                    if sev != "info" else {},
                ))

    return findings


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

    valid_statuses = {"new", "active", "in_progress", "done", "abandoned",
                      "blocked", "deferred", "backlog", "cancelled", "superseded"}
    valid_types = {"story", "bug", "bug-fix", "debt", "tech-debt", "chore",
                   "epic", "release", "spike", "enhancement", "feature",
                   "net-new-feature", "milestone"}

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
                    findings.append(Finding(
                        id=f"file-diagnostics:duplicate-id:{item_id}",
                        category="file_diagnostics",
                        severity="error",
                        summary=f"ID {item_id} is used by multiple files",
                        detail=f"duplicate-id: {item_id} in {p} and {seen_ids[item_id]}",
                        file_paths=[str(p), str(seen_ids[item_id])],
                        fix_type="prompted",
                        fix_recipe={"action": "prompt", "type": "config_conflict",
                                    "file": str(p), "line": 0, "options": []},
                    ))
                else:
                    seen_ids[item_id] = p
            else:
                findings.append(Finding(
                    id=f"file-diagnostics:missing-field-id:{p.name}",
                    category="file_diagnostics",
                    severity="warning",
                    summary=f"{p.name} has no ID in its frontmatter",
                    detail=f"missing-field:id in {p}",
                    file_paths=[str(p)],
                    fix_type="report-only",
                    fix_recipe={},
                ))

            if not fm.get("title"):
                findings.append(Finding(
                    id=f"file-diagnostics:missing-field-title:{p.name}",
                    category="file_diagnostics",
                    severity="warning",
                    summary=f"{p.name} has no title in its frontmatter",
                    detail=f"missing-field:title in {p}",
                    file_paths=[str(p)],
                    fix_type="report-only",
                    fix_recipe={},
                ))

            if not fm.get("type"):
                findings.append(Finding(
                    id=f"file-diagnostics:missing-field-type:{p.name}",
                    category="file_diagnostics",
                    severity="warning",
                    summary=f"{p.name} has no type set",
                    detail=f"missing-field:type in {p}",
                    file_paths=[str(p)],
                    fix_type="prompted",
                    fix_recipe={"action": "prompt", "type": "config_conflict",
                                "file": str(p), "line": 0,
                                "options": list(valid_types)},
                ))

            if not fm.get("status"):
                findings.append(Finding(
                    id=f"file-diagnostics:missing-field-status:{p.name}",
                    category="file_diagnostics",
                    severity="warning",
                    summary=f"{p.name} has no status set",
                    detail=f"missing-field:status in {p}",
                    file_paths=[str(p)],
                    fix_type="prompted",
                    fix_recipe={"action": "prompt", "type": "config_conflict",
                                "file": str(p), "line": 0,
                                "options": list(valid_statuses)},
                ))

            status_raw = str(fm.get("status", "")).lower().strip().strip('"')
            status = status_raw.split("(")[0].split("—")[0].strip()
            if status and status not in valid_statuses:
                findings.append(Finding(
                    id=f"file-diagnostics:unknown-status:{p.name}",
                    category="file_diagnostics",
                    severity="warning",
                    summary=f"{p.name} has an unrecognized status: {status}",
                    detail=f"unknown-status:{status} in {p}",
                    file_paths=[str(p)],
                    fix_type="prompted",
                    fix_recipe={"action": "prompt", "type": "config_conflict",
                                "file": str(p), "line": 0, "options": list(valid_statuses)},
                ))

            item_type = str(fm.get("type", "")).lower()
            if item_type and item_type not in valid_types:
                findings.append(Finding(
                    id=f"file-diagnostics:unknown-type:{p.name}",
                    category="file_diagnostics",
                    severity="warning",
                    summary=f"{p.name} has an unrecognized type: {item_type}",
                    detail=f"unknown-type:{item_type} in {p}",
                    file_paths=[str(p)],
                    fix_type="prompted",
                    fix_recipe={"action": "prompt", "type": "config_conflict",
                                "file": str(p), "line": 0, "options": list(valid_types)},
                ))

    return findings


def check_onboarding_state(state: ProjectState) -> list[Finding]:
    findings: list[Finding] = []
    skills_path = state.project_dir / ".sweetclaude" / "state" / "skills.yaml"

    if state.skills_yaml is None:
        if skills_path.parent.is_dir():
            findings.append(Finding(
                id="onboarding-state:missing:skills.yaml",
                category="onboarding_state",
                severity="info",
                summary="Skills configuration hasn't been set up yet",
                detail=f"skills.yaml missing at {skills_path}",
                file_paths=[str(skills_path)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "bootstrap",
                            "script": "generate-session-state.sh"},
            ))
    elif state.skills_yaml:
        schema = state.skills_yaml.get("schema_version")
        if schema is not None and schema < 2:
            findings.append(Finding(
                id="onboarding-state:schema-v1:skills.yaml",
                category="onboarding_state",
                severity="warning",
                summary="Skills file needs upgrading to the current format",
                detail=f"skills.yaml schema_version={schema}, expected >=2",
                file_paths=[str(skills_path)],
                fix_type="prompted",
                fix_recipe={"action": "prompt", "type": "bootstrap",
                            "script": "generate-session-state.sh"},
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
        if sdata:
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


CHECKS: dict[str, Callable[[ProjectState], list[Finding]]] = {
    "state_integrity":    check_state_integrity,
    "hook_health":        check_hook_health,
    "storage_lint":       check_storage_lint,
    "migration_currency": check_migration_currency,
    "config_compat":      check_config_compat,
    "file_diagnostics":   check_file_diagnostics,
    "onboarding_state":   check_onboarding_state,
    "env_wiring":         check_env_wiring,
}


# ---------------------------------------------------------------------------
# Project state builder
# ---------------------------------------------------------------------------

def _read_yaml(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError):
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
    for _key, entries in (data.get("plugins") or {}).items():
        if "sweetclaude" in _key.lower() and entries:
            return entries[0].get("version")
    return None


def _find_migration_runner(project_dir: Path) -> Path | None:
    candidate = project_dir / "scripts" / "migrations" / "runner.py"
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
                    rules_files[f.name] = content

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
            sorted((project_dir / "hooks").glob("*.sh"))
            if (project_dir / "hooks").is_dir()
            else []
        ),
        hook_manifest=_read_json(project_dir / "hooks" / "hooks-manifest.json"),
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


def auto_cleanup_suppressions(
    project_dir: Path, current_finding_ids: set[str]
) -> set[str]:
    entries = load_suppressions(project_dir)
    if not entries:
        return set()
    resolved = [e for e in entries if e.get("finding_id") not in current_finding_ids]
    remaining = [e for e in entries if e.get("finding_id") in current_finding_ids]
    if resolved:
        save_suppressions(project_dir, remaining)
    return {e["finding_id"] for e in resolved}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def _scan(project_state: ProjectState) -> dict:
    skipped: list[dict] = []
    all_findings: list[Finding] = []

    for name, fn in CHECKS.items():
        try:
            all_findings.extend(fn(project_state))
        except DependencyMissing as e:
            skipped.append({"category": name, "reason": str(e)})

    all_finding_ids = {f.id for f in all_findings}
    suppressed_ids = {s.get("finding_id") for s in project_state.suppressions if s.get("finding_id")}
    resolved_ids = auto_cleanup_suppressions(
        project_state.project_dir, all_finding_ids
    )

    for f in all_findings:
        if f.id in resolved_ids:
            f.previously_suppressed = True

    active = [f for f in all_findings if f.id not in suppressed_ids]

    return {
        "findings": [asdict(f) for f in active],
        "skipped_categories": skipped,
        "suppressions_resolved": sorted(resolved_ids),
        "project_state_summary": build_state_summary(project_state),
    }


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
        dest.write_text(diff_text)


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


def _apply_transform(content: bytes, recipe: dict, project_dir: Path) -> bytes:
    action = recipe["action"]

    if action == "write_field":
        text = content.decode("utf-8")
        data = yaml.safe_load(text) or {}
        data[recipe["key"]] = recipe["value"]
        return yaml.safe_dump(data, default_flow_style=False).encode("utf-8")

    if action == "delete_file":
        return b""

    if action == "create_dir":
        return b""

    if action == "rebuild_cache":
        return content

    if action == "run_script":
        return content

    raise ValueError(f"Unknown recipe action: {action}")


def _check_precondition(recipe: dict, content: bytes, file_path: Path) -> bool:
    """Return True if the fix is already applied (skip)."""
    action = recipe["action"]

    if action == "write_field":
        try:
            data = yaml.safe_load(content.decode("utf-8")) or {}
            return data.get(recipe["key"]) == recipe["value"]
        except (yaml.YAMLError, UnicodeDecodeError):
            return False

    if action == "delete_file":
        return not file_path.exists()

    if action == "create_dir":
        target = Path(recipe["path"])
        return target.is_dir()

    return False


def execute_recipe(
    project_dir: Path, recipe: dict, archive_path: Path
) -> RecipeResult:
    action = recipe["action"]

    if action == "run_script":
        cmd = recipe.get("cmd", [])
        if len(cmd) < 2:
            raise ValueError("run_script recipe must have cmd with >= 2 elements")
        script_name = Path(cmd[1]).name
        if script_name not in RUN_SCRIPT_ALLOWLIST:
            raise ValueError(
                f"Script '{script_name}' not in allowlist: {RUN_SCRIPT_ALLOWLIST}"
            )
        result = subprocess.run(
            cmd + recipe.get("args", []),
            cwd=project_dir, capture_output=True, timeout=30,
        )
        return RecipeResult(
            finding_id="",
            before_hash="",
            after_hash=None,
            backup_path=None,
            success=result.returncode == 0,
            error=result.stderr.decode() if result.returncode != 0 else None,
        )

    if action == "rebuild_cache":
        cache_script = project_dir / "scripts" / "cache.py"
        if not cache_script.exists():
            raise DependencyMissing("cache.py not found")
        result = subprocess.run(
            [sys.executable, str(cache_script), "--project-dir", str(project_dir), "--rebuild"],
            cwd=project_dir, capture_output=True, timeout=30,
        )
        return RecipeResult(
            finding_id="",
            before_hash="",
            after_hash=None,
            backup_path=None,
            success=result.returncode == 0,
            error=result.stderr.decode() if result.returncode != 0 else None,
        )

    if action == "create_dir":
        target = Path(recipe["path"])
        if not target.is_absolute():
            target = project_dir / target
        if _check_precondition(recipe, b"", target):
            h = _hash_bytes(b"")
            return RecipeResult("", h, h, None, True)
        target.mkdir(parents=True, exist_ok=True)
        return RecipeResult("", _hash_bytes(b""), _hash_bytes(b""), None, True)

    file_key = recipe.get("file", "")
    file_path = Path(file_key)
    if not file_path.is_absolute():
        file_path = project_dir / file_path

    content = file_path.read_bytes() if file_path.exists() else b""

    if _check_precondition(recipe, content, file_path):
        h = _hash_bytes(content)
        return RecipeResult("", h, h, None, True)

    before_hash = backup_content(archive_path, file_path, content)

    if action == "delete_file":
        if file_path.exists():
            file_path.unlink()
        write_diff(archive_path, file_path, content, b"")
        return RecipeResult(
            "", before_hash, _hash_bytes(b""),
            archive_path / "before" / _sanitize_path(str(file_path)), True,
        )

    new_content = _apply_transform(content, recipe, project_dir)
    _atomic_write(file_path, new_content)
    after_hash = _hash_bytes(new_content)
    write_diff(archive_path, file_path, content, new_content)
    return RecipeResult(
        "", before_hash, after_hash,
        archive_path / "before" / _sanitize_path(str(file_path)), True,
    )


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
            actions.append({
                "action": "auto-fix",
                "finding_id": f["id"],
                "category": f["category"],
                "description": f["summary"],
                "file_path": recipe.get("file", ""),
                "before_hash": result.before_hash,
                "after_hash": result.after_hash,
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

    manifest = {
        "timestamp": _now_iso(),
        "version": _resolve_installed_version() or "unknown",
        "safety_branch": safety_branch,
        "actions": all_actions,
        "post_fix_findings": [],
        "summary": {
            "auto_fixed": auto_fixed,
            "user_fixed": user_fixed,
            "skipped": skipped,
            "failed": errors,
        },
    }
    write_manifest(archive_path, manifest)

    findings_summary = [
        {"id": f["id"], "severity": f["severity"], "summary": f["summary"]}
        for f in (scan_findings or [])
    ]

    last_run = {
        "timestamp": manifest["timestamp"],
        "version": manifest["version"],
        "summary": manifest["summary"],
        "findings": findings_summary,
        "menu_preference": menu_preference,
    }
    last_run_path = project_dir / ".sweetclaude" / "state" / "last-doctor-run.json"
    last_run_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = last_run_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(last_run, indent=2))
    os.replace(tmp, last_run_path)

    return {"path": str(last_run_path)}


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

    _add("scan")

    _add("create-archive")

    p_fix = _add("auto-fix")
    p_fix.add_argument("--archive-dir", required=True, type=Path)
    p_fix.add_argument("--include-prompted", action="store_true", default=False)

    p_rescan = _add("post-fix-rescan")
    p_rescan.add_argument("--categories", required=True)

    p_record = sub.add_parser("record-action")
    p_record.add_argument("--archive-dir", required=True, type=Path)

    _add("dry-run")

    p_persist = _add("persist")
    p_persist.add_argument("--archive-dir", required=True, type=Path)
    p_persist.add_argument("--menu-preference", default=None)
    p_persist.add_argument("--safety-branch", default=None)

    _add("prune-archives")

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
            _emit(_scan(state))

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

        elif args.cmd == "prune-archives":
            pruned = prune_archives(args.project_dir.resolve())
            _emit({"pruned": pruned})

    except Exception as e:
        print(json.dumps({"error": type(e).__name__, "message": str(e)}), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
