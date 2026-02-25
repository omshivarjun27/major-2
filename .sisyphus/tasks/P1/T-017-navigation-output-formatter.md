# T-017: navigation-output-formatter

> Phase: P1 | Cluster: CL-VIS | Risk: Low | State: not_started

## Objective

Extend `MicroNavFormatter` in `core/vision/spatial.py` with three new capabilities:
a clock-position output mode (12-hour clockface directions), configurable verbosity
levels (terse, normal, verbose), and internationalization placeholder hooks for future
language support.

The current formatter (lines 805-907) has `format_short_cue()` and `format_verbose()`
but no way to express directions as clock positions ("chair at 10 o'clock"), no
single method that adjusts detail level dynamically, and no path toward localized
strings. Blind users familiar with clock-position spatial references will benefit
from this alternative output mode, and the verbosity control lets downstream
consumers (TTS, Braille display, REST API) request the right level of detail.

## Current State (Codebase Audit 2026-02-25)

- `MicroNavFormatter` (lines 805-907):
  - `MICRO_NAV_SYSTEM_PROMPT` (lines 812-826): LLM prompt template for navigation
    cues. Uses direction words ("ahead", "left", "right").
  - `format_short_cue()` (lines 828-864): Generates a TTS-ready string ~15 words max.
    Rounds distance to nearest 0.5 m. Prefixes: "Stop!" for CRITICAL, "Caution," for
    NEAR_HAZARD. Appends action recommendation for critical/near obstacles.
  - `format_verbose()` (lines 866-892): Multi-sentence prose. Reports direction in
    degrees (`abs(obs.direction_deg):.0f degrees`). Limits to 3 obstacles.
  - `format_telemetry()` (line 894): Returns `[obs.to_dict() for obs in obstacles]`.
  - `format_all()` (lines 898-907): Returns `NavigationOutput(short_cue, verbose, telemetry, has_critical)`.
- `Direction` enum (shared/schemas): FAR_LEFT, LEFT, SLIGHTLY_LEFT, CENTER,
  SLIGHTLY_RIGHT, RIGHT, FAR_RIGHT. Values are human-readable strings.
- `SpatialFuser._calculate_direction()` (lines 661-685) uses `HORIZONTAL_FOV=70`
  degrees, thresholds at -25, -15, -5, 5, 15, 25 degrees.
- No clock-position mapping exists anywhere in the codebase.
- No verbosity levels or i18n infrastructure in the formatter.
- `NavigationOutput` dataclass has: `short_cue`, `verbose_description`, `telemetry`,
  `has_critical`. No field for clock position or verbosity metadata.

## Implementation Plan

### Step 1: Add clock-position mapping

Create a method `_direction_to_clock()` that maps `Direction` enum values to clock
positions. The mapping follows standard orientation where 12 o'clock is directly
ahead.

```python
DIRECTION_TO_CLOCK = {
    Direction.FAR_LEFT: 9,
    Direction.LEFT: 10,
    Direction.SLIGHTLY_LEFT: 11,
    Direction.CENTER: 12,
    Direction.SLIGHTLY_RIGHT: 1,
    Direction.RIGHT: 2,
    Direction.FAR_RIGHT: 3,
}

def _direction_to_clock(self, direction: Direction) -> int:
    return self.DIRECTION_TO_CLOCK.get(direction, 12)
```

### Step 2: Implement format_clock_position()

New method that generates cues using clock positions instead of cardinal directions.

```python
def format_clock_position(self, obstacles: List[ObstacleRecord]) -> str:
    if not obstacles:
        return "All clear."
    top = obstacles[0]
    clock = self._direction_to_clock(top.direction)
    dist = round(top.distance_m * 2) / 2
    if top.priority == Priority.CRITICAL:
        return f"Stop! {top.class_name.title()} at {clock} o'clock, {dist:.1g} meters."
    elif top.priority == Priority.NEAR_HAZARD:
        return f"Caution, {top.class_name} at {clock} o'clock, {dist:.1g} meters."
    return f"{top.class_name.title()} at {clock} o'clock, {dist:.0f} meters."
```

### Step 3: Implement format_with_verbosity()

A unified method that takes a verbosity level and delegates to the appropriate
format function.

```python
from enum import Enum

class Verbosity(Enum):
    TERSE = "terse"      # max 8 words, critical info only
    NORMAL = "normal"    # current short_cue behavior
    VERBOSE = "verbose"  # current format_verbose behavior

def format_with_verbosity(
    self, obstacles: List[ObstacleRecord], verbosity: Verbosity = Verbosity.NORMAL
) -> str:
    if verbosity == Verbosity.TERSE:
        return self._format_terse(obstacles)
    elif verbosity == Verbosity.VERBOSE:
        return self.format_verbose(obstacles)
    return self.format_short_cue(obstacles)

def _format_terse(self, obstacles: List[ObstacleRecord]) -> str:
    if not obstacles:
        return "Clear."
    top = obstacles[0]
    dist = round(top.distance_m)
    dir_short = top.direction.value.split()[-1]  # "left", "right", "ahead"
    if top.priority == Priority.CRITICAL:
        return f"Stop! {dir_short}."
    return f"{top.class_name} {dist}m {dir_short}."
```

### Step 4: Add i18n string table placeholders

Create a localization structure that holds all user-facing strings. Start with
English, and provide a clear extension point for additional languages.

```python
_STRINGS = {
    "en": {
        "path_clear": "Path clear.",
        "all_clear": "All clear.",
        "clear_terse": "Clear.",
        "stop": "Stop!",
        "caution": "Caution,",
        "at_clock": "at {clock} o'clock",
        "meters": "{dist} meters",
        "meter": "{dist} meter",
        "step_right": "step right",
        "step_left": "step left",
        "stop_reassess": "stop and reassess",
        "proceed_caution": "proceed with caution",
        "critical_hazard": "This is a critical hazard requiring immediate attention.",
        "near_hazard": "This is a near hazard.",
        "detected_at": "A {class_name} is detected {dist} {direction} of center.",
    }
}

def _get_string(self, key: str, **kwargs) -> str:
    template = self._strings.get(key, key)
    return template.format(**kwargs) if kwargs else template
```

### Step 5: Add Verbosity enum to shared schemas

Add the `Verbosity` enum to `shared/schemas/__init__.py` so other modules can
import it. Keep it alongside `Priority` and `Direction`.

### Step 6: Update format_all() to accept verbosity and clock_mode

Extend the signature to optionally include clock-position output in telemetry
and respect verbosity for the short cue.

### Step 7: Write 5 unit tests

Cover clock mapping, verbosity levels, i18n string resolution, edge cases, and
output consistency.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_nav_formatter.py` | 5+ unit tests for MicroNavFormatter extensions |

## Files to Modify

| File | Change |
|------|--------|
| `core/vision/spatial.py` | Add `format_clock_position()`, `format_with_verbosity()`, `_format_terse()`, `_direction_to_clock()`, `_STRINGS` table, and `_get_string()` to MicroNavFormatter |
| `shared/schemas/__init__.py` | Add `Verbosity` enum (TERSE, NORMAL, VERBOSE) |
| `core/vision/AGENTS.md` | Document new formatter methods, clock mapping, verbosity levels, i18n hooks |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_nav_formatter.py` | `test_clock_position_mapping` - verify each Direction maps to correct clock hour (e.g., FAR_LEFT=9, CENTER=12, FAR_RIGHT=3) |
| | `test_format_clock_position_output` - create obstacles at known positions, verify output contains "X o'clock" |
| | `test_verbosity_terse` - verify terse mode produces max 8 words, no extra detail |
| | `test_verbosity_normal_matches_short_cue` - verify NORMAL produces same output as format_short_cue |
| | `test_verbosity_verbose_matches_format_verbose` - verify VERBOSE produces same output as format_verbose |
| | `test_i18n_string_table_english` - verify all English strings resolve correctly with format kwargs |
| | `test_format_with_empty_obstacles` - verify all three verbosity levels handle empty list gracefully |

## Acceptance Criteria

- [ ] `format_clock_position()` returns string with "{N} o'clock" direction for each obstacle
- [ ] Clock mapping: FAR_LEFT=9, LEFT=10, SLIGHTLY_LEFT=11, CENTER=12, SLIGHTLY_RIGHT=1, RIGHT=2, FAR_RIGHT=3
- [ ] `format_with_verbosity(obstacles, Verbosity.TERSE)` returns max 8 words
- [ ] `format_with_verbosity(obstacles, Verbosity.NORMAL)` matches `format_short_cue()` output
- [ ] `format_with_verbosity(obstacles, Verbosity.VERBOSE)` matches `format_verbose()` output
- [ ] `_STRINGS["en"]` contains all user-facing strings as a localization table
- [ ] `_get_string()` resolves templates with keyword arguments
- [ ] `Verbosity` enum added to `shared/schemas/__init__.py`
- [ ] All format methods handle empty obstacle list without exceptions
- [ ] Existing `format_short_cue()` and `format_verbose()` behavior unchanged (backward compat)
- [ ] All unit tests pass: `pytest tests/unit/test_nav_formatter.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean
- [ ] `core/vision/AGENTS.md` updated

## Upstream Dependencies

T-016 (spatial-fusion-pipeline). The formatter extensions are self-contained, but
validating them against real pipeline output requires T-016 to be complete. Unit
tests can use manually constructed `ObstacleRecord` objects without T-016.

## Downstream Unblocks

T-021 (TTS integration for navigation output)

## Estimated Scope

- New code: ~120 LOC (clock mapping ~15, format methods ~50, i18n table ~30, Verbosity enum ~10, _get_string ~15)
- Modified code: ~10 lines in spatial.py (format_all signature), ~5 lines in shared/schemas
- Tests: ~100 LOC
- Risk: Low. All changes are additive. Existing formatter methods keep their signatures
  and behavior. The i18n structure is a placeholder dictionary, not a full gettext
  system, which keeps scope small while providing a clear upgrade path. The Verbosity
  enum addition to shared/schemas is backward compatible since no existing code
  references it.
