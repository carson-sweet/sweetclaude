# Session Export Format — section templates

**Sections:**
1. [Executive Summary](#section-1-executive-summary)
2. [Conversation Transcript](#section-2-conversation-transcript)
3. [Deliverables Inventory](#section-3-deliverables-inventory)
4. [Input File Manifest](#section-4-input-file-manifest)
5. [Web Search Inventory](#section-5-web-search-inventory)
6. [Project Knowledge References](#section-6-project-knowledge-references)
7. [Decision Log](#section-7-decision-log)
8. [Open Items / Next Actions](#section-8-open-items--next-actions)
9. [Key Entities Index](#section-9-key-entities-index)
10. [Artifact Dependency Map](#section-10-artifact-dependency-map)
11. [Continuity Prompt](#section-11-continuity-prompt)

**Optional sections:**
- [Sensitive Content Flag](#optional-section-sensitive-content-flag)
- [Token Estimate](#optional-section-token-estimate)
- [Model and Tool Audit](#optional-section-model-and-tool-audit)

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
