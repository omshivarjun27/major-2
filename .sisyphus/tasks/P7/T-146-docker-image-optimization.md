# T-146: Docker Image Optimization

**Status**: not_started
**Priority**: P7 — DevOps
**Created**: 2026-03-02

## Summary
Optimize Docker image with multi-stage build, dev dependency removal, HEALTHCHECK directive, pinned base images, and Trivy security scan. Target: <1.5GB image size, zero critical vulnerabilities, startup <30s.

## Deliverables
- Optimized multi-stage Dockerfile (`deployments/docker/Dockerfile`)
- HEALTHCHECK directive for container orchestration
- Trivy scan configuration and baseline
- Image size and startup time benchmarks

## Acceptance Criteria
- [ ] Multi-stage build separates build and runtime stages
- [ ] Dev dependencies excluded from production image
- [ ] HEALTHCHECK directive added with appropriate interval and timeout
- [ ] Base images pinned to specific digest/version
- [ ] Trivy scan reports zero critical vulnerabilities
- [ ] Final image size < 1.5GB
- [ ] Container startup time < 30 seconds
