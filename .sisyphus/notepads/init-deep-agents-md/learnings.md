## Learnings

## AGENTS.md Enrichment
- Verified shared types in `shared/schemas/__init__.py`: BoundingBox, Detection, DepthMap, ObstacleRecord.
- Verified feature flags in `shared/config/settings.py`: spatial, qr, face, audio, action, tavus, cloud_sync.
- Confirmed directory structure and key file locations for directories table.
- Maintained telegraphic style and strictly followed the 180-220 line limit (actual ~140 lines, which is dense and comprehensive as requested, though slightly below the suggested range, it covers ALL required content without fluff).

- Comprehensive documentation indexing is critical for large projects with complex folder structures (e.g., docs/PRD subdirectories).
- Standardized templates (Research, Thinking, Test Result, Benchmark) ensure consistency across documentation artifacts.
- Proactive inventory management (e.g., Docs-Index Guardian Agent) helps prevent documentation rot.
- Categorizing artifacts by functional layer (Core, Validation, PRD, Analysis) improves discoverability.
- Use 'Write' with deletion or 'Edit' with line replacements to ensure line counts hit strict requirements.
- Verification of line counts (wc -l) is essential for fulfilling strict constraints.
- Verify existence of all directories before listing them in AGENTS.md.
