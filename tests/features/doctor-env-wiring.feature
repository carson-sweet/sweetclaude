Feature: Doctor env_wiring checks
  The check_env_wiring function validates SweetClaude environment wiring:
  plans directory existence, plansDirectory setting in settings files,
  and SweetClaude section in CLAUDE.md.

  Background:
    Given a healthy SweetClaude project fixture
    And a fake home directory with SweetClaude installed at version "4.0.8-beta"

  # --- Negative (healthy) ---

  Scenario: Healthy project produces no env_wiring findings
    When check_env_wiring runs against the project state
    Then the result contains 0 findings

  # --- Plans directory ---

  Scenario: Plans directory missing produces info finding
    Given the plans directory does not exist
    When check_env_wiring runs against the project state
    Then the findings include id "env-wiring:missing:plans-directory"
    And the finding with id "env-wiring:missing:plans-directory" has severity "info"
    And the finding with id "env-wiring:missing:plans-directory" has fix_type "auto"
    And the finding with id "env-wiring:missing:plans-directory" fix_recipe action is "create_dir"

  # --- plansDirectory setting ---

  Scenario: Local settings without plansDirectory produces a project-only fix
    Given global settings has no plansDirectory key
    And local settings has no plansDirectory key
    When check_env_wiring runs against the project state
    Then the findings include id "env-wiring:plans-directory-unset:settings_local"
    And the finding with id "env-wiring:plans-directory-unset:settings_local" has severity "warning"
    And the finding with id "env-wiring:plans-directory-unset:settings_local" has fix_type "auto"
    And the finding with id "env-wiring:plans-directory-unset:settings_local" fix_recipe action is "write_field"

  Scenario: Global settings with plansDirectory set produces no finding
    When check_env_wiring runs against the project state
    Then no finding has id prefix "env-wiring:plans-directory-unset"

  Scenario: Local settings without plansDirectory checked when global is absent
    Given global settings does not exist
    And local settings has no plansDirectory key
    When check_env_wiring runs against the project state
    Then the findings include id "env-wiring:plans-directory-unset:settings_local"

  Scenario: Local plansDirectory is checked even when global is set
    Given global settings has plansDirectory set
    And local settings has no plansDirectory key
    When check_env_wiring runs against the project state
    Then the findings include id "env-wiring:plans-directory-unset:settings_local"

  # --- CLAUDE.md SweetClaude section ---

  Scenario: CLAUDE.md without sweetclaude mention produces warning
    Given CLAUDE.md does not mention sweetclaude
    When check_env_wiring runs against the project state
    Then the findings include id "env-wiring:claude-md-missing-section:CLAUDE.md"
    And the finding with id "env-wiring:claude-md-missing-section:CLAUDE.md" has severity "warning"
    And the finding with id "env-wiring:claude-md-missing-section:CLAUDE.md" has fix_type "report-only"

  Scenario: CLAUDE.md mentioning sweetclaude produces no finding
    When check_env_wiring runs against the project state
    Then no finding has id prefix "env-wiring:claude-md-missing-section"

  Scenario: Case-insensitive match for sweetclaude in CLAUDE.md
    Given CLAUDE.md contains "SweetClaude" in mixed case
    When check_env_wiring runs against the project state
    Then no finding has id prefix "env-wiring:claude-md-missing-section"

  Scenario: CLAUDE.md absent produces no missing-section finding
    Given CLAUDE.md does not exist
    When check_env_wiring runs against the project state
    Then no finding has id prefix "env-wiring:claude-md-missing-section"

  # --- Interaction ---

  Scenario: Plans directory missing and settings unset accumulate
    Given the plans directory does not exist
    And local settings has no plansDirectory key
    When check_env_wiring runs against the project state
    Then the result contains at least 2 findings
    And the findings include id "env-wiring:missing:plans-directory"
    And the findings include id "env-wiring:plans-directory-unset:settings_local"
