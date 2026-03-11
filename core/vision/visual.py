import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from livekit import rtc
from PIL import Image

# Performance constants - ULTRA-LOW-LATENCY MODE
MAX_IMAGE_SIZE = (480, 360)  # Aggressive reduction for speed
SPATIAL_IMAGE_SIZE = (240, 180)  # Tiny for spatial processing
MAX_OBSTACLES = 2  # Strict limit
FRAME_BUFFER_SIZE = 1  # Single frame - no buffering delay
SPATIAL_COOLDOWN_MS = 300  # Minimum ms between spatial calls

# Import spatial perception module
from .spatial import NavigationOutput, ObstacleRecord, Priority, SpatialProcessor, create_spatial_processor

# Simple logger without custom handler, will use root logger's config
logger = logging.getLogger("visual-processor")


def convert_video_frame_to_pil(frame) -> Optional[Image.Image]:
    """
    FAST convert LiveKit VideoFrame to PIL Image.
    Explicitly releases intermediate buffers to avoid memory build-up.
    """
    try:
        # Already PIL Image - fast path
        if isinstance(frame, Image.Image):
            return frame

        # LiveKit VideoFrame with convert method
        if hasattr(frame, 'convert'):
            rgba_frame = frame.convert(rtc.VideoBufferType.RGBA)
            img = Image.frombytes('RGBA', (rgba_frame.width, rgba_frame.height), bytes(rgba_frame.data))
            # Release RGBA buffer immediately
            del rgba_frame
            rgb = img.convert('RGB')
            img.close()
            del img
            return rgb

        # Direct data access fallback
        if hasattr(frame, 'data') and hasattr(frame, 'width'):
            width, height = frame.width, frame.height
            data = bytes(frame.data)
            data_len = len(data)

            if data_len == width * height * 4:
                rgba = Image.frombytes('RGBA', (width, height), data)
                rgb = rgba.convert('RGB')
                rgba.close()
                del rgba, data
                return rgb
            elif data_len == width * height * 3:
                return Image.frombytes('RGB', (width, height), data)

        logger.warning(f"Unknown frame type: {type(frame)}")
        return None

    except Exception as e:
        logger.error(f"Frame conversion error: {e}")
        return None


def resize_image_for_processing(img: Image.Image, max_size: Tuple[int, int] = MAX_IMAGE_SIZE) -> Image.Image:
    """FAST resize - use NEAREST for speed, BILINEAR for quality."""
    if img.width <= max_size[0] and img.height <= max_size[1]:
        return img

    ratio = min(max_size[0] / img.width, max_size[1] / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    # BILINEAR is 2-3x faster than LANCZOS with acceptable quality
    return img.resize(new_size, Image.Resampling.BILINEAR)


class VisualProcessor:
    """
    ULTRA-LOW-LATENCY visual processor.
    Single-frame capture, aggressive caching, minimal memory.
    Target: <100ms frame capture + processing.

    NEW: Each captured frame is tagged with a timestamp and frame_id
    for freshness validation downstream.
    """

    __slots__ = (
        'latest_frame', '_frames_buffer', '_buffer_size', '_cached_video_track',
        '_persistent_stream', '_stream_track_sid',
        '_enable_spatial', '_spatial_processor', '_last_nav_output', '_last_obstacles',
        '_spatial_cooldown', '_last_spatial_time',
        '_frame_sequence', '_last_capture_epoch_ms', '_last_frame_id',
    )

    def __init__(self, enable_spatial: bool = True):
        self.latest_frame: Optional[Image.Image] = None
        self._frames_buffer: List[Image.Image] = []
        self._buffer_size = FRAME_BUFFER_SIZE
        self._cached_video_track: Optional[rtc.RemoteVideoTrack] = None
        self._persistent_stream: Optional[rtc.VideoStream] = None
        self._stream_track_sid: Optional[str] = None

        # Spatial perception (lazy init for speed)
        self._enable_spatial = enable_spatial
        self._spatial_processor: Optional[SpatialProcessor] = None
        self._last_nav_output: Optional[NavigationOutput] = None
        self._last_obstacles: List[ObstacleRecord] = []
        self._spatial_cooldown = SPATIAL_COOLDOWN_MS / 1000.0
        self._last_spatial_time = 0.0

        # Frame identity tracking
        self._frame_sequence: int = 0
        self._last_capture_epoch_ms: float = 0.0
        self._last_frame_id: str = ""

        if enable_spatial:
            self._init_spatial_processor()

    def _init_spatial_processor(self):
        """Initialize spatial processor with FAST defaults.

        Auto-detects YOLO and MiDaS model files on disk so that
        `SPATIAL_USE_YOLO` / `SPATIAL_USE_MIDAS` env-vars default to
        *true* when the corresponding ONNX file is present.
        """
        try:
            yolo_path = os.environ.get("YOLO_MODEL_PATH", "models/yolov8n.onnx")
            midas_path = os.environ.get("MIDAS_MODEL_PATH", "models/midas_v21_small_256.onnx")

            # Auto-enable when model file present on disk
            use_yolo_env = os.environ.get("SPATIAL_USE_YOLO", "").lower()
            if use_yolo_env in ("true", "false"):
                use_yolo = use_yolo_env == "true"
            else:
                use_yolo = os.path.isfile(yolo_path)
                if use_yolo:
                    logger.info("YOLO model auto-detected at %s — enabling real detector", yolo_path)

            use_midas_env = os.environ.get("SPATIAL_USE_MIDAS", "").lower()
            if use_midas_env in ("true", "false"):
                use_midas = use_midas_env == "true"
            else:
                use_midas = os.path.isfile(midas_path)
                if use_midas:
                    logger.info("MiDaS model auto-detected at %s — enabling real depth", midas_path)

            # SPEED: Disable heavy features by default
            enable_segmentation = os.environ.get("ENABLE_SEGMENTATION", "false").lower() == "true"
            enable_depth_env = os.environ.get("ENABLE_DEPTH", "").lower()
            if enable_depth_env in ("true", "false"):
                enable_depth = enable_depth_env == "true"
            else:
                # Auto-enable depth when MiDaS is active
                enable_depth = use_midas or True  # SimpleDepth always available

            self._spatial_processor = create_spatial_processor(
                use_yolo=use_yolo,
                yolo_model_path=yolo_path if use_yolo else None,
                use_midas=use_midas,
                midas_model_path=midas_path if use_midas else None,
                enable_segmentation=enable_segmentation,
                enable_depth=enable_depth
            )
            mode = "REAL" if (use_yolo or use_midas) else "mock"
            logger.info("Spatial processor initialized (%s mode, yolo=%s, midas=%s)",
                        mode, use_yolo, use_midas)
        except Exception as e:
            logger.warning(f"Spatial processor init failed: {e}")
            self._spatial_processor = None

    @property
    def spatial_enabled(self) -> bool:
        """Check if spatial perception is enabled and ready"""
        return self._spatial_processor is not None and self._spatial_processor.is_ready

    @property
    def last_frame_id(self) -> str:
        """Get the frame_id of the most recently captured frame."""
        return self._last_frame_id

    @property
    def last_capture_epoch_ms(self) -> float:
        """Get the epoch_ms timestamp of the most recently captured frame."""
        return self._last_capture_epoch_ms

    def is_frame_fresh(self, max_age_ms: float = 500.0) -> bool:
        """Check if the most recent frame is within freshness budget."""
        if self._last_capture_epoch_ms <= 0:
            return False
        age = (time.time() * 1000) - self._last_capture_epoch_ms
        return age <= max_age_ms

    @property
    def last_navigation(self) -> Optional[NavigationOutput]:
        """Get last navigation output from spatial processing"""
        return self._last_nav_output

    @property
    def last_obstacles(self) -> List[ObstacleRecord]:
        """Get last detected obstacles"""
        return self._last_obstacles

    async def process_spatial(self, image: Optional[Image.Image] = None) -> Optional[NavigationOutput]:
        """
        FAST spatial perception with rate limiting.
        Returns cached result if called too frequently.
        """
        if not self._spatial_processor:
            return None

        # Rate limiting - return cached result if too soon
        current_time = time.time()
        if current_time - self._last_spatial_time < self._spatial_cooldown:
            return self._last_nav_output

        frame = image or self.latest_frame
        if frame is None:
            return None

        try:
            # Convert if needed
            if not isinstance(frame, Image.Image):
                pil_image = convert_video_frame_to_pil(frame)
                if pil_image is None:
                    return None
            else:
                pil_image = frame

            # FAST resize
            pil_image = resize_image_for_processing(pil_image, SPATIAL_IMAGE_SIZE)

            nav_output = await self._spatial_processor.process_frame(pil_image)
            self._last_nav_output = nav_output
            self._last_obstacles = self._spatial_processor.last_obstacles[:MAX_OBSTACLES]
            self._last_spatial_time = current_time

            return nav_output
        except Exception as e:
            logger.error(f"Spatial processing error: {e}")
            return None

    async def get_quick_warning(self, image: Optional[Image.Image] = None) -> str:
        """
        Get immediate hazard warning (low-latency path).
        Bypasses full pipeline for critical obstacles.
        """
        if not self._spatial_processor:
            return "Spatial perception not available."

        frame = image or self.latest_frame
        if frame is None:
            return "No frame available."

        try:
            # Convert VideoFrame to PIL Image if needed
            if not isinstance(frame, Image.Image):
                pil_image = convert_video_frame_to_pil(frame)
                if pil_image is None:
                    return "Unable to process frame."
            else:
                pil_image = frame

            return await self._spatial_processor.get_quick_warning(pil_image)
        except Exception as e:
            logger.error(f"Quick warning error: {e}")
            return "Unable to assess obstacles."

    def get_spatial_context(self) -> str:
        """
        Get spatial context summary for LLM prompts.
        Returns text description of obstacles for inclusion in vision context.
        """
        if not self._last_obstacles:
            return "No obstacles currently detected."

        lines = ["Detected obstacles:"]
        for obs in self._last_obstacles[:5]:  # Limit to top 5
            lines.append(
                f"- {obs.class_name}: {obs.distance_m:.1f}m {obs.direction.value}, "
                f"priority={obs.priority.value}"
            )
        return "\n".join(lines)

    async def enable_camera(self, room: rtc.Room) -> None:
        """Send a signal to enable the camera for the remote participant."""
        logger.info("Enabling camera...")
        try:
            await room.local_participant.publish_data(
                "camera_enable", reliable=True, topic="camera"
            )
            logger.info("Camera enable signal sent")
        except Exception as e:
            logger.error(f"Error enabling camera: {e}")
            raise

    async def get_video_track(self, room: rtc.Room, timeout: float = 10.0) -> rtc.RemoteVideoTrack:
        """
        Sets up video track handling using LiveKit's subscription model.
        Returns the first available video track or raises TimeoutError.
        """
        # Return cached track if available
        if self._cached_video_track is not None:
            return self._cached_video_track

        logger.info("Waiting for video track...")
        video_track_future = asyncio.Future[rtc.RemoteVideoTrack]()

        # Check existing tracks first
        for participant in room.remote_participants.values():
            logger.info(f"Checking participant: {participant.identity}")
            for pub in participant.track_publications.values():
                if (pub.track and
                    pub.track.kind == rtc.TrackKind.KIND_VIDEO and
                    isinstance(pub.track, rtc.RemoteVideoTrack)):

                    logger.info(f"Found existing video track: {pub.track.sid}")
                    self._cached_video_track = pub.track
                    return self._cached_video_track

        # Set up listener for future video tracks
        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.TrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            if (not video_track_future.done() and
                track.kind == rtc.TrackKind.KIND_VIDEO and
                isinstance(track, rtc.RemoteVideoTrack)):

                logger.info(f"Subscribed to video track: {track.sid}")
                self._cached_video_track = track
                video_track_future.set_result(track)

        # Add timeout in case no video track arrives
        try:
            track = await asyncio.wait_for(video_track_future, timeout=timeout)
            return track
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for video track after {timeout} seconds")
            raise TimeoutError(f"No video track received within {timeout} seconds")

    async def capture_frame(self, room: rtc.Room) -> Optional[Image.Image]:
        """FAST single frame capture — reuses a persistent VideoStream to avoid memory leaks."""
        try:
            # Get video track (cached)
            if self._cached_video_track is None:
                video_track = await self.get_video_track(room, timeout=5.0)
            else:
                video_track = self._cached_video_track

            # Create or reuse a single persistent VideoStream
            if not hasattr(self, "_persistent_stream") or self._persistent_stream is None:
                self._persistent_stream = rtc.VideoStream(video_track)
                self._stream_track_sid = getattr(video_track, "sid", None)
                logger.info("Created persistent VideoStream for frame capture")

            # If the track changed, recreate the stream
            current_sid = getattr(video_track, "sid", None)
            if current_sid != self._stream_track_sid:
                try:
                    await self._persistent_stream.aclose()
                except Exception:
                    pass
                self._persistent_stream = rtc.VideoStream(video_track)
                self._stream_track_sid = current_sid
                logger.info("Recreated VideoStream — track changed")

            # Pull a single frame from the persistent stream
            async for event in self._persistent_stream:
                frame = event.frame
                self.latest_frame = frame
                # Tag with identity for freshness tracking
                self._frame_sequence += 1
                self._last_capture_epoch_ms = time.time() * 1000
                self._last_frame_id = f"frm_{self._frame_sequence:08d}"
                return frame

            return self.latest_frame

        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            # Reset stream on error so next call creates a fresh one
            self._persistent_stream = None
            return None

    def get_latest_frame(self) -> Optional[Image.Image]:
        """Get the most recently captured frame."""
        return self.latest_frame

    async def capture_and_analyze_spatial(self, room: rtc.Room) -> Tuple[Optional[Image.Image], Optional[NavigationOutput]]:
        """
        Capture frame and run spatial analysis in one call.
        Returns tuple of (image, navigation_output).
        """
        image = await self.capture_frame(room)
        if image is None:
            return None, None

        nav_output = await self.process_spatial(image)
        return image, nav_output

    def has_critical_obstacles(self) -> bool:
        """Check if any critical obstacles are detected"""
        return any(obs.priority == Priority.CRITICAL for obs in self._last_obstacles)

    def get_obstacle_summary(self) -> Dict[str, Any]:
        """Get structured summary of detected obstacles"""
        if not self._last_obstacles:
            return {"count": 0, "obstacles": [], "has_critical": False}

        return {
            "count": len(self._last_obstacles),
            "obstacles": [obs.to_dict() for obs in self._last_obstacles],
            "has_critical": self.has_critical_obstacles(),
            "short_cue": self._last_nav_output.short_cue if self._last_nav_output else None
        }
