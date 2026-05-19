Feature: Pre-sync test validation gate
  As a SweetClaude developer syncing changes to the installed path
  I want the sync script to run the hook test suite before copying
  So that a hook with failing tests can never reach the installed path

  Background:
    Given the sync script exists at scripts/sync-to-installed.sh
    And a valid installed plugin path with a hooks/ directory containing shell files
    And the project is in the IMPLEMENT phase

  Scenario: 302-1 Sync runs test suite before copying
    Given tests/test-hooks.sh exists and all tests pass
    When I run the sync script
    Then the output contains evidence that test-hooks.sh was executed
    And the output contains "All hook tests passed" or equivalent
    And the sync completes successfully with exit code 0

  Scenario: 302-2 Test failure blocks sync
    Given tests/test-hooks.sh exists and at least one test fails
    When I run the sync script
    Then the sync exits with code 2
    And stderr contains "tests failed" or "Sync blocked"
    And the installed hooks/ directory is unchanged from before the sync attempt

  Scenario: 302-3 Force flag does not bypass test gate
    Given the project phase is "verify" (not implement)
    And tests/test-hooks.sh exists and at least one test fails
    When I run the sync script with --force
    Then the sync exits with code 2
    And stderr contains "tests failed" or "Sync blocked"
    And the installed hooks/ directory is unchanged

  Scenario: 302-4 Test success allows sync to proceed
    Given tests/test-hooks.sh exists and all tests pass
    When I run the sync script
    Then the sync completes successfully with exit code 0
    And the installed hooks/ directory contains the synced hooks from the repo

  Scenario: 302-dry-run Tests still run in dry-run mode
    Given tests/test-hooks.sh exists and all tests pass
    When I run the sync script with --dry-run
    Then the output contains evidence that test-hooks.sh was executed
    And the sync exits with code 0
    And the installed hooks/ directory is unchanged (dry-run does not copy)

  Scenario: 302-dry-run-fail Tests fail in dry-run mode
    Given tests/test-hooks.sh exists and at least one test fails
    When I run the sync script with --dry-run
    Then the sync exits with code 2
    And stderr contains "tests failed" or "Sync blocked"
    And the installed hooks/ directory is unchanged
