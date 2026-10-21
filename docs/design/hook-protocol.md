# Claude Code hook protocol (verified)

**Version:** 1.0

**Date:** 2026-10-20

**Verified against:** Claude Code 2.1.305, using live probe plugins loaded with `--plugin-dir`. These facts are the contract for SweetClaude's hook tests; the captured inputs are in `tests/fixtures/hook_payloads/`.

## Input

- Every hook receives one JSON object on stdin. Common fields: `session_id`, `transcript_path`, `cwd`, `hook_event_name`. Most events also carry `prompt_id` and `permission_mode`.
- PreToolUse and PostToolUse add `tool_name`, `tool_input` and `tool_use_id`; PostToolUse also adds `tool_response` and `duration_ms`.
- `tool_input` by tool:
  - Write: `file_path`, `content`
  - Edit: `file_path`, `old_string`, `new_string`, `replace_all`
  - Bash: `command`, `description`
  - Skill: `skill`
- UserPromptSubmit adds `prompt`. Stop adds `stop_hook_active` and `last_assistant_message`. SessionStart adds `source`.
- Environment variables Claude Code sets for hooks include `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA`.
- `CLAUDE_TOOL_NAME`, `CLAUDE_FILE_PATH` and `CLAUDE_TRANSCRIPT_PATH` are not set. A hook that reads them sees empty values.

## Output (each verified by a live run)

| Event | Output | Observed effect |
|---|---|---|
| PreToolUse | stdout `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "<reason>"}}`, exit 0 | The tool call is blocked; the model sees the reason. |
| PreToolUse | stderr `<reason>`, exit 2 | The tool call is blocked; the model sees the stderr text. |
| PreToolUse | stdout `{"ok": false}`, exit 0 | Ignored. The tool call runs. |
| PostToolUse | stdout `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "<text>"}}` | The text reaches the model alongside the tool result. |
| PostToolUse | stdout `{"decision": "block", "reason": "<text>"}` | The reason reaches the model as hook feedback; the tool has already run. |
| Stop | stdout `{"decision": "block", "reason": "<text>"}` when `stop_hook_active` is false | The session continues and the model acts on the reason. |
| UserPromptSubmit | stdout `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "<text>"}}` | The text reaches the model with the prompt. |

## Rules for SweetClaude hooks

1. Read tool details from stdin JSON, never from environment variables.
2. Block a tool call only with a PreToolUse `permissionDecision: deny`, or with exit 2 and a reason on stderr.
3. Return feedback to the model with `additionalContext`, or with a `decision: block` reason for PostToolUse and Stop.
4. Never print `{"ok": ...}`; it has no effect.
5. A Stop hook that blocks must check `stop_hook_active` so it cannot loop.
