---
title: "Versioning Strategy"
version: 1.0.0
date: 2026-02-22T15:31:00Z
architecture_mode: hybrid_cloud_local_gpu
---

# Versioning Strategy

This document outlines the versioning strategy for the Voice & Vision Assistant for Blind, covering the application, REST API, machine learning models, and embedding compatibility. It ensures system stability, predictable upgrades, and clear migration paths for this single-user assistive device.

## 1. Semantic Versioning Rules

The application follows Semantic Versioning 2.0.0 (SemVer) for all releases. Versions are expressed in the `MAJOR.MINOR.PATCH` format.

- **MAJOR (X.y.z)**: Incremented for breaking changes that require significant user or developer intervention. This includes modifications to the REST API response envelope format (e.g., changing `SuccessEnvelope` or `ErrorEnvelope`), updates to the WebRTC signaling protocol that prevent old agents from connecting, or structural changes to the memory storage format. A MAJOR bump signifies that the system is no longer backward compatible with previous versions.
- **MINOR (x.Y.z)**: Incremented for additive changes that introduce new capabilities without disrupting existing workflows. This covers the addition of new REST endpoints, the introduction of new perception models to the pipeline (like a specialized medical label detector or an upgraded face recognition engine), or the expansion of the memory subsystem's capabilities. MINOR updates are expected to be seamless for the user and maintain full compatibility with existing clients.
- **PATCH (x.y.Z)**: Incremented for low-risk updates focused on stability and maintenance. Examples include bug fixes in the perception logic, performance tuning for the RTX 4060 GPU, security patches for third-party dependencies, or updating model weights to a newer epoch without changing the underlying architecture.

### Release Cycle and Documentation
Every release, regardless of the version increment, must be accompanied by detailed release notes. These notes are stored in the `docs/releases/` directory and categorized by version number. Each entry must clearly state:
1. The primary purpose of the update (e.g., "Improved Braille recognition accuracy").
2. A list of all changed or added endpoints.
3. Any required configuration changes in the `.env` file.
4. Model version changes and their associated VRAM impact.
5. Migration steps for existing memory indices if a MAJOR version is involved.

### Versioning Workflow
The following workflow is mandated for all code changes to maintain version integrity across the hybrid architecture:
1. **Branching Strategy**: All development occurs on feature branches branched from `main`. Branches are named `vX.Y.Z/description` to signal the intended version increment.
2. **Conventional Commits**: Commit messages must follow the standard format (e.g., `feat:`, `fix:`, `refactor:`) to allow for automated generation of the `CHANGELOG.md` file.
3. **Automated Testing**: The CI/CD pipeline executes a full test suite (429+ tests) including unit, integration, and performance benchmarks. A version cannot be tagged if any test fails.
4. **Git Tagging**: Upon successful merge, the repository is tagged with the semantic version. This tag triggers the build of the production Docker image.
5. **Rollback Verification**: Before a MAJOR release is finalized, the rollback procedure (restoring from an `/export/full` backup) must be verified in a staging environment.

Version tags in the git repository must match the Semantic Versioning format precisely, ensuring that the CI/CD pipeline can correctly identify and deploy the appropriate artifacts. Pre-release versions use hyphenated tags like `-alpha.N` or `-beta.N` (e.g., `1.0.0-alpha.1`). The current application version is **1.0.0**.

## 2. API Versioning

The REST API serves as the primary integration point for the assistant's various components. Given the single-user nature of the device, a straightforward and predictable versioning scheme is prioritized over more complex header-based negotiation.

- **URL Prefixing**: All active endpoints are versioned via the URL path, starting with `/v1/` (e.g., `http://localhost:8000/v1/memory/search`). This explicit versioning allows developers to know exactly which API contract they are interacting with.
- **Major Version Transition**: When a MAJOR version increment occurs, the system will support both the old and new versions simultaneously for a transition period. For instance, `/v1/` and `/v2/` will coexist until the deprecation window closes.
- **Deprecation Policy**: A minimum 3-month overlap period is provided between API versions. During this time, the system supports both versions to allow for client updates. This period is critical for ensuring that the assistive device remains functional during upgrades.
- **Success and Error Envelopes**: All API responses are wrapped in a standardized envelope.
    - **SuccessEnvelope**: Contains `success: true`, a `data` object for the payload, and a `meta` object for versioning and timing information.
    - **ErrorEnvelope**: Contains `success: false`, an `error` object with a message and error code, and a `meta` object for diagnostic context.
- **Header-Based Versioning Rationale**: While header-based versioning (e.g., `Accept: application/vnd.assistant.v1+json`) is powerful for large-scale multi-tenant APIs, it adds unnecessary complexity for a local device API. URL prefixing is more visible in logs and easier to debug for the single-user deployment.

### Documentation and OpenAPI
The `openapi.yaml` file is the source of truth for the API versioning. Every endpoint defined in the specification must include the version tag in its description. Automated tools check that the implemented endpoints in `apps/api/server.py` align with the versioning documented in the YAML file. All current endpoints documented in the system architecture are considered part of the v1 API.

### Response Schema Examples
To illustrate the stability of the v1 API, the following JSON schemas are guaranteed not to change until the introduction of v2:

**Successful Perception Result:**
```json
{
  "success": true,
  "data": {
    "detections": [
      { "label": "chair", "confidence": 0.95, "distance": 1.2 }
    ]
  },
  "meta": {
    "api_version": "1.0.0",
    "processing_time_ms": 120,
    "model": "yolov8n"
  }
}
```

**Memory Consent Status:**
```json
{
  "success": true,
  "data": {
    "consent_given": true,
    "last_updated": "2026-02-22T10:00:00Z"
  },
  "meta": {
    "api_version": "1.0.0"
  }
}
```

## 3. Model Version Tracking

Machine learning models are tracked independently of the application version to manage their specific update cycles and resource requirements.

| Model | Current Version | Format | Location | Est. VRAM | Peak VRAM | Latency | Update Method |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| YOLO v8n | v8 nano | ONNX | `models/yolov8n.onnx` | ~200MB | 220MB | < 50ms | File replace |
| MiDaS v2.1 | v2.1 small | ONNX | `models/midas_small.onnx` | ~100MB | 110MB | < 100ms | File replace |
| qwen3-embed | 4b | Ollama | Local Ollama | ~2,000MB | 2,100MB | < 200ms | `ollama pull` |
| qwen3.5:cloud | cloud | Ollama | Cloud runtime | N/A | N/A | < 500ms | Managed |
| EasyOCR | Latest | PyTorch | pip package | ~500MB | 550MB | < 300ms | pip upgrade |
| Face Detect | Current | PyTorch | pip package | ~300MB | 320MB | < 80ms | pip upgrade |
| Braille OCR | v1.0 | PyTorch | `models/braille.pt` | ~150MB | 160MB | < 150ms | File replace |

### Model Verification Protocols
Before any model version is updated in the production matrix, it undergoes a strict verification protocol:
1. **VRAM Benchmark**: The model must fit within its allocated budget on the RTX 4060 (8GB VRAM). The cumulative peak usage of all active models must not exceed 3.5GB to leave room for system overhead.
2. **Latency SLA**: Every model must meet its specified latency target. For example, YOLO v8n must process frames in under 50ms to maintain real-time navigation cues.
3. **Accuracy Regression**: New model versions are tested against a golden dataset to ensure that perception accuracy (mAP for detection, WER for OCR) has not degraded.
4. **ONNX Optimization**: Wherever possible, models are converted to ONNX format to leverage the CUDA Execution Provider for maximum efficiency.

## 4. Embedding Version Compatibility

The memory subsystem is built on a Vector RAG (Retrieval-Augmented Generation) pipeline that is highly sensitive to the embedding space.

- **Embedding Model**: The current standard is `qwen3-embedding:4b`, producing 384-dimensional dense vectors. These vectors represent the semantic meaning of the processed text and visual descriptions.
- **Vector Space Consistency**: Because the FAISS index (IndexFlatL2) calculates Euclidean distance between these vectors, any change in the embedding model (even a different version of the same model) creates a "semantic shift." This shift makes old vectors incomparable with new ones.
- **Dimensionality Constraint**: The FAISS index is initialized with a fixed dimension count. If `qwen3-embedding` is updated to a version with 512 dimensions, the existing 384-dimension index will throw a runtime error and fail to load.
- **Rule of Thumb**: Any change to the embedding model architecture or output dimensionality is strictly classified as a MAJOR version change for the entire application.

### Migration Process

When upgrading the embedding model, the following sequence is enforced:
1. **Freeze**: Memory ingestion is temporarily suspended to prevent data inconsistency during the migration.
2. **Export**: All existing memories are exported via the `/v1/export/full` endpoint, including raw text and metadata.
3. **Switch**: The local Ollama instance is updated to the new embedding model version.
4. **Re-embed**: A migration utility iterates through the exported text and generates new embeddings using the updated model.
5. **Rebuild**: The FAISS index is cleared and rebuilt from the ground up using the new vectors.
6. **Verify**: The system runs a set of retrieval benchmarks to ensure that search quality has not been compromised.
7. **Resume**: Ingestion and search operations are restored.

### Handling Semantic Drift
In cases where a model update does not change dimensionality but does change the semantic distribution (semantic drift), the system will provide a "re-indexing" utility. This tool iterates through the existing metadata, fetches the raw text, and generates new embeddings without requiring a full manual export. A version compatibility marker (storing the model name and dimension) is kept in the FAISS index metadata to prevent accidental loading of incompatible indices.

### Case Study: Embedding Migration Scenario
Consider a transition from `qwen3-embedding:4b` (384-dim) to a hypothetical `qwen4-embedding:8b` (512-dim).
- **Trigger**: The new model provides superior localization for specific medical labeling tasks.
- **Complexity**: This is a MAJOR version increment due to the dimensionality change.
- **Execution**: The `migrate_embeddings.py` script is used to orchestrate the export-reembed-import flow described above.
- **Verification**: A retrieval comparison test is performed on a set of 100 benchmark queries to ensure that the "top-1" accuracy has improved by at least 5% before the old index is retired.

## 5. Migration Rules

Migration triggers and procedures vary based on the scope of the change and the impact on the user experience.

- **MAJOR Bump Triggers**:
    - Changes to the REST API response envelope shape (e.g., renaming the `data` field).
    - Embedding model changes requiring a complete FAISS index rebuild.
    - Breaking changes to the WebRTC signaling protocol or LiveKit agent orchestration.
    - Fundamental changes to the memory storage format on disk (e.g., migrating from JSON to a database).
- **MINOR Bump Triggers**:
    - Adding new REST endpoints (e.g., a new `/v1/perception/qr/analyze` path).
    - Introducing new models to the perception pipeline (e.g., specialized gesture recognition).
    - Adding new feature flags for opt-in capabilities like persistent face tracking.
    - Introducing new monitoring or telemetry metrics for system health.
- **PATCH Bump Triggers**:
    - Bug fixes in existing endpoints or processing logic.
    - Updating model weights while maintaining the same architecture and dimension.
    - Adjusting default configuration values for better VRAM utilization.
    - Updating third-party dependency versions to address security vulnerabilities.

### Config Migration Logic
The application uses a robust configuration loader in `shared/config/`. When a new version introduces new environment variables, the loader ensures that:
- Default values are provided for all new keys, allowing the system to start with an old `.env` file.
- Warnings are logged for any deprecated keys that are still present.
- A "config doctor" utility is available to help the user migrate their local `.env` file to the latest format without losing custom settings.

#### Config Doctor Utility Features
The `config-doctor` tool provides the following automated checks to prevent versioning-related configuration errors:
- **Mandatory Key Validation**: Checks that all keys required for the `architecture_mode` are present in the `.env` file.
- **Value Range Enforcement**: Ensures that confidence thresholds and distance limits are within logical bounds (e.g., 0.0 to 1.0).
- **Path Sanitization**: Verifies that all local model paths are absolute and accessible by the application user.
- **Secret Obfuscation**: Validates API key formatting without logging the actual sensitive content to the terminal.

## 6. Backward Compatibility Guarantees

The system provides specific guarantees to ensure reliability within a MAJOR version release, acknowledging that blind users rely on consistent behavior for their safety and independence.

- **REST API**: The response envelope format, including the `success`, `data`, and `meta` fields, remains stable. Field names within payloads will not be removed or renamed.
- **WebRTC Protocol**: The LiveKit room protocol and signaling mechanisms are preserved. Existing agent scripts will continue to function without modification.
- **Memory Format**: The FAISS index and associated metadata formats are maintained as long as the embedding model version is constant.
- **Feature Flags**: New flags always default to `false` (opt-in), and existing flags are never removed without a MAJOR version increment.
- **Configuration**: New environment variables are introduced with default values. The removal of any existing environment variable is treated as a breaking change.
- **Model Fallbacks**: CPU fallback paths are maintained for all GPU-accelerated models. This ensures that even if the GPU budget is exceeded or driver issues occur, the system can still provide degraded but functional assistance.

### Long-Term Support (LTS) Models
Certain models, such as the Braille recognition engine and basic object detection, are designated for Long-Term Support. These models will receive weight updates and bug fixes while keeping their architecture and API signature identical for at least 12 months. This provides a stable foundation for the accessibility features that users rely on most for daily independence.

### Compliance and Accessibility Guarantees
Consistency is paramount for blind users who rely on auditory and haptic feedback.
1. **TTS Consistency**: The choice of TTS voice (ElevenLabs voice profile) is treated as a versioned artifact. Sudden changes to the primary assistant voice are avoided within a MAJOR version.
2. **Audio Cue Stability**: High-priority alert sounds (e.g., for low battery or obstacle detection) follow a strict "no-change" policy within a MAJOR version to preserve the user's learned responses.
3. **Response Pacing**: The timing and verbosity of descriptions are tuned for accessibility. Any significant changes to the "concise vs. verbose" logic require a MINOR version bump.

By adhering to these guarantees, the Voice & Vision Assistant maintains a high level of operational stability while allowing for continuous technological improvement.
