# Specification: Comprehensive Feature Mapping Analysis

## Overview
Perform a full, autonomous Feature Mapping analysis of the entire codebase by thoroughly reading every source code file. The objective is to identify, document, and map the dependency chains for every distinct capability the project exposes. The output will be a highly structured `FEATURE_MAP.md` and an accompanying machine-readable `FEATURE_MAP.json`.

## Functional Requirements
- **Strategy:** Utilize a script or sub-agent to autonomously read and process every valid source code file.
- **Skip List:** Ignore the following directories: `node_modules`, `.git`, `__pycache__`, `.venv`, `dist`, `build`, `.next`, `coverage`.
- **Feature Discovery:** Read existing `AGENTS.md` files for context, then read ALL unskipped source, test, config, and environment files to identify actual user-facing and system-level features based on ground truth code.
- **Dependency Tracing:** For each feature, follow actual import/call chains to document:
  - Entry points (routes, CLI, UI).
  - Relevant files and folders.
  - Shared utilities/services, database models/schemas.
  - External APIs, environment variables, and config keys.
  - Dependent and dependency features.
- **Data Output:** 
  - Generate `FEATURE_MAP.json` to represent the mapped dependency graph.
  - Generate `FEATURE_MAP.md` matching a strict block structure per feature: Description, Entry Point, Status, Files, Folders, Dependencies, Connected Features, Debug Entry Points, and Code Insights.
  - Include an **Index Table** at the top of `FEATURE_MAP.md`.
  - Include an **Orphaned Files/Folders** section at the bottom of `FEATURE_MAP.md`.
- **Progress Tracking:** Output `📖 Reading: ./path/to/file.ext` and `✓ Mapped: [Feature Name] — X files read, Y dependencies traced` to the console without pausing.
- **Completion Summary:** Output final metrics (total features, total source files read, referenced files, hotspot shared files, unread files).

## Out of Scope
- Modifying any application source code.
- Creating or updating `AGENTS.md` files.
- Running tests or deploying the application.
- Pausing for user input between features.