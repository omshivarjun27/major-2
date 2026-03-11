# Braille Context

## Purpose
Module responsible for braille functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `braille_capture.py`: Implementation/configuration file.
- `braille_classifier.py`: Implementation/configuration file.
- `braille_ocr.py`: Implementation/configuration file.
- `braille_segmenter.py`: Implementation/configuration file.
- `embossing_guidance.py`: Implementation/configuration file.
- `scenario_analysis.md`: Implementation/configuration file.
- `__init__.py`: Implementation/configuration file.

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
