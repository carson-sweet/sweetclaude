Feature: Doctor hook_health checks
  The check_hook_health function validates SweetClaude hook infrastructure:
  hooks.json presence, hook script syntax (bash -n), and rules file presence.

  Background:
    Given a healthy SweetClaude project fixture
    And a fake home directory with SweetClaude installed at version "4.0.8-beta"

  # --- Negative (healthy) ---

  Scenario: Healthy project produces no hook_health findings
    When check_hook_health runs against the project state
    Then the result contains 0 findings

  # --- hooks.json checks ---

  Scenario: hooks.json is missing
    Given hooks.json does not exist in the plugin bundle
    When check_hook_health runs against the project state
    Then the result contains at least 1 finding
    And the findings include id "hook-health:missing:hooks.json"
    And the finding with id "hook-health:missing:hooks.json" has severity "error"
    And the finding with id "hook-health:missing:hooks.json" has fix_type "report-only"

  Scenario: hooks.json is empty dict (not None) produces no finding
    Given hooks.json contains an empty JSON object
    When check_hook_health runs against the project state
    Then no finding has id "hook-health:missing:hooks.json"

  # --- Hook script syntax checks ---

  Scenario: Hook script with valid syntax produces no finding
    Given the project has a hook file "good-hook.sh" with content "#!/bin/bash\nexit 0\n"
    When check_hook_health runs against the project state
    Then no finding has id prefix "hook-health:syntax-error"

  Scenario: Hook script with syntax error produces error finding
    Given the project has a hook file "bad-hook.sh" with content "#!/bin/bash\nif then\n"
    When check_hook_health runs against the project state
    Then the findings include id "hook-health:syntax-error:bad-hook.sh"
    And the finding with id "hook-health:syntax-error:bad-hook.sh" has severity "error"
    And the finding with id "hook-health:syntax-error:bad-hook.sh" has fix_type "report-only"

  Scenario: Multiple hook scripts with mixed syntax
    Given the project has a hook file "good.sh" with content "#!/bin/bash\nexit 0\n"
    And the project has a hook file "bad.sh" with content "#!/bin/bash\nif then\n"
    When check_hook_health runs against the project state
    Then the findings include id "hook-health:syntax-error:bad.sh"
    And no finding has id "hook-health:syntax-error:good.sh"

  Scenario: No hook files in project produces no syntax findings
    When check_hook_health runs against the project state
    Then no finding has id prefix "hook-health:syntax-error"

  Scenario: Empty hook file (zero bytes) passes syntax check
    Given the project has a hook file "empty.sh" with content ""
    When check_hook_health runs against the project state
    Then no finding has id "hook-health:syntax-error:empty.sh"

  Scenario: Binary content in hook file produces syntax error finding
    Given the project has a hook file "not-bash.sh" with content "this is not a valid shell script at all \x00\x01"
    When check_hook_health runs against the project state
    Then the findings include id "hook-health:syntax-error:not-bash.sh"

  # --- Exception handling (bash -n timeout/crash) ---

  Scenario: bash -n timeout is silently skipped
    Given the project has a hook file "slow.sh" with content "#!/bin/bash\nexit 0\n"
    And bash -n will raise TimeoutExpired for "slow.sh"
    When check_hook_health runs against the project state
    Then no finding has id "hook-health:syntax-error:slow.sh"

  Scenario: bash -n OSError is silently skipped and other files still checked
    Given the project has a hook file "broken.sh" with content "#!/bin/bash\nexit 0\n"
    And the project has a hook file "good.sh" with content "#!/bin/bash\nexit 0\n"
    And bash -n will raise OSError for "broken.sh"
    When check_hook_health runs against the project state
    Then no finding has id "hook-health:syntax-error:broken.sh"
    And no finding has id "hook-health:syntax-error:good.sh"

  # --- Rules file checks ---

  Scenario: One rules file missing produces one warning
    Given rules file "interaction-model.md" does not exist in the fake home
    When check_hook_health runs against the project state
    Then the findings include id "hook-health:missing-rule:interaction-model.md"
    And the finding with id "hook-health:missing-rule:interaction-model.md" has severity "warning"
    And the finding with id "hook-health:missing-rule:interaction-model.md" has fix_type "prompted"
    And the finding with id "hook-health:missing-rule:interaction-model.md" fix_recipe action is "prompt"
    And the finding with id "hook-health:missing-rule:interaction-model.md" fix_recipe type is "hook_restore"

  Scenario: All three rules files missing produces three warnings
    Given rules file "interaction-model.md" does not exist in the fake home
    And rules file "phase-gates.md" does not exist in the fake home
    And rules file "tdd-levels.md" does not exist in the fake home
    When check_hook_health runs against the project state
    Then the result contains at least 3 findings with id prefix "hook-health:missing-rule"
    And the findings include id "hook-health:missing-rule:interaction-model.md"
    And the findings include id "hook-health:missing-rule:phase-gates.md"
    And the findings include id "hook-health:missing-rule:tdd-levels.md"

  # --- Interaction: multiple check blocks fire together ---

  Scenario: hooks.json missing and rules file missing accumulate findings
    Given hooks.json does not exist in the plugin bundle
    And rules file "tdd-levels.md" does not exist in the fake home
    When check_hook_health runs against the project state
    Then the result contains at least 2 findings
    And the findings include id "hook-health:missing:hooks.json"
    And the findings include id "hook-health:missing-rule:tdd-levels.md"
