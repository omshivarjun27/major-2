# Agent Documentation System - Decisions

## 2026-02-23 Naming Decision
 DECISION: Keep AGENTS.md as canonical filename, do NOT create Agent.md files
 RATIONALE: 14 files already exist with this convention, CI references it, avoids confusion
 Oracle recommendation aligned with this approach
 User intent honored: create richer per-directory documentation using existing naming convention

## 2026-02-23 Structure Decision
 Root AGENTS.md: Update to 10-section format per user spec
 Folder AGENTS.md: Update to 9-section format per user spec
 Existing 14 files: Intelligently merge new structure with existing content
 New files: Create using 9-section folder template
 Priority: Code-heavy directories first, stubs/empty dirs last
