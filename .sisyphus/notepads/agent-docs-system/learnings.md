# Agent Documentation System - Learnings

## 2026-02-23 Initial Analysis
 Repository has 14 existing AGENTS.md files (uppercase, plural)
 Zero Agent.md files exist — user request interpreted as concept not filename
 Oracle recommends keeping AGENTS.md naming convention
 Root AGENTS.md is 201 lines, referenced by CI/pyproject.toml
 ~50+ directories lack any agent documentation
 110 total directories (including __pycache__)
 Subagent timeout pattern: deep/writing tasks that attempt 500+ line files WILL timeout — split into parts
 Triple-duplication bug: verify content appears exactly ONCE after append operations
 Windows environment: Python is `py` via C:\Windows\py.exe
 Prohibited terms: Claude, Anthropic, OpenAI — must not appear in NEW documentation
 No placeholder text: TBD, TODO, coming soon
 Tone: Professional engineering, Staff Engineer reporting to CTO
 Conservative estimates: Never inflate progress or maturity
