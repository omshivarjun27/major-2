"""
Session Logger for Spatial Perception Pipeline
===============================================

Logs frame-by-frame telemetry data including detections, navigation cues,
latency metrics, and system state for offline analysis and debugging.

Usage:
    # Import and use in your application
    from tests.realtime.session_logger import SessionRecorder

    recorder = SessionRecorder("my_session")
    recorder.log_frame(frame, nav_output, obstacles, metrics)
    recorder.close()

Author: Ally Vision Team
"""

import gzip
import json
import logging
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger("session-logger")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FrameRecord:
    """Record for a single frame"""
    frame_id: int
    timestamp: float
    relative_time_ms: float

    # Navigation output
    navigation_cue: str
    has_critical: bool

    # Obstacles
    obstacle_count: int
    obstacles: List[Dict[str, Any]]

    # Performance metrics
    latency_ms: float
    fps: float
    memory_mb: float

    # Frame metadata
    frame_width: int
    frame_height: int
    frame_checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionMetadata:
    """Metadata for a recording session"""
    session_id: str
    start_time: str
    end_time: str = ""

    # Configuration
    detector_type: str = ""
    depth_type: str = ""
    segmentation_enabled: bool = False
    depth_enabled: bool = True

    # Camera info
    camera_index: int = 0
    frame_width: int = 0
    frame_height: int = 0
    target_fps: float = 30.0

    # Session stats
    total_frames: int = 0
    duration_seconds: float = 0.0
    avg_latency_ms: float = 0.0
    avg_fps: float = 0.0

    # Annotations
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    environment: str = ""  # desk, indoor, outdoor

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# SESSION RECORDER
# =============================================================================

class SessionRecorder:
    """
    Records session data asynchronously to disk.

    Features:
    - Async logging with background writer thread
    - Frame subsampling for video recording
    - Compressed telemetry output
    - Automatic session summary
    """

    def __init__(
        self,
        session_name: Optional[str] = None,
        output_dir: str = "logs/sessions",
        save_video: bool = True,
        save_frames: bool = False,
        video_fps: float = 15.0,
        video_subsample: int = 2,  # Save every Nth frame
        compress_telemetry: bool = True
    ):
        self.session_name = session_name or datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.output_dir = Path(output_dir)
        self.save_video = save_video
        self.save_frames = save_frames
        self.video_fps = video_fps
        self.video_subsample = video_subsample
        self.compress_telemetry = compress_telemetry

        # Create session directory
        self.session_path = self.output_dir / self.session_name
        self.session_path.mkdir(parents=True, exist_ok=True)

        if self.save_frames:
            (self.session_path / "frames").mkdir(exist_ok=True)

        # Initialize metadata
        self.metadata = SessionMetadata(
            session_id=self.session_name,
            start_time=datetime.now().isoformat()
        )

        # State
        self.frame_count = 0
        self.start_timestamp: Optional[float] = None
        self.latencies: List[float] = []
        self.fps_values: List[float] = []

        # Video writer
        self.video_writer: Optional[cv2.VideoWriter] = None

        # Async logging
        self.log_queue: Queue = Queue(maxsize=1000)
        self.writer_thread: Optional[threading.Thread] = None
        self.is_running = False

        # Start background writer
        self._start_writer_thread()

        logger.info(f"Session recorder initialized: {self.session_path}")

    def _start_writer_thread(self):
        """Start background writer thread"""
        self.is_running = True

        # Open telemetry file
        telemetry_path = self.session_path / "telemetry.jsonl"
        if self.compress_telemetry:
            telemetry_path = self.session_path / "telemetry.jsonl.gz"
            self._telemetry_file = gzip.open(telemetry_path, "wt", encoding="utf-8")
        else:
            self._telemetry_file = open(telemetry_path, "w", encoding="utf-8")

        def writer_loop():
            while self.is_running or not self.log_queue.empty():
                try:
                    record = self.log_queue.get(timeout=0.1)
                    self._write_record(record)
                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"Writer error: {e}")

        self.writer_thread = threading.Thread(target=writer_loop, daemon=True)
        self.writer_thread.start()

    def _write_record(self, record: Dict[str, Any]):
        """Write a record to the telemetry file"""
        try:
            self._telemetry_file.write(json.dumps(record) + "\n")
            self._telemetry_file.flush()
        except Exception as e:
            logger.error(f"Failed to write record: {e}")

    def init_video(self, width: int, height: int):
        """Initialize video writer"""
        if not self.save_video:
            return

        self.metadata.frame_width = width
        self.metadata.frame_height = height

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_path = str(self.session_path / "recording.mp4")
        self.video_writer = cv2.VideoWriter(
            video_path, fourcc, self.video_fps, (width, height)
        )
        logger.info(f"Video writer initialized: {video_path}")

    def set_config(
        self,
        detector_type: str = "",
        depth_type: str = "",
        segmentation_enabled: bool = False,
        depth_enabled: bool = True,
        camera_index: int = 0,
        target_fps: float = 30.0
    ):
        """Set session configuration"""
        self.metadata.detector_type = detector_type
        self.metadata.depth_type = depth_type
        self.metadata.segmentation_enabled = segmentation_enabled
        self.metadata.depth_enabled = depth_enabled
        self.metadata.camera_index = camera_index
        self.metadata.target_fps = target_fps

    def set_environment(self, environment: str, notes: str = "", tags: List[str] = None):
        """Set environment metadata"""
        self.metadata.environment = environment
        self.metadata.notes = notes
        self.metadata.tags = tags or []

    def log_frame(
        self,
        frame: np.ndarray,
        navigation_cue: str,
        has_critical: bool,
        obstacles: List[Dict[str, Any]],
        latency_ms: float,
        fps: float,
        memory_mb: float = 0.0
    ):
        """
        Log a single frame.

        Args:
            frame: BGR numpy array
            navigation_cue: Current navigation text
            has_critical: Whether there's a critical obstacle
            obstacles: List of obstacle dictionaries
            latency_ms: Frame processing latency
            fps: Current FPS
            memory_mb: Current memory usage
        """
        self.frame_count += 1
        current_time = time.time()

        if self.start_timestamp is None:
            self.start_timestamp = current_time

        relative_time = (current_time - self.start_timestamp) * 1000

        # Track metrics
        self.latencies.append(latency_ms)
        self.fps_values.append(fps)

        # Create frame record
        record = FrameRecord(
            frame_id=self.frame_count,
            timestamp=current_time,
            relative_time_ms=relative_time,
            navigation_cue=navigation_cue,
            has_critical=has_critical,
            obstacle_count=len(obstacles),
            obstacles=obstacles,
            latency_ms=latency_ms,
            fps=fps,
            memory_mb=memory_mb,
            frame_width=frame.shape[1],
            frame_height=frame.shape[0],
            frame_checksum=str(hash(frame.tobytes()) % 100000)
        )

        # Queue for async writing
        try:
            self.log_queue.put_nowait(record.to_dict())
        except:
            pass  # Drop if queue full

        # Save video frame (with subsampling)
        if self.video_writer and self.frame_count % self.video_subsample == 0:
            self.video_writer.write(frame)

        # Save individual frame if enabled
        if self.save_frames and self.frame_count % 10 == 0:  # Every 10th frame
            frame_path = self.session_path / "frames" / f"frame_{self.frame_count:06d}.jpg"
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

    def add_event(self, event_type: str, details: Dict[str, Any] = None):
        """Log a discrete event (button press, mode change, etc.)"""
        event = {
            "type": "event",
            "event_type": event_type,
            "timestamp": time.time(),
            "frame_id": self.frame_count,
            "details": details or {}
        }
        try:
            self.log_queue.put_nowait(event)
        except:
            pass

    def add_annotation(self, text: str, severity: str = "info"):
        """Add a human annotation to the session"""
        annotation = {
            "type": "annotation",
            "text": text,
            "severity": severity,
            "timestamp": time.time(),
            "frame_id": self.frame_count
        }
        try:
            self.log_queue.put_nowait(annotation)
        except:
            pass

    def close(self):
        """Close session and write summary"""
        logger.info("Closing session recorder...")

        # Stop writer thread
        self.is_running = False
        if self.writer_thread:
            self.writer_thread.join(timeout=5.0)

        # Close telemetry file
        if hasattr(self, '_telemetry_file'):
            self._telemetry_file.close()

        # Close video writer
        if self.video_writer:
            self.video_writer.release()

        # Update metadata
        self.metadata.end_time = datetime.now().isoformat()
        self.metadata.total_frames = self.frame_count

        if self.start_timestamp:
            self.metadata.duration_seconds = time.time() - self.start_timestamp

        if self.latencies:
            self.metadata.avg_latency_ms = sum(self.latencies) / len(self.latencies)

        if self.fps_values:
            self.metadata.avg_fps = sum(self.fps_values) / len(self.fps_values)

        # Save metadata
        metadata_path = self.session_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

        # Generate summary
        self._write_summary()

        logger.info(f"Session saved: {self.session_path}")
        logger.info(f"  Frames: {self.frame_count}")
        logger.info(f"  Duration: {self.metadata.duration_seconds:.1f}s")
        logger.info(f"  Avg Latency: {self.metadata.avg_latency_ms:.1f}ms")

    def _write_summary(self):
        """Write human-readable summary"""
        summary_path = self.session_path / "summary.txt"

        with open(summary_path, "w") as f:
            f.write(f"Session: {self.session_name}\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"Start: {self.metadata.start_time}\n")
            f.write(f"End: {self.metadata.end_time}\n")
            f.write(f"Duration: {self.metadata.duration_seconds:.1f} seconds\n\n")

            f.write("Configuration:\n")
            f.write(f"  Detector: {self.metadata.detector_type}\n")
            f.write(f"  Depth: {self.metadata.depth_type}\n")
            f.write(f"  Segmentation: {self.metadata.segmentation_enabled}\n")
            f.write(f"  Environment: {self.metadata.environment}\n\n")

            f.write("Statistics:\n")
            f.write(f"  Total Frames: {self.frame_count}\n")
            f.write(f"  Avg Latency: {self.metadata.avg_latency_ms:.1f} ms\n")
            f.write(f"  Avg FPS: {self.metadata.avg_fps:.1f}\n\n")

            if self.metadata.notes:
                f.write(f"Notes: {self.metadata.notes}\n")

            if self.metadata.tags:
                f.write(f"Tags: {', '.join(self.metadata.tags)}\n")


# =============================================================================
# SESSION LOADER
# =============================================================================

class SessionLoader:
    """
    Loads and parses recorded session data.

    Usage:
        loader = SessionLoader("logs/sessions/my_session")
        metadata = loader.get_metadata()
        frames = loader.iter_frames()
    """

    def __init__(self, session_path: str):
        self.session_path = Path(session_path)

        if not self.session_path.exists():
            raise FileNotFoundError(f"Session not found: {session_path}")

        self._metadata: Optional[SessionMetadata] = None
        self._frame_cache: Dict[int, FrameRecord] = {}

    def get_metadata(self) -> SessionMetadata:
        """Load session metadata"""
        if self._metadata:
            return self._metadata

        metadata_path = self.session_path / "metadata.json"
        with open(metadata_path, "r") as f:
            data = json.load(f)

        self._metadata = SessionMetadata(**data)
        return self._metadata

    def iter_frames(self, start: int = 0, end: Optional[int] = None):
        """
        Iterate over frame records.

        Args:
            start: Starting frame index
            end: Ending frame index (exclusive)

        Yields:
            FrameRecord objects
        """
        telemetry_path = self.session_path / "telemetry.jsonl.gz"
        if not telemetry_path.exists():
            telemetry_path = self.session_path / "telemetry.jsonl"

        opener = gzip.open if str(telemetry_path).endswith('.gz') else open

        with opener(telemetry_path, "rt", encoding="utf-8") as f:
            frame_idx = 0
            for line in f:
                data = json.loads(line)

                # Skip events and annotations
                if data.get("type") in ("event", "annotation"):
                    continue

                if frame_idx < start:
                    frame_idx += 1
                    continue

                if end is not None and frame_idx >= end:
                    break

                yield FrameRecord(**data)
                frame_idx += 1

    def get_frame(self, frame_id: int) -> Optional[FrameRecord]:
        """Get a specific frame by ID"""
        if frame_id in self._frame_cache:
            return self._frame_cache[frame_id]

        for record in self.iter_frames():
            if record.frame_id == frame_id:
                self._frame_cache[frame_id] = record
                return record

        return None

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all events from the session"""
        events = []

        telemetry_path = self.session_path / "telemetry.jsonl.gz"
        if not telemetry_path.exists():
            telemetry_path = self.session_path / "telemetry.jsonl"

        opener = gzip.open if str(telemetry_path).endswith('.gz') else open

        with opener(telemetry_path, "rt", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("type") == "event":
                    events.append(data)

        return events

    def get_annotations(self) -> List[Dict[str, Any]]:
        """Get all annotations from the session"""
        annotations = []

        telemetry_path = self.session_path / "telemetry.jsonl.gz"
        if not telemetry_path.exists():
            telemetry_path = self.session_path / "telemetry.jsonl"

        opener = gzip.open if str(telemetry_path).endswith('.gz') else open

        with opener(telemetry_path, "rt", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("type") == "annotation":
                    annotations.append(data)

        return annotations

    def get_video_path(self) -> Optional[Path]:
        """Get path to recording video"""
        video_path = self.session_path / "recording.mp4"
        return video_path if video_path.exists() else None

    def get_frame_image_path(self, frame_id: int) -> Optional[Path]:
        """Get path to saved frame image"""
        # Try exact frame
        frame_path = self.session_path / "frames" / f"frame_{frame_id:06d}.jpg"
        if frame_path.exists():
            return frame_path

        # Find nearest saved frame
        frames_dir = self.session_path / "frames"
        if not frames_dir.exists():
            return None

        saved_frames = sorted(frames_dir.glob("frame_*.jpg"))
        if not saved_frames:
            return None

        # Find closest
        closest = min(saved_frames, key=lambda p: abs(int(p.stem.split("_")[1]) - frame_id))
        return closest

    def compute_statistics(self) -> Dict[str, Any]:
        """Compute detailed statistics from the session"""
        latencies = []
        fps_values = []
        obstacle_counts = []
        critical_frames = 0

        for record in self.iter_frames():
            latencies.append(record.latency_ms)
            fps_values.append(record.fps)
            obstacle_counts.append(record.obstacle_count)
            if record.has_critical:
                critical_frames += 1

        if not latencies:
            return {}

        import statistics as stats

        return {
            "total_frames": len(latencies),
            "latency": {
                "mean": stats.mean(latencies),
                "median": stats.median(latencies),
                "stdev": stats.stdev(latencies) if len(latencies) > 1 else 0,
                "min": min(latencies),
                "max": max(latencies),
                "p95": sorted(latencies)[int(len(latencies) * 0.95)],
                "p99": sorted(latencies)[int(len(latencies) * 0.99)]
            },
            "fps": {
                "mean": stats.mean(fps_values),
                "min": min(fps_values),
                "max": max(fps_values)
            },
            "obstacles": {
                "mean": stats.mean(obstacle_counts),
                "max": max(obstacle_counts),
                "total_detections": sum(obstacle_counts)
            },
            "critical_frames": critical_frames,
            "critical_frame_ratio": critical_frames / len(latencies)
        }


# =============================================================================
# ANALYSIS UTILITIES
# =============================================================================

def compare_sessions(session_paths: List[str]) -> Dict[str, Any]:
    """Compare statistics across multiple sessions"""
    results = {}

    for path in session_paths:
        loader = SessionLoader(path)
        metadata = loader.get_metadata()
        stats = loader.compute_statistics()

        results[metadata.session_id] = {
            "metadata": metadata.to_dict(),
            "statistics": stats
        }

    return results


def export_to_csv(session_path: str, output_path: str):
    """Export session telemetry to CSV"""
    import csv

    loader = SessionLoader(session_path)

    with open(output_path, "w", newline="") as f:
        writer = None

        for i, record in enumerate(loader.iter_frames()):
            record_dict = record.to_dict()

            # Flatten obstacles
            record_dict["obstacles"] = len(record_dict["obstacles"])

            if writer is None:
                writer = csv.DictWriter(f, fieldnames=record_dict.keys())
                writer.writeheader()

            writer.writerow(record_dict)

    logger.info(f"Exported to: {output_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Session Logger Utilities")
    subparsers = parser.add_subparsers(dest="command")

    # List sessions
    list_parser = subparsers.add_parser("list", help="List recorded sessions")
    list_parser.add_argument("--dir", default="logs/sessions", help="Sessions directory")

    # Session info
    info_parser = subparsers.add_parser("info", help="Show session info")
    info_parser.add_argument("session", help="Session path")

    # Export to CSV
    export_parser = subparsers.add_parser("export", help="Export session to CSV")
    export_parser.add_argument("session", help="Session path")
    export_parser.add_argument("--output", "-o", required=True, help="Output CSV path")

    # Compare sessions
    compare_parser = subparsers.add_parser("compare", help="Compare sessions")
    compare_parser.add_argument("sessions", nargs="+", help="Session paths")

    args = parser.parse_args()

    if args.command == "list":
        sessions_dir = Path(args.dir)
        if sessions_dir.exists():
            for session_dir in sorted(sessions_dir.iterdir()):
                if session_dir.is_dir():
                    print(f"  {session_dir.name}")

    elif args.command == "info":
        loader = SessionLoader(args.session)
        metadata = loader.get_metadata()
        stats = loader.compute_statistics()

        print(f"\nSession: {metadata.session_id}")
        print(f"Duration: {metadata.duration_seconds:.1f}s")
        print(f"Frames: {metadata.total_frames}")
        print(f"Avg Latency: {stats.get('latency', {}).get('mean', 0):.1f}ms")
        print(f"Avg FPS: {stats.get('fps', {}).get('mean', 0):.1f}")

    elif args.command == "export":
        export_to_csv(args.session, args.output)

    elif args.command == "compare":
        results = compare_sessions(args.sessions)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
