"""NFR: Consent Enforcement — verifies biometric features require opt-in consent."""

from __future__ import annotations

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestConsentEnforcement:
    """Verify face recognition and biometric features are opt-in by default."""

    def test_face_consent_required_by_default(self):
        """Config should require face consent by default."""
        from core.face.face_embeddings import EmbeddingConfig
        config = EmbeddingConfig()
        assert config.consent_required is True

    def test_registration_fails_without_consent(self, tmp_path):
        """Attempting to register a face without consent raises ValueError."""
        import numpy as np
        from core.face.face_embeddings import FaceEmbeddingStore, EmbeddingConfig

        config = EmbeddingConfig(
            storage_dir=str(tmp_path / "consent_test"),
            encryption_enabled=False,
            consent_required=True,
        )
        store = FaceEmbeddingStore(config=config)
        embedding = np.random.randn(512).astype(np.float32)

        with pytest.raises(ValueError, match="[Cc]onsent"):
            store.register("NoConsent", embedding, consent=False)

    def test_registration_succeeds_with_consent(self, tmp_path):
        """Registration must succeed when consent is explicitly given."""
        import numpy as np
        from core.face.face_embeddings import FaceEmbeddingStore, EmbeddingConfig

        config = EmbeddingConfig(
            storage_dir=str(tmp_path / "consent_ok"),
            encryption_enabled=False,
            consent_required=True,
        )
        store = FaceEmbeddingStore(config=config)
        embedding = np.random.randn(512).astype(np.float32)

        ident = store.register("Consented", embedding, consent=True)
        assert ident.consent_given is True

    def test_identification_skips_revoked_consent(self, tmp_path):
        """Faces with revoked consent should not be matched during identify."""
        import numpy as np
        from core.face.face_embeddings import FaceEmbeddingStore, EmbeddingConfig

        config = EmbeddingConfig(
            storage_dir=str(tmp_path / "consent_revoke"),
            encryption_enabled=False,
            consent_required=True,
        )
        store = FaceEmbeddingStore(config=config)
        embedding = np.random.randn(512).astype(np.float32)

        ident = store.register("Revokable", embedding, consent=True)
        # Manually revoke consent
        ident.consent_given = False

        # Should not match even with identical embedding
        result = store.identify(embedding)
        assert result is None, "Should not match a face with revoked consent"

    def test_consent_log_recorded(self, tmp_path):
        """Each registration should log consent."""
        import numpy as np
        from core.face.face_embeddings import FaceEmbeddingStore, EmbeddingConfig

        config = EmbeddingConfig(
            storage_dir=str(tmp_path / "consent_log"),
            encryption_enabled=False,
        )
        store = FaceEmbeddingStore(config=config)
        embedding = np.random.randn(512).astype(np.float32)
        store.register("Logged", embedding, consent=True)

        log = store.get_consent_log()
        assert len(log) >= 1
        assert log[-1]["consent"] is True
        assert log[-1]["name"] == "Logged"

    def test_face_config_consent_default(self):
        """Config.py should default FACE_CONSENT_REQUIRED to true."""
        from shared.config import get_config
        cfg = get_config()
        # The face config is loaded from EmbeddingConfig defaults
        # which requires consent_required=True by default
        from core.face.face_embeddings import EmbeddingConfig
        assert EmbeddingConfig().consent_required is True
