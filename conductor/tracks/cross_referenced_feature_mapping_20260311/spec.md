# Specification: Cross-Referenced Feature Mapping Analysis

## Overview
Perform a full, autonomous Feature Mapping analysis of the entire codebase, heavily cross-referencing against existing architecture documentation (`CODEBASE_ARCHITECTURE.md`, `CODEBASE_DATAFLOW.md`, `CODEBASE_MODULES.md`) and `AGENTS.md` files. The objective is to produce a single, unified feature inventory that validates documented features against the actual source code, highlighting discrepancies and orphaned code. The output will be a highly structured `FEATURE_MAP.md` and an accompanying machine-readable `FEATURE_MAP.json`.

## Functional Requirements
- **Strategy:** Utilize a script or sub-agent to autonomously read and process every valid source code file.
- **Skip List:** Ignore the following directories: `node_modules`, `.git`, `__pycache__`, `.venv`, `dist`, `build`, `.next`, `coverage`.
- **Feature Discovery & Cross-Referencing:**
  - Parse `CODEBASE_ARCHITECTURE.md`, `CODEBASE_DATAFLOW.md`, and `CODEBASE_MODULES.md` to extract documented features.
  - Parse all `AGENTS.md` files.
  - Read ALL unskipped source, test, config, and environment files.
  - Merge findings into a single inventory, tagging the source (Docs, AGENTS.md, Code, or All).
  - Mark features found in docs but not in code as **Documented but not implemented**.
- **Dependency Tracing & Validation:** For each feature, follow actual import/call chains to document the graph. Cross-reference these findings against `CODEBASE_DATAFLOW.md` and flag discrepancies explicitly (e.g., `⚠️ Discrepancy: [doc] vs [code]`).
- **Data Output:** 
  - Generate `FEATURE_MAP.json` to represent the mapped dependency graph.
  - Generate `FEATURE_MAP.md` matching a strict block structure per feature, including a new **Doc vs Code** section and a **Source** attribute.
  - Include an **Index Table** at the top of `FEATURE_MAP.md`.
  - Include an **Orphaned Files/Folders** section at the bottom of `FEATURE_MAP.md`.
- **Progress Tracking:** Output `📖 Reading: ./path/to/file.ext` and `✓ Mapped: [Feature Name] — X files read, Y dependencies traced` to the console without pausing.
- **Completion Summary:** Output final metrics, specifically including "Features found in docs but missing in code", "Features found in code but missing in docs", and "Total discrepancies found between docs and code".

## Out of Scope
- Modifying any application source code.
- Creating or updating `AGENTS.md`, `CODEBASE_ARCHITECTURE.md`, `CODEBASE_DATAFLOW.md`, or `CODEBASE_MODULES.md` files.
- Running tests or deploying the application.
- Pausing for user input between features.