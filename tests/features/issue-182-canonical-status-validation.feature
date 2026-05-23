Feature: Canonical status validation module
  As a SweetClaude operator
  I need all status writes to go through a single validated path
  So that status values are always canonical, transitions are enforced,
  and file moves are atomic with status changes.

  Background:
    Given the canonical status vocabulary is: new, ready, active, in-review, blocked, on-hold, deferred, done, declined, abandoned, superseded
    And the terminal statuses are: done, declined, abandoned, superseded

  # --- Validation API ---

  Scenario Outline: validate() accepts canonical status values
    When I call validate with "<status>"
    Then it returns True

    Examples:
      | status      |
      | new         |
      | ready       |
      | active      |
      | in-review   |
      | blocked     |
      | on-hold     |
      | deferred    |
      | done        |
      | declined    |
      | abandoned   |
      | superseded  |

  Scenario Outline: validate() rejects non-canonical status values
    When I call validate with "<status>"
    Then it returns False

    Examples:
      | status       |
      | backlog      |
      | in_progress  |
      | cancelled    |
      | proposed     |
      | achieved     |
      | dropped      |
      | compleet     |
      |              |

  Scenario Outline: validate() rejects values with whitespace or wrong case
    When I call validate with "<status>"
    Then it returns False

    Examples:
      | status   |
      |  active  |
      | done     |
      | Active   |
      | DONE     |
      | In-Review|

  Scenario: validate() rejects None
    When I call validate with None
    Then it returns False

  Scenario: assert_valid() raises ValueError for non-canonical status
    When I call assert_valid with "backlog"
    Then it raises ValueError with the invalid value and the list of valid statuses

  Scenario: assert_valid() does not raise for canonical status
    When I call assert_valid with "active"
    Then no exception is raised

  # --- Transition validation ---

  Scenario Outline: validate_transition() allows non-terminal to any status
    Given an issue with status "<old>"
    When I call validate_transition from "<old>" to "<new>" for entity type "issue"
    Then the transition is allowed

    Examples:
      | old      | new         |
      | new      | ready       |
      | ready    | active      |
      | active   | in-review   |
      | active   | blocked     |
      | active   | on-hold     |
      | new      | deferred    |
      | active   | done        |
      | new      | declined    |

  Scenario Outline: validate_transition() blocks terminal to non-terminal without reopen
    Given an issue with status "<old>"
    When I call validate_transition from "<old>" to "<new>" for entity type "issue"
    Then the transition is blocked with a message about requiring reopen

    Examples:
      | old         | new    |
      | done        | active |
      | declined    | ready  |
      | abandoned   | active |
      | superseded  | new    |

  Scenario: validate_transition() allows terminal to non-terminal with explicit reopen
    Given an issue with status "done"
    When I call validate_transition from "done" to "new" for entity type "issue" with reopen flag
    Then the transition is allowed

  Scenario: validate_transition() allows no-op transition silently
    Given an issue with status "active"
    When I call validate_transition from "active" to "active" for entity type "issue"
    Then the transition is allowed

  Scenario Outline: validate_transition() rejects non-canonical old or new values
    When I call validate_transition from "<old>" to "<new>" for entity type "issue"
    Then the transition is rejected with a validation error

    Examples:
      | old        | new     |
      | backlog    | active  |
      | active     | shipped |

  # --- Non-terminal status writes ---

  Scenario: write_status() updates frontmatter and preserves file body
    Given a markdown file at "backlog/ISSUE-200-test.md" with status "new" and body content "## Description\nTest issue."
    When I call write_status on that file with status "active" and actor "go"
    Then the file's frontmatter status is "active"
    And the file's body content is unchanged
    And an audit log entry exists with actor "go", entity "ISSUE-200", old "new", new "active"
    And the cache has been rebuilt

  Scenario: write_status() uses atomic write pattern
    Given a markdown file at "backlog/ISSUE-201-test.md" with status "new"
    When I call write_status on that file with status "ready" and actor "project-backlog-triage"
    Then no temporary files remain in the directory
    And the file is not corrupted

  Scenario: write_status() rejects invalid status
    Given a markdown file at "backlog/ISSUE-202-test.md" with status "new"
    When I call write_status on that file with status "backlog" and actor "test"
    Then the write is rejected with a validation error
    And the file's frontmatter status is still "new"
    And no audit log entry is created

  Scenario: write_status() rejects blocked transition
    Given a markdown file at "backlog/ISSUE-203-test.md" with status "done"
    When I call write_status on that file with status "active" and actor "test"
    Then the write is rejected with a transition error
    And the file's frontmatter status is still "done"

  Scenario: write_status() handles file with UTF-8 BOM
    Given a markdown file at "backlog/ISSUE-204-test.md" with status "new" and a UTF-8 BOM
    When I call write_status on that file with status "active" and actor "go"
    Then the file's frontmatter status is "active"
    And the file's body content is unchanged

  Scenario: write_status() handles file with CRLF line endings
    Given a markdown file at "backlog/ISSUE-205-test.md" with status "new" and CRLF line endings
    When I call write_status on that file with status "active" and actor "go"
    Then the file's frontmatter status is "active"
    And the file's body content is unchanged

  Scenario: write_status() rejects file with empty frontmatter
    Given a markdown file at "backlog/ISSUE-206-test.md" with empty frontmatter
    When I call write_status on that file with status "active" and actor "go"
    Then the write is rejected with a clear error about missing status field

  Scenario: write_status() rejects file with no frontmatter delimiters
    Given a markdown file at "backlog/ISSUE-207-test.md" with no frontmatter
    When I call write_status on that file with status "active" and actor "go"
    Then the write is rejected with a clear error about missing frontmatter

  Scenario: write_status() rejects file with no status key in frontmatter
    Given a markdown file at "backlog/ISSUE-208-test.md" with frontmatter but no status key
    When I call write_status on that file with status "active" and actor "go"
    Then the write is rejected with a clear error about missing status field

  Scenario: write_status() rejects nonexistent file
    When I call write_status on "backlog/ISSUE-209-nonexistent.md" with status "active" and actor "go"
    Then the write is rejected with a file-not-found error

  Scenario: write_status() rejects non-terminal write on file in done directory
    Given a markdown file at "roadmap/issues/done/ISSUE-204-test.md" with status "done"
    When I call write_status on that file with status "active" and actor "test"
    Then the write is rejected because non-terminal status cannot be set on a file in a done directory

  Scenario: write_status() no-op transition produces no audit entry
    Given a markdown file at "backlog/ISSUE-205-noop.md" with status "active"
    When I call write_status on that file with status "active" and actor "go"
    Then the write succeeds silently
    And no audit log entry is created for ISSUE-205-noop

  # --- Terminal status writes with file moves ---

  Scenario: set_terminal() writes status and moves file to done directory
    Given a markdown file at "roadmap/issues/ISSUE-210-test.md" with status "active"
    When I call set_terminal on that file with status "done" and actor "project-issues"
    Then the file exists at "roadmap/issues/done/ISSUE-210-test.md"
    And the file no longer exists at "roadmap/issues/ISSUE-210-test.md"
    And the file's frontmatter status is "done"
    And the file's frontmatter has a closed_date field
    And an audit log entry exists with actor "project-issues", entity "ISSUE-210", old "active", new "done"
    And the cache has been rebuilt

  Scenario: set_terminal() moves backlog declines to archived
    Given a markdown file at "backlog/ISSUE-211-test.md" with status "new"
    When I call set_terminal on that file with status "declined" and actor "project-issues"
    Then the file exists at "backlog/archived/ISSUE-211-test.md"
    And the file no longer exists at "backlog/ISSUE-211-test.md"
    And the file's frontmatter status is "declined"

  Scenario: set_terminal() rejects non-terminal status
    Given a markdown file at "roadmap/issues/ISSUE-212-test.md" with status "active"
    When I call set_terminal on that file with status "ready" and actor "test"
    Then the write is rejected because "ready" is not a terminal status
    And the file has not moved

  Scenario: set_terminal() is atomic — file move failure rolls back everything
    Given a markdown file at "roadmap/issues/ISSUE-213-test.md" with status "active"
    And the destination directory "roadmap/issues/done/" is not writable
    When I call set_terminal on that file with status "done" and actor "test"
    Then the write is rejected with a filesystem error
    And the file's frontmatter status is still "active"
    And the file has not moved
    And no audit log entry is created for ISSUE-213
    And the cache does not reflect status "done" for ISSUE-213

  Scenario: set_terminal() creates destination directory if it does not exist
    Given a markdown file at "roadmap/issues/ISSUE-214-test.md" with status "active"
    And the directory "roadmap/issues/done/" does not exist
    When I call set_terminal on that file with status "done" and actor "go"
    Then the directory "roadmap/issues/done/" is created
    And the file exists at "roadmap/issues/done/ISSUE-214-test.md"

  Scenario: set_terminal() rejects move when destination file already exists
    Given a markdown file at "roadmap/issues/ISSUE-215-test.md" with status "active"
    And a file already exists at "roadmap/issues/done/ISSUE-215-test.md"
    When I call set_terminal on that file with status "done" and actor "go"
    Then the write is rejected with a collision error
    And the original file's frontmatter status is still "active"
    And the original file has not moved

  # --- CLI entry point ---

  Scenario: CLI set command succeeds
    Given a markdown file at "backlog/ISSUE-220-test.md" with status "new"
    When I run "python3 scripts/status.py set --file backlog/ISSUE-220-test.md --status active --actor go"
    Then the exit code is 0
    And stdout contains JSON with "status" equal to "active"

  Scenario: CLI set command fails on invalid status
    When I run "python3 scripts/status.py set --file backlog/ISSUE-221-test.md --status backlog --actor test"
    Then the exit code is 1
    And stdout contains JSON with "error" describing the invalid status

  Scenario: CLI set-terminal command moves file
    Given a markdown file at "roadmap/issues/ISSUE-222-test.md" with status "active"
    When I run "python3 scripts/status.py set-terminal --file roadmap/issues/ISSUE-222-test.md --status done --actor go"
    Then the exit code is 0
    And the file exists at "roadmap/issues/done/ISSUE-222-test.md"

  Scenario: CLI set command fails when --actor is omitted
    Given a markdown file at "backlog/ISSUE-223-test.md" with status "new"
    When I run "python3 scripts/status.py set --file backlog/ISSUE-223-test.md --status active"
    Then the exit code is 1
    And stdout contains JSON with "error" describing the missing actor

  Scenario: CLI set command fails when --file points to nonexistent file
    When I run "python3 scripts/status.py set --file backlog/ISSUE-224-nonexistent.md --status active --actor test"
    Then the exit code is 1
    And stdout contains JSON with "error" describing file not found

  Scenario: CLI validate command checks a value
    When I run "python3 scripts/status.py validate --status in-review"
    Then the exit code is 0
    When I run "python3 scripts/status.py validate --status cancelled"
    Then the exit code is 1

  # --- doctor.py integration ---

  Scenario: doctor.py validates against the canonical 11 statuses
    Given a markdown file at "backlog/ISSUE-230-test.md" with status "in-review"
    When I run doctor.py file_diagnostics on the project
    Then no finding is reported for ISSUE-230-test.md

  Scenario: doctor.py rejects legacy status values
    Given a markdown file at "backlog/ISSUE-231-test.md" with status "in_progress"
    When I run doctor.py file_diagnostics on the project
    Then a finding is reported for ISSUE-231-test.md with problem "unknown-status"

  Scenario: doctor.py imports CANONICAL_STATUSES from status.py
    When status.py is not importable
    Then doctor.py fails with an explicit ImportError
    And does not fall back to a hardcoded status set

  # --- Cache verification ---

  Scenario: Cache reflects new status after write_status
    Given a markdown file at "backlog/ISSUE-232-test.md" with status "new"
    When I call write_status on that file with status "active" and actor "go"
    Then the cache row for ISSUE-232 has status "active"

  Scenario: Cache reflects new path after set_terminal
    Given a markdown file at "roadmap/issues/ISSUE-233-test.md" with status "active"
    When I call set_terminal on that file with status "done" and actor "go"
    Then the cache row for ISSUE-233 has status "done"
    And the cache row for ISSUE-233 has source_path containing "done/ISSUE-233-test.md"

  # --- Storage-lint integration ---

  Scenario: set_terminal followed by doctor storage-lint produces zero findings
    Given a markdown file at "roadmap/issues/ISSUE-234-test.md" with status "active"
    When I call set_terminal on that file with status "done" and actor "go"
    And I run doctor.py storage_lint on the project
    Then no done-status-mismatch finding is reported for ISSUE-234

  # --- Audit log ---

  Scenario: Audit log entries are JSONL format
    Given a markdown file at "backlog/ISSUE-240-test.md" with status "new"
    When I call write_status on that file with status "active" and actor "go"
    Then the audit log at ".sweetclaude/metrics/status-audit.jsonl" contains a line
    And that line is valid JSON with keys: ts, actor, entity, file, old, new

  Scenario: Audit log is append-only across multiple writes
    Given a markdown file at "backlog/ISSUE-241-test.md" with status "new"
    When I call write_status with status "ready" and actor "triage"
    And I call write_status with status "active" and actor "go"
    Then the audit log contains 2 entries for ISSUE-241
    And the first entry shows new→ready
    And the second entry shows ready→active

  # --- Milestone vocabulary alignment ---

  Scenario: Milestone skill maps its vocabulary before calling status.py
    Given a milestone file at "roadmap/milestones/MS-099-test.md" with status "achieved"
    When the milestone skill updates this milestone's status
    Then status.py receives "done" not "achieved"

  Scenario: Existing milestones with legacy vocabulary are backfilled
    Given milestones exist with statuses "proposed", "active", "achieved", "dropped"
    When the backfill migration runs
    Then "proposed" milestones have status "new"
    And "achieved" milestones have status "done"
    And "dropped" milestones have status "declined"
    And "active" milestones remain "active"
