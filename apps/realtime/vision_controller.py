# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Vision controller — extracted vision processing logic from agent.py (T-039).

Owns frame capture orchestration, model dispatch, spatial perception, VQA
reasoning, and result aggregation for the real-time pipeline.  Each public
function accepts a ``UserData`` instance and returns a user-facing string.
The agent delegates its ``@function_tool`` methods here.
"""

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger("ally-vision-controller")


# ---------------------------------------------------------------------------
# Frame helpers
# ---------------------------------------------------------------------------

async def capture_fresh_frame(userdata: Any) -> Optional[Any]:
    """Capture a fresh camera frame via the visual processor.

    Returns the image or None if unavailable.
    """
    if userdata.visual_processor is None or userdata.room_ctx is None:
        return None
    return await userdata.visual_processor.capture_frame(userdata.room_ctx.room)


def check_frame_freshness(userdata: Any, capture_ts: Optional[float]) -> Optional[str]:
    """Return a fallback message if the frame is stale, else None."""
    try:
        from application.frame_processing.freshness import FALLBACK_MESSAGE, is_frame_fresh
    except ImportError:
        return None
    if capture_ts and not is_frame_fresh(capture_ts):
        return FALLBACK_MESSAGE
    return None


def heartbeat(userdata: Any, component: str = "camera") -> None:
    """Send a watchdog heartbeat if the watchdog is active."""
    if userdata._watchdog is not None:
        userdata._watchdog.heartbeat(component)


# ---------------------------------------------------------------------------
# Ollama streaming analysis
# ---------------------------------------------------------------------------

async def run_ollama_analysis(userdata: Any, analysis_llm: Any, visual_ctx: Any) -> None:
    """Stream vision analysis from the LLM into userdata chunks."""
    try:
        async with analysis_llm.chat(chat_ctx=visual_ctx) as stream:
            async for chunk in stream:
                if chunk and hasattr(chunk.delta, "content") and chunk.delta.content:
                    content = chunk.delta.content
                    userdata._ollama_chunks.append(content)
                    if userdata._add_chunk_callback:
                        userdata._add_chunk_callback(content)
        userdata._analysis_complete = True
    except Exception as e:
        error_msg = f"Vision error: {str(e)[:50]}"
        userdata._ollama_chunks.append(error_msg)
        if userdata._add_chunk_callback:
            userdata._add_chunk_callback(error_msg)
        userdata._analysis_complete = True


# ---------------------------------------------------------------------------
# analyze_vision
# ---------------------------------------------------------------------------

async def analyze_vision(userdata: Any, query: str, *, llm_model: str, llm_base_url: str, llm_api_key: str) -> str:
    """Visual scene analysis with freshness gate and failsafe.

    Returns a user-facing string.
    """
    from livekit.agents.llm.chat_context import ChatContext, ImageContent
    from livekit.plugins import openai

    FAILSAFE = "I can't see clearly right now — proceed with caution."
    userdata.current_tool = "visual"

    try:
        image = await capture_fresh_frame(userdata)
        if image is None:
            return "Camera unavailable. " + FAILSAFE

        capture_ts = userdata.visual_processor.last_capture_epoch_ms
        stale_msg = check_frame_freshness(userdata, capture_ts)
        if stale_msg:
            logger.warning("analyze_vision: stale frame detected, returning failsafe")
            return stale_msg

        heartbeat(userdata)

        # Reset state
        userdata._ollama_chunks.clear()
        userdata._add_chunk_callback = None
        userdata._analysis_complete = False

        # Parallel: spatial + vision LLM
        spatial_context = ""
        if userdata.visual_processor.spatial_enabled:
            spatial_task = asyncio.create_task(userdata.visual_processor.process_spatial(image))
            try:
                nav_output = await asyncio.wait_for(spatial_task, timeout=0.2)
                if nav_output:
                    userdata._last_nav_output = nav_output
                    spatial_context = f"\nSpatial: {nav_output.short_cue}"
                    if nav_output.has_critical:
                        userdata._pending_spatial_warning = nav_output.short_cue
            except asyncio.TimeoutError:
                pass

        # Setup visual context
        visual_ctx = ChatContext()
        from apps.realtime.prompts import VISION_SYSTEM_PROMPT

        visual_ctx.add_message(role="system", content=VISION_SYSTEM_PROMPT)
        visual_ctx.add_message(
            role="user",
            content=[f"Answer briefly: {query}{spatial_context}", ImageContent(image=image)],
        )

        # Fast LLM call
        analysis_llm = openai.LLM(
            model=llm_model,
            base_url=llm_base_url,
            api_key=llm_api_key,
            temperature=0.2,
        )
        asyncio.create_task(run_ollama_analysis(userdata, analysis_llm, visual_ctx))

        userdata._model_choice = llm_model
        return "Analyzing..."

    except Exception as e:
        logger.error(f"Vision error: {e}")
        return FAILSAFE


# ---------------------------------------------------------------------------
# detect_obstacles
# ---------------------------------------------------------------------------

async def detect_obstacles(userdata: Any, detail_level: str = "quick") -> str:
    """Obstacle detection with freshness gate. Target: <200ms."""
    FAILSAFE = "I can't see clearly right now — proceed with caution."
    userdata.current_tool = "spatial"

    try:
        image = await capture_fresh_frame(userdata)
        if image is None:
            return "Camera unavailable. " + FAILSAFE

        if not userdata.visual_processor.spatial_enabled:
            return "Sensing unavailable. " + FAILSAFE

        capture_ts = userdata.visual_processor.last_capture_epoch_ms
        stale_msg = check_frame_freshness(userdata, capture_ts)
        if stale_msg:
            logger.warning("detect_obstacles: stale frame, returning failsafe")
            return stale_msg

        heartbeat(userdata)

        if detail_level == "quick":
            try:
                warning = await asyncio.wait_for(
                    userdata.visual_processor.get_quick_warning(image), timeout=0.5
                )
            except asyncio.TimeoutError:
                logger.warning("Quick obstacle detection timed out")
                return FAILSAFE
            userdata._pending_spatial_warning = warning

            if userdata.should_debounce(warning):
                logger.debug(f"Debounced duplicate cue: {warning}")
                return warning
            userdata.record_cue(warning)
            return warning
        else:
            try:
                nav_output = await asyncio.wait_for(
                    userdata.visual_processor.process_spatial(image), timeout=0.5
                )
            except asyncio.TimeoutError:
                logger.warning("Detailed obstacle detection timed out")
                return FAILSAFE
            if nav_output is None:
                return "Path clear."

            userdata._last_nav_output = nav_output
            if nav_output.has_critical:
                userdata._pending_spatial_warning = nav_output.short_cue

            cue = nav_output.short_cue
            if userdata.should_debounce(cue):
                logger.debug(f"Debounced duplicate cue: {cue}")
                return cue
            userdata.record_cue(cue)
            return cue

    except Exception as e:
        logger.error(f"Obstacle detection error: {e}")
        return FAILSAFE
    finally:
        userdata.current_tool = "general"


# ---------------------------------------------------------------------------
# analyze_spatial_scene
# ---------------------------------------------------------------------------

async def analyze_spatial_scene(userdata: Any, query: str = "What obstacles?") -> str:
    """Spatial analysis with VQA fallback. Target: <200ms."""
    FAILSAFE = "I can't see clearly right now — proceed with caution."
    userdata.current_tool = "spatial"

    try:
        image = await capture_fresh_frame(userdata)
        if image is None:
            return "Camera unavailable. " + FAILSAFE

        if not userdata.visual_processor.spatial_enabled:
            return "Sensing unavailable. " + FAILSAFE

        capture_ts = userdata.visual_processor.last_capture_epoch_ms
        stale_msg = check_frame_freshness(userdata, capture_ts)
        if stale_msg:
            logger.warning("analyze_spatial_scene: stale frame, returning failsafe")
            return stale_msg

        heartbeat(userdata)

        # Use VQA Engine if available
        vqa_available = False
        try:
            from core.vqa import PerceptionPipeline  # noqa: F401

            vqa_available = True
        except ImportError:
            pass

        if vqa_available and userdata._vqa_pipeline:
            try:
                cue = await asyncio.wait_for(
                    run_vqa_spatial(userdata, image, query), timeout=0.5
                )
            except asyncio.TimeoutError:
                logger.warning("VQA spatial analysis timed out, falling back")
                cue = None
            if cue:
                if userdata.should_debounce(cue):
                    logger.debug(f"Debounced duplicate cue: {cue}")
                else:
                    userdata.record_cue(cue)
                return cue

        # Fallback to spatial pipeline
        try:
            nav_output = await asyncio.wait_for(
                userdata.visual_processor.process_spatial(image), timeout=0.5
            )
        except asyncio.TimeoutError:
            logger.warning("Spatial pipeline timed out")
            return FAILSAFE

        if nav_output is None:
            return "Path clear."

        userdata._last_nav_output = nav_output
        userdata._last_obstacles = userdata.visual_processor.last_obstacles

        if nav_output.has_critical:
            userdata._pending_spatial_warning = nav_output.short_cue

        cue = nav_output.short_cue
        if userdata.should_debounce(cue):
            logger.debug(f"Debounced duplicate cue: {cue}")
        else:
            userdata.record_cue(cue)
        return cue

    except Exception as e:
        logger.error(f"Spatial error: {e}")
        return FAILSAFE
    finally:
        userdata.current_tool = "general"


# ---------------------------------------------------------------------------
# VQA spatial helper
# ---------------------------------------------------------------------------

async def run_vqa_spatial(userdata: Any, image: Any, query: str) -> str:
    """Run VQA engine for spatial analysis. Target: <300ms vision."""
    try:
        from PIL import Image as PILImage

        from core.vision.visual import convert_video_frame_to_pil
        from core.vqa import MicroNavFormatter, QuickAnswers, build_scene_graph

        if not isinstance(image, PILImage.Image):
            image = convert_video_frame_to_pil(image)
            if image is None:
                return "Path clear."

        perception = await userdata._vqa_pipeline.process(image)
        scene_graph = build_scene_graph(perception)
        fused = userdata._vqa_fuser.fuse(perception)

        if userdata._vqa_memory and userdata._vqa_session_id:
            userdata._vqa_memory.store(scene_graph, userdata._vqa_session_id, question=query)

        quick = QuickAnswers.try_quick_answer(query, fused)
        if quick:
            return quick

        formatter = MicroNavFormatter()
        return formatter.format(fused, scene_graph)

    except Exception as e:
        logger.error(f"VQA spatial error: {e}")
        nav_output = await userdata.visual_processor.process_spatial(image)
        return nav_output.short_cue if nav_output else "Path clear."


# ---------------------------------------------------------------------------
# ask_visual_question
# ---------------------------------------------------------------------------

async def ask_visual_question(userdata: Any, question: str) -> str:
    """Answer a visual question using VQA reasoning. Target: <500ms."""
    userdata.current_tool = "vqa"

    try:
        image = await capture_fresh_frame(userdata)
        if image is None:
            return "Camera unavailable. I can't see clearly right now — proceed with caution."

        capture_ts = userdata.visual_processor.last_capture_epoch_ms
        stale_msg = check_frame_freshness(userdata, capture_ts)
        if stale_msg:
            logger.warning("ask_visual_question: stale frame")
            return stale_msg

        vqa_available = False
        try:
            from core.vqa import PerceptionPipeline  # noqa: F401

            vqa_available = True
        except ImportError:
            pass

        if vqa_available and userdata._vqa_pipeline and userdata._vqa_reasoner:
            from PIL import Image as PILImage

            from core.vision.visual import convert_video_frame_to_pil
            from core.vqa import VQARequest, build_scene_graph

            if not isinstance(image, PILImage.Image):
                image = convert_video_frame_to_pil(image)
                if image is None:
                    return "I can't see clearly right now — proceed with caution."

            perception = await userdata._vqa_pipeline.process(image)
            scene_graph = build_scene_graph(perception)
            fused = userdata._vqa_fuser.fuse(perception)

            vqa_request = VQARequest(
                question=question,
                image=image,
                scene_graph=scene_graph,
                fused_result=fused,
                max_tokens=100,
            )
            response = await userdata._vqa_reasoner.answer(vqa_request)

            if userdata._vqa_memory and userdata._vqa_session_id:
                userdata._vqa_memory.store(
                    scene_graph, userdata._vqa_session_id, question=question, answer=response.answer
                )
            return response.get_full_answer()

        # Fallback to Ollama
        return await analyze_with_ollama(userdata, image, question)

    except Exception as e:
        logger.error(f"VQA error: {e}")
        return "I can't see clearly right now — proceed with caution."
    finally:
        userdata.current_tool = "general"


# ---------------------------------------------------------------------------
# Ollama fallback
# ---------------------------------------------------------------------------

async def analyze_with_ollama(userdata: Any, image: Any, question: str) -> str:
    """Fallback visual analysis using Ollama."""
    try:
        if userdata.ollama_handler:
            _, response, error = await userdata.ollama_handler.model_choice_with_analysis(image, question)
            if error:
                logger.warning(f"Ollama analysis error: {error}")
            return response[:200] if response else "Unable to analyze."
    except Exception as e:
        logger.error(f"Ollama fallback error: {e}")
    return "Unable to analyze."


# ---------------------------------------------------------------------------
# get_navigation_cue
# ---------------------------------------------------------------------------

async def get_navigation_cue(userdata: Any) -> str:
    """Get a quick navigation cue from a fresh camera frame."""
    FAILSAFE = "I can't see clearly right now — proceed with caution."

    try:
        image = await capture_fresh_frame(userdata)
        if image is None:
            return "Camera unavailable. " + FAILSAFE

        capture_ts = userdata.visual_processor.last_capture_epoch_ms
        stale_msg = check_frame_freshness(userdata, capture_ts)
        if stale_msg:
            logger.warning("get_navigation_cue: stale frame, returning failsafe")
            return stale_msg

        try:
            warning = await asyncio.wait_for(
                userdata.visual_processor.get_quick_warning(image), timeout=0.5
            )
        except asyncio.TimeoutError:
            logger.warning("Navigation cue timed out")
            return FAILSAFE
        return warning

    except Exception as e:
        logger.error(f"Error getting navigation cue: {e}")
        return FAILSAFE


# ---------------------------------------------------------------------------
# read_text (OCR)
# ---------------------------------------------------------------------------

async def read_text(userdata: Any, query: str = "read text") -> str:
    """Read text from the camera using OCR."""
    userdata.current_tool = "ocr"
    FAILSAFE = "I can't read the text clearly right now."

    ocr_available = False
    try:
        from core.ocr import OCRPipeline  # noqa: F401

        ocr_available = True
    except ImportError:
        pass

    if not ocr_available or userdata._ocr_pipeline is None:
        return "Text reading is not available."

    try:
        image = await capture_fresh_frame(userdata)
        if image is None:
            return "Camera unavailable. " + FAILSAFE

        from PIL import Image as PILImage

        from core.vision.visual import convert_video_frame_to_pil

        if not isinstance(image, PILImage.Image):
            image = convert_video_frame_to_pil(image)
            if image is None:
                return FAILSAFE

        result = await asyncio.wait_for(userdata._ocr_pipeline.process(image), timeout=2.0)

        if result.error:
            logger.warning(f"OCR error: {result.error}")
            return FAILSAFE
        if not result.full_text.strip():
            return "No readable text detected."
        return f"Text reads: {result.full_text.strip()}"

    except asyncio.TimeoutError:
        logger.warning("OCR timed out")
        return FAILSAFE
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return FAILSAFE
    finally:
        userdata.current_tool = "general"
