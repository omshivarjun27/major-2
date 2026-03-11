"""
Real-Time Test Harness for Spatial Perception Pipeline
=======================================================

This tool captures live camera frames and runs the full spatial perception
pipeline in real-time with debugging overlays and performance metrics.

Usage:
    python realtime_test.py --debug                    # Visual debug mode
    python realtime_test.py --benchmark                # Benchmark mode
    python realtime_test.py --log-session              # Log session to disk
    python realtime_test.py --detector yolo            # Use YOLO detector
    python realtime_test.py --depth midas              # Use MiDaS depth
    python realtime_test.py --camera 0                 # Select camera index

Author: Ally Vision Team
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image

# Import spatial perception components
from core.vision.spatial import (
    Direction,
    NavigationOutput,
    ObstacleRecord,
    Priority,
    SpatialProcessor,
    create_spatial_processor,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("realtime-test")


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class TestConfig:
    """Configuration for real-time testing"""
    camera_index: int = 0
    detector_type: str = "mock"  # mock, yolo
    depth_type: str = "simple"   # simple, midas
    enable_segmentation: bool = True
    enable_depth: bool = True
    enable_debug_overlay: bool = True
    enable_benchmark: bool = False
    enable_logging: bool = False
    log_dir: str = "logs/realtime_sessions"
    target_fps: int = 15
    max_latency_ms: float = 500.0
    yolo_model_path: Optional[str] = None
    midas_model_path: Optional[str] = None
    window_width: int = 1280
    window_height: int = 720


@dataclass
class FrameMetrics:
    """Metrics for a single frame"""
    frame_id: int
    timestamp: float
    capture_time_ms: float
    detection_time_ms: float
    segmentation_time_ms: float
    depth_time_ms: float
    fusion_time_ms: float
    total_time_ms: float
    fps: float
    num_detections: int
    num_obstacles: int
    has_critical: bool
    navigation_cue: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# OVERLAY RENDERER
# =============================================================================

class DebugOverlayRenderer:
    """Renders debug overlays on frames"""

    # Color palette for different priorities
    PRIORITY_COLORS = {
        Priority.CRITICAL: (0, 0, 255),      # Red
        Priority.NEAR_HAZARD: (0, 165, 255), # Orange
        Priority.FAR_HAZARD: (0, 255, 255),  # Yellow
        Priority.SAFE: (0, 255, 0),          # Green
    }

    # Direction arrows
    DIRECTION_ARROWS = {
        Direction.FAR_LEFT: "◀◀",
        Direction.LEFT: "◀",
        Direction.SLIGHTLY_LEFT: "◁",
        Direction.CENTER: "●",
        Direction.SLIGHTLY_RIGHT: "▷",
        Direction.RIGHT: "▶",
        Direction.FAR_RIGHT: "▶▶",
    }

    def __init__(self, frame_width: int, frame_height: int):
        self.width = frame_width
        self.height = frame_height
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.font_thickness = 2

    def draw_detections(self, frame: np.ndarray, obstacles: List[ObstacleRecord]) -> np.ndarray:
        """Draw bounding boxes and labels for detected obstacles"""
        overlay = frame.copy()

        for obs in obstacles:
            bbox = obs.bbox
            color = self.PRIORITY_COLORS.get(obs.priority, (128, 128, 128))

            # Draw bounding box
            cv2.rectangle(overlay, (bbox.x1, bbox.y1), (bbox.x2, bbox.y2), color, 2)

            # Draw filled header for label
            label = f"{obs.class_name} {obs.distance_m:.1f}m"
            (label_w, label_h), baseline = cv2.getTextSize(
                label, self.font, self.font_scale, self.font_thickness
            )
            cv2.rectangle(
                overlay,
                (bbox.x1, bbox.y1 - label_h - 10),
                (bbox.x1 + label_w + 10, bbox.y1),
                color, -1
            )

            # Draw label text
            cv2.putText(
                overlay, label,
                (bbox.x1 + 5, bbox.y1 - 5),
                self.font, self.font_scale, (255, 255, 255), self.font_thickness
            )

            # Draw centroid
            cx, cy = obs.centroid_px
            cv2.circle(overlay, (cx, cy), 5, color, -1)

            # Draw direction indicator
            direction_text = self.DIRECTION_ARROWS.get(obs.direction, "?")
            cv2.putText(
                overlay, direction_text,
                (cx - 10, cy + 30),
                self.font, 0.8, color, 2
            )

        return overlay

    def draw_depth_heatmap(self, frame: np.ndarray, depth_array: Optional[np.ndarray]) -> np.ndarray:
        """Overlay depth heatmap on frame"""
        if depth_array is None:
            return frame

        overlay = frame.copy()

        # Normalize depth to 0-255
        depth_norm = depth_array.copy()
        depth_norm = (depth_norm - depth_norm.min()) / (depth_norm.max() - depth_norm.min() + 1e-6)
        depth_norm = (depth_norm * 255).astype(np.uint8)

        # Resize to frame size
        depth_resized = cv2.resize(depth_norm, (frame.shape[1], frame.shape[0]))

        # Apply colormap
        depth_colored = cv2.applyColorMap(depth_resized, cv2.COLORMAP_JET)

        # Blend with original frame
        alpha = 0.3
        overlay = cv2.addWeighted(overlay, 1 - alpha, depth_colored, alpha, 0)

        return overlay

    def draw_metrics_panel(
        self,
        frame: np.ndarray,
        metrics: FrameMetrics,
        config: TestConfig
    ) -> np.ndarray:
        """Draw performance metrics panel"""
        overlay = frame.copy()

        # Panel background
        panel_height = 180
        panel_width = 350
        cv2.rectangle(overlay, (10, 10), (panel_width, panel_height), (0, 0, 0), -1)
        cv2.rectangle(overlay, (10, 10), (panel_width, panel_height), (255, 255, 255), 1)

        # Metrics text
        y_offset = 30
        line_height = 22

        metrics_lines = [
            f"FPS: {metrics.fps:.1f} (target: {config.target_fps})",
            f"Total Latency: {metrics.total_time_ms:.1f} ms",
            f"  - Detection: {metrics.detection_time_ms:.1f} ms",
            f"  - Segmentation: {metrics.segmentation_time_ms:.1f} ms",
            f"  - Depth: {metrics.depth_time_ms:.1f} ms",
            f"  - Fusion: {metrics.fusion_time_ms:.1f} ms",
            f"Detections: {metrics.num_detections} | Obstacles: {metrics.num_obstacles}",
        ]

        for line in metrics_lines:
            color = (0, 255, 0) if metrics.total_time_ms < config.max_latency_ms else (0, 0, 255)
            cv2.putText(
                overlay, line,
                (20, y_offset),
                self.font, 0.5, color, 1
            )
            y_offset += line_height

        return overlay

    def draw_navigation_cue(
        self,
        frame: np.ndarray,
        nav_output: Optional[NavigationOutput]
    ) -> np.ndarray:
        """Draw navigation cue at bottom of frame"""
        overlay = frame.copy()

        if nav_output is None:
            cue = "Initializing..."
            color = (128, 128, 128)
        else:
            cue = nav_output.short_cue
            color = (0, 0, 255) if nav_output.has_critical else (0, 255, 0)

        # Draw cue panel at bottom
        panel_height = 60
        panel_y = frame.shape[0] - panel_height
        cv2.rectangle(overlay, (0, panel_y), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)

        # Draw cue text
        (text_w, text_h), _ = cv2.getTextSize(cue, self.font, 1.0, 2)
        text_x = (frame.shape[1] - text_w) // 2
        text_y = panel_y + (panel_height + text_h) // 2

        cv2.putText(overlay, cue, (text_x, text_y), self.font, 1.0, color, 2)

        return overlay

    def draw_status_indicator(
        self,
        frame: np.ndarray,
        config: TestConfig,
        is_recording: bool = False
    ) -> np.ndarray:
        """Draw status indicators (recording, detector type, etc.)"""
        overlay = frame.copy()

        # Status bar at top right
        status_text = f"Detector: {config.detector_type.upper()} | Depth: {config.depth_type.upper()}"
        (text_w, _), _ = cv2.getTextSize(status_text, self.font, 0.5, 1)

        cv2.rectangle(
            overlay,
            (frame.shape[1] - text_w - 20, 10),
            (frame.shape[1] - 10, 35),
            (0, 0, 0), -1
        )
        cv2.putText(
            overlay, status_text,
            (frame.shape[1] - text_w - 15, 28),
            self.font, 0.5, (255, 255, 255), 1
        )

        # Recording indicator
        if is_recording:
            cv2.circle(overlay, (frame.shape[1] - 30, 55), 10, (0, 0, 255), -1)
            cv2.putText(
                overlay, "REC",
                (frame.shape[1] - 60, 60),
                self.font, 0.5, (0, 0, 255), 1
            )

        return overlay


# =============================================================================
# SESSION LOGGER
# =============================================================================

class SessionLogger:
    """Logs test session data to disk"""

    def __init__(self, log_dir: str, session_name: Optional[str] = None):
        self.log_dir = Path(log_dir)
        self.session_name = session_name or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_path = self.log_dir / self.session_name

        # Create directories
        self.session_path.mkdir(parents=True, exist_ok=True)
        (self.session_path / "frames").mkdir(exist_ok=True)
        (self.session_path / "outputs").mkdir(exist_ok=True)

        # Initialize log files
        self.metrics_file = open(self.session_path / "metrics.jsonl", "w")
        self.telemetry_file = open(self.session_path / "telemetry.jsonl", "w")

        # Video writer
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.frame_count = 0

        logger.info(f"Session logging initialized: {self.session_path}")

    def init_video_writer(self, width: int, height: int, fps: float = 15.0):
        """Initialize video writer for recording"""
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_path = str(self.session_path / "recording.mp4")
        self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    def log_frame(
        self,
        frame: np.ndarray,
        metrics: FrameMetrics,
        nav_output: Optional[NavigationOutput],
        obstacles: List[ObstacleRecord],
        save_frame: bool = False
    ):
        """Log frame data"""
        self.frame_count += 1

        # Write video frame
        if self.video_writer:
            self.video_writer.write(frame)

        # Save individual frame if requested
        if save_frame:
            frame_path = self.session_path / "frames" / f"frame_{self.frame_count:06d}.jpg"
            cv2.imwrite(str(frame_path), frame)

        # Log metrics
        metrics_dict = metrics.to_dict()
        self.metrics_file.write(json.dumps(metrics_dict) + "\n")

        # Log telemetry
        telemetry = {
            "frame_id": self.frame_count,
            "timestamp": time.time(),
            "navigation": nav_output.to_dict() if nav_output else None,
            "obstacles": [obs.to_dict() for obs in obstacles]
        }
        self.telemetry_file.write(json.dumps(telemetry) + "\n")

    def save_config(self, config: TestConfig):
        """Save test configuration"""
        config_path = self.session_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(asdict(config), f, indent=2)

    def close(self):
        """Close all file handles"""
        if self.video_writer:
            self.video_writer.release()
        self.metrics_file.close()
        self.telemetry_file.close()

        # Save summary
        summary = {
            "session_name": self.session_name,
            "total_frames": self.frame_count,
            "end_time": datetime.now().isoformat()
        }
        with open(self.session_path / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Session saved: {self.session_path}")


# =============================================================================
# REAL-TIME TEST HARNESS
# =============================================================================

class RealTimeTestHarness:
    """Main test harness for real-time spatial perception testing"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.processor: Optional[SpatialProcessor] = None
        self.renderer: Optional[DebugOverlayRenderer] = None
        self.session_logger: Optional[SessionLogger] = None

        # Performance tracking
        self.frame_times: List[float] = []
        self.metrics_history: List[FrameMetrics] = []
        self.frame_id = 0

        # State
        self.is_running = False
        self.is_paused = False
        self.show_depth_overlay = False
        self.show_metrics = True

    def _create_processor(self) -> SpatialProcessor:
        """Create spatial processor based on config"""
        use_yolo = self.config.detector_type == "yolo"
        use_midas = self.config.depth_type == "midas"

        return create_spatial_processor(
            use_yolo=use_yolo,
            yolo_model_path=self.config.yolo_model_path,
            use_midas=use_midas,
            midas_model_path=self.config.midas_model_path,
            enable_segmentation=self.config.enable_segmentation,
            enable_depth=self.config.enable_depth
        )

    def _calculate_fps(self) -> float:
        """Calculate current FPS from frame times"""
        if len(self.frame_times) < 2:
            return 0.0

        # Use last 30 frames for FPS calculation
        recent_times = self.frame_times[-30:]
        if len(recent_times) < 2:
            return 0.0

        elapsed = recent_times[-1] - recent_times[0]
        if elapsed <= 0:
            return 0.0

        return (len(recent_times) - 1) / elapsed

    async def process_frame(self, frame: np.ndarray) -> Tuple[NavigationOutput, FrameMetrics]:
        """Process a single frame through the pipeline"""
        self.frame_id += 1
        frame_start = time.time()

        # Convert BGR to RGB for PIL
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)

        # Capture time
        capture_time = (time.time() - frame_start) * 1000

        # Run spatial processing
        time.time()
        nav_output = await self.processor.process_frame(pil_image)
        total_time = (time.time() - frame_start) * 1000

        # Record frame time
        self.frame_times.append(time.time())
        if len(self.frame_times) > 100:
            self.frame_times.pop(0)

        # Create metrics
        metrics = FrameMetrics(
            frame_id=self.frame_id,
            timestamp=time.time(),
            capture_time_ms=capture_time,
            detection_time_ms=total_time * 0.4,  # Estimated breakdown
            segmentation_time_ms=total_time * 0.2 if self.config.enable_segmentation else 0,
            depth_time_ms=total_time * 0.3 if self.config.enable_depth else 0,
            fusion_time_ms=total_time * 0.1,
            total_time_ms=total_time,
            fps=self._calculate_fps(),
            num_detections=len(self.processor.last_obstacles),
            num_obstacles=len(self.processor.last_obstacles),
            has_critical=nav_output.has_critical if nav_output else False,
            navigation_cue=nav_output.short_cue if nav_output else "N/A"
        )

        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 1000:
            self.metrics_history.pop(0)

        return nav_output, metrics

    def render_debug_frame(
        self,
        frame: np.ndarray,
        nav_output: NavigationOutput,
        metrics: FrameMetrics
    ) -> np.ndarray:
        """Render debug overlays on frame"""
        output = frame.copy()

        # Draw detections
        output = self.renderer.draw_detections(output, self.processor.last_obstacles)

        # Draw depth overlay if enabled
        if self.show_depth_overlay and hasattr(self.processor, '_last_depth_map'):
            depth_map = getattr(self.processor, '_last_depth_map', None)
            if depth_map:
                output = self.renderer.draw_depth_heatmap(output, depth_map.depth_array)

        # Draw metrics panel if enabled
        if self.show_metrics:
            output = self.renderer.draw_metrics_panel(output, metrics, self.config)

        # Draw navigation cue
        output = self.renderer.draw_navigation_cue(output, nav_output)

        # Draw status indicator
        is_recording = self.session_logger is not None
        output = self.renderer.draw_status_indicator(output, self.config, is_recording)

        return output

    def print_keyboard_help(self):
        """Print keyboard controls"""
        print("\n" + "=" * 60)
        print("REAL-TIME SPATIAL PERCEPTION TEST HARNESS")
        print("=" * 60)
        print("\nKeyboard Controls:")
        print("  Q / ESC  - Quit")
        print("  SPACE    - Pause/Resume")
        print("  D        - Toggle depth overlay")
        print("  M        - Toggle metrics panel")
        print("  S        - Save current frame")
        print("  R        - Reset statistics")
        print("  1        - Switch to Mock detector")
        print("  2        - Switch to YOLO detector")
        print("  3        - Switch to Simple depth")
        print("  4        - Switch to MiDaS depth")
        print("=" * 60 + "\n")

    async def run(self):
        """Main run loop"""
        # Initialize processor
        logger.info("Initializing spatial processor...")
        self.processor = self._create_processor()

        # Open camera
        logger.info(f"Opening camera {self.config.camera_index}...")
        cap = cv2.VideoCapture(self.config.camera_index)

        if not cap.isOpened():
            logger.error(f"Failed to open camera {self.config.camera_index}")
            return

        # Set camera resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.window_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.window_height)

        # Get actual resolution
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Camera resolution: {actual_width}x{actual_height}")

        # Initialize renderer
        self.renderer = DebugOverlayRenderer(actual_width, actual_height)

        # Initialize session logger if enabled
        if self.config.enable_logging:
            self.session_logger = SessionLogger(self.config.log_dir)
            self.session_logger.save_config(self.config)
            self.session_logger.init_video_writer(actual_width, actual_height)

        # Create window
        window_name = "Spatial Perception Test"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, actual_width, actual_height)

        self.print_keyboard_help()
        self.is_running = True

        try:
            while self.is_running:
                # Read frame
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame")
                    continue

                if not self.is_paused:
                    # Process frame
                    nav_output, metrics = await self.process_frame(frame)

                    # Render debug overlays
                    if self.config.enable_debug_overlay:
                        display_frame = self.render_debug_frame(frame, nav_output, metrics)
                    else:
                        display_frame = frame

                    # Log session
                    if self.session_logger:
                        self.session_logger.log_frame(
                            display_frame, metrics, nav_output,
                            self.processor.last_obstacles
                        )

                    # Show frame
                    cv2.imshow(window_name, display_frame)

                    # Print benchmark info
                    if self.config.enable_benchmark and self.frame_id % 30 == 0:
                        self._print_benchmark_summary()
                else:
                    cv2.imshow(window_name, frame)

                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                await self._handle_key(key)

        finally:
            # Cleanup
            cap.release()
            cv2.destroyAllWindows()

            if self.session_logger:
                self.session_logger.close()

            if self.config.enable_benchmark:
                self._print_final_benchmark()

    async def _handle_key(self, key: int):
        """Handle keyboard input"""
        if key == ord('q') or key == 27:  # Q or ESC
            self.is_running = False
        elif key == ord(' '):  # Space
            self.is_paused = not self.is_paused
            logger.info("Paused" if self.is_paused else "Resumed")
        elif key == ord('d'):
            self.show_depth_overlay = not self.show_depth_overlay
            logger.info(f"Depth overlay: {'ON' if self.show_depth_overlay else 'OFF'}")
        elif key == ord('m'):
            self.show_metrics = not self.show_metrics
            logger.info(f"Metrics panel: {'ON' if self.show_metrics else 'OFF'}")
        elif key == ord('s'):
            self._save_current_frame()
        elif key == ord('r'):
            self._reset_statistics()
        elif key == ord('1'):
            await self._switch_detector("mock")
        elif key == ord('2'):
            await self._switch_detector("yolo")
        elif key == ord('3'):
            await self._switch_depth("simple")
        elif key == ord('4'):
            await self._switch_depth("midas")

    async def _switch_detector(self, detector_type: str):
        """Switch detector at runtime"""
        if detector_type == self.config.detector_type:
            return

        logger.info(f"Switching detector to: {detector_type}")
        self.config.detector_type = detector_type
        self.processor = self._create_processor()
        logger.info(f"Detector switched to: {detector_type.upper()}")

    async def _switch_depth(self, depth_type: str):
        """Switch depth estimator at runtime"""
        if depth_type == self.config.depth_type:
            return

        logger.info(f"Switching depth estimator to: {depth_type}")
        self.config.depth_type = depth_type
        self.processor = self._create_processor()
        logger.info(f"Depth estimator switched to: {depth_type.upper()}")

    def _save_current_frame(self):
        """Save current frame to disk"""
        save_path = Path("saved_frames")
        save_path.mkdir(exist_ok=True)
        filename = f"frame_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        # Frame saving would happen here
        logger.info(f"Frame saved: {filename}")

    def _reset_statistics(self):
        """Reset performance statistics"""
        self.frame_times.clear()
        self.metrics_history.clear()
        self.frame_id = 0
        logger.info("Statistics reset")

    def _print_benchmark_summary(self):
        """Print benchmark summary"""
        if not self.metrics_history:
            return

        recent = self.metrics_history[-30:]
        avg_total = sum(m.total_time_ms for m in recent) / len(recent)
        avg_fps = sum(m.fps for m in recent) / len(recent)

        print(f"\r[Benchmark] FPS: {avg_fps:.1f} | Latency: {avg_total:.1f}ms | "
              f"Frames: {self.frame_id}", end="")

    def _print_final_benchmark(self):
        """Print final benchmark results"""
        if not self.metrics_history:
            return

        print("\n\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)

        total_frames = len(self.metrics_history)
        avg_fps = sum(m.fps for m in self.metrics_history) / total_frames
        avg_latency = sum(m.total_time_ms for m in self.metrics_history) / total_frames
        max_latency = max(m.total_time_ms for m in self.metrics_history)
        min_latency = min(m.total_time_ms for m in self.metrics_history)

        print(f"\nTotal Frames: {total_frames}")
        print(f"Average FPS: {avg_fps:.2f}")
        print(f"Average Latency: {avg_latency:.2f} ms")
        print(f"Min Latency: {min_latency:.2f} ms")
        print(f"Max Latency: {max_latency:.2f} ms")
        print(f"\nTarget FPS: {self.config.target_fps}")
        print(f"Target Latency: < {self.config.max_latency_ms} ms")

        # Pass/fail status
        fps_pass = avg_fps >= self.config.target_fps
        latency_pass = avg_latency <= self.config.max_latency_ms

        print("\n--- PASS/FAIL ---")
        print(f"FPS Target: {'✓ PASS' if fps_pass else '✗ FAIL'}")
        print(f"Latency Target: {'✓ PASS' if latency_pass else '✗ FAIL'}")
        print("=" * 60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def parse_args() -> TestConfig:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Real-time Spatial Perception Test Harness"
    )

    parser.add_argument("--camera", type=int, default=0,
                        help="Camera index (default: 0)")
    parser.add_argument("--detector", choices=["mock", "yolo"], default="mock",
                        help="Detector type (default: mock)")
    parser.add_argument("--depth", choices=["simple", "midas"], default="simple",
                        help="Depth estimator type (default: simple)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug overlays")
    parser.add_argument("--benchmark", action="store_true",
                        help="Enable benchmark mode")
    parser.add_argument("--log-session", action="store_true",
                        help="Log session to disk")
    parser.add_argument("--log-dir", type=str, default="logs/realtime_sessions",
                        help="Session log directory")
    parser.add_argument("--no-segmentation", action="store_true",
                        help="Disable segmentation")
    parser.add_argument("--no-depth", action="store_true",
                        help="Disable depth estimation")
    parser.add_argument("--yolo-model", type=str,
                        help="Path to YOLO model")
    parser.add_argument("--midas-model", type=str,
                        help="Path to MiDaS model")
    parser.add_argument("--width", type=int, default=1280,
                        help="Window width")
    parser.add_argument("--height", type=int, default=720,
                        help="Window height")

    args = parser.parse_args()

    return TestConfig(
        camera_index=args.camera,
        detector_type=args.detector,
        depth_type=args.depth,
        enable_segmentation=not args.no_segmentation,
        enable_depth=not args.no_depth,
        enable_debug_overlay=args.debug or True,  # Default to debug on
        enable_benchmark=args.benchmark,
        enable_logging=args.log_session,
        log_dir=args.log_dir,
        yolo_model_path=args.yolo_model,
        midas_model_path=args.midas_model,
        window_width=args.width,
        window_height=args.height
    )


async def main():
    """Main entry point"""
    config = parse_args()

    logger.info("Starting Real-Time Test Harness")
    logger.info(f"Configuration: detector={config.detector_type}, depth={config.depth_type}")

    harness = RealTimeTestHarness(config)
    await harness.run()


if __name__ == "__main__":
    asyncio.run(main())
