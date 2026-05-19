---
id: DESIGN-304
story: STORY-304
spec: SPEC-304
epic: EP-010
version: 2.0
date: 2026-05-19
supersedes: design-304 v1.0 (2026-05-18)
status: approved
---

# Design: STORY-304 Bash-based hook repair recovery

Companion to SPEC-304 v2.0. This document captures the load-bearing design decisions only; the spec is the source of truth for behavior and acceptance.

## 1. Why Bash is the recovery channel

`hooks/hooks.json` registers `test-guardian.sh` and `auto-test-runner.sh` with `"matcher": "Write|Edit"`. The matcher is a tool-name regex evaluated by the Claude Code harness; the Bash tool name does not match, so Bash invocations are never routed through these hooks. When a Write/Edit hook is itself broken (syntax error or non-zero exit), the harness blocks Write and Edit calls — but Bash continues to work.

This is not a side effect we are exploiting. It is the intended escape hatch baked into the matcher architecture: Bash is needed for compile/test/restore workflows, and gating it would create unrecoverable deadlocks. STORY-304 codifies this property into a documented recovery channel and a script that uses it.

`artifact-guardian.sh` does match `Bash`, but it gates Bash invocations that touch artifact-protected paths (e.g. story state files). `~/.claude/plugins/cache/.../hooks/` is not an artifact-protected path, so a recovery `cp` is not blocked.

## 2. Output contract constants

The emergency script emits a small set of pinned strings (`CONTRACT_LINE_INSTALL`, `CONTRACT_LINE_RESTORED_PREFIX`, etc.) declared as `readonly` near the top of the script. The test script sources the script with `EMERGENCY_RESTORE_SOURCE_ONLY=1` set — a sentinel that causes the script to `return 0` immediately after defining constants, without executing main logic. The test then asserts substrings of script stdout against these in-process constants.

Why constants-by-source instead of constants-in-a-separate-file:
- Single source of truth (the script). No drift between script output and test expectations.
- No build step or import path; works with pure bash.
- The script file is small enough that the duplication cost (constant declarations in script body) is acceptable for the clarity gain.

Why not just `grep` for hard-coded literals in the test:
- A change to the script output silently passes the test if the test literal is unchanged. Sourcing forces the test to pull the actual current strings.

## 3. Test isolation

Three pieces of isolation:

- **Sandboxed HOME via per-test tmpdir.** Each test creates `$TEST_TMPDIR/tN/install` with its own `hooks/` and optional `hooks.bak/`. Tests do not touch the real `~/.claude/plugins/`.
- **`BASH_SOURCE`-based path resolution.** The script computes `REPO_ROOT` from `$(dirname "$SCRIPT_PATH")/..` where `SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"`. No `git rev-parse`. This means tests do not need a git repo in the sandbox and the script is portable to environments without git.
- **`INSTALL_PATH` env var as back door.** Tests set `INSTALL_PATH` to point at the sandbox; the script detects this is an explicit override and (a) skips `installed_plugins.json` resolution and (b) skips the `$HOME/.claude/plugins/` prefix check.

Why not git: git introduces a hard dependency on the script being inside a working tree, breaks portability into chroots/containers without git, and gives no path-resolution benefit over `BASH_SOURCE`.

## 4. `set -e` (script) vs `set -euo pipefail` (test) asymmetry

Deliberate.

- **Script: `set -e` only.** The recovery script's job is to make a best effort under degraded conditions. The path-resolution branches use `|| true` to swallow expected misses (no `installed_plugins.json`, no `find` matches). Strict `-u` would force defensive `${VAR:-}` annotations on every reference of an env var that may legitimately be empty during recovery. `-o pipefail` would propagate failures from `find ... | head -1` patterns where a short-circuit at `head` is the desired behavior. The cost of strictness exceeds the benefit for a recovery tool.

- **Test: `set -euo pipefail`.** Tests must fail loudly. An unset variable in the test harness is a bug, not a graceful degradation. A failing pipeline silently passing would let a regression through. The test is short, controlled, and authored to satisfy strict mode.

This asymmetry is intentional and the spec calls it out so future maintainers do not "normalize" the script to strict mode.

## 5. `INSTALL_PATH` back-door semantics

The back door has two effects, both required for the test design:

1. **Skip `installed_plugins.json` resolution.** The script trusts the caller's value verbatim.
2. **Skip the `$HOME/.claude/plugins/` prefix check.** The check exists to prevent a poisoned `installed_plugins.json` from causing the script to write outside the plugin tree. Tests need to write to a sandboxed tmpdir, which by construction is not under the plugin tree.

The back door is gated by a single signal — `INSTALL_PATH` non-empty at script entry — captured into `INSTALL_PATH_OVERRIDE`. There is no separate `--unsafe` flag; the env-var pattern is the documented interface for testing.

Security note: a user who can set environment variables in the Claude Code session can already set `PATH`, write to arbitrary files via Bash, etc. The back door does not widen the attack surface. The prefix check defends against a corrupted `installed_plugins.json`, not against a hostile caller.

## 6. In-place rewrite rationale

v1.0 of SPEC-304 was draft-status and unimplemented. The deltas to reach v2.0 (output contract, three-test structure, back-door semantics, deliverable enumeration, exit-code and absence-behavior tables) touch nearly every section. Options considered:

- **New parallel files** (`story-304-spec-v2.md`, `design-304-v2.md`) — would force every downstream reader (skill, sync script, doc index) to disambiguate which is canonical and would leave v1.0 in place as a tripping hazard.
- **In-place rewrite with `supersedes:` frontmatter** — chosen. Single canonical artifact at the well-known path. Provenance preserved in the `supersedes:` field. Git history retains the v1.0 content for anyone who needs to compare.

Decision: in-place rewrite. `supersedes: SPEC-304 v1.0 (2026-05-18)` in frontmatter is the audit trail.
