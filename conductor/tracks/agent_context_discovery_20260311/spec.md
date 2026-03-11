# Specification: Agent Context Discovery and Documentation (AGENTS.md)

## Overview
Recursively scan the entire project directory to create a complete `DIRECTORY_TREE.md` file, followed by a bottom-up generation or update of `AGENTS.md` files in every relevant directory. This documentation effort is completely autonomous and ensures AI agents have deep, context-aware instructions for each module.

## Functional Requirements
- **Directory Tree Generation:** Generate a `DIRECTORY_TREE.md` in the root folder capturing the full project structure.
- **Processing Order:** Process directories bottom-up (deepest first, root last).
- **Skip List:** Ignore the following directories: `node_modules`, `.git`, `__pycache__`, `.venv`, `dist`, `build`, `.next`, `coverage`.
- **Subdirectory AGENTS.md:** Create/Update with:
  - Purpose of the directory/module.
  - Key files and their roles.
  - Patterns, conventions, and rules.
  - Dependencies on/relationships with other modules.
  - Gotchas or important notes.
- **Root AGENTS.md:** Create/Update with:
  - Overall project purpose and architecture.
  - Tech stack and major dependencies.
  - Build, run, and test instructions.
  - High-level folder structure overview.
  - Links to all immediate subdirectory `AGENTS.md` files.
- **Update Strategy:** For existing `AGENTS.md` files (including root), make updates if required or remove and replace them entirely if they are too old or inaccurate.
- **Console Output:** Print `✓ Written: ./path/to/AGENTS.md` for successful writes and `⊘ Skipped: ./path/to/dir (excluded)` for skipped directories. Print a final summary of total directories scanned, files created, updated, and skipped.

## Out of Scope
- Modifying any application source code.
- Generating external API documentation.
- Running tests or deploying the application.