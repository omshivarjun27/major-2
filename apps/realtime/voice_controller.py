# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Voice controller — extracted voice/search/QR logic from agent.py (T-040).

Owns STT routing, TTS dispatch, internet search, QR/AR scanning, and
stream processing.  Each public function accepts a ``UserData`` instance
and returns a user-facing string (or yields ``ChatChunk`` for streaming).
"""

import asyncio
import logging
import os
import time
from typing import Any, AsyncGenerator

logger = logging.getLogger("ally-voice-controller")


# ---------------------------------------------------------------------------
# Internet search
# ---------------------------------------------------------------------------

async def search_internet(userdata: Any, query: str) -> str:
    """Search for up-to-date information on the web."""
    userdata.current_tool = "internet"
    logger.info(f"Searching: {query[:30]}...")

    try:
        search_results = await userdata.internet_search.search(query)
        formatted_results = userdata.internet_search.format_results(search_results)
        response = f"Here's what I found about '{query}':\n\n{formatted_results}"
        userdata.last_response = response
        userdata.current_tool = "general"
        return response

    except Exception as e:
        logger.error(f"Error searching the internet: {e}")
        return f"I encountered an error while searching for information about '{query}': {str(e)}"


# ---------------------------------------------------------------------------
# QR / AR scanning
# ---------------------------------------------------------------------------

async def scan_qr_code(userdata: Any, query: str = "scan") -> str:
    """Scan for QR codes or AR tags using the camera.

    Captures a fresh frame, decodes any QR/AR content,
    and returns a contextual spoken message.
    """
    userdata.current_tool = "qr"
    logger.info(f"[QR] scan_qr_code invoked — query='{query}'")

    if not userdata._qr_enabled or not userdata._qr_scanner:
        logger.warning("[QR] QR scanning disabled or scanner not initialised")
        return "QR scanning is not available."

    try:
        # Step 1: Fresh frame capture
        logger.info("[QR] Capturing fresh camera frame…")
        from apps.realtime.vision_controller import capture_fresh_frame, check_frame_freshness

        raw_frame = await capture_fresh_frame(userdata)
        if raw_frame is None:
            logger.error("[QR] capture_frame returned None — camera unavailable")
            return "Camera unavailable."

        capture_ts = userdata.visual_processor.last_capture_epoch_ms
        stale_msg = check_frame_freshness(userdata, capture_ts)
        if stale_msg:
            logger.warning("[QR] Stale frame detected")
            return "Camera feed interrupted — please try again."

        logger.info(f"[QR] Raw frame type: {type(raw_frame).__name__}")

        # Step 2: Convert LiveKit VideoFrame → PIL Image
        from PIL import Image as PILImage  # noqa: F401
        from PIL import ImageFilter

        from core.vision.visual import convert_video_frame_to_pil

        if isinstance(raw_frame, PILImage.Image):
            pil_image = raw_frame
        else:
            pil_image = convert_video_frame_to_pil(raw_frame)
        if pil_image is None:
            logger.error("[QR] Frame-to-PIL conversion failed")
            return "Unable to process camera frame."
        logger.info(f"[QR] PIL image ready: {pil_image.size[0]}x{pil_image.size[1]} mode={pil_image.mode}")

        # Step 3: Pre-process for QR readability
        gray_image = pil_image.convert("L")
        sharp_image = gray_image.filter(ImageFilter.SHARPEN)
        scan_images = [sharp_image, gray_image, pil_image]
        logger.info("[QR] Pre-processing complete (grayscale + sharpen)")

        # Step 4: Scan for QR codes
        detections = []
        idx = 0
        for idx, img in enumerate(scan_images):
            logger.info(f"[QR] Scanning variant {idx + 1}/{len(scan_images)} ({img.mode}, {img.size})…")
            found = await userdata._qr_scanner.scan_async(img)
            if found:
                detections = found
                logger.info(f"[QR] ✓ Found {len(found)} code(s) on variant {idx + 1}")
                break
        if not detections:
            logger.info("[QR] No QR codes found across all image variants")

        # Structured telemetry
        _qr_frame_id = f"qr_{int(time.time() * 1000)}"
        try:
            from shared.logging.logging_config import log_event as _qr_log

            _qr_log(
                "qr-scanner",
                "qr_scan_attempt",
                component="scan_qr_code",
                frame_id=_qr_frame_id,
                qr_found=bool(detections),
                qr_data=detections[0].raw_data[:80] if detections else None,
                num_variants_tried=idx + 1 if detections else len(scan_images),
            )
        except Exception:
            pass  # logging must never break the pipeline

        # Step 5: Scan for AR markers
        ar_markers = []
        if userdata._ar_handler and userdata._ar_handler.is_ready:
            logger.info("[QR] Checking for AR markers…")
            ar_markers = await userdata._ar_handler.detect_async(pil_image)
            if ar_markers:
                logger.info(f"[QR] ✓ Found {len(ar_markers)} AR marker(s)")
            else:
                logger.info("[QR] No AR markers detected")

        if not detections and not ar_markers:
            logger.info("[QR] Nothing detected — returning guidance")
            if os.environ.get("DEBUG_ENDPOINTS_ENABLED", "").lower() == "true":
                try:
                    _dbg_dir = os.path.join("data", "debug_frames")
                    os.makedirs(_dbg_dir, exist_ok=True)
                    pil_image.save(os.path.join(_dbg_dir, f"qr_fail_{int(time.time() * 1000)}.jpg"))
                    logger.info("[QR] Debug frame saved to %s", _dbg_dir)
                except Exception as _save_err:
                    logger.debug("[QR] Debug frame save failed: %s", _save_err)
            return "No QR code or AR tag detected. Try pointing the camera directly at the code and holding steady."

        # Step 6: Decode first QR detection
        if detections:
            raw = detections[0].raw_data
            logger.info(f"[QR] Decoding QR data: '{raw[:80]}' (format={detections[0].format_type})")

            if userdata._qr_cache:
                cached = userdata._qr_cache.get(raw)
                if cached:
                    msg = cached.contextual_message
                    if cached.navigation_available:
                        msg += " Would you like me to guide you there?"
                    logger.info("[QR] Cache HIT — returning cached message")
                    return msg

            decoded = await userdata._qr_decoder.decode(raw)
            logger.info(f"[QR] Decoded type={decoded.content_type.value} nav={decoded.navigation_available}")

            if userdata._qr_cache:
                userdata._qr_cache.put(
                    raw_data=decoded.raw_data,
                    content_type=decoded.content_type.value,
                    contextual_message=decoded.contextual_message,
                    metadata=decoded.metadata,
                    source="online",
                    navigation_available=decoded.navigation_available,
                    lat=decoded.lat,
                    lon=decoded.lon,
                )
                logger.info("[QR] Result cached")

            msg = decoded.contextual_message
            if decoded.navigation_available:
                msg += " Would you like me to guide you there?"
            logger.info(f"[QR] Returning message: '{msg[:100]}'")
            return msg

        # Only AR markers
        ids = [str(m.marker_id) for m in ar_markers[:3]]
        msg = f"Detected AR marker(s): {', '.join(ids)}."
        logger.info(f"[QR] AR-only result: {msg}")
        return msg

    except Exception as e:
        logger.error(f"[QR] scan_qr_code exception: {e}", exc_info=True)
        return "Error scanning QR code."
    finally:
        userdata.current_tool = "general"


# ---------------------------------------------------------------------------
# Stream processing
# ---------------------------------------------------------------------------

async def process_stream(
    chat_ctx: Any,
    tools: Any,
    userdata: Any,
    *,
    llm_model: str,
    llm_base_url: str,
    llm_api_key: str,
) -> AsyncGenerator[Any, None]:
    """Route LLM streaming output — handles both vision and standard chat."""
    from livekit.agents.llm.llm import ChatChunk, ChoiceDelta
    from livekit.plugins import openai

    full_response = ""

    # Handle vision analysis
    if userdata.current_tool == "visual" and userdata._model_choice:
        if userdata._model_choice == llm_model:
            chunk_queue: asyncio.Queue[str] = asyncio.Queue()
            done_event = asyncio.Event()
            userdata._add_chunk_callback = lambda c: chunk_queue.put_nowait(c)

            for c in userdata._ollama_chunks:
                chunk_queue.put_nowait(c)

            try:
                while not (done_event.is_set() and chunk_queue.empty()):
                    try:
                        chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.05)
                        full_response += chunk
                        yield ChatChunk(
                            id="cmpl",
                            delta=ChoiceDelta(role="assistant", content=chunk),
                            usage=None,
                        )
                    except asyncio.TimeoutError:
                        if userdata._analysis_complete and chunk_queue.empty():
                            done_event.set()
            finally:
                userdata._add_chunk_callback = None
                userdata._ollama_chunks.clear()

        elif userdata._ollama_analysis:
            full_response = userdata._ollama_analysis
            yield ChatChunk(
                id="cmpl",
                delta=ChoiceDelta(role="assistant", content=full_response),
                usage=None,
            )
            userdata._ollama_analysis = None

        else:
            full_response = "Vision unavailable."
            yield ChatChunk(
                id="cmpl",
                delta=ChoiceDelta(role="assistant", content=full_response),
                usage=None,
            )

        userdata._model_choice = None

    # Standard LLM
    else:
        llm_instance = openai.LLM(
            model=llm_model,
            base_url=llm_base_url,
            api_key=llm_api_key,
            temperature=0.2,
        )
        async with llm_instance.chat(chat_ctx=chat_ctx, tools=tools) as stream:
            async for chunk in stream:
                if (
                    isinstance(chunk, ChatChunk)
                    and chunk.delta
                    and hasattr(chunk.delta, "content")
                    and chunk.delta.content
                ):
                    full_response += chunk.delta.content
                yield chunk

    userdata.last_response = full_response
