Feature: STORY-301 Backup-on-sync with rollback support

  The sync script backs up installed hooks to hooks.bak/ before overwriting,
  providing a single-generation rollback point for STORY-304 hook repair.

  Background:
    Given scripts/sync-to-installed.sh exists and is executable
    And a valid installed_plugins.json pointing to an installed path with hooks/

  # 301-1
  Scenario: Backup directory created after sync
    Given the installed path has a hooks/ directory with .sh files
    When I run sync-to-installed.sh
    Then hooks.bak/ exists at the installed path
    And the exit code is 0

  # 301-2
  Scenario: Backup contains all .sh files from pre-sync hooks
    Given the installed path has 5 .sh files in hooks/
    When I run sync-to-installed.sh
    Then hooks.bak/ contains exactly 5 .sh files

  # 301-2 (non-shell files)
  Scenario: Backup includes non-shell files
    Given the installed path has hooks/hooks.json
    When I run sync-to-installed.sh
    Then hooks.bak/hooks.json exists

  # 301-3
  Scenario: Backup happens before any hook file is modified
    Given the installed path has hooks/canary.txt (not present in the repo)
    When I run sync-to-installed.sh
    Then hooks.bak/canary.txt exists
    And hooks/canary.txt does not exist (overwritten by rsync from repo)

  # 301-4
  Scenario: Previous backup is overwritten (single generation)
    Given the installed path has hooks/ with canary-1.txt
    When I run sync-to-installed.sh
    Then hooks.bak/ contains canary-1.txt
    When I add canary-2.txt to hooks/ and run sync again
    Then hooks.bak/ contains canary-2.txt
    And hooks.bak/ does not contain canary-1.txt

  # 301-5
  Scenario: Backup failure aborts sync with exit code 3
    Given the installed path's hooks.bak.tmp cannot be created (parent read-only)
    When I run sync-to-installed.sh
    Then the exit code is 3
    And stderr contains "Backup failed" or "Cannot remove"
    And the installed hooks/ directory is unchanged

  # 301-6
  Scenario: Exit code 3 is distinct from other failure codes
    Given exit code 1 is phase check, 2 is test gate, 4 is sync, 5 is path
    Then exit code 3 is used exclusively for backup failure
