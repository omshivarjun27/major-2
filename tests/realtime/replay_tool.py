"""
Replay Tool for Spatial Perception Sessions
============================================

Replays recorded sessions with optional re-processing through the pipeline.
Useful for debugging, comparing configurations, and validating fixes.

Usage:
    python replay_tool.py SESSION_PATH              # Basic replay
    python replay_tool.py SESSION_PATH --reprocess  # Re-run through pipeline
    python replay_tool.py SESSION_PATH --compare    # Compare with new config
    python replay_tool.py SESSION_PATH --export-video  # Export annotated video

Author: Ally Vision Team
"""

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Generator, Optional, Tuple

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image
from session_logger import FrameRecord, SessionLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("replay-tool")


# =============================================================================
# REPLAY CONFIGURATION
# =============================================================================

@dataclass
class ReplayConfig:
    """Configuration for replay"""
    session_path: str
    playback_speed: float = 1.0
    start_frame: int = 0
    end_frame: Optional[int] = None
    show_original_cues: bool = True
    show_metrics: bool = True
    pause_on_critical: bool = False
    loop: bool = False
    reprocess: bool = False
    reprocess_detector: str = "mock"
    reprocess_depth: str = "simple"
    export_video: bool = False
    export_path: Optional[str] = None
    window_width: int = 1280
    window_height: int = 720


# =============================================================================
# VIDEO FRAME PROVIDER
# =============================================================================

class VideoFrameProvider:
    """Provides frames from recorded video"""

    def __init__(self, video_path: Path):
        self.video_path = video_path
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_count = 0
        self.fps = 0.0
        self.width = 0
        self.height = 0
        self._open()

    def _open(self):
        """Open video file"""
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video not found: {self.video_path}")

        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video: {self.video_path}")

        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Video: {self.frame_count} frames, {self.fps:.1f} FPS, {self.width}x{self.height}")

    def seek(self, frame_idx: int):
        """Seek to specific frame"""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read next frame"""
        return self.cap.read()

    def get_current_frame_idx(self) -> int:
        """Get current frame index"""
        return int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

    def close(self):
        """Close video"""
        if self.cap:
            self.cap.release()

    def __iter__(self) -> Generator[Tuple[int, np.ndarray], None, None]:
        """Iterate over all frames"""
        self.seek(0)
        frame_idx = 0
        while True:
            ret, frame = self.read()
            if not ret:
                break
            yield frame_idx, frame
            frame_idx += 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# =============================================================================
# REPLAY OVERLAY RENDERER
# =============================================================================

class ReplayOverlayRenderer:
    """Renders overlays during replay"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def draw_playback_bar(
        self,
        frame: np.ndarray,
        current_frame: int,
        total_frames: int,
        is_paused: bool,
        playback_speed: float
    ) -> np.ndarray:
        """Draw playback progress bar"""
        overlay = frame.copy()
        bar_height = 30
        bar_y = self.height - bar_height

        # Background
        cv2.rectangle(overlay, (0, bar_y), (self.width, self.height), (40, 40, 40), -1)

        # Progress bar
        progress = current_frame / max(total_frames, 1)
        bar_width = int(self.width * progress)
        cv2.rectangle(overlay, (0, bar_y + 5), (bar_width, self.height - 5), (0, 150, 255), -1)

        # Time/frame text
        time_text = f"Frame {current_frame}/{total_frames}"
        cv2.putText(overlay, time_text, (10, bar_y + 20), self.font, 0.5, (255, 255, 255), 1)

        # Playback status
        status = "⏸ PAUSED" if is_paused else f"▶ {playback_speed:.1f}x"
        cv2.putText(overlay, status, (self.width - 100, bar_y + 20), self.font, 0.5, (255, 255, 255), 1)

        return overlay

    def draw_telemetry_panel(
        self,
        frame: np.ndarray,
        record: FrameRecord
    ) -> np.ndarray:
        """Draw telemetry info panel"""
        overlay = frame.copy()

        # Panel background
        panel_width = 300
        panel_height = 150
        cv2.rectangle(overlay, (10, 10), (panel_width, panel_height), (0, 0, 0), -1)
        cv2.rectangle(overlay, (10, 10), (panel_width, panel_height), (100, 100, 100), 1)

        # Title
        cv2.putText(overlay, "REPLAY TELEMETRY", (20, 35), self.font, 0.6, (0, 255, 255), 1)

        # Metrics
        y = 60
        lines = [
            f"Frame ID: {record.frame_id}",
            f"Latency: {record.latency_ms:.1f} ms",
            f"FPS: {record.fps:.1f}",
            f"Obstacles: {record.obstacle_count}",
            f"Critical: {'YES' if record.has_critical else 'No'}"
        ]

        for line in lines:
            color = (0, 0, 255) if "Critical: YES" in line else (200, 200, 200)
            cv2.putText(overlay, line, (20, y), self.font, 0.45, color, 1)
            y += 18

        return overlay

    def draw_navigation_cue(
        self,
        frame: np.ndarray,
        cue: str,
        has_critical: bool,
        is_reprocessed: bool = False
    ) -> np.ndarray:
        """Draw navigation cue"""
        overlay = frame.copy()

        # Cue panel
        panel_height = 50
        panel_y = self.height - 80

        color = (0, 0, 200) if has_critical else (0, 150, 0)
        cv2.rectangle(overlay, (0, panel_y), (self.width, panel_y + panel_height), color, -1)

        # Label
        label = "REPROCESSED" if is_reprocessed else "ORIGINAL"
        cv2.putText(overlay, label, (10, panel_y + 20), self.font, 0.4, (255, 255, 255), 1)

        # Cue text
        (text_w, _), _ = cv2.getTextSize(cue, self.font, 0.7, 2)
        text_x = (self.width - text_w) // 2
        cv2.putText(overlay, cue, (text_x, panel_y + 35), self.font, 0.7, (255, 255, 255), 2)

        return overlay

    def draw_comparison_view(
        self,
        frame: np.ndarray,
        original_cue: str,
        original_critical: bool,
        new_cue: str,
        new_critical: bool
    ) -> np.ndarray:
        """Draw comparison between original and reprocessed results"""
        overlay = frame.copy()

        # Split panel
        panel_y = self.height - 100
        mid_x = self.width // 2

        # Original (left)
        color_orig = (0, 0, 200) if original_critical else (0, 150, 0)
        cv2.rectangle(overlay, (0, panel_y), (mid_x - 2, self.height - 30), color_orig, -1)
        cv2.putText(overlay, "ORIGINAL", (10, panel_y + 20), self.font, 0.4, (255, 255, 255), 1)
        cv2.putText(overlay, original_cue[:40], (10, panel_y + 45), self.font, 0.5, (255, 255, 255), 1)

        # New (right)
        color_new = (0, 0, 200) if new_critical else (0, 150, 0)
        cv2.rectangle(overlay, (mid_x + 2, panel_y), (self.width, self.height - 30), color_new, -1)
        cv2.putText(overlay, "REPROCESSED", (mid_x + 10, panel_y + 20), self.font, 0.4, (255, 255, 255), 1)
        cv2.putText(overlay, new_cue[:40], (mid_x + 10, panel_y + 45), self.font, 0.5, (255, 255, 255), 1)

        return overlay

    def draw_help_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw keyboard help overlay"""
        overlay = frame.copy()

        # Semi-transparent background
        help_overlay = np.zeros_like(frame)
        cv2.rectangle(help_overlay, (0, 0), (self.width, self.height), (0, 0, 0), -1)
        overlay = cv2.addWeighted(overlay, 0.3, help_overlay, 0.7, 0)

        # Help text
        help_lines = [
            "KEYBOARD CONTROLS",
            "",
            "SPACE     - Pause/Resume",
            "LEFT/RIGHT - Frame step (when paused)",
            "UP/DOWN   - Adjust playback speed",
            "R         - Restart from beginning",
            "T         - Toggle telemetry panel",
            "C         - Toggle comparison mode",
            "S         - Save current frame",
            "Q/ESC     - Quit",
            "",
            "Press H to hide this help"
        ]

        y = 100
        for i, line in enumerate(help_lines):
            color = (0, 255, 255) if i == 0 else (255, 255, 255)
            scale = 0.8 if i == 0 else 0.6
            cv2.putText(overlay, line, (50, y), self.font, scale, color, 2 if i == 0 else 1)
            y += 35

        return overlay


# =============================================================================
# REPLAY PLAYER
# =============================================================================

class ReplayPlayer:
    """Main replay player"""

    def __init__(self, config: ReplayConfig):
        self.config = config
        self.loader = SessionLoader(config.session_path)
        self.metadata = self.loader.get_metadata()

        # Video provider
        video_path = self.loader.get_video_path()
        if video_path:
            self.video_provider = VideoFrameProvider(video_path)
        else:
            self.video_provider = None
            logger.warning("No video recording found - telemetry only mode")

        # Renderer
        self.renderer = ReplayOverlayRenderer(
            self.video_provider.width if self.video_provider else 640,
            self.video_provider.height if self.video_provider else 480
        )

        # State
        self.is_paused = False
        self.show_telemetry = True
        self.show_help = False
        self.show_comparison = False
        self.current_frame = config.start_frame
        self.playback_speed = config.playback_speed

        # Frame records cache
        self._frame_records: Dict[int, FrameRecord] = {}
        self._load_frame_records()

        # Reprocessing
        self.processor = None
        if config.reprocess:
            self._init_processor()

    def _load_frame_records(self):
        """Load all frame records into memory"""
        logger.info("Loading frame records...")
        for record in self.loader.iter_frames():
            self._frame_records[record.frame_id] = record
        logger.info(f"Loaded {len(self._frame_records)} frame records")

    def _init_processor(self):
        """Initialize spatial processor for reprocessing"""
        try:
            from core.vision.spatial import create_spatial_processor

            use_yolo = self.config.reprocess_detector == "yolo"
            use_midas = self.config.reprocess_depth == "midas"

            self.processor = create_spatial_processor(
                use_yolo=use_yolo,
                use_midas=use_midas
            )
            logger.info(f"Processor initialized: {self.config.reprocess_detector}/{self.config.reprocess_depth}")
        except Exception as e:
            logger.error(f"Failed to initialize processor: {e}")
            self.processor = None

    async def reprocess_frame(self, frame: np.ndarray) -> Tuple[str, bool]:
        """Reprocess frame through pipeline"""
        if not self.processor:
            return "N/A", False

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            nav_output = await self.processor.process_frame(pil_image)
            return nav_output.short_cue, nav_output.has_critical
        except Exception as e:
            logger.error(f"Reprocess error: {e}")
            return "Error", False

    def get_frame_record(self, frame_idx: int) -> Optional[FrameRecord]:
        """Get frame record by index (with video subsample adjustment)"""
        # Account for video subsampling (every Nth frame saved)
        # This is approximate - we try to find the closest record
        for offset in range(10):
            if frame_idx + offset in self._frame_records:
                return self._frame_records[frame_idx + offset]
            if frame_idx - offset in self._frame_records:
                return self._frame_records[frame_idx - offset]

        # Fall back to first available
        if self._frame_records:
            return list(self._frame_records.values())[0]
        return None

    async def run(self):
        """Run replay"""
        if not self.video_provider:
            logger.error("No video to replay")
            return

        window_name = f"Replay: {self.metadata.session_id}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.config.window_width, self.config.window_height)

        # Video export
        video_writer = None
        if self.config.export_video:
            export_path = self.config.export_path or f"replay_{self.metadata.session_id}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                export_path, fourcc, self.video_provider.fps,
                (self.video_provider.width, self.video_provider.height)
            )
            logger.info(f"Exporting to: {export_path}")

        self.video_provider.seek(self.current_frame)

        logger.info("Starting replay (press H for help)")

        try:
            while True:
                if not self.is_paused:
                    ret, frame = self.video_provider.read()
                    if not ret:
                        if self.config.loop:
                            self.video_provider.seek(self.config.start_frame)
                            continue
                        else:
                            break

                    self.current_frame = self.video_provider.get_current_frame_idx()

                    # Check end frame
                    if self.config.end_frame and self.current_frame >= self.config.end_frame:
                        if self.config.loop:
                            self.video_provider.seek(self.config.start_frame)
                            continue
                        else:
                            break
                else:
                    # When paused, re-read current frame
                    self.video_provider.seek(max(0, self.current_frame - 1))
                    ret, frame = self.video_provider.read()
                    if not ret:
                        break

                # Get telemetry record
                record = self.get_frame_record(self.current_frame)

                # Draw overlays
                display_frame = frame.copy()

                if self.show_telemetry and record:
                    display_frame = self.renderer.draw_telemetry_panel(display_frame, record)

                # Navigation cue
                if record:
                    if self.show_comparison and self.config.reprocess:
                        new_cue, new_critical = await self.reprocess_frame(frame)
                        display_frame = self.renderer.draw_comparison_view(
                            display_frame,
                            record.navigation_cue, record.has_critical,
                            new_cue, new_critical
                        )
                    else:
                        display_frame = self.renderer.draw_navigation_cue(
                            display_frame,
                            record.navigation_cue,
                            record.has_critical
                        )

                # Playback bar
                display_frame = self.renderer.draw_playback_bar(
                    display_frame,
                    self.current_frame,
                    self.video_provider.frame_count,
                    self.is_paused,
                    self.playback_speed
                )

                # Help overlay
                if self.show_help:
                    display_frame = self.renderer.draw_help_overlay(display_frame)

                # Show frame
                cv2.imshow(window_name, display_frame)

                # Export frame
                if video_writer:
                    video_writer.write(display_frame)

                # Pause on critical
                if self.config.pause_on_critical and record and record.has_critical:
                    self.is_paused = True

                # Handle input
                wait_time = int(1000 / (self.video_provider.fps * self.playback_speed))
                wait_time = max(1, wait_time)

                key = cv2.waitKey(wait_time if not self.is_paused else 50) & 0xFF

                if not await self._handle_key(key):
                    break

        finally:
            if video_writer:
                video_writer.release()
            cv2.destroyAllWindows()
            self.video_provider.close()

    async def _handle_key(self, key: int) -> bool:
        """Handle keyboard input. Returns False to exit."""
        if key == ord('q') or key == 27:  # Q or ESC
            return False
        elif key == ord(' '):
            self.is_paused = not self.is_paused
        elif key == ord('h'):
            self.show_help = not self.show_help
        elif key == ord('t'):
            self.show_telemetry = not self.show_telemetry
        elif key == ord('c'):
            self.show_comparison = not self.show_comparison
        elif key == ord('r'):
            self.video_provider.seek(self.config.start_frame)
            self.current_frame = self.config.start_frame
        elif key == ord('s'):
            self._save_current_frame()
        elif key == 81 or key == 2:  # LEFT arrow
            if self.is_paused:
                self.current_frame = max(0, self.current_frame - 1)
        elif key == 83 or key == 3:  # RIGHT arrow
            if self.is_paused:
                self.current_frame = min(self.video_provider.frame_count - 1, self.current_frame + 1)
        elif key == 82 or key == 0:  # UP arrow
            self.playback_speed = min(4.0, self.playback_speed + 0.25)
        elif key == 84 or key == 1:  # DOWN arrow
            self.playback_speed = max(0.25, self.playback_speed - 0.25)

        return True

    def _save_current_frame(self):
        """Save current frame"""
        save_dir = Path("replay_captures")
        save_dir.mkdir(exist_ok=True)

        filename = f"capture_{self.metadata.session_id}_{self.current_frame:06d}.jpg"
        filepath = save_dir / filename

        # Get current frame
        self.video_provider.seek(max(0, self.current_frame - 1))
        ret, frame = self.video_provider.read()
        if ret:
            cv2.imwrite(str(filepath), frame)
            logger.info(f"Saved: {filepath}")


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Replay recorded sessions")

    parser.add_argument("session", help="Path to session directory")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Playback speed (default: 1.0)")
    parser.add_argument("--start", type=int, default=0,
                        help="Start frame")
    parser.add_argument("--end", type=int,
                        help="End frame")
    parser.add_argument("--loop", action="store_true",
                        help="Loop playback")
    parser.add_argument("--pause-on-critical", action="store_true",
                        help="Pause on critical obstacles")
    parser.add_argument("--reprocess", action="store_true",
                        help="Re-run frames through pipeline")
    parser.add_argument("--detector", default="mock",
                        choices=["mock", "yolo"],
                        help="Detector for reprocessing")
    parser.add_argument("--depth", default="simple",
                        choices=["simple", "midas"],
                        help="Depth estimator for reprocessing")
    parser.add_argument("--export-video", action="store_true",
                        help="Export annotated video")
    parser.add_argument("--export-path", type=str,
                        help="Export video path")
    parser.add_argument("--width", type=int, default=1280,
                        help="Window width")
    parser.add_argument("--height", type=int, default=720,
                        help="Window height")

    return parser.parse_args()


async def main():
    args = parse_args()

    config = ReplayConfig(
        session_path=args.session,
        playback_speed=args.speed,
        start_frame=args.start,
        end_frame=args.end,
        loop=args.loop,
        pause_on_critical=args.pause_on_critical,
        reprocess=args.reprocess,
        reprocess_detector=args.detector,
        reprocess_depth=args.depth,
        export_video=args.export_video,
        export_path=args.export_path,
        window_width=args.width,
        window_height=args.height
    )

    player = ReplayPlayer(config)
    await player.run()


if __name__ == "__main__":
    asyncio.run(main())
