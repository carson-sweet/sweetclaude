"""Upgrade-path docs: 4.x readers only get commands that exist on 4.x until
they restart, 3.x -> stable removes the old sweetclaude-stable marketplace
before adding @main, and the retired-beta switch is the documented fix."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "user-guide"

SC_COMMAND = re.compile(r"/sweetclaude:[A-Za-z][\w-]*")
RESTART = re.compile(r"\brestart", re.IGNORECASE)
PASSAGE_END = r"\n\*\*[A-Z]|\n#{1,6} |\n→|To stay on 3\.x"

MARKETPLACE_UPDATE = "/plugin marketplace update sweetclaude-stable"
PLUGIN_UPDATE = "/plugin update sweetclaude@sweetclaude-stable"
ADD_MAIN = "/plugin marketplace add carson-sweet/sweetclaude@main"
INSTALL_STABLE = "/plugin install sweetclaude@sweetclaude-stable"
REMOVE_OLD_STABLE = "/plugin marketplace remove sweetclaude-stable"
REMOVE_BETA = "/plugin marketplace remove sweetclaude-beta"
BETA_UPDATE = "/plugin update sweetclaude@sweetclaude-beta"


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _passage(rel, start, end=PASSAGE_END):
    text = _read(rel)
    i = text.find(start)
    assert i >= 0, f"{rel}: passage starting {start!r} not found"
    tail = text[i + len(start):]
    m = re.search(end, tail)
    return text[i: i + len(start) + (m.start() if m else len(tail))]


def _positions(passage, literal):
    return [m.start() for m in re.finditer(re.escape(literal) + r"(?![\w@./-])", passage)]


def _changelog_4x_paragraphs():
    section = _passage("CHANGELOG.md", "## [5.0.0]", r"\n## \[")
    paragraphs = [p for p in re.split(r"\n\s*\n", section)
                  if "4.x" in p and "upgrad" in p.lower()]
    assert paragraphs, "CHANGELOG.md [5.0.0]: no paragraph with the 4.x upgrade sentence"
    return paragraphs


FOUR_X_PASSAGES = [
    pytest.param("README.md", lambda: [_passage("README.md", "**From 4.x:**")], True, id="readme-from-4x"),
    pytest.param("CHANGELOG.md", _changelog_4x_paragraphs, True, id="changelog-5.0.0"),
    pytest.param(
        "docs/user-guide/install.md",
        lambda: [_passage("docs/user-guide/install.md", "**Upgrading from 4.x:**")],
        True,
        id="install-upgrading-from-4x",
    ),
    pytest.param(
        "docs/user-guide/upgrading-to-5.md",
        lambda: [_passage("docs/user-guide/upgrading-to-5.md", "## Upgrading from 4.x", r"\n## ")],
        True,
        id="upgrading-to-5",
    ),
    pytest.param(
        "docs/user-guide/migration-and-recovery.md",
        lambda: [_passage("docs/user-guide/migration-and-recovery.md", "## Safe Order", r"\n## ")],
        False,
        id="migration-and-recovery-safe-order",
    ),
    pytest.param(
        "docs/user-guide/v4-migration.md",
        lambda: [_passage("docs/user-guide/v4-migration.md", "## Short Version", r"\n## ")],
        False,
        id="v4-migration-short-version",
    ),
]


UPGRADE_SEQUENCES = [p for p in FOUR_X_PASSAGES if p.values[2]]


class TestAC1FourXReadersGetOnlyPluginCommandsBeforeRestart:
    @pytest.mark.parametrize("rel,get_passages,needs_plugin_steps", FOUR_X_PASSAGES)
    def test_only_plugin_commands_before_restart(self, rel, get_passages, needs_plugin_steps):
        for passage in get_passages():
            restart = RESTART.search(passage)
            assert restart, f"{rel}: 4.x upgrade passage never mentions restarting Claude Code"
            offenders = SC_COMMAND.findall(passage[: restart.start()])
            assert offenders == [], (
                f"{rel}: /sweetclaude: commands given before the restart "
                f"(they do not exist on 4.x): {offenders}"
            )

    @pytest.mark.parametrize("rel,get_passages,needs_plugin_steps", UPGRADE_SEQUENCES)
    def test_plugin_update_steps_come_first(self, rel, get_passages, needs_plugin_steps):
        for passage in get_passages():
            restart = RESTART.search(passage)
            before = passage[: restart.start()] if restart else passage
            market = before.find(MARKETPLACE_UPDATE)
            update = before.find(PLUGIN_UPDATE)
            assert market >= 0, f"{rel}: {MARKETPLACE_UPDATE!r} missing before the restart"
            assert update > market, f"{rel}: {PLUGIN_UPDATE!r} must follow the marketplace update, before the restart"

    def test_4x_update_command_not_recommended_for_moving_to_5x(self):
        pattern = re.compile(r"/sweetclaude:update\b|4\.x update command|4\.x command\b")
        files = [ROOT / "README.md"] + sorted((ROOT / "docs").rglob("*.md"))
        offenders = []
        for f in files:
            for block in re.split(r"\n\s*\n", f.read_text(encoding="utf-8")):
                m = pattern.search(block)
                if m:
                    offenders.append(f"{f.relative_to(ROOT)}: {m.group(0)!r}")
        changelog = _read("CHANGELOG.md")
        current = changelog.split("\n## [4.", 1)[0]
        for block in re.split(r"\n\s*\n", current):
            m = pattern.search(block)
            if m:
                offenders.append(f"CHANGELOG.md (5.x entries): {m.group(0)!r}")
        assert offenders == [], f"4.x /sweetclaude:update recommended for the 5.x move: {offenders}"


THREE_X_PASSAGES = [
    pytest.param("README.md", lambda: _passage("README.md", "**From 3.x:**"), id="readme-from-3x"),
    pytest.param(
        "docs/user-guide/install.md",
        lambda: _passage("docs/user-guide/install.md", "**Upgrading from 3.x:**"),
        id="install-upgrading-from-3x",
    ),
    pytest.param(
        "docs/README.md",
        lambda: _passage("docs/README.md", "To move a 3.x project", r"\n#{1,6} |To stay on 3\.x|Legacy 3\.x uses"),
        id="docs-readme-3x-guidance",
    ),
]


class TestAC2ThreeXToStableRemovesOldMarketplaceFirst:
    @pytest.mark.parametrize("rel,get_passage", THREE_X_PASSAGES)
    def test_removes_old_stable_marketplace_only_before_adding_main(self, rel, get_passage):
        passage = get_passage()
        adds = _positions(passage, ADD_MAIN)
        removes = _positions(passage, REMOVE_OLD_STABLE)
        assert adds, f"{rel}: 3.x -> stable sequence never runs {ADD_MAIN!r}"
        assert removes, (
            f"{rel}: 3.x -> stable sequence never runs {REMOVE_OLD_STABLE!r} "
            "(3.x registered its marketplace as sweetclaude-stable)"
        )
        late = [r for r in removes if r > adds[0]]
        assert late == [], (
            f"{rel}: {REMOVE_OLD_STABLE!r} appears after {ADD_MAIN!r}; "
            "it would remove the marketplace just installed from"
        )

    @pytest.mark.parametrize("rel,get_passage", THREE_X_PASSAGES)
    def test_installs_stable_after_adding_main(self, rel, get_passage):
        passage = get_passage()
        adds = _positions(passage, ADD_MAIN)
        installs = _positions(passage, INSTALL_STABLE)
        assert adds, f"{rel}: missing {ADD_MAIN!r}"
        assert installs, f"{rel}: missing {INSTALL_STABLE!r}"
        assert installs[0] > adds[0], f"{rel}: {INSTALL_STABLE!r} must follow {ADD_MAIN!r}"

    @pytest.mark.parametrize("rel,get_passage", THREE_X_PASSAGES)
    def test_restart_mentioned_before_any_sweetclaude_command(self, rel, get_passage):
        passage = get_passage()
        restart = RESTART.search(passage)
        assert restart, f"{rel}: 3.x -> stable sequence never mentions restarting Claude Code"
        early = SC_COMMAND.findall(passage[: restart.start()])
        assert early == [], f"{rel}: /sweetclaude: commands given before the restart: {early}"


class TestAC3BetaRescueUsesTheRetiredBetaSwitch:
    REL = "docs/user-guide/beta-rescue.md"

    def test_does_not_instruct_updating_the_beta_plugin(self):
        assert BETA_UPDATE not in _read(self.REL), (
            f"{self.REL}: still instructs {BETA_UPDATE!r}; the beta channel is retired"
        )

    def test_contains_the_three_switch_commands_in_order(self):
        text = _read(self.REL)
        add = text.find(ADD_MAIN)
        install = text.find(INSTALL_STABLE)
        remove = text.find(REMOVE_BETA)
        assert add >= 0, f"{self.REL}: missing {ADD_MAIN!r}"
        assert install >= 0, f"{self.REL}: missing {INSTALL_STABLE!r}"
        assert remove >= 0, f"{self.REL}: missing {REMOVE_BETA!r}"
        assert add < install < remove, (
            f"{self.REL}: switch commands out of order; need add, install, remove-beta"
        )

    def test_configure_commands_come_after_a_restart_following_the_switch(self):
        text = _read(self.REL)
        remove = text.find(REMOVE_BETA)
        assert remove >= 0, f"{self.REL}: missing {REMOVE_BETA!r}, so no switch to restart after"
        restart = RESTART.search(text, remove)
        assert restart, f"{self.REL}: no restart mention after the switch commands"
        early = [m.group(0) for m in SC_COMMAND.finditer(text[: restart.start()])
                 if m.group(0).startswith("/sweetclaude:configure")]
        assert early == [], f"{self.REL}: /sweetclaude:configure given before the post-switch restart: {early}"
