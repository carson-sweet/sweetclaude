"""ISSUE-244: beta-channel users must be nudged to the stable channel once a
stable release of their major exists. The stale-beta guard is untouched — this
is a pure advisory helper.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import update as update_mod


def _notice(channel, installed_version, stable_tags):
    return update_mod.beta_stable_migration_notice(
        channel=channel,
        installed_version=installed_version,
        stable_tags=stable_tags,
    )


def test_beta_user_with_stable_release_gets_notice():
    n = _notice("beta", "4.5.0-beta", ["v4.5.0", "v4.4.1-beta", "v3.68.6"])
    assert n is not None
    assert "sweetclaude-stable" in n or "@main" in n, n
    assert "4.5.0" in n


def test_stable_channel_user_gets_no_notice():
    assert _notice("stable", "4.5.0", ["v4.5.0"]) is None


def test_beta_user_without_stable_release_gets_no_notice():
    # only prereleases and an older-major stable exist
    assert _notice("beta", "4.5.0-beta", ["v4.4.1-beta", "v3.68.6"]) is None


def test_beta_user_older_stable_major_only_gets_no_notice():
    # a stable exists but only for major 3 (legacy), not the user's major 4
    assert _notice("beta", "4.5.0-beta", ["v3.68.6", "v4.4.0-beta"]) is None


def test_notice_names_the_one_time_switch():
    n = _notice("beta", "4.5.0-beta", ["v4.5.0"])
    assert n is not None
    low = n.lower()
    assert "marketplace" in low and "install" in low, n
    assert "beta" in low  # explains the channel being left/retired


def test_update_skill_surfaces_beta_migration():
    skill = (Path(__file__).parents[1] / "skills" / "update" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "beta_stable_migration_notice" in skill or "beta-migration" in skill, (
        "update SKILL.md must surface the beta->stable migration notice"
    )
