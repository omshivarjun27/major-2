"""Unit tests for MicroNavFormatter extensions (T-017).

Tests clock-position output, verbosity levels, and i18n string table.
"""

from core.vision.spatial import MicroNavFormatter
from shared.schemas import (
    BoundingBox,
    Direction,
    ObstacleRecord,
    Priority,
    SizeCategory,
    Verbosity,
)


def _make_obstacle(
    class_name: str = "chair",
    distance_m: float = 1.5,
    direction: Direction = Direction.SLIGHTLY_LEFT,
    priority: Priority = Priority.NEAR_HAZARD,
    action: str = "step right",
) -> ObstacleRecord:
    """Helper to build a minimal ObstacleRecord for formatter tests."""
    return ObstacleRecord(
        id="obj_1",
        class_name=class_name,
        bbox=BoundingBox(100, 100, 200, 200),
        centroid_px=(150, 150),
        distance_m=distance_m,
        direction=direction,
        direction_deg=-12.0,
        mask_confidence=0.7,
        detection_confidence=0.85,
        priority=priority,
        size_category=SizeCategory.MEDIUM,
        action_recommendation=action,
    )


class TestNavFormatter:
    """Tests for MicroNavFormatter clock, verbosity, and i18n extensions."""

    def test_clock_position_mapping(self):
        """Each Direction maps to the correct clock hour."""
        fmt = MicroNavFormatter()
        expected = {
            Direction.FAR_LEFT: 9,
            Direction.LEFT: 10,
            Direction.SLIGHTLY_LEFT: 11,
            Direction.CENTER: 12,
            Direction.SLIGHTLY_RIGHT: 1,
            Direction.RIGHT: 2,
            Direction.FAR_RIGHT: 3,
        }
        for direction, clock in expected.items():
            assert fmt._direction_to_clock(direction) == clock, f"{direction} should map to {clock}"

    def test_format_clock_position_output(self):
        """format_clock_position produces 'X o'clock' string."""
        fmt = MicroNavFormatter()
        obs = _make_obstacle(direction=Direction.LEFT, priority=Priority.NEAR_HAZARD)
        result = fmt.format_clock_position([obs])
        assert "10 o'clock" in result
        assert "Caution" in result

    def test_verbosity_terse(self):
        """Terse mode produces at most 8 words."""
        fmt = MicroNavFormatter()
        obs = _make_obstacle(distance_m=3.0, priority=Priority.FAR_HAZARD, direction=Direction.RIGHT)
        result = fmt.format_with_verbosity([obs], Verbosity.TERSE)
        word_count = len(result.split())
        assert word_count <= 8, f"Terse output has {word_count} words: '{result}'"

    def test_verbosity_normal_matches_short_cue(self):
        """NORMAL verbosity matches format_short_cue output."""
        fmt = MicroNavFormatter()
        obs = _make_obstacle()
        assert fmt.format_with_verbosity([obs], Verbosity.NORMAL) == fmt.format_short_cue([obs])

    def test_verbosity_verbose_matches_format_verbose(self):
        """VERBOSE verbosity matches format_verbose output."""
        fmt = MicroNavFormatter()
        obs = _make_obstacle()
        assert fmt.format_with_verbosity([obs], Verbosity.VERBOSE) == fmt.format_verbose([obs])

    def test_i18n_string_table_english(self):
        """_get_string resolves English templates with kwargs."""
        fmt = MicroNavFormatter(locale="en")
        assert fmt._get_string("stop") == "Stop!"
        assert fmt._get_string("meters", dist="3") == "3 meters"
        assert fmt._get_string("at_clock", clock=10) == "at 10 o'clock"
        assert "detected" in fmt._get_string("detected_at", class_name="chair", dist="2m", direction="left")

    def test_format_with_empty_obstacles(self):
        """All three verbosity levels handle empty obstacle list gracefully."""
        fmt = MicroNavFormatter()
        assert fmt.format_with_verbosity([], Verbosity.TERSE) == "Clear."
        assert fmt.format_with_verbosity([], Verbosity.NORMAL) == "Path clear."
        assert "clear" in fmt.format_with_verbosity([], Verbosity.VERBOSE).lower()
