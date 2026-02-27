## 1. Purpose
- Establish structured JSON logging across the shared layer with PII scrubbing.
- Provide a minimal, safe, and uniform logging surface for all modules to use.
- Ensure log formats are machine-parsable for centralized analysis and tracing.
- Enforce redaction policies to protect user privacy in all logs.
- Document logger lifecycle, levels, and configuration defaults.

## 2. Components
- JSONFormatter producing consistent key-value entries for events.
- PII scrubber utility integrated into all log handlers.
- Logger adapter to enforce uniform fields (service, environment, correlation-id).
- Contextual enrichment hooks for tracing and correlation across modules.
- Redaction rules for names, emails, tokens, and secrets in logs.
- Log rotation and retention strategy in production deployments.

## 3. Dependencies
- Python 3.10+ and standard logging module.
- No hard dependencies on external services; logs are buffered locally and shipped later.
- Must not import from higher layers; logging is a shared capability only.
- Tests reside under tests/logging.

## 4. Tasks
- Implement JSON logging with a stable schema and redaction policy.
- Integrate a pii_scrubber to sanitize sensitive fields before emission.
- Create a logger factory with environment-driven levels and output sinks.
- Add unit tests for redaction and formatting.
- Add documentation on log schema and usage patterns for developers.
- Ensure logs are safe in development and production (no secrets visible).

## 5. Design
- Centralize log fields: timestamp, level, message, service, env, request_id, user_id.
- Redaction is applied at the emission point; raw data is kept in memory but never logged.
- Support structured fields for correlation (trace, span, parent IDs).
- Provide safe defaults and sensible rollover/rotation policies.
- Use a small, testable surface area to avoid architectural drift.

## 6. Research
- Review best practices for structured logging and redaction in Python apps.
- Evaluate compatibility with log aggregation tools and SIEM pipelines.
- Explore options for asynchronous or buffered logging to avoid hot-path latency.
- Consider log sampling for high-traffic scenarios to reduce volume.

## 7. Risk
- Incomplete redaction leading to PII leakage in production logs.
- Performance impact on hot paths if logging is too verbose.
- Misconfiguration of sinks causing log loss or duplication.
- Hard-to-track correlation if correlation fields are missing.

## 8. Improvements
- Add a log schema validator to catch schema drift during tests.
- Integrate with tracing frameworks for end-to-end visibility.
- Provide a CLI to dump current logger configuration for debugging.
- Add sample dashboards and query templates for common events.

## 9. Change Log
- Created AGENTS.md for shared/logging with JSON formatting and pii scrubber basics.
- Established field schema and redaction policy to protect privacy.
- Documented the developer guidance for consistency across modules.
