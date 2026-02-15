"""
Memory Engine - Embeddings Module
==================================

Text, image, and audio embedding generation using lightweight models.
Supports Ollama embedding models for text and optional CLIP for images.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union

import numpy as np

logger = logging.getLogger("memory-embeddings")

# Lazy import for Ollama client
_ollama_client = None
_clip_model = None
_clip_processor = None


def _get_ollama_client():
    """Lazy load Ollama client for embeddings."""
    global _ollama_client
    if _ollama_client is None:
        try:
            import ollama
            _ollama_client = ollama
            logger.info("Ollama client loaded for embeddings")
        except ImportError:
            logger.error("ollama not installed. Run: pip install ollama")
            raise
    return _ollama_client


class BaseEmbedder(ABC):
    """Abstract base class for embedders."""
    
    @abstractmethod
    def embed(self, data: Any) -> np.ndarray:
        """Generate embedding for input data."""
        pass
    
    @abstractmethod
    def embed_batch(self, data_list: List[Any]) -> np.ndarray:
        """Generate embeddings for batch of inputs."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass
    
    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Check if embedder is ready."""
        pass


class TextEmbedder(BaseEmbedder):
    """Text embedding using Ollama embedding models.
    
    Default model: qwen3-embedding:4b
    Uses Ollama's embedding API for efficient local inference.
    """
    
    def __init__(self, model_name: str = "qwen3-embedding:4b"):
        self._model_name = model_name
        self._client = None
        self._ready = False
        self._dimension = None  # Auto-detected on first embed
    
    def _ensure_client(self):
        """Ensure Ollama client is loaded and model dimension is detected."""
        if self._client is None:
            self._client = _get_ollama_client()
            # Probe dimension with a test embedding
            try:
                response = self._client.embed(model=self._model_name, input="test")
                embeddings = response.get("embeddings", response.get("embedding", []))
                if embeddings:
                    first = embeddings[0] if isinstance(embeddings[0], list) else embeddings
                    self._dimension = len(first)
                    logger.info(f"Ollama embedding model '{self._model_name}' loaded. Dimension: {self._dimension}")
                else:
                    self._dimension = 0
                    logger.warning(f"Could not detect dimension for model '{self._model_name}'")
            except Exception as e:
                logger.warning(f"Could not probe model dimension: {e}. Will detect on first real embed.")
                self._dimension = 0
            self._ready = True
    
    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """L2-normalize a vector."""
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text string.
        
        Args:
            text: Input text string
            
        Returns:
            Normalized embedding vector
        """
        self._ensure_client()
        start = time.time()
        
        # Clean and truncate text if needed
        text = text.strip()
        if len(text) > 512:
            text = text[:512]
        
        response = self._client.embed(model=self._model_name, input=text)
        embeddings = response.get("embeddings", response.get("embedding", []))
        vec = embeddings[0] if isinstance(embeddings[0], list) else embeddings
        
        embedding = self._normalize(np.array(vec, dtype=np.float32))
        
        # Update dimension if not yet set
        if self._dimension is None or self._dimension == 0:
            self._dimension = len(vec)
        
        elapsed_ms = (time.time() - start) * 1000
        logger.debug(f"Text embedding generated in {elapsed_ms:.1f}ms")
        
        return embedding
    
    def embed_batch(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """Generate embeddings for batch of texts.
        
        Args:
            texts: List of text strings
            batch_size: Batch size for encoding
            
        Returns:
            Array of normalized embedding vectors (N x dim)
        """
        self._ensure_client()
        start = time.time()
        
        # Clean texts
        cleaned = [t.strip()[:512] for t in texts]
        
        # Ollama embed API supports batch input
        response = self._client.embed(model=self._model_name, input=cleaned)
        raw = response.get("embeddings", response.get("embedding", []))
        
        embeddings = []
        for vec in raw:
            v = np.array(vec, dtype=np.float32)
            embeddings.append(self._normalize(v))
        
        result = np.array(embeddings, dtype=np.float32)
        
        # Update dimension if not yet set
        if (self._dimension is None or self._dimension == 0) and len(embeddings) > 0:
            self._dimension = len(embeddings[0])
        
        elapsed_ms = (time.time() - start) * 1000
        logger.debug(f"Batch embedding ({len(texts)} texts) in {elapsed_ms:.1f}ms")
        
        return result
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        self._ensure_client()
        return self._dimension
    
    @property
    def is_ready(self) -> bool:
        """Check if embedder is ready."""
        return self._ready


class MockTextEmbedder(BaseEmbedder):
    """Mock text embedder for testing (no model loading)."""
    
    def __init__(self, dimension: int = 384):
        self._dimension = dimension
        self._ready = True
    
    def embed(self, text: str) -> np.ndarray:
        """Generate deterministic mock embedding based on text hash."""
        np.random.seed(hash(text) % (2**31))
        embedding = np.random.randn(self._dimension).astype(np.float32)
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding
    
    def embed_batch(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """Generate mock embeddings for batch."""
        return np.array([self.embed(t) for t in texts])
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def is_ready(self) -> bool:
        return True


class ImageEmbedder(BaseEmbedder):
    """Image embedding using CLIP (optional).
    
    Disabled by default to save resources.
    Enable via IMAGE_EMBEDDING_ENABLED=true.
    """
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", enabled: bool = False):
        self._model_name = model_name
        self._enabled = enabled
        self._model = None
        self._processor = None
        self._ready = False
        self._dimension = 512  # CLIP base dimension
    
    def _ensure_model(self):
        """Lazy load CLIP model if enabled."""
        if not self._enabled:
            logger.debug("Image embedding disabled")
            return
        
        if self._model is None:
            try:
                from transformers import CLIPModel, CLIPProcessor
                logger.info(f"Loading CLIP model: {self._model_name}")
                self._model = CLIPModel.from_pretrained(self._model_name)
                self._processor = CLIPProcessor.from_pretrained(self._model_name)
                self._ready = True
                logger.info("CLIP model loaded")
            except ImportError:
                logger.warning("transformers not installed. Image embedding disabled.")
                self._enabled = False
            except Exception as e:
                logger.error(f"Failed to load CLIP model: {e}")
                self._enabled = False
    
    def embed(self, image: Any) -> np.ndarray:
        """Generate embedding for an image.
        
        Args:
            image: PIL Image or numpy array
            
        Returns:
            Normalized embedding vector, or zeros if disabled
        """
        if not self._enabled:
            return np.zeros(self._dimension, dtype=np.float32)
        
        self._ensure_model()
        if self._model is None:
            return np.zeros(self._dimension, dtype=np.float32)
        
        try:
            import torch
            inputs = self._processor(images=image, return_tensors="pt")
            with torch.no_grad():
                features = self._model.get_image_features(**inputs)
            embedding = features[0].numpy()
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Image embedding failed: {e}")
            return np.zeros(self._dimension, dtype=np.float32)
    
    def embed_batch(self, images: List[Any], batch_size: int = 4) -> np.ndarray:
        """Generate embeddings for batch of images."""
        if not self._enabled:
            return np.zeros((len(images), self._dimension), dtype=np.float32)
        
        # Process one at a time for simplicity
        return np.array([self.embed(img) for img in images])
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def is_ready(self) -> bool:
        return self._ready


class AudioEmbedder(BaseEmbedder):
    """Audio embedding stub.
    
    Currently falls back to text embedding of transcript.
    Future: integrate audio2vec or wav2vec.
    """
    
    def __init__(self, text_embedder: Optional[TextEmbedder] = None, enabled: bool = False):
        self._text_embedder = text_embedder
        self._enabled = enabled
        self._dimension = 384  # Same as text for fusion
    
    def embed(self, audio_data: Any, transcript: Optional[str] = None) -> np.ndarray:
        """Generate embedding for audio.
        
        Currently uses transcript as fallback.
        
        Args:
            audio_data: Audio bytes (unused currently)
            transcript: Text transcript of audio
            
        Returns:
            Embedding vector (from transcript) or zeros
        """
        if transcript and self._text_embedder:
            return self._text_embedder.embed(transcript)
        return np.zeros(self._dimension, dtype=np.float32)
    
    def embed_batch(self, data_list: List[Any], transcripts: Optional[List[str]] = None) -> np.ndarray:
        """Generate embeddings for batch."""
        if transcripts and self._text_embedder:
            return self._text_embedder.embed_batch(transcripts)
        return np.zeros((len(data_list), self._dimension), dtype=np.float32)
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def is_ready(self) -> bool:
        return self._text_embedder is not None and self._text_embedder.is_ready


class MultimodalFuser:
    """Fuse embeddings from multiple modalities.
    
    Supports concatenation or weighted averaging with normalization.
    """
    
    def __init__(
        self,
        text_embedder: Optional[TextEmbedder] = None,
        image_embedder: Optional[ImageEmbedder] = None,
        audio_embedder: Optional[AudioEmbedder] = None,
        fusion_method: str = "average",  # "average" or "concat"
    ):
        self._text_embedder = text_embedder
        self._image_embedder = image_embedder
        self._audio_embedder = audio_embedder
        self._fusion_method = fusion_method
    
    def fuse(
        self,
        text: Optional[str] = None,
        image: Optional[Any] = None,
        audio: Optional[Any] = None,
        audio_transcript: Optional[str] = None,
        weights: Optional[dict] = None,
    ) -> np.ndarray:
        """Fuse embeddings from available modalities.
        
        Args:
            text: Text input
            image: Image input
            audio: Audio input
            audio_transcript: Transcript for audio
            weights: Optional weights for each modality
            
        Returns:
            Fused and normalized embedding vector
        """
        embeddings = []
        modality_weights = []
        
        default_weights = weights or {"text": 1.0, "image": 0.8, "audio": 0.6}
        
        # Text embedding
        if text and self._text_embedder:
            emb = self._text_embedder.embed(text)
            if np.any(emb):
                embeddings.append(emb)
                modality_weights.append(default_weights.get("text", 1.0))
        
        # Image embedding
        if image is not None and self._image_embedder:
            emb = self._image_embedder.embed(image)
            if np.any(emb):
                embeddings.append(emb)
                modality_weights.append(default_weights.get("image", 0.8))
        
        # Audio embedding (via transcript)
        if (audio is not None or audio_transcript) and self._audio_embedder:
            emb = self._audio_embedder.embed(audio, audio_transcript)
            if np.any(emb):
                embeddings.append(emb)
                modality_weights.append(default_weights.get("audio", 0.6))
        
        if not embeddings:
            # No embeddings available, return text embedder dimension zeros
            dim = self._text_embedder.dimension if self._text_embedder else 384
            return np.zeros(dim, dtype=np.float32)
        
        if self._fusion_method == "concat":
            # Concatenate all embeddings
            fused = np.concatenate(embeddings)
        else:
            # Weighted average (default)
            # All embeddings should be same dimension for averaging
            # Pad shorter ones if needed
            max_dim = max(e.shape[0] for e in embeddings)
            padded = []
            for emb in embeddings:
                if emb.shape[0] < max_dim:
                    emb = np.pad(emb, (0, max_dim - emb.shape[0]))
                padded.append(emb)
            
            # Weighted average
            weights_arr = np.array(modality_weights)
            weights_arr = weights_arr / weights_arr.sum()  # Normalize weights
            fused = np.average(padded, axis=0, weights=weights_arr)
        
        # Normalize final embedding
        norm = np.linalg.norm(fused)
        if norm > 0:
            fused = fused / norm
        
        return fused.astype(np.float32)
    
    @property
    def dimension(self) -> int:
        """Return output dimension based on fusion method."""
        if self._fusion_method == "concat":
            dim = 0
            if self._text_embedder:
                dim += self._text_embedder.dimension
            if self._image_embedder:
                dim += self._image_embedder.dimension
            if self._audio_embedder:
                dim += self._audio_embedder.dimension
            return dim if dim > 0 else 384
        else:
            # Average uses max dimension
            dims = []
            if self._text_embedder:
                dims.append(self._text_embedder.dimension)
            if self._image_embedder and self._image_embedder.is_ready:
                dims.append(self._image_embedder.dimension)
            if self._audio_embedder:
                dims.append(self._audio_embedder.dimension)
            return max(dims) if dims else 384


def create_embedders(config=None):
    """Factory to create embedders based on config.
    
    Returns:
        Tuple of (text_embedder, image_embedder, audio_embedder, fuser)
    """
    if config is None:
        from .config import get_memory_config
        config = get_memory_config()
    
    # Text embedder (always available)
    text_embedder = TextEmbedder(model_name=config.text_embedding_model)
    
    # Image embedder (optional)
    image_embedder = ImageEmbedder(
        model_name=config.image_embedding_model,
        enabled=config.image_embedding_enabled,
    )
    
    # Audio embedder (uses text as fallback)
    audio_embedder = AudioEmbedder(
        text_embedder=text_embedder,
        enabled=config.audio_embedding_enabled,
    )
    
    # Multimodal fuser
    fuser = MultimodalFuser(
        text_embedder=text_embedder,
        image_embedder=image_embedder,
        audio_embedder=audio_embedder,
        fusion_method="average",
    )
    
    return text_embedder, image_embedder, audio_embedder, fuser
