---
title: "Rollout & Migration Plan"
version: 1.0.0
date: 2026-02-22T15:31:00Z
architecture_mode: hybrid_cloud_local_gpu
---

# Rollout and Migration Plan

This document defines the strategy for promoting the Voice & Vision Assistant from development to production environments. It covers the deployment flow, scaling strategies, and migration paths for critical components like the FAISS index and model weights. The goal is to ensure a reliable and predictable update process for the assistive technology.

## 1. Dev → Staging → Production Promotion Flow

The promotion flow ensures that code changes move through increasingly rigorous environments before reaching the user. Each stage has specific hardware configurations and validation gates to catch issues early.

### 1.1 Development Environment
The development stage happens on local machines, typically equipped with an NVIDIA RTX 4060 GPU. Developers run all services locally, including the FastAPI server, LiveKit agent, and local Ollama instance. This environment allows for rapid iteration and debugging of the perception pipeline and reasoning logic.

Developers are responsible for:
- Writing unit tests for new features and bug fixes.
- Running the `ruff` linter and formatter to ensure code quality and consistency.
- Verifying that architectural boundaries are respected via `lint-imports`.
- Ensuring that no secrets are committed to the `.env` file using local scanning tools.
- Manual testing of voice commands and visual feedback using a webcam.

### 1.2 Staging Environment
Staging serves as a pre-production mirror. It uses a Docker-based environment that replicates the production stack as closely as possible. Staging uses sandbox API keys for cloud services like Deepgram and ElevenLabs to avoid production data contamination and unnecessary costs. It provides a stable ground for integration testing and performance benchmarking.

In staging, the following activities take place:
- Integration testing across all system layers, from vision to speech synthesis.
- Performance benchmarking of the perception pipeline to ensure it meets latency targets.
- Verification of cloud service connectivity and graceful fallback mechanisms.
- Security scans using `detect-secrets` on the final build artifacts.
- Load testing of the REST API endpoints to ensure they handle concurrent requests.

### 1.3 Production Environment
The production environment is the live system used by the end user. It features full cloud integration, a GPU-enabled Docker container with pass-through, and active monitoring. Production uses the main LiveKit room and primary API credentials for all services.

Production standards include:
- High availability for the core transport layer (LiveKit).
- Active monitoring of system health, GPU memory usage, and processing latency.
- Secure handling of all user data, with encryption for sensitive files.
- Automated restarts via the watchdog service if stalls are detected.
- Log aggregation for troubleshooting production issues.

### 1.4 Promotion Gates
Transitioning between environments requires meeting these strict criteria:
- **Unit & Integration Tests**: All tests in the `tests/` directory must pass with a 180-second timeout.
- **Linting & Formatting**: `ruff check` and `ruff format` must be clean without any ignored errors.
- **Architectural Boundaries**: `lint-imports` must verify that layer constraints remain intact.
- **Security Scans**: `detect-secrets` must report no leaked credentials in any committed file.
- **Docker Build**: The image must build successfully using the multi-stage Dockerfile without warnings.
- **Documentation**: All new features must be documented in the corresponding PRD or LLD artifacts.

## 2. Blue-Green Deployment Strategy

We use a blue-green strategy to minimize downtime during updates. This approach involves two identical environments, blue and green, running the Docker containers.

### 2.1 Traffic Management
A local load balancer or a simple Docker Compose swap manages traffic. While one version (blue) handles live requests, the new version (green) is deployed and tested in isolation. Once the green environment passes health checks, traffic switches over instantly.

The traffic switch is handled at the network level, ensuring that existing sessions are completed before the old container is shut down. This prevents user disruption during minor updates or bug fixes. For the WebRTC agent, new connections are routed to the green instance, while the blue instance remains active until all active calls end.

### 2.2 Maintenance Windows
Since this is a single-user system, the blue-green swap effectively functions as a hot-swap during scheduled maintenance. If the new version fails a health check after the switch, the system reverts to the previous environment immediately.

Maintenance windows are scheduled during periods of low usage, typically in the late evening. Users are notified through the voice interface if a restart is required for a major system update that might interrupt their experience.

## 3. Canary Strategy for Cloud Services

The system relies on several cloud providers for LLM reasoning (qwen3.5:cloud), speech-to-text, and text-to-speech. We use a canary approach for configuration changes to these external dependencies.

### 3.1 Gradual Rollout
When updating API versions or switching model identifiers, we apply changes to staging first. We monitor cloud latency and error rates during this period. Feature flags in the `shared.config` module allow us to toggle between different cloud service versions without redeploying the entire stack.

We rollout changes to a small subset of requests (or a test user account) before applying them to the entire production environment. This limits the blast radius of any potential cloud-side regressions or breaking changes in provider APIs.

### 3.2 Metric Monitoring
During a canary rollout, we track specific metrics:
- **TTFT (Time to First Token)**: Must stay under 150ms for LLM responses to ensure a natural conversation.
- **STT Latency**: Real-time transcription must maintain a low lag for responsive interaction.
- **API Error Rates**: Any increase in 4xx or 5xx errors triggers an immediate rollback to the previous configuration.
- **Cost Impact**: We monitor usage levels to ensure the new model or version fits within the operational budget.

Monitoring dashboards provide real-time visibility into cloud provider performance, allowing the operations team to react quickly to service degradations before they impact the user.

## 4. GPU Scaling Strategy

The hardware strategy focuses on vertical scaling to meet VRAM requirements for local model inference on a single node.

### 4.1 Vertical Scaling Path
The baseline hardware is an RTX 4060 with 8GB VRAM. If future model upgrades require more memory, the path involves moving to an RTX 4070 (12GB) or 4080 (16GB). The single-user, single-node design means horizontal GPU scaling is not supported or required for this use case.

Vertical scaling is simpler to manage, reduces configuration complexity, and avoids the latency overhead associated with multi-node communication. The 8GB VRAM limit is the primary constraint for our current model selection.

### 4.2 VRAM Budget Management
The current peak VRAM usage is approximately 3.1GB, which fits comfortably within the 8GB limit. This leaves significant room for higher-resolution vision models or larger local embedding models in future releases. 

VRAM allocation breakdown:
- qwen3-embedding:4b (local embedding): ~2.0GB
- OCR (EasyOCR primary backend): ~0.5GB
- YOLO v8n (object detection): ~0.2GB
- MiDaS v2.1 (depth estimation): ~0.1GB
- Face Detection (tracking and embeddings): ~0.3GB

We use `torch.cuda.memory_allocated()` to monitor memory usage before and after inference tasks. If total VRAM usage exceeds 90% of the available capacity, the system triggers a warning log and may automatically disable non-essential models like face detection or secondary OCR backends to preserve stability.

## 5. FAISS Index Migration

The memory engine currently uses `IndexFlatL2`, which is a brute-force search algorithm. As the vector count grows, we must migrate to an Approximate Nearest Neighbor (ANN) index to maintain performance.

### 5.1 Target Index Types
Following the backlog item BACKLOG-005, we will migrate to `IVFFlat` or `HNSWFlat` for improved search performance. The goal is to keep search latency under 50ms for up to 5,000 vectors.

ANN indices provide sub-linear search time at the cost of a small decrease in retrieval precision. This trade-off is acceptable for the memory retrieval use case where user experience is driven by response speed.

### 5.2 Migration Steps
The migration involves the following steps:
1. **Export Vectors**: Dump all existing embeddings and metadata from the current `data/memory_index/` directory into a portable format.
2. **Create New Index**: Initialize the ANN index with the correct dimensions (matching the 4096-dim qwen3-embedding:4b model).
3. **Index Training**: For IVFFlat, train the index centroids on a representative sample of existing vectors to optimize clustering.
4. **Bulk Insert**: Load the exported vectors into the new index structure in batches.
5. **Verify Quality**: Run a set of benchmark queries to ensure search accuracy hasn't degraded significantly.
6. **Production Swap**: Replace the old index files with the new ones during a scheduled maintenance window.

### 5.3 Backward Compatibility
The system will maintain a fallback mechanism to the old index file if the new one fails to load correctly during the migration window. We keep the old index on disk as a backup for 30 days after a successful migration to allow for emergency reverts.

## 6. Model Update Strategy

Updating ML models requires careful versioning and performance verification to avoid regressions in perception accuracy or system stability.

### 6.1 Version Pinning
Models are pinned to specific versions to ensure consistency across environments:
- **YOLO v8n**: The ONNX weight file is stored in `models/yolov8n.onnx` and versioned in the metadata.
- **MiDaS v2.1**: The weight file is `models/midas_v21_small_256.onnx`.
- **Local Embedding**: The `qwen3-embedding:4b` model is tracked via Ollama's local tag system.
- **Cloud LLM**: The `qwen3.5:cloud` version is tracked via the Ollama cloud identifier in the environment config.

### 6.2 Update Process
When a new model version is released (e.g., YOLO v10), it undergoes testing in staging. We benchmark it against existing performance SLAs for latency, VRAM footprint, and detection accuracy. 

The update process includes:
- Quantization testing (e.g., INT8 vs FP16) to optimize for the RTX 4060 hardware.
- Accuracy verification on the standard perception test set (e.g., COCO for detection).
- Latency measurement in the integrated pipeline under realistic frame rates.
- Documentation of the model changes and any expected behavioral shifts in the release notes.

If the new model passes all checks, we update the weight files or model tags in the deployment configuration and push the change through the standard promotion flow.

## 7. Rollback Plan

A robust rollback plan is essential for maintaining system availability when an update goes wrong.

### 7.1 Rollback Procedures
The system supports several levels of rollback depending on the failure type:
- **Docker Image**: Use `docker tag` and `docker push` to revert to the previous stable image. This is the fastest way to recover from code errors or logic bugs.
- **Model Weights**: Restore the previous ONNX files from the `models/` backup directory. This handles perception regressions or model-specific crashes.
- **Configuration**: Revert environment variables or the `config.yaml` file to the last known good state. This fixes cloud connectivity or credential issues.
- **FAISS Index**: Restore the `data/memory_index/` directory from the most recent daily backup. This recovers from data corruption or index incompatibility.

### 7.2 Service Level Agreements (SLA)
- **Docker Swap**: Should take less than 5 minutes from failure detection to resolution.
- **Full System Rollback**: Including models and data, should be completed within 15 minutes.

Rollback triggers include:
- Frame processing latency exceeding 2 seconds for more than 5 consecutive frames.
- Cloud service error rate exceeding 10% over a 5-minute window.
- System crashes or watchdog restarts occurring more than once per hour.
- User feedback indicating significant regressions in voice interaction quality.

## 8. Data Backup Strategy

Regular backups protect user data and system state from hardware failure, data corruption, or accidental deletion.

### 8.1 Backup Components
- **FAISS Index**: File-level backup of the `data/memory_index/` directory containing vectors and metadata.
- **QR Cache**: Backup of the `qr_cache/` JSON files to prevent re-scanning of known locations and products.
- **Face Consent**: Backup of the `data/face_consent.json` file to preserve privacy settings and user permissions.
- **Session Data**: Full exports of user interactions are available via the `/export/full` REST endpoint for troubleshooting.
- **Config Files**: Backup of `config.yaml` and `.env` (stored securely and encrypted).

### 8.2 Frequency and Retention
- **Index Backups**: Performed daily at 3:00 AM to capture new memory entries.
- **Cache & Consent**: Performed weekly as these change less frequently than memory.
- **Retention**: We maintain a 7-day rolling window of daily backups and a 4-week window of weekly backups to balance storage space and recovery options.

### 8.3 Restoration Testing
Every month, the operations team performs a restoration test. They verify that the system can be fully recovered from the backups on a clean staging environment. This ensures that the backups are valid, the encryption keys are accessible, and the restoration procedure is well-documented.

Data integrity is checked using MD5 checksums stored alongside the backup files. Any checksum mismatch during the backup or restoration process triggers an immediate alert and a new backup attempt. Backup files are stored on a separate physical disk or a secure cloud storage bucket to prevent total loss in case of local hardware failure.

## 9. Monitoring and Post-Rollout Validation

After a successful production swap, the system enters a high-priority monitoring phase for the first 24 hours. During this period, the following validation steps are performed:

- **Manual Verification**: A technician performs a series of standard voice interactions to ensure the assistant is responding correctly and perception models are functioning as expected.
- **Log Analysis**: Automated scripts scan the production logs for any new warnings or errors that were not present in the staging environment.
- **Latency Tracking**: We compare real-world processing times with the benchmarks established during staging to verify that the system remains responsive under varied lighting and network conditions.
- **User Feedback Collection**: For major releases, we monitor user interaction patterns to detect any unusual drops in engagement that might indicate a subtle issue with the updated features.

If any anomalies are detected during the post-rollout phase, the engineering team evaluates the severity. Minor issues may be addressed with a hotfix, while critical failures trigger the rollback procedures described in Section 7. This rigorous validation ensures that every release maintains the high standards of accessibility and reliability required for this assistive device.
