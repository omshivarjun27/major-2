# Implementation Plan: Cross-Referenced Feature Mapping

## Phase 1: Documentation Parsing and Pre-analysis [checkpoint: f9b716c]
- [x] Task: Create a script or sub-agent harness to systematically crawl the directory tree, respecting the skip list. a3b978b
- [x] Task: Parse `CODEBASE_ARCHITECTURE.md`, `CODEBASE_DATAFLOW.md`, `CODEBASE_MODULES.md`, and all `AGENTS.md` files to extract the documented feature inventory and expected data flows. a3b978b
- [x] Task: Conductor - User Manual Verification 'Documentation Parsing and Pre-analysis' (Protocol in workflow.md)

## Phase 2: Full Codebase Read and Discovery
- [~] Task: Execute the file reader to ingest every valid source, config, and test file, logging `📖 Reading: ./path/to/file` for progress.
- [~] Task: Identify primary entry points (routes, CLI commands) and distinctly categorize them into features based on the ground truth code.
- [~] Task: Merge the code-discovered features with the document-discovered features, assigning the correct "Source" tags (e.g., "Documented but not implemented").
- [ ] Task: Conductor - User Manual Verification 'Full Codebase Read and Discovery' (Protocol in workflow.md)

## Phase 3: Dependency Tracing and Discrepancy Validation
- [~] Task: Trace import chains and function calls for each identified feature to map out connected files, folders, shared services, and DB schemas.
- [~] Task: Cross-reference the traced dependency graph against the expectations from `CODEBASE_DATAFLOW.md` and generate discrepancy warnings. Log `✓ Mapped: [Feature Name]...` as they complete.
- [~] Task: Analyze the graph to identify orphaned files/folders (not attached to any feature) and hot-spot shared files.
- [ ] Task: Conductor - User Manual Verification 'Dependency Tracing and Discrepancy Validation' (Protocol in workflow.md)

## Phase 4: Output Generation and Summary
- [ ] Task: Generate and save the parsed dependency graph as `FEATURE_MAP.json`.
- [ ] Task: Generate `FEATURE_MAP.md` matching the specified structure, including the index table, Doc vs Code section, and orphaned files section.
- [ ] Task: Output the final completion summary with metrics (total features, missing docs, missing code, discrepancies, hotspots, etc.) to the console.
- [ ] Task: Conductor - User Manual Verification 'Output Generation and Summary' (Protocol in workflow.md)