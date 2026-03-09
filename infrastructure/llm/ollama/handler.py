"""
Ollama Handler Module - Optimized for the visually impaired assistance
Uses SiliconFlow API (OpenAI-compatible) for cloud-based ollama/qwen3-vl model
"""

import base64
import io
import json
import logging
from typing import Any, Dict, Optional, Tuple

import httpx
from PIL import Image

from ..config import get_config, get_llm_timeout_config
from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    register_circuit_breaker,
)
from infrastructure.resilience.retry_policy import get_retry_policy

# Simple logger without custom handler, will use root logger's config
logger = logging.getLogger("ollama-handler")

# Constants
SYSTEM_PROMPT = """Binary classifier for images. Respond in JSON format:

IF image contains humans/person/faces → "OLLAMA" + answer query like you see the visual.
IF NO humans/faces → "QWEN" + empty string

JSON format:
{
  "model_choice": "QWEN" or "OLLAMA",
  "analysis": "" if QWEN, answer if OLLAMA
}"""

# Ollama API endpoint (local)
OLLAMA_BASE_URL = "http://localhost:11434/v1"

_OLLAMA_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    reset_timeout_s=30.0,
    half_open_max_calls=1,
    success_threshold=1,
)

class OllamaHandler:
    """Streamlined handler for Ollama API integration via SiliconFlow."""

    def __init__(self) -> None:
        """Initialize the Ollama API handler with config-driven timeouts and pooling."""
        try:
            config = get_config()
            self.api_key: str = config["OLLAMA_VL_API_KEY"]
            self.model_id: str = config["OLLAMA_VL_MODEL_ID"]
            self.max_tokens: int = config["MAX_TOKENS"]
            self.temperature: float = config["TEMPERATURE"]

            logger.info("Initializing Ollama handler with model: %s", self.model_id)

            # Quick validation and setup
            if not self.api_key:
                logger.error("No OLLAMA_VL_API_KEY provided in configuration")
                self.is_ready = False
                self._verified = False
                self.client: Optional[httpx.AsyncClient] = None
                self._cb = None
                self._retry_policy = None
                return

            # Structured timeouts from config
            timeout_cfg = get_llm_timeout_config()
            timeout = httpx.Timeout(
                connect=timeout_cfg["connect"],
                read=timeout_cfg["read"],
                write=timeout_cfg["total"],
                pool=timeout_cfg["connect"],
            )

            # Connection pool limits
            pool_limits = httpx.Limits(
                max_connections=config.get("LLM_MAX_CONNECTIONS", 20),
                max_keepalive_connections=config.get("LLM_MAX_KEEPALIVE", 10),
            )

            # Set up async HTTP client for Ollama API with pooling
            self.client = httpx.AsyncClient(
                base_url=OLLAMA_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
                limits=pool_limits,
            )
            self.is_ready = True

            # Circuit breaker and shared retry policy
            self._cb = register_circuit_breaker("ollama", config=_OLLAMA_CB_CONFIG)
            self._retry_policy = get_retry_policy("ollama_reasoning")
            self._verified = False
            self._image_cache: Dict[int, str] = {}
            self._IMAGE_CACHE_MAX = 64  # Bounded LRU: evicts oldest when full
            logger.info("Ollama client initialized successfully")

        except Exception as e:
            logger.error("Error during Ollama handler initialization: %s", e)
            self.is_ready = False
            self._verified = False
            self.client = None
            self._cb = None
            self._retry_policy = None

    async def verify_connection(self) -> bool:
        """Verify the connection is working."""
        if self._verified:
            return True

        if not self.api_key:
            logger.error("No API key provided for Ollama")
            self.is_ready = False
            return False

        # Just check API key presence, no need for a test call
        self.is_ready = True
        self._verified = True
        logger.info("Ollama handler verified with model %s", self.model_id)
        return True

    async def _request_with_retry(self, url: str, **kwargs: Any) -> httpx.Response:
        """HTTP POST through circuit breaker + shared retry policy.

        Replaces the ad-hoc retry loop with shared resilience infrastructure:
        - Circuit breaker tracks failures and trips after threshold
        - Retry policy handles exponential backoff with jitter
        - Error classifier determines if errors are retryable
        """
        if self._cb is None or self._retry_policy is None:
            # Resilience not initialized — direct call
            response = await self.client.post(url, **kwargs)
            response.raise_for_status()
            return response

        async def _single_attempt() -> httpx.Response:
            """Single attempt through circuit breaker."""
            return await self._cb.call(self._make_request, url, **kwargs)

        return await self._retry_policy.execute(
            _single_attempt,
            service_name="ollama",
        )

    async def _make_request(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute a single HTTP POST request."""
        response = await self.client.post(url, **kwargs)
        response.raise_for_status()
        return response

    async def model_choice_with_analysis(
        self, image: object, query: str
    ) -> Tuple[str, str, Optional[str]]:
        """
        Make a model choice (OLLAMA vs QWEN) and get analysis in a single call.

        Args:
            image: Image to analyze
            query: User query about the image

        Returns:
            Tuple of (model_choice, analysis, error)
        """
        # Quick validation
        if not self.is_ready:
            return "ollama:qwen3.5:397b-cloud", "", "Vision API not configured"

        # Verify connection on first use
        if not self._verified and not await self.verify_connection():
            return "ollama:qwen3.5:397b-cloud", "", "Vision API connection failed"

        try:
            # Convert image to base64
            base64_image = await self._convert_and_optimize_image(image)
            if not base64_image:
                return "ollama:qwen3.5:397b-cloud", "", "Failed to process the image"

            # Make the API call to SiliconFlow (OpenAI-compatible)
            payload = {
                "model": self.model_id,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {
                            "type": "text",
                            "text": (
                                "Answer this query about the seeing the visual in front"
                                " of the user.please dont mention the image or user"
                                f" word in your answer: {query}"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ]},
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "stream": False,
            }

            response = await self._request_with_retry("/chat/completions", json=payload)
            completion = response.json()

            # Parse response
            response_json = completion["choices"][0]["message"]["content"]
            response_data = json.loads(response_json)

            # Extract data
            model_choice = response_data.get("model_choice", "QWEN").upper()
            ollama_analysis = response_data.get("analysis", "") if model_choice == "OLLAMA" else ""

            # Validate
            if model_choice not in ["OLLAMA", "QWEN"]:
                logger.warning(
                    "Invalid model choice: %s, defaulting to ollama:qwen3.5:397b-cloud",
                    model_choice,
                )
                model_choice = "ollama:qwen3.5:397b-cloud"

            logger.info("Model choice: %s, analysis available: %s", model_choice, bool(ollama_analysis))
            return model_choice, ollama_analysis, None

        except Exception as e:
            logger.error("Error in model_choice_with_analysis: %s", e)
            return "ollama:qwen3.5:397b-cloud", "", str(e)

    def health(self) -> Dict[str, Any]:
        """Health snapshot including circuit breaker state."""
        return {
            "is_ready": self.is_ready,
            "verified": self._verified,
            "circuit_breaker": self._cb.snapshot() if self._cb else None,
        }

    async def close(self) -> None:
        """Gracefully close the underlying httpx session."""
        if self.client is not None:
            try:
                await self.client.aclose()
            except Exception as e:
                logger.debug("Error closing Ollama HTTP client: %s", e)
            finally:
                self.client = None

    async def _convert_and_optimize_image(self, image: object, target_mb: float = 3.5) -> Optional[str]:
        """Convert image to base64 string with size optimization."""
        try:
            # Try to use cached image
            if hasattr(image, 'tobytes'):
                try:
                    image_hash = hash(image.tobytes())
                    if image_hash in self._image_cache:
                        return self._image_cache[image_hash]
                except Exception:
                    pass  # Continue if hashing fails

            # Convert to PIL Image if needed
            if not isinstance(image, Image.Image):
                if hasattr(image, 'to_pil'):
                    image = image.to_pil()
                elif hasattr(image, 'to_ndarray'):
                    import numpy as np
                    arr = image.to_ndarray()
                    if arr.dtype != np.uint8:
                        arr = np.uint8(arr)
                    image = Image.fromarray(arr)
                elif hasattr(image, 'data') and hasattr(image, 'width') and hasattr(image, 'height'):
                    # Handle VideoFrame from LiveKit
                    try:
                        import cv2
                        import numpy as np

                        data_len = len(image.data)
                        bytes_per_pixel = data_len / (image.width * image.height)

                        if 1.4 < bytes_per_pixel < 1.6:  # YUV format
                            yuv = np.frombuffer(image.data, dtype=np.uint8)
                            yuv = yuv.reshape((image.height * 3 // 2, image.width))
                            rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_I420)
                            image = Image.fromarray(rgb)
                        elif 2.9 < bytes_per_pixel < 4.1:  # RGB/RGBA format
                            channels = round(bytes_per_pixel)
                            img_array = np.frombuffer(image.data, dtype=np.uint8)
                            img_array = img_array.reshape((image.height, image.width, channels))
                            if channels == 4:
                                img_array = img_array[:, :, :3]
                            image = Image.fromarray(img_array)
                        else:
                            return None
                    except Exception as e:
                        logger.error(f"Error converting VideoFrame: {e}")
                        return None
                else:
                    return None

            # Check current size and optimize if needed
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            size_mb = len(buffer.getvalue()) * 1.4 / (1024 * 1024)

            # If small enough, use as is
            if size_mb <= target_mb:
                encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')

                # Cache result (bounded LRU)
                if hasattr(image, 'tobytes'):
                    try:
                        h = hash(image.tobytes())
                        if len(self._image_cache) >= self._IMAGE_CACHE_MAX:
                            oldest = next(iter(self._image_cache))
                            del self._image_cache[oldest]
                        self._image_cache[h] = encoded
                    except Exception:
                        pass

                return encoded

            # Need optimization
            if size_mb <= target_mb * 1.2:
                # Just reduce quality
                min_q, max_q = 45, 85
                while min_q < max_q - 5:
                    mid_q = (min_q + max_q) // 2
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=mid_q)
                    if len(buffer.getvalue()) * 1.4 / (1024 * 1024) <= target_mb:
                        min_q = mid_q
                    else:
                        max_q = mid_q

                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=min_q)
            else:
                # Resize the image
                scale = (target_mb / size_mb) ** 0.5
                new_size = tuple(int(dim * scale) for dim in image.size)
                image = image.resize(new_size, Image.BICUBIC)
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=85)

            # Encode and cache (bounded LRU)
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            if hasattr(image, 'tobytes'):
                try:
                    h = hash(image.tobytes())
                    if len(self._image_cache) >= self._IMAGE_CACHE_MAX:
                        oldest = next(iter(self._image_cache))
                        del self._image_cache[oldest]
                    self._image_cache[h] = encoded
                except Exception:
                    pass

            return encoded

        except Exception as e:
            logger.error(f"Error in _convert_and_optimize_image: {e}")
            return None
