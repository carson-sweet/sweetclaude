# SPDX-License-Identifier: AGPL-3.0-or-later
"""ISSUE-241: beta channel retirement.

The beta channel is retired (decision log #35/#36): the manifest marks it
retired, plugin-state recognizes retired-channel installs and routes them to
a front-door stop carrying the one-time switch to stable, channel
classification reflects the post-promotion model (4.x default is stable,
3.x is legacy), the release gate refuses retired-channel releases, and CI no
longer targets beta-4.x. The stale-beta guard machinery survives — it is
generalized, not gutted.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "maintenance"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import capability_manifest as cm

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "plugin_state", REPO_ROOT / "scripts" / "maintenance" / "plugin-state.py"
)
plugin_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin_state)

_gate_spec = importlib.util.spec_from_file_location(
    "release_gate", REPO_ROOT / "scripts" / "release_gate.py"
)
release_gate = importlib.util.module_from_spec(_gate_spec)
_gate_spec.loader.exec_module(release_gate)


SWITCH_COMMANDS = [
    "/plugin marketplace add carson-sweet/sweetclaude@main",
    "/plugin install sweetclaude@sweetclaude-stable",
    "/plugin marketplace remove sweetclaude-beta",
]


def _write_installed(home: Path, data: dict) -> None:
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _install_dir(home: Path, *parts: str) -> str:
    path = home.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _entry(home: Path, key: str, version: str) -> dict:
    install = _install_dir(home, ".claude", "plugins", "cache", key.split("@")[-1], "sweetclaude", version)
    return {
        key: [{
            "scope": "user",
            "installPath": install,
            "version": version,
            "gitCommitSha": "abc1234",
            "lastUpdated": "2026-08-01T00:00:00Z",
        }]
    }


class TestManifestRetirement:
    def test_beta_channel_is_marked_retired(self):
        manifest = cm.load_manifest()
        assert manifest["channels"]["beta"].get("retired") is True

    def test_channel_retired_accessor(self):
        assert cm.channel_retired("beta") is True
        assert cm.channel_retired("stable") is False
        assert cm.channel_retired("legacy") is False

    def test_retired_channel_names_a_target_channel(self):
        manifest = cm.load_manifest()
        target = manifest["channels"]["beta"].get("retirement_target_channel")
        assert target == "stable"
        assert target in manifest["channels"]

    def test_stale_beta_minimum_survives_retirement(self):
        # The guard is generalized, not gutted: minimum_safe_version stays.
        assert cm.minimum_safe_version("beta") == "4.1.9-beta"


class TestChannelClassification:
    def test_beta_marketplace_is_beta(self):
        assert plugin_state._channel("sweetclaude@sweetclaude-beta", {"version": "4.5.0-beta"}) == "beta"

    def test_stable_marketplace_is_stable(self):
        assert plugin_state._channel("sweetclaude@sweetclaude-stable", {"version": "4.5.1"}) == "stable"

    def test_legacy_marketplace_is_legacy(self):
        assert plugin_state._channel("sweetclaude@sweetclaude-legacy", {"version": "3.68.6"}) == "legacy"

    def test_bare_marketplace_prerelease_is_beta(self):
        assert plugin_state._channel("sweetclaude@sweetclaude", {"version": "4.1.2-beta"}) == "beta"

    def test_bare_marketplace_4x_release_is_stable(self):
        # Post-promotion: a non-prerelease 4.x install defaults to stable.
        assert plugin_state._channel("sweetclaude@sweetclaude", {"version": "4.5.1"}) == "stable"

    def test_bare_marketplace_5x_release_is_stable(self):
        assert plugin_state._channel("sweetclaude@sweetclaude", {"version": "5.0.0"}) == "stable"

    def test_bare_marketplace_3x_is_legacy(self):
        assert plugin_state._channel("sweetclaude@sweetclaude", {"version": "3.68.6"}) == "legacy"


class TestInspectRetiredChannel:
    def test_beta_install_is_flagged_retired_with_switch_commands(self, tmp_path):
        _write_installed(tmp_path, {"version": 2, "plugins": _entry(tmp_path, "sweetclaude@sweetclaude-beta", "4.5.1-beta")})
        result = plugin_state.inspect_state(tmp_path, None, None)
        assert result["ok"] is True
        assert result["channel"] == "beta"
        assert result["channel_retired"] is True
        assert result["retirement_target_channel"] == "stable"
        for command in SWITCH_COMMANDS:
            assert command in result["retirement_switch_commands"]

    def test_current_beta_is_retired_even_when_not_stale(self, tmp_path):
        # Retirement supersedes staleness: a beta above minimum_safe_version
        # still gets the front-door stop.
        _write_installed(tmp_path, {"version": 2, "plugins": _entry(tmp_path, "sweetclaude@sweetclaude-beta", "4.5.1-beta")})
        result = plugin_state.inspect_state(tmp_path, None, None)
        assert result["stale_beta_install"] is False
        assert result["channel_retired"] is True

    def test_stale_beta_guard_still_fires_for_old_betas(self, tmp_path):
        _write_installed(tmp_path, {"version": 2, "plugins": _entry(tmp_path, "sweetclaude@sweetclaude-beta", "4.1.2-beta")})
        result = plugin_state.inspect_state(tmp_path, None, None)
        assert result["stale_beta_install"] is True
        assert result["channel_retired"] is True

    def test_stable_install_is_not_retired(self, tmp_path):
        _write_installed(tmp_path, {"version": 2, "plugins": _entry(tmp_path, "sweetclaude@sweetclaude-stable", "4.5.1")})
        result = plugin_state.inspect_state(tmp_path, None, None)
        assert result["channel"] == "stable"
        assert result["channel_retired"] is False
        assert result["retirement_switch_commands"] == []

    def test_legacy_install_is_not_retired(self, tmp_path):
        _write_installed(tmp_path, {"version": 2, "plugins": _entry(tmp_path, "sweetclaude@sweetclaude-legacy", "3.68.6")})
        result = plugin_state.inspect_state(tmp_path, None, None)
        assert result["channel"] == "legacy"
        assert result["expected_ref"] == "stable-3.x"
        assert result["channel_retired"] is False

    def test_fail_closed_state_treats_beta_as_retired(self, tmp_path):
        _write_installed(tmp_path, {"version": 2, "plugins": _entry(tmp_path, "sweetclaude@sweetclaude-beta", "4.5.1-beta")})
        result = plugin_state._fail_closed_shell_state(tmp_path, None, None, "boom")
        assert result["channel_retired"] is True


class TestShellEmission:
    def test_shell_emits_channel_retired(self, tmp_path, capsys):
        _write_installed(tmp_path, {"version": 2, "plugins": _entry(tmp_path, "sweetclaude@sweetclaude-beta", "4.5.1-beta")})
        result = plugin_state.inspect_state(tmp_path, None, None)
        plugin_state._emit_shell(result)
        out = capsys.readouterr().out
        assert "SC_PLUGIN_CHANNEL_RETIRED='true'" in out

    def test_preflight_exports_channel_retired(self):
        text = (REPO_ROOT / "scripts" / "preflight.sh").read_text(encoding="utf-8")
        assert "SC_PLUGIN_CHANNEL_RETIRED" in text


class TestReleaseGateRefusesRetiredChannel:
    def test_beta_release_is_refused(self):
        with pytest.raises(ValueError, match="retired"):
            release_gate._validate_channel("4.6.0-beta", "beta", "beta-4.x")

    def test_stable_release_still_allowed(self):
        release_gate._validate_channel("5.0.0", "stable", "main")

    def test_stable_release_rejects_previous_major(self):
        with pytest.raises(ValueError, match="stable releases must be 5.x"):
            release_gate._validate_channel("4.6.0", "stable", "main")


class TestCiRetargeted:
    def test_pr_suite_no_longer_targets_beta_branch(self):
        text = (REPO_ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
        assert "beta-4.x" not in text

    def test_release_workflow_does_not_route_tags_to_beta_branch(self):
        text = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        assert "branch=beta-4.x" not in text

    def test_bump_version_guidance_names_live_channels_only(self):
        # bump-version.sh is a local-only helper (gitignored, absent on CI).
        script = REPO_ROOT / "scripts" / "bump-version.sh"
        if not script.exists():
            pytest.skip("bump-version.sh is a local-only helper, not distributed")
        assert "beta-4.x" not in script.read_text(encoding="utf-8")


class TestFrontDoorStops:
    """The retired-channel stop is grep-anchored in the front-door skills,
    like the recovery contract in skill-library/configure/update/SKILL.md."""

    # bootstrap and doctor consume preflight.sh shell vars; update consumes
    # update.py preflight JSON fields.
    @pytest.mark.parametrize(
        ("skill", "anchor"),
        [
            ("bootstrap", "SC_PLUGIN_CHANNEL_RETIRED"),
            ("doctor", "SC_PLUGIN_CHANNEL_RETIRED"),
            ("update", "`channel_retired`"),
        ],
    )
    def test_skill_carries_retired_channel_stop(self, skill, anchor):
        category = {"bootstrap": None, "doctor": "configure", "update": "configure"}[skill]
        root = REPO_ROOT / "skills" if category is None else REPO_ROOT / "skill-library" / category
        text = (root / skill / "SKILL.md").read_text(encoding="utf-8")
        assert anchor in text, f"{skill} missing retired-channel stop"
        assert "SweetClaude channel retired." in text, f"{skill} missing retired stop heading"
        for command in SWITCH_COMMANDS:
            assert command in text, f"{skill} missing switch command: {command}"
