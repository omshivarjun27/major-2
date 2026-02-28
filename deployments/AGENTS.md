## Purpose
- Define deployment guidance for containerized services and compose configurations.
- Capture multi-stage build practices, runtime user considerations, and security posture.
- Provide a reference for maintainers to ensure repeatable, auditable deployments.

## Components
- Dockerfiles, docker-compose files, and related deployment scripts.
- Health checks, logging configuration, and resource limits.
- Security notes including non-root usage and privilege boundaries.

## Dependencies
- Requires proper configuration in configs/AGENTS.md to align with envs.
- Needs CI/pipeline steps for validation and image tagging.
- Depends on infrastructure service adapters for image composition.

## Tasks
- Add non-root user usage to all Dockerfiles where missing.
- Harden Docker images with multi-stage builds and minimal base images.
- Validate build-cache strategy and image size targets.

## Design
- Emphasize reproducible builds and deterministic tagging.
- Isolate build-stage artifacts from runtime-stage containers.
- Ensure images are testable via lightweight integration tests.

## Research
- Evaluate the trade-offs of different base images for security vs. size.
- Review best practices for container hardening and runtime isolation.
- Assess impact of root-running Dockerfiles in the current plan.

## Risk
- Security gaps if images run as root or expose sensitive layers.
- Build failures due to cache misses or network constraints.
- Drift between local dev and production container configurations.

## Improvements
- Introduce a security baseline checklist for each image.
- Implement automated image scanning and vulnerability reporting.
- Standardize labels and metadata across all images.

## Change Log
- 2026-02-23: Established AGENTS.md for deployments directory.
- 2026-02-23: Documented docker-related design and risk areas.
