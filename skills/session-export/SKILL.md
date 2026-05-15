---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Export a Claude.ai session as a complete, portable package."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:session-export" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Session Export Skill

Produces a complete, portable record of a Claude.ai session. Captures the conversation, work product, reasoning, decisions, and continuity artifacts needed to resume work later.

The full section-by-section template lives in [export-format.md](export-format.md). Read it when generating the export.

---

## Step 0: Platform Detection (Always Do This First)

Before generating any output, detect the environment and announce what is and is not available. Print this block at the top of your response:

```
SESSION EXPORT — PLATFORM CAPABILITIES
Environment: [Claude.ai Web | Claude.ai Desktop | Claude Code | Cowork]
✓ Conversation transcript — available
✓ Deliverables inventory — available (files created this session)
✓ Input file manifest — available (uploaded files visible in context)
✓ Web search inventory — available (tool calls visible in context)
✓ Project knowledge references — [available if in a Project / not applicable]
✓ Executive summary — available
✓ Decision log — available
✓ Open items / next actions — available
✓ Key entities index — available
✓ Continuity prompt — available
✓ Artifact dependency map — available
✗ Real timestamps — NOT AVAILABLE (Claude.ai does not expose turn timestamps)
✗ ZIP bundle — NOT AVAILABLE in Claude.ai (files presented individually)
✗ Precise token count — NOT AVAILABLE (approximation only)
✗ Sensitive content scan — PARTIAL (text only, not binary file contents)
```

Adjust the checkmarks based on actual environment. In Claude Code, ZIP bundling and timestamps from session metadata may be available. In Claude.ai web/desktop, they are not.

Do not attempt features marked ✗. Note the limitation in the relevant section and move on.

---

## Step 1: Scope Selection

If the user asked for everything, proceed through all sections in order.

If the user asked for a subset (e.g., "just the transcript" or "just the files"), produce only those sections. Then offer the full export: "Produced [X]. Generate the full session export with decisions, open items, and continuity prompt too?"

**Standard sections (always include unless user says otherwise):**
1. Executive Summary
2. Conversation Transcript
3. Deliverables Inventory
4. Input File Manifest
5. Web Search Inventory
6. Project Knowledge References (if in a Project)
7. Decision Log
8. Open Items / Next Actions
9. Key Entities Index
10. Artifact Dependency Map
11. Continuity Prompt

**Optional sections (include if session warrants):**
- Sensitive Content Flag (if session contained PII, API keys, legal details, financial figures)
- Token Estimate (rough, with caveat)
- Model and Tool Audit

---

## Step 2: Generate the Export

Read [export-format.md](export-format.md). Produce a single markdown file containing all selected sections — using the templates in that file verbatim — and write it to `/mnt/user-data/outputs/session-export-[YYYY-MM-DD].md`. Present it via `present_files`.

If the session produced other files, present them alongside the export file in the same `present_files` call.

---

## Step 3: Present the Export

After generating the markdown file:

1. Run `present_files` with the export file first, then any other session deliverables.
2. Tell the user what was included and what was omitted due to platform limits.
3. If the session is in a Project, note that the export file is not added to project knowledge automatically. The user must upload it manually for future searchability.

Example closing:
```
Session export complete. Produced:
- session-export-2026-04-12.md (this document — all 11 sections)
- [other files]

Not included due to Claude.ai limitations:
- Real timestamps (not exposed by platform)
- ZIP bundle (files presented individually above)
- Precise token count (omitted)

To continue this work in a new session: paste the Continuity Prompt (Section 11)
at the start of the conversation, then upload the session export file for full context.
```

---

## Quality Standards

- Never fabricate timestamps, token counts, or file metadata.
- Never reproduce full tool output verbatim. Summarize.
- For voice transcription turns, summarize accurately. Do not editorialize.
- Decision log entries reflect what was decided, not what seems optimal in hindsight.
- Open items must be exhaustive. Include too many rather than too few.
- The continuity prompt must work for a Claude instance with zero other context.

---

## Known Limitations (Claude.ai Web and Desktop)

| Feature | Status | Workaround |
|---------|--------|------------|
| Turn timestamps | ✗ Not available | Note absence; user can add approximate times manually |
| ZIP bundle | ✗ Not available | Present files individually; include manifest in export |
| Precise token counts | ✗ Not available | Rough word-count estimate with caveat |
| Sensitive content scan of binary files | ✗ Not available | Text-only scan; note limitation |
| Project knowledge directory listing | Partial | Query-based only; shows what was accessed, not full index |
| Session metadata (duration, model version) | Partial | Model name available from system context; duration not available |

All of the above are available in Claude Code with appropriate tooling. For richer exports, run sessions in Claude Code where full audit trail matters.
