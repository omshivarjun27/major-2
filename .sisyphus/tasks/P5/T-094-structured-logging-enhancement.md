# T-094: Structured Logging Enhancement

## Metadata
- **Phase**: P5
- **Cluster**: CL-OPS
- **Risk Tier**: Low
- **Upstream Deps**: [T-091]
- **Downstream Impact**: [T-108]
- **Current State**: completed

## Objective

Enhance the structured logging system in `shared/logging/` to emit JSON-formatted logs with consistent fields:
- timestamp, level, module, function
- correlation_id, session_id
- latency_ms, service_name

Add log aggregation configuration for ELK stack or Loki. Ensure all modules use the structured logger consistently.
Add request tracing via correlation IDs that propagate through the full pipeline from STT input to TTS output.

## Acceptance Criteria

1. LogContext class for correlation ID management
2. Correlation IDs propagate through async calls
3. Loki/ELK configuration templates
4. Unit tests verify correlation ID propagation

## Implementation Notes

- Build on existing logging_config.py
- Use contextvars for async-safe correlation
- Add middleware/decorator for auto-propagation
