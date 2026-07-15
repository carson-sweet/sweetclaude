#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SweetClaude update orchestrator.

Single-process script with subcommands. Each subcommand does one thing,
takes explicit arguments, and returns JSON on stdout. The SKILL.md calls
subcommands in sequence, reads their output, and presents results to the user.

Subcommands:
    preflight       Resolve plugin install state and clear decline if needed
    check           Clone latest from GitHub and compare to installed version
    safety-check    Identify removed skills with live project artifacts
    major-gate      Detect v3 → v4 major version boundary
    sync            Copy source to all installed locations
    metadata        Update installed_plugins.json and project version
    project-check   Scan project for drift, orphans, legacy taxonomy
    report          Generate the success report text
    cleanup         Remove temp directory
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _sanitize_for_json(data: dict) -> dict:
    """Replace raw newlines in string values so output survives echo in zsh."""
    out = {}
    for k, v in data.items():
        if isinstance(v, str):
            out[k] = v.replace("\n", " | ").replace("\r", "")
        elif isinstance(v, dict):
            out[k] = _sanitize_for_json(v)
        elif isinstance(v, list):
            out[k] = [
                _sanitize_for_json(i) if isinstance(i, dict)
                else i.replace("\n", " | ").replace("\r", "") if isinstance(i, str)
                else i
                for i in v
            ]
        else:
            out[k] = v
    return out


def _json_out(data: dict) -> None:
    json.dump(_sanitize_for_json(data), sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            cmd, returncode=127, stdout="", stderr=f"{cmd[0]}: command not found",
        )


def _major_version(v: str) -> int:
    m = re.match(r"^v?(\d+)", str(v or ""))
    return int(m.group(1)) if m else 0


def _semver_tuple(v):
    """(major, minor, patch) for a version string, or None if unparseable."""
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(v or ""))
    return tuple(int(p) for p in m.groups()) if m else None


def _is_prerelease(v) -> bool:
    return bool(re.search(r"-(?:beta|rc|alpha)", str(v or ""), re.IGNORECASE))


def beta_stable_migration_notice(*, channel, installed_version, stable_tags):
    """Advisory-only (ISSUE-244): when a beta-channel user's major now has a
    published stable release, return a notice guiding the one-time switch to the
    stable channel. Returns None otherwise. Does not touch the stale-beta guard.

    stable_tags: iterable of published release tags (e.g. from git ls-remote).
    """
    if channel != "beta":
        return None
    installed_major = _major_version(installed_version)
    stable_versions = []
    for tag in stable_tags or []:
        t = str(tag).strip()
        if not t or _is_prerelease(t):
            continue
        if _major_version(t) >= installed_major and _semver_tuple(t):
            stable_versions.append(t.lstrip("v"))
    if not stable_versions:
        return None
    latest = max(stable_versions, key=lambda s: _semver_tuple(s))
    return (
        f"SweetClaude {latest} is available on the stable channel.\n"
        "You are on the beta channel, which is being retired. Your installed "
        "code already matches the stable release, but future stable updates "
        "will not reach the beta channel.\n\n"
        "One-time switch to stable — run in this order so you are never "
        "double-installed (both channels' skills and hooks load at once):\n"
        "  /plugin marketplace add carson-sweet/sweetclaude@main\n"
        "  /plugin install sweetclaude@sweetclaude-stable\n"
        "  /plugin marketplace remove sweetclaude-beta\n\n"
        "(Removing the beta marketplace uninstalls its plugin, so add and "
        "install stable first.) Then run /sweetclaude:update on the stable "
        "channel; your project data migrates normally."
    )


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def cmd_preflight(args: argparse.Namespace) -> int:
    """Resolve plugin install state. Wraps preflight.sh + plugin-state.py."""
    project_dir = str(args.project_dir or os.getcwd())
    plugin_root = args.plugin_root or os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    script_dir = Path(__file__).resolve().parent

    result: dict = {"ok": False}

    # Version-dir heal (inline the logic from preflight.sh step 1)
    result["version_dir_healed"] = False
    plugins_json = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if plugins_json.exists():
        try:
            data = json.loads(plugins_json.read_text(encoding="utf-8"))
            for k, versions in data.get("plugins", {}).items():
                if "sweetclaude" not in k.lower():
                    continue
                for entry in versions:
                    if entry.get("scope") != "user":
                        continue
                    install_path = entry.get("installPath", "").rstrip("/")
                    version = entry.get("version", "")
                    if not install_path or not version or not os.path.isdir(install_path):
                        continue
                    parent = os.path.dirname(install_path)
                    version_dir = os.path.join(parent, version)
                    if version_dir == install_path or os.path.isdir(version_dir):
                        continue
                    os.makedirs(version_dir, exist_ok=True)
                    ret = _run(["rsync", "-a", install_path + "/", version_dir + "/"])
                    if ret.returncode == 0:
                        entry["installPath"] = version_dir
                        tmp = tempfile.NamedTemporaryFile(
                            "w", dir=str(plugins_json.parent),
                            suffix=".tmp", delete=False, encoding="utf-8",
                        )
                        json.dump(data, tmp, indent=2)
                        tmp.close()
                        os.replace(tmp.name, str(plugins_json))
                        result["version_dir_healed"] = True
        except Exception:
            pass

    # Resolve runner path
    runner_path = script_dir / "migrations" / "runner.py"
    result["runner"] = str(runner_path) if runner_path.exists() else ""

    # Plugin state via plugin-state.py
    plugin_state_script = script_dir / "maintenance" / "plugin-state.py"
    if plugin_state_script.exists():
        cmd = [
            sys.executable, str(plugin_state_script),
            "--project-dir", project_dir,
            "inspect",
        ]
        if plugin_root:
            cmd.extend(["--current-root", plugin_root])
        ps = _run(cmd)
        if ps.returncode == 0:
            try:
                state = json.loads(ps.stdout)
                result.update(state)
            except json.JSONDecodeError:
                pass

    # Clear decline if requested
    result["decline_cleared"] = False
    if args.from_update:
        sc_yaml = Path(project_dir) / ".sweetclaude" / "state" / "sweetclaude.yaml"
        clear_script = script_dir / "maintenance" / "clear-decline.py"
        if sc_yaml.exists() and clear_script.exists():
            cd = _run([sys.executable, str(clear_script), project_dir])
            if "cleared" in cd.stdout:
                result["decline_cleared"] = True

    if not result.get("ok"):
        result["ok"] = result.get("plugin_ok", False)

    _json_out(result)
    return 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def _top_changelog_section(source_dir) -> str:
    """Return the first release section of CHANGELOG.md (heading + body up to
    the next section) as fallback update notes. Empty string if unavailable."""
    try:
        text = Path(source_dir, "CHANGELOG.md").read_text(encoding="utf-8")
    except Exception:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    started = False
    for line in lines:
        if line.startswith("## ["):
            if started:
                break
            started = True
        if started:
            if line.strip() == "---":
                continue
            out.append(line)
    return "\n".join(out).strip()


def cmd_check(args: argparse.Namespace) -> int:
    """Clone latest from GitHub and compare versions."""
    tmpdir = tempfile.mkdtemp(prefix="sweetclaude-update-")
    source_dir = os.path.join(tmpdir, "sweetclaude")
    repo_url = args.repo or "https://github.com/carson-sweet/sweetclaude"
    ref = args.ref

    # Clone
    clone_ok = False
    clone_error = ""
    if shutil.which("gh"):
        owner_repo = repo_url.replace("https://github.com/", "")
        ret = _run(["gh", "repo", "clone", owner_repo, source_dir,
                     "--", "--depth", "1", "--branch", ref])
        if ret.returncode == 0:
            clone_ok = True
        else:
            clone_error = ret.stderr.strip()
    if not clone_ok:
        ret = _run(["git", "clone", "--depth", "1", "--branch", ref, repo_url, source_dir])
        if ret.returncode == 0:
            clone_ok = True
        else:
            clone_error = ret.stderr.strip()

    if not clone_ok:
        auth_error = "auth" in clone_error.lower() or "permission" in clone_error.lower()
        _json_out({
            "ok": False,
            "error": "clone_failed",
            "auth_error": auth_error,
            "detail": clone_error,
            "tmpdir": tmpdir,
        })
        return 1

    # Read source version
    effective_sha = _run(["git", "-C", source_dir, "rev-parse", "HEAD"]).stdout.strip()
    try:
        pkg = json.loads(Path(source_dir, "package.json").read_text(encoding="utf-8"))
        new_version = pkg.get("version", "unknown")
    except Exception:
        new_version = "unknown"

    up_to_date = effective_sha == args.installed_sha

    # Changelog since installed. The clone is shallow (--depth 1), so a
    # git-range log fails whenever the installed commit is not in the shallow
    # tip's history (the common case) — leaving the changelog blank, which
    # reads like an error. Fall back to the top CHANGELOG.md section so the
    # user always gets human-readable notes for the version being offered.
    changelog = ""
    if not up_to_date and args.installed_sha:
        log = _run(["git", "-C", source_dir, "log", "--oneline",
                     f"{args.installed_sha}..{effective_sha}"])
        if log.returncode == 0:
            changelog = log.stdout.strip()
    if not up_to_date and not changelog:
        changelog = _top_changelog_section(source_dir)

    # Diff summary
    diff_summary = {}
    install_path = args.install_path or ""
    plugin_root = args.plugin_root or ""
    if not up_to_date and install_path:
        for name, src_sub, dest in [
            ("skills", "skills", os.path.join(install_path, "skills")),
            ("scripts", "scripts", os.path.join(install_path, "scripts")),
            ("rules", "rules", os.path.join(plugin_root or install_path, "rules")),
            ("hooks", "hooks", os.path.join(plugin_root or install_path, "hooks")),
            ("config", "config", os.path.join(plugin_root or install_path, "config")),
        ]:
            src = os.path.join(source_dir, src_sub)
            if os.path.isdir(src) and os.path.isdir(dest):
                d = _run(["diff", "-rq", src, dest])
                lines = [l for l in d.stdout.strip().splitlines() if l]
                diff_summary[name] = len(lines)
            elif os.path.isdir(src):
                diff_summary[name] = -1  # new directory

    # Detect new skills
    new_skills = []
    if not up_to_date and install_path:
        src_skills = Path(source_dir, "skills")
        dst_skills = Path(install_path, "skills")
        if src_skills.is_dir():
            for d in src_skills.iterdir():
                if d.is_dir() and not (dst_skills / d.name).is_dir():
                    new_skills.append(d.name)

    _json_out({
        "ok": True,
        "up_to_date": up_to_date,
        "source_dir": source_dir,
        "tmpdir": tmpdir,
        "effective_sha": effective_sha,
        "new_version": new_version,
        "changelog": changelog,
        "diff_summary": diff_summary,
        "new_skills": new_skills,
    })
    return 0


# ---------------------------------------------------------------------------
# safety-check
# ---------------------------------------------------------------------------

def cmd_safety_check(args: argparse.Namespace) -> int:
    """Check for removed skills that have live project artifacts."""
    source_dir = args.source
    install_path = args.install_path
    project_dir = str(args.project_dir or os.getcwd())

    sc_dir = Path(project_dir) / ".sweetclaude"
    if not sc_dir.exists():
        _json_out({"ok": True, "removed_skills": [], "has_live_artifacts": False})
        return 0

    # Find removed skills
    removed = []
    src_skills = Path(source_dir, "skills")
    dst_skills = Path(install_path, "skills")
    if dst_skills.is_dir() and src_skills.is_dir():
        for d in dst_skills.iterdir():
            if d.is_dir() and not (src_skills / d.name).is_dir():
                removed.append(d.name)

    if not removed:
        _json_out({"ok": True, "removed_skills": [], "has_live_artifacts": False})
        return 0

    # Resolve product base
    product_base = ".sweetclaude/product"
    ap = Path(project_dir) / ".sweetclaude" / "artifact-privacy.yaml"
    if ap.exists():
        try:
            import yaml
            d = yaml.safe_load(ap.read_text(encoding="utf-8")) or {}
            pb = d.get("categories", {}).get("product", {}).get("base_path", "")
            if pb:
                product_base = pb.rstrip("/")
        except Exception:
            pass

    # Check artifact paths for each removed skill
    artifact_map = {
        "product-milestones": [f"{product_base}/milestones/MS-*.md"],
        "product-parking-lot": [f"{product_base}/backlog/ISSUE-*.md", f"{product_base}/backlog/stories/*.md"],
        "product-backlog": [f"{product_base}/backlog/ISSUE-*.md", f"{product_base}/backlog/stories/*.md"],
        "product-sprint-plan": [f"{product_base}/sprints/*"],
        "user-personas": [".sweetclaude/state/personas.yaml"],
        "product-user-stories": [f"{product_base}/stories/US-*.md"],
        "document-corpus": [".sweetclaude/state/corpus-pipeline.yaml"],
    }

    affected = []
    from glob import glob
    for skill in removed:
        patterns = artifact_map.get(skill, [])
        for pat in patterns:
            full = os.path.join(project_dir, pat)
            matches = glob(full)
            if matches:
                affected.append({
                    "skill": skill,
                    "pattern": pat,
                    "count": len(matches),
                })
                break

    _json_out({
        "ok": True,
        "removed_skills": removed,
        "has_live_artifacts": len(affected) > 0,
        "affected": affected,
    })
    return 0


# ---------------------------------------------------------------------------
# major-gate
# ---------------------------------------------------------------------------

def cmd_major_gate(args: argparse.Namespace) -> int:
    """Detect whether a v3 → v4 major version boundary applies."""
    current = _major_version(args.installed_version)
    incoming = _major_version(args.incoming_version)
    _json_out({
        "ok": True,
        "gate_applies": current == 3 and incoming >= 4,
        "current_major": current,
        "incoming_major": incoming,
    })
    return 0


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

def cmd_sync(args: argparse.Namespace) -> int:
    """Sync source to all installed locations."""
    source = args.source
    install_path = args.install_path
    plugin_root = args.plugin_root or install_path

    errors = []

    def rsync_dir(src: str, dst: str, delete: bool = True) -> bool:
        cmd = ["rsync", "-a"]
        if delete:
            cmd.append("--delete")
        cmd.extend([src.rstrip("/") + "/", dst.rstrip("/") + "/"])
        r = _run(cmd)
        if r.returncode != 0:
            errors.append(f"rsync {src} -> {dst}: {r.stderr.strip()}")
            return False
        return True

    # Skills → install path
    rsync_dir(f"{source}/skills", f"{install_path}/skills")

    # Hooks → install path
    rsync_dir(f"{source}/hooks", f"{install_path}/hooks")

    # Top-level files
    for f in ["CLAUDE.md", "package.json", "LICENSE", "CHANGELOG.md"]:
        src = os.path.join(source, f)
        if os.path.isfile(src):
            try:
                shutil.copy2(src, os.path.join(install_path, f))
            except OSError as exc:
                errors.append(f"copy {src} -> {install_path}/{f}: {exc}")

    # Plugin manifest
    rsync_dir(f"{source}/.claude-plugin", f"{install_path}/.claude-plugin", delete=False)

    # Scripts
    if os.path.isdir(f"{source}/scripts"):
        rsync_dir(f"{source}/scripts", f"{install_path}/scripts")

    # Framework dirs → plugin root (may differ from install path)
    for d in ["rules", "hooks", "config"]:
        src = os.path.join(source, d)
        dst = os.path.join(plugin_root, d)
        if os.path.isdir(src):
            rsync_dir(src, dst)

    # Make hooks executable
    hooks_dir = os.path.join(plugin_root, "hooks")
    if os.path.isdir(hooks_dir):
        for f in os.listdir(hooks_dir):
            if f.endswith(".sh"):
                fp = os.path.join(hooks_dir, f)
                os.chmod(fp, os.stat(fp).st_mode | 0o111)

    # Version-named directory sync
    version_dir = ""
    try:
        pkg = json.loads(Path(source, "package.json").read_text(encoding="utf-8"))
        new_ver = pkg.get("version", "")
    except Exception:
        new_ver = ""

    if new_ver:
        parent = os.path.dirname(install_path)
        vdir = os.path.join(parent, new_ver)
        if vdir != install_path:
            version_dir = vdir
            os.makedirs(vdir, exist_ok=True)
            for d in ["skills", "hooks", "scripts", "rules", "config"]:
                src = os.path.join(source, d)
                if os.path.isdir(src):
                    os.makedirs(os.path.join(vdir, d), exist_ok=True)
                    rsync_dir(src, os.path.join(vdir, d))
            rsync_dir(f"{source}/.claude-plugin", f"{vdir}/.claude-plugin", delete=False)
            for f in ["CLAUDE.md", "package.json", "LICENSE", "CHANGELOG.md"]:
                src_f = os.path.join(source, f)
                if os.path.isfile(src_f):
                    try:
                        shutil.copy2(src_f, os.path.join(vdir, f))
                    except OSError as exc:
                        errors.append(f"copy {src_f} -> {vdir}/{f}: {exc}")

    # Hook reconciliation (ensure-global-hooks.py)
    hook_cleaned = 0
    hook_script = Path(plugin_root) / "scripts" / "maintenance" / "ensure-global-hooks.py"
    if not hook_script.exists():
        hook_script = Path(__file__).resolve().parent / "maintenance" / "ensure-global-hooks.py"
    if hook_script.exists():
        hr = _run([sys.executable, str(hook_script)])
        for line in hr.stdout.splitlines():
            if "cleaned:" in line:
                try:
                    hook_cleaned += int(line.split("cleaned:")[-1].strip().split()[0])
                except (ValueError, IndexError):
                    hook_cleaned += 1

    # Verify sync
    verify_errors = []
    sync_target = version_dir or install_path
    for d in ["skills", "scripts"]:
        src = os.path.join(source, d)
        dst = os.path.join(sync_target, d)
        if os.path.isdir(src):
            v = _run(["diff", "-rq", src, dst])
            if v.stdout.strip():
                verify_errors.append(f"{d}: {v.stdout.strip()}")

    # Check skills-registry.yaml
    registry_ok = os.path.isfile(os.path.join(plugin_root, "config", "skills-registry.yaml"))

    _json_out({
        "ok": len(errors) == 0,
        "errors": errors,
        "version_dir": version_dir,
        "sync_target": sync_target,
        "hook_cleaned": hook_cleaned,
        "verify_errors": verify_errors,
        "registry_ok": registry_ok,
    })
    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------

def cmd_metadata(args: argparse.Namespace) -> int:
    """Update installed_plugins.json and project installed_version."""
    script_dir = Path(__file__).resolve().parent
    plugin_state_script = script_dir / "maintenance" / "plugin-state.py"

    result: dict = {"ok": False}

    # Repair plugin metadata
    if plugin_state_script.exists():
        cmd = [
            sys.executable, str(plugin_state_script),
            "--project-dir", str(args.project_dir or os.getcwd()),
            "repair",
            "--plugin-key", args.plugin_key,
            "--install-path", args.install_path,
            "--version", args.version,
            "--sha", args.sha,
        ]
        ps = _run(cmd)
        try:
            result = json.loads(ps.stdout)
        except json.JSONDecodeError:
            result = {"ok": False, "error": ps.stderr.strip()}

    # Update project installed_version
    project_dir = str(args.project_dir or os.getcwd())
    sc_yaml = Path(project_dir) / ".sweetclaude" / "state" / "sweetclaude.yaml"
    result["project_version_updated"] = False
    if sc_yaml.exists():
        try:
            import yaml
            with open(sc_yaml) as f:
                d = yaml.safe_load(f) or {}
            framework = d.setdefault("framework", {})
            changed = False
            if framework.get("installed_version") != args.version:
                framework["installed_version"] = args.version
                changed = True
            # Reconcile update.available against the just-installed version in
            # the same write. An update consumes/supersedes any previously
            # recorded "available" at or below the new version; leaving it set
            # makes bootstrap offer a downgrade. A genuinely newer available
            # (above installed) is preserved. Not deferred to a health check.
            upd = framework.get("update")
            if isinstance(upd, dict):
                avail = upd.get("available")
                avail_t = _semver_tuple(avail) if isinstance(avail, str) else None
                inst_t = _semver_tuple(args.version)
                if avail_t is not None and inst_t is not None and avail_t <= inst_t:
                    upd["available"] = None
                    changed = True
            if changed:
                tmp = tempfile.NamedTemporaryFile(
                    "w", dir=str(sc_yaml.parent), suffix=".tmp",
                    delete=False, encoding="utf-8",
                )
                yaml.safe_dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
                tmp.close()
                os.replace(tmp.name, str(sc_yaml))
                result["project_version_updated"] = True
        except Exception as exc:
            result["project_version_error"] = str(exc)

    _json_out(result)
    return 0


# ---------------------------------------------------------------------------
# project-check
# ---------------------------------------------------------------------------

def cmd_project_check(args: argparse.Namespace) -> int:
    """Scan project for drift, orphans, legacy taxonomy, bold-format files."""
    project_dir = str(args.project_dir or os.getcwd())
    sc_yaml = Path(project_dir) / ".sweetclaude" / "state" / "sweetclaude.yaml"

    if not sc_yaml.exists():
        _json_out({"ok": True, "skipped": True, "reason": "no_project"})
        return 0

    result: dict = {"ok": True, "skipped": False}

    # Drift detection
    runner = args.runner or ""
    result["drift_count"] = 0
    result["drift_lines"] = []
    if runner and os.path.isfile(runner):
        dr = _run([sys.executable, runner, "--project-dir", project_dir, "--scan-drift"])
        for line in dr.stdout.splitlines():
            if "[DRIFT]" in line:
                result["drift_count"] += 1
                result["drift_lines"].append(line.strip())

    # Orphan scan
    result["orphan_count"] = 0
    result["orphan_output"] = None
    migrate_script = args.migrate_script or ""
    if not migrate_script:
        candidate = Path(__file__).resolve().parent / "migrate" / "migrate-v3-to-v4.py"
        if candidate.exists():
            migrate_script = str(candidate)
    if migrate_script and os.path.isfile(migrate_script):
        orph = _run([sys.executable, migrate_script, "scan-orphans", "--project-dir", project_dir])
        if orph.returncode == 0 and orph.stdout.strip():
            try:
                od = json.loads(orph.stdout)
                result["orphan_count"] = od.get("orphan_count", 0)
                if result["orphan_count"] > 0:
                    result["orphan_output"] = od
            except json.JSONDecodeError:
                pass
    result["migrate_script"] = migrate_script

    # Legacy taxonomy count
    result["old_taxonomy_count"] = 0
    backlog = Path(project_dir) / ".sweetclaude" / "product" / "backlog"
    if backlog.is_dir():
        count = 0
        for prefix in ["BL-", "STORY-", "BUG-", "DEBT-", "CHORE-"]:
            for p in backlog.rglob(f"{prefix}*.md"):
                count += 1
        result["old_taxonomy_count"] = count

    # Bold-format file count
    result["bold_format_count"] = 0
    converter = Path.home() / ".claude" / "scripts" / "sweetclaude" / "format_converter.py"
    if converter.exists():
        bf = _run([sys.executable, str(converter), "--project-dir", project_dir, "--dry-run"])
        if bf.returncode == 0:
            result["bold_format_count"] = bf.stdout.count('"action": "would_convert"')

    _json_out(result)
    return 0


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def cmd_cleanup(args: argparse.Namespace) -> int:
    """Remove temp directory."""
    tmpdir = args.tmpdir
    real_tmpdir = os.path.realpath(tmpdir) if tmpdir else ""
    real_tempbase = os.path.realpath(tempfile.gettempdir())
    if real_tmpdir and os.path.isdir(real_tmpdir) and real_tmpdir.startswith(real_tempbase + "/"):
        shutil.rmtree(real_tmpdir, ignore_errors=True)
        _json_out({"ok": True, "removed": real_tmpdir})
    else:
        _json_out({"ok": False, "error": f"refusing to remove: {tmpdir}"})
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_channel_migration(args: argparse.Namespace) -> int:
    """Advisory beta->stable nudge (ISSUE-244). Queries published stable tags
    and returns a migration notice when the beta user's major has a stable
    release. Never fails the update flow — advisory only."""
    repo_url = args.repo or "https://github.com/carson-sweet/sweetclaude"
    stable_tags: list[str] = []
    ret = _run(["git", "ls-remote", "--tags", repo_url])
    if ret.returncode == 0:
        for line in ret.stdout.splitlines():
            ref = line.split("refs/tags/")[-1].strip() if "refs/tags/" in line else ""
            if ref and not ref.endswith("^{}"):
                stable_tags.append(ref)
    notice = beta_stable_migration_notice(
        channel=args.channel,
        installed_version=args.installed_version,
        stable_tags=stable_tags,
    )
    _json_out({"ok": True, "migrate": notice is not None, "notice": notice})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude update orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # preflight
    p = sub.add_parser("preflight")
    p.add_argument("--project-dir", type=Path, default=None)
    p.add_argument("--plugin-root", default="")
    p.add_argument("--from-update", action="store_true")

    # check
    p = sub.add_parser("check")
    p.add_argument("--ref", required=True)
    p.add_argument("--installed-sha", default="")
    p.add_argument("--repo", default="")
    p.add_argument("--install-path", default="")
    p.add_argument("--plugin-root", default="")

    # safety-check
    p = sub.add_parser("safety-check")
    p.add_argument("--source", required=True)
    p.add_argument("--install-path", required=True)
    p.add_argument("--project-dir", type=Path, default=None)

    # major-gate
    p = sub.add_parser("major-gate")
    p.add_argument("--installed-version", required=True)
    p.add_argument("--incoming-version", required=True)

    # sync
    p = sub.add_parser("sync")
    p.add_argument("--source", required=True)
    p.add_argument("--install-path", required=True)
    p.add_argument("--plugin-root", default="")

    # metadata
    p = sub.add_parser("metadata")
    p.add_argument("--plugin-key", required=True)
    p.add_argument("--install-path", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--project-dir", type=Path, default=None)

    # project-check
    p = sub.add_parser("project-check")
    p.add_argument("--project-dir", type=Path, default=None)
    p.add_argument("--runner", default="")
    p.add_argument("--migrate-script", default="")

    # cleanup
    p = sub.add_parser("cleanup")
    p.add_argument("--tmpdir", required=True)

    # channel-migration (ISSUE-244): advisory beta->stable nudge
    p = sub.add_parser("channel-migration")
    p.add_argument("--channel", required=True)
    p.add_argument("--installed-version", required=True)
    p.add_argument("--repo", default="")

    args = parser.parse_args(argv)

    dispatch = {
        "preflight": cmd_preflight,
        "check": cmd_check,
        "safety-check": cmd_safety_check,
        "major-gate": cmd_major_gate,
        "sync": cmd_sync,
        "metadata": cmd_metadata,
        "project-check": cmd_project_check,
        "cleanup": cmd_cleanup,
        "channel-migration": cmd_channel_migration,
    }

    try:
        return dispatch[args.cmd](args)
    except Exception as exc:
        _json_out({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
