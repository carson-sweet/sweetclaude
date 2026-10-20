# Utils Library Index

This index is read only after Tier 1 selected this category. Choose one workflow; do not load every workflow body.

| Workflow | Trigger / outcome |
|---|---|
| `big-picture` | Show the full project at a glance — the roadmap pipeline with its milestones, epics and issues. Covers whole-project status, overview, and where any piece of work currently sits. |
| `corpus-consolidate` | Scan source directories, deduplicate files, copy unique files into corpus/raw/inbox/. |
| `corpus-promote` | Finalize approved documents from corpus/working/. |
| `corpus-rag-reindex` | Rebuild RAG collections from source files. |
| `corpus-rag-setup` | Configure and run local semantic search on project documents using mcp-local-rag. |
| `corpus-reconcile` | Take staged files and work with the user to produce approved canonical documents in corpus/working/. |
| `corpus-status` | Show the current state of the document corpus pipeline — file counts in each stage, last-run timestamps per step, and recommended next action. |
| `corpus-triage` | Classify files in corpus/raw/inbox/ as keep-as-is, needs-reconciliation, discard, or defer. |
| `dashboard` | Launch a local web dashboard showing roadmap, releases, epics, backlog, dependencies, git history, and skill activity. |
| `document-corpus` | Manage the full document corpus pipeline — consolidate raw files, triage, reconcile into canonical documents, promote, set up semantic search (RAG), and reindex. |
| `documents-update-docs` | Update documentation when implementation changes behavior. |
| `misc-meeting-prep` | Prepare for a specific meeting. |
| `next-steps` | Walk through the pipeline step by step. |
| `recap` | Produce a concise 'where we are' summary: current phase, active work item, last 3 commits, checkpoint state, and any open flags. |
| `report-failure` | Write one structured failure report and root cause analysis to .sweetclaude/failure/. Invoke ONLY when the user explicitly asks to record/report a failure, mistake, or incident. Never auto-invoke. |
| `session-export` | Export a Claude.ai session as a complete, portable package. |
