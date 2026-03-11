# Analysis Context

## Purpose
Module responsible for analysis functionality.

## Key Files
- `analysis_report.json`: Implementation/configuration file.
- `architecture_risks.md`: Implementation/configuration file.
- `ci_summary.json`: Implementation/configuration file.
- `component_inventory.json`: Implementation/configuration file.
- `data_flows.md`: Implementation/configuration file.
- `data_model_inventory.json`: Implementation/configuration file.
- `entry_points.json`: Implementation/configuration file.
- `hybrid_readiness.md`: Implementation/configuration file.
- `language_summary.json`: Implementation/configuration file.
- `phase1_summary.md`: Implementation/configuration file.
- ... and 8 more files.

## Patterns and Conventions
- Follow standard Python naming conventions.
- Maintain modularity and single responsibility.
- Refer to `conductor/` or root guidelines for specific architectural patterns.

## Dependencies
- Interacts with sibling modules and shared utilities.
- Relies on core/ and shared/ components.

## Gotchas and Important Notes
- Ensure paths are resolved relative to the project root.
- Watch out for circular dependencies when importing from other modules.
