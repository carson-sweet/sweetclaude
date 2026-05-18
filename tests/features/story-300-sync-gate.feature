Feature: Phase-aware sync gate (STORY-300)
  The sync-to-installed script syncs repo hooks to the installed plugin path.
  It must block sync during the IMPLEMENT phase to protect the safety buffer.

  Background:
    Given a temporary directory structure with:
      - A fake installed plugin path with a hooks/ subdirectory
      - A fake installed_plugins.json pointing to that path
      - A repo root with hooks/*.sh files to sync
      - HOME isolated to prevent reading real ~/.claude/

  # ── Criterion 300-1 ──────────────────────────────────────────────────────────

  Scenario: Script exists and is executable
    Then scripts/sync-to-installed.sh exists
    And scripts/sync-to-installed.sh is executable

  # ── Criterion 300-2 ──────────────────────────────────────────────────────────

  Scenario: Sync blocked when phase.yaml contains "phase: implement"
    Given phase.yaml contains "phase: implement"
    When I run sync-to-installed.sh
    Then the exit code is non-zero
    And stderr contains "IMPLEMENT"

  # ── Criterion 300-3 ──────────────────────────────────────────────────────────

  Scenario: Sync blocked when phase.yaml contains "phase: IMPLEMENT" (uppercase)
    Given phase.yaml contains "phase: IMPLEMENT"
    When I run sync-to-installed.sh
    Then the exit code is non-zero
    And stderr contains "IMPLEMENT"

  # ── Criterion 300-4 ──────────────────────────────────────────────────────────

  Scenario: Sync proceeds when no phase file exists
    Given phase.yaml does not exist
    And sweetclaude.yaml does not contain an active implement phase
    When I run sync-to-installed.sh with --dry-run
    Then the exit code is 0

  # ── Criterion 300-5 ──────────────────────────────────────────────────────────

  Scenario: Sync proceeds when phase is "verify"
    Given phase.yaml contains "phase: verify"
    When I run sync-to-installed.sh with --dry-run
    Then the exit code is 0

  # ── Criterion 300-6 ──────────────────────────────────────────────────────────

  Scenario: --force overrides phase check
    Given phase.yaml contains "phase: implement"
    When I run sync-to-installed.sh with --force
    Then the exit code is 0

  # ── Criterion 300-7a ─────────────────────────────────────────────────────────

  Scenario: --force appends entry to decision log on actual sync
    Given phase.yaml contains "phase: implement"
    And decision-log.md exists with at least one row
    When I run sync-to-installed.sh with --force
    Then decision-log.md has a new row containing today's date
    And the new row contains "force" or "Force"

  # ── Criterion 300-7b ─────────────────────────────────────────────────────────

  Scenario: --force --dry-run does NOT append to decision log
    Given phase.yaml contains "phase: implement"
    And decision-log.md exists with at least one row
    When I run sync-to-installed.sh with --force --dry-run
    Then decision-log.md has no new rows

  # ── Criterion 300-9 ──────────────────────────────────────────────────────────

  Scenario: Sync blocked when sweetclaude.yaml has work.active.phase implement
    Given phase.yaml does not exist
    And sweetclaude.yaml contains work.active.phase set to "implement"
    When I run sync-to-installed.sh
    Then the exit code is non-zero
    And stderr contains "IMPLEMENT"

  # ── Criterion 300-10 ─────────────────────────────────────────────────────────

  Scenario: --dry-run runs checks without syncing
    Given phase.yaml contains "phase: verify"
    When I run sync-to-installed.sh with --dry-run
    Then the exit code is 0
    And stdout contains "Dry run"
    And no files at the installed path were modified

  # ── Criterion 300-11 ─────────────────────────────────────────────────────────

  Scenario: Unknown argument produces error
    When I run sync-to-installed.sh with --bogus
    Then the exit code is non-zero
    And stderr contains "Unknown argument"

  # ── Exit code contract ───────────────────────────────────────────────────────

  Scenario: Path resolution failure produces exit code 5
    Given installed_plugins.json does not exist or points to invalid path
    When I run sync-to-installed.sh with --dry-run
    Then the exit code is 5
