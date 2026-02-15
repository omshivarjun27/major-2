"""
Memory Engine - Configuration Module
=====================================

Memory-specific configuration loaded from environment variables.
Provides sensible defaults for resource-constrained devices.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("memory-config")


@dataclass
class MemoryConfig:
    """Configuration for the memory engine.
    
    All settings can be overridden via environment variables with
    the MEMORY_ prefix (e.g., MEMORY_ENABLED=true).
    """
    
    # Core settings (privacy-first: memory opt-in)
    enabled: bool = False
    retention_days: int = 30
    max_vectors: int = 5000
    index_path: str = "./data/memory_index/"
    
    # Privacy & Security
    encryption_enabled: bool = False
    encryption_key_env: str = "MEMORY_ENCRYPTION_KEY"
    save_raw_media: bool = False  # Only save if user consents
    telemetry_enabled: bool = False
    
    # Embedding models
    text_embedding_model: str = "qwen3-embedding:4b"
    image_embedding_enabled: bool = False
    image_embedding_model: str = "clip-ViT-B-32"
    audio_embedding_enabled: bool = False
    
    # Retrieval settings
    rag_k: int = 5
    similarity_threshold: float = 0.1
    
    # Performance settings
    embedding_batch_size: int = 8
    async_indexing: bool = True
    index_commit_interval_sec: float = 5.0
    
    # Light mode for resource-constrained devices
    light_mode: bool = False
    
    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Load configuration from environment variables."""
        
        def get_bool(key: str, default: bool) -> bool:
            val = os.environ.get(key, "").lower()
            if val in ("true", "1", "yes", "on"):
                return True
            if val in ("false", "0", "no", "off"):
                return False
            return default
        
        def get_int(key: str, default: int) -> int:
            try:
                return int(os.environ.get(key, default))
            except ValueError:
                return default
        
        def get_float(key: str, default: float) -> float:
            try:
                return float(os.environ.get(key, default))
            except ValueError:
                return default
        
        config = cls(
            enabled=get_bool("MEMORY_ENABLED", False),
            retention_days=get_int("MEMORY_RETENTION_DAYS", 30),
            max_vectors=get_int("MEMORY_MAX_VECTORS", 5000),
            index_path=os.environ.get("MEMORY_INDEX_PATH", "./data/memory_index/"),
            encryption_enabled=get_bool("MEMORY_ENCRYPTION", False),
            encryption_key_env=os.environ.get("MEMORY_ENCRYPTION_KEY_ENV", "MEMORY_ENCRYPTION_KEY"),
            save_raw_media=get_bool("MEMORY_SAVE_RAW", False),
            telemetry_enabled=get_bool("MEMORY_TELEMETRY", False),
            text_embedding_model=os.environ.get("EMBEDDING_MODEL", "qwen3-embedding:4b"),
            image_embedding_enabled=get_bool("IMAGE_EMBEDDING_ENABLED", False),
            image_embedding_model=os.environ.get("IMAGE_EMBEDDING_MODEL", "clip-ViT-B-32"),
            audio_embedding_enabled=get_bool("AUDIO_EMBEDDING_ENABLED", False),
            rag_k=get_int("RAG_K", 5),
            similarity_threshold=get_float("MEMORY_SIMILARITY_THRESHOLD", 0.1),
            embedding_batch_size=get_int("EMBEDDING_BATCH_SIZE", 8),
            async_indexing=get_bool("MEMORY_ASYNC_INDEXING", True),
            index_commit_interval_sec=get_float("MEMORY_COMMIT_INTERVAL", 5.0),
            light_mode=get_bool("MEMORY_LIGHT_MODE", False),
        )
        
        # Light mode overrides
        if config.light_mode:
            config.image_embedding_enabled = False
            config.audio_embedding_enabled = False
            config.max_vectors = min(config.max_vectors, 1000)
            logger.info("Memory engine running in LIGHT MODE (text-only, reduced capacity)")
        
        return config
    
    def ensure_index_dir(self) -> Path:
        """Ensure the index directory exists and return its path."""
        path = Path(self.index_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_encryption_key(self) -> Optional[bytes]:
        """Get encryption key from environment if encryption is enabled."""
        if not self.encryption_enabled:
            return None
        key = os.environ.get(self.encryption_key_env)
        if not key:
            logger.warning(
                f"Encryption enabled but {self.encryption_key_env} not set. "
                "Data will NOT be encrypted."
            )
            return None
        # Key should be 32 bytes for AES-256
        key_bytes = key.encode()
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\0')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        return key_bytes


# Global config instance (lazy-loaded)
_config: Optional[MemoryConfig] = None


def get_memory_config() -> MemoryConfig:
    """Get the global memory configuration (singleton)."""
    global _config
    if _config is None:
        _config = MemoryConfig.from_env()
        logger.info(f"Memory config loaded: enabled={_config.enabled}, "
                   f"max_vectors={_config.max_vectors}, "
                   f"retention_days={_config.retention_days}")
    return _config


def reset_config() -> None:
    """Reset config for testing purposes."""
    global _config
    _config = None
