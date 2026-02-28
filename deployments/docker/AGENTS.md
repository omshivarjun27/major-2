## Purpose
- Document the multi-stage Dockerfile strategy and container runtime posture.
- Outline build-time steps, runtime user choices, and security considerations.
- Provide guidance for maintainers to reproduce locally and in CI.

## Components
- Multi-stage Dockerfile, base images, and final runtime image.
- Build args, environment variables, and health check integration.
- Image tagging, caching strategy, and non-root execution notes.

## Dependencies
- Requires Docker daemon access and compatible CI runners.
- Relies on configs/AGENTS.md for environment configurations used in images.
- Depends on deployments/docker/ wrappers for local testing workflows.

## Tasks
- Refactor to ensure non-root user is used in all stages where feasible.
- Minimize final image size by pruning unnecessary build artifacts.
- Add static analysis to catch root user usage and insecure practices.

## Design
- Isolate build-time dependencies from runtime to reduce attack surface.
- Use explicit USER and HEALTHCHECK directives for reliable operation.
- Tag images with version hashes and semantic tags for traceability.

## Research
- Compare base images for security and size trade-offs.
- Investigate best-practice for non-root execution in multi-stage builds.
- Assess compatibility with CI cache strategies and reproducibility.

## Risk
- Running as root or leaking build-time secrets into final images.
- CI cache misses leading to long rebuild times.
- Platform differences causing image incompatibilities across environments.

## Improvements
- Introduce a docker-hardening checklist for every image.
- Add automated image scanning and license checks in CI.
- Document rollback procedures for failed deployments.

## Change Log
- 2026-02-23: Created AGENTS.md for deployments/docker directory.
- 2026-02-23: Outlined security and build considerations.
