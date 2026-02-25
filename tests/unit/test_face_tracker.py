import itertools
from typing import Iterable, List

import pytest

from core.face.face_detector import FaceDetection
from core.face.face_tracker import FaceTracker, TrackerConfig
from shared.schemas import BoundingBox, Detection

_FACE_COUNTER = itertools.count()


@pytest.fixture
def tracker() -> FaceTracker:
    config = TrackerConfig(max_tracked=5, max_disappeared=3)
    return FaceTracker(config=config)


def make_detection(x1: int, y1: int, x2: int, y2: int, conf: float = 0.9) -> Detection:
    return Detection(
        id=f"det_{next(_FACE_COUNTER)}",
        class_name="face",
        confidence=conf,
        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
    )


def _to_face_detection(detection: Detection) -> FaceDetection:
    return FaceDetection(
        face_id=detection.id,
        bbox=(
            detection.bbox.x1,
            detection.bbox.y1,
            detection.bbox.x2,
            detection.bbox.y2,
        ),
        confidence=detection.confidence,
        timestamp_ms=1.0,
    )


def _as_face_detections(detections: Iterable[Detection]) -> List[FaceDetection]:
    return [_to_face_detection(det) for det in detections]


def _get_tracked(tracker: FaceTracker) -> List:
    get_tracked = getattr(tracker, "get_tracked", None)
    if callable(get_tracked):
        return get_tracked()
    return tracker.get_active_tracks()


def _compute_iou(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
    if hasattr(FaceTracker, "_compute_iou"):
        return FaceTracker._compute_iou(box_a, box_b)
    return FaceTracker._iou(box_a, box_b)


def test_initial_frame_creates_tracks(tracker: FaceTracker) -> None:
    detections = [make_detection(0, 0, 10, 10), make_detection(20, 20, 30, 30)]

    tracked = tracker.update(_as_face_detections(detections))

    assert len(tracked) == 2
    assert len({track.track_id for track in tracked}) == 2


def test_same_face_keeps_track_id(tracker: FaceTracker) -> None:
    first_update = tracker.update(_as_face_detections([make_detection(0, 0, 10, 10)]))
    original_id = first_update[0].track_id

    second_update = tracker.update(_as_face_detections([make_detection(0, 0, 10, 10)]))

    assert len(second_update) == 1
    assert second_update[0].track_id == original_id


def test_disappeared_face_removed(tracker: FaceTracker) -> None:
    tracker.update(_as_face_detections([make_detection(0, 0, 10, 10)]))

    tracked = []
    for _ in range(4):
        tracked = tracker.update([])

    assert tracked == []
    assert tracker.count() == 0


def test_max_tracked_limit(tracker: FaceTracker) -> None:
    detections = [make_detection(x, x, x + 10, x + 10) for x in range(8)]

    tracked = tracker.update(_as_face_detections(detections))

    assert len(tracked) == 5
    assert tracker.count() == 5


def test_iou_computation_identical_boxes() -> None:
    iou = _compute_iou((0, 0, 10, 10), (0, 0, 10, 10))

    assert iou == pytest.approx(1.0)


def test_iou_computation_no_overlap() -> None:
    iou = _compute_iou((0, 0, 10, 10), (20, 20, 30, 30))

    assert iou == pytest.approx(0.0)


def test_clear_resets_all_state(tracker: FaceTracker) -> None:
    tracker.update(_as_face_detections([make_detection(0, 0, 10, 10), make_detection(20, 20, 30, 30)]))

    tracker.clear()

    assert tracker.count() == 0
    assert _get_tracked(tracker) == []


def test_health_reports_counts(tracker: FaceTracker) -> None:
    tracker.update(_as_face_detections([make_detection(0, 0, 10, 10), make_detection(20, 20, 30, 30)]))

    health = tracker.health()

    assert health.get("track_count", health.get("total_tracks")) == 2
    assert health.get("active_tracks", 2) == 2
    assert health["config"]["max_disappeared"] == 3

    if "frame_count" in health:
        assert health["frame_count"] >= 1
