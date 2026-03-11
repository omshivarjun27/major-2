# Implementation Plan: Agent Context Discovery

## Phase 1: Setup and Pre-scan [checkpoint: 0aba7dc]
- [x] Task: Map the directory tree recursively, ignoring the skip list (`node_modules`, `.git`, `__pycache__`, `.venv`, `dist`, `build`, `.next`, `coverage`). 19188d7
- [x] Task: Write the mapped tree structure to `DIRECTORY_TREE.md` in the root directory. 19188d7
- [x] Task: Conductor - User Manual Verification 'Setup and Pre-scan' (Protocol in workflow.md)

## Phase 2: Bottom-Up Directory Processing
- [ ] Task: Determine the bottom-up order for all un-skipped directories.
- [ ] Task: For each valid subdirectory, analyze its contents to understand purpose, files, patterns, dependencies, and gotchas.
- [ ] Task: Create or update `AGENTS.md` in each subdirectory with the analyzed information and log `✓ Written: ./path/to/AGENTS.md`. Log `⊘ Skipped: ...` for excluded paths.
- [ ] Task: Conductor - User Manual Verification 'Bottom-Up Directory Processing' (Protocol in workflow.md)

## Phase 3: Root Directory Processing and Completion
- [ ] Task: Process the root directory: analyze the project to summarize overall architecture, tech stack, build instructions, and folder structure.
- [ ] Task: Create or update `AGENTS.md` in the root directory with the project summary and links to immediate subdirectory `AGENTS.md` files.
- [ ] Task: Output the final completion summary (total scanned, created, updated, skipped directories).
- [ ] Task: Conductor - User Manual Verification 'Root Directory Processing and Completion' (Protocol in workflow.md)