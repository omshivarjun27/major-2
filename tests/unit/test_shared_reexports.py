# pyright: reportMissingTypeArgument=false
"""Tests for shared/__init__.py re-export cleanup (T-047).

Verifies:
- All canonical symbols are re-exported from shared (backward compat)
- shared.X is the same object as shared.schemas.X (single definition)
- __all__ lists every re-exported symbol
"""

import shared
import shared.schemas

# ---------------------------------------------------------------------------
# Canonical symbols that MUST be re-exported
# ---------------------------------------------------------------------------

EXPECTED_SYMBOLS = [
    # Enums
    "Priority",
    "Direction",
    "SizeCategory",
    "SpatialRelation",
    "Verbosity",
    # Core data structures
    "BoundingBox",
    "DepthMap",
    "Detection",
    "NavigationOutput",
    "ObstacleRecord",
    "OCRResult",
    "OCRWord",
    "PerceptionResult",
    "ReasoningResult",
    "SegmentationMask",
    # ABCs
    "DepthEstimator",
    "ObjectDetector",
    "Segmenter",
]


class TestSharedReExports:
    """Verify shared/__init__.py is a thin re-export of shared.schemas."""

    def test_all_expected_symbols_accessible(self) -> None:
        """Every canonical symbol is importable from shared."""
        for name in EXPECTED_SYMBOLS:
            assert hasattr(shared, name), f"shared.{name} missing"

    def test_identity_with_schemas(self) -> None:
        """shared.X is shared.schemas.X (same object, not a copy)."""
        for name in EXPECTED_SYMBOLS:
            obj_shared = getattr(shared, name)
            obj_schemas = getattr(shared.schemas, name)
            assert obj_shared is obj_schemas, (
                f"shared.{name} is not the same object as shared.schemas.{name}"
            )

    def test_all_list_complete(self) -> None:
        """__all__ contains every expected symbol."""
        all_set = set(shared.__all__)
        for name in EXPECTED_SYMBOLS:
            assert name in all_set, f"{name} missing from shared.__all__"

    def test_no_duplicate_definitions(self) -> None:
        """shared/__init__.py should NOT define classes itself (just re-export)."""
        import pathlib

        init_path = pathlib.Path(shared.__file__)
        source = init_path.read_text(encoding="utf-8")
        # Should not contain 'class Priority' etc. — only import statements
        for name in EXPECTED_SYMBOLS:
            assert f"class {name}" not in source, (
                f"shared/__init__.py still defines 'class {name}' — "
                "should only re-export from shared.schemas"
            )

    def test_file_is_compact(self) -> None:
        """shared/__init__.py should be under 80 lines (thin re-export)."""
        import pathlib

        init_path = pathlib.Path(shared.__file__)
        lines = init_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) < 80, (
            f"shared/__init__.py has {len(lines)} lines — "
            "expected < 80 for a thin re-export module"
        )
