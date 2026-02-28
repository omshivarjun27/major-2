1. Folder Purpose
- This AGENTS.md documents the top-layer FastAPI REST server in apps/api.
- It exposes port 8000 for management, state queries, and orchestration endpoints.
- The goal is to provide stable, well-scoped HTTP surfaces that others can reuse.
- It acts as the gateway to domain logic implemented in core/application layers.
- The document serves as a contract for maintainers and new contributors.

2. Contained Components
- server.py: FastAPI application with 28 endpoints orchestrating requests to core modules.
- __init__.py: Package initializer and API router exports.
- dependencies (internal): middleware, auth stubs, and request validators.
- schemas: request/response models used by API handlers.
- tests: unit/integration tests under tests for REST endpoints (not in this folder).

3. Dependency Graph
- API layer depends on application services for business rules.
- Middleware depends on shared utilities for logging and error handling.
- Validation schemas depend on pydantic models defined in shared/
- No direct access to infrastructure; adapters live behind the application layer.
- The graph enforces the 5-layer boundary: shared -> core -> application -> infrastructure -> apps.

4. Task Tracking
- Status: in_progress - endpoint catalog validation in progress.
- Pending tasks: validate security headers, add input validation, improve rate-limiting hooks.
- Completed tasks: initial endpoint scaffolding and FastAPI app startup checks.
- Owners: API team, with collaboration from dev-ops and security.

5. Design Thinking
- Prefer explicit request schemas and typed responses to minimize ambiguity.
- Keep business logic out of route handlers; delegate to application services.
- Implement robust error propagation with JSON error bodies and consistent status codes.
- Use feature flags for risky endpoints and gradual rollout in production.
- Consider backwards compatibility when evolving public API contracts.

6. Research Notes
- Review of representative FastAPI patterns shows value in dependency injection and routers.
- Investigate existing security headers and input validation strategies in the repo.
- Documented endpoint usage with curl examples would aid onboarding.
- Security recommendation: avoid exposing internal schemas and ensure proper CORS settings.
- Plan to align with 5-layer architecture to minimize coupling.

7. Risk Assessment
- R1: Surface area growth increases attack surface and maintenance burden.
- R2: Misconfigured dependencies may create circular imports across layers.
- R3: Performance risk if 28 endpoints perform expensive operations synchronously.
- R4: Data validation gaps may lead to security vulnerabilities.
- R5: Incomplete error handling could leak sensitive information.

8. improvement Suggestions
- Introduce endpoint-level tests with realistic payloads.
- Add centralized error handler middleware for uniform responses.
- Incremental rollout plan with feature flags for new endpoints.
- Document each endpoint with usage notes in docs or PRD.
- Establish lint rules to enforce consistent API design.

9. Folder Change Log
- 2026-02-23: Created AGENTS.md for apps/api to codify top-layer API practices.
- 2026-02-23: Drafted sections covering design goals and risks.
