---
spdx-license: AGPL-3.0-or-later
description: Export a Claude.ai session as a complete, portable package. Includes conversation transcript, deliverables inventory, file manifest, web searches, decisions, open items, entity index, and continuity prompt. Trigger on "export this session", "wrap up", "package this conversation", "session handoff", "session report", "save this conversation", or when switching models. Also trigger when the user asks for summary + files together.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Session Export Skill

Produces a complete, portable record of a Claude.ai session. Captures the conversation, work product, reasoning, decisions, and continuity artifacts needed to resume work later.

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

Produce a single markdown file containing all selected sections. Write it to `/mnt/user-data/outputs/session-export-[YYYY-MM-DD].md` and present it via `present_files`.

If the session produced other files, present them alongside the export file in the same `present_files` call.

Use this structure:

---

### Section 1: Executive Summary

3-5 paragraphs. Write for a reader who was not in the conversation. Cover:
- What the session was about and the central goal
- What was accomplished (decisions, documents, research)
- What remains open
- The recommended next step

Prose only. No bullet points in this section.

---

### Section 2: Conversation Transcript

Full turn-by-turn record. Format each turn as:

```
## Turn [N]
**Speaker:** [User | Claude]
**Input modality:** [Typed | Voice transcription | File upload | Tool result]

[Content of the turn]
```

For tool calls within a Claude turn, render as code blocks:
```python
# Tool: [tool_name]
# Parameters: [key params only, not full output]
tool_name(param1="value", param2="value")
# Result summary: [1-2 sentence summary of what was returned]
```

For long voice transcriptions, summarize the key content accurately. Do not reproduce raw transcription artifacts. Note when summarized: `[Summarized from voice transcription]`

If timestamps are not available, note once at the top: `Note: Turn timestamps are not available in this environment.` Do not fabricate timestamps.

---

### Section 3: Deliverables Inventory

Every file created during this session via `create_file`, `bash_tool`, or other file-generating tools. Format as:

| # | Filename | Type | Location | Description | Presented to User |
|---|----------|------|----------|-------------|-------------------|
| 1 | example.docx | Word Document | /mnt/user-data/outputs/ | Draft research access agreement | Yes |

Include files that were created but may have been intermediate (e.g., scripts used to generate other files). Note which are final deliverables vs. intermediate artifacts.

If no files were created: "No files were created during this session."

---

### Section 4: Input File Manifest

Every file uploaded by the user during the session. Format as:

| # | Filename | Upload Path | Referenced in Turn(s) | Content Summary |
|---|----------|-------------|----------------------|-----------------|
| 1 | report.pdf | /mnt/user-data/uploads/report.pdf | 12, 15, 22 | Q3 financial report covering... |

Note: Upload paths are as seen in the session context. Files may no longer be accessible after session end.

If no files were uploaded: "No files were uploaded during this session."

---

### Section 5: Web Search Inventory

Every web search and web fetch performed during this session. Format as:

**Search [N]:** `[query string]`
- Tool used: `web_search` / `web_fetch`
- URL (if fetch): [url]
- Result summary: [1-2 sentences on what was found]
- Used in Turn: [N]

If no searches were performed: "No web searches were conducted during this session."

---

### Section 6: Project Knowledge References

*(Include only if session was conducted inside a Claude.ai Project)*

Every `project_knowledge_search` query made during the session:

**Query [N]:** `[query string]`
- Turn: [N]
- Retrieved from: [document title or description if identifiable]
- Summary: [what was retrieved and how it was used]

Note: This reflects queries made, not the full contents of the project knowledge base.

If not in a Project: omit this section entirely.

---

### Section 7: Decision Log

Every significant decision made during the session, including options considered and reasoning. This is a structured record, not a summary.

Format each entry as:

**Decision [N]: [Short title]**
- Turn: [N]
- Options considered: [list]
- Decision made: [what was decided]
- Reasoning: [why]
- Reversible: [Yes / No / Partially]

Focus on decisions that affect future work, architecture, relationships, or strategy. Skip formatting decisions.

---

### Section 8: Open Items / Next Actions

Every stated or implied next step, open question, unresolved issue, or pending action. Format as a checklist:

**Next Actions:**
- [ ] [Action] — Owner: [User / Claude / Third party] — Priority: [High / Medium / Low]

**Open Questions:**
- [ ] [Question] — Context: [why it matters]

**Unresolved Issues:**
- [ ] [Issue] — Context: [what needs to happen]

---

### Section 9: Key Entities Index

Named people, organizations, technologies, documents, and concepts in the session. Format as:

| Entity | Type | Description | First appears in Turn |
|--------|------|-------------|----------------------|
| Alex | Person | Project lead, session participant | 1 |
| Acme Corp | Organization | The company building the product | 3 |

Types: Person, Organization, Technology, Document, Concept, Location

---

### Section 10: Artifact Dependency Map

Shows which files reference or depend on other files. Format as:

```
session-export-2026-04-12.md
  └── references → project_requirements.docx
  └── references → navigation-routes.jsx

session-handoff.md
  └── references → project_requirements.docx
  └── references → navigation-routes.jsx
  └── references → full-transcript.md
```

If no dependencies exist between files, note: "Files produced in this session are independent."

---

### Section 11: Continuity Prompt

A ready-to-paste prompt for the next session. Write as a briefing for the next Claude instance. Keep it under 200 words. Convey:
- Who the user is and what they are working on
- What was accomplished in this session
- What the most important open item or next step is
- What documents to load or reference

Format:
```
CONTINUITY PROMPT — paste at start of next session:

You are continuing a session with [User name/description]. [2-3 sentences of critical context]. 
In the previous session, [key accomplishments in 1-2 sentences]. The most important next step is 
[specific action]. [If applicable: The session export document is attached — read it before proceeding.]
```

---

### Optional Section: Sensitive Content Flag

*(Include if the session contained PII, credentials, legal content, financial figures, or named third parties)*

Review the conversation text and flag:
- Named individuals (non-public) — turns where they appear
- Financial figures — turns where they appear
- Legal content — turns where it appears
- Any content that should be removed before sharing the export

Format:
```
⚠ SENSITIVE CONTENT NOTICE
This export contains content that should be reviewed before sharing:
- Named individuals: [list] — appears in turns [N, N]
- Financial figures: [list] — appears in turns [N, N]
- Legal content: [description] — appears in turns [N, N]
```

Note: This scan covers text content only. Binary file contents are not scanned.

---

### Optional Section: Token Estimate

*(Include only if user requests it)*

```
TOKEN ESTIMATE (approximate)
Note: Precise token counts are not available in Claude.ai. This is a rough estimate 
based on word count × 1.3 (average tokens per word).

Approximate session length: ~[N] words → ~[N] tokens
At Claude Sonnet pricing (~$3/M input tokens): ~$[X]
This is an estimate only. Actual cost depends on model, caching, and Anthropic pricing.
```

---

### Optional Section: Model and Tool Audit

```
MODEL AND TOOL AUDIT
Model: [Model name from system context]
Tools invoked this session:
- web_search: [N] calls
- web_fetch: [N] calls
- create_file: [N] calls
- bash_tool: [N] calls
- view: [N] calls
- present_files: [N] calls
- project_knowledge_search: [N] calls
- [other tools]: [N] calls
```

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
