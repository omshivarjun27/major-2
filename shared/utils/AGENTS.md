## 1. Purpose
- Define utility primitives that are leaned on by all layers.
- Document interfaces for encryption, timing, and runtime diagnostics.
- Ensure reusability, testability, and safety across the codebase.
- Promote a minimal, dependency-light approach for shared utilities.

## 2. Components
- encryption.py: AES-256-GCM based encryption/decryption utilities.
- timing.py: High-resolution timing helpers for profiling and timeout guards.
- runtime_diagnostics.py: Health and runtime checks (830 LOC) for quick triage.
- Shared helpers for error wrapping and safe casting where appropriate.
- Minimal IO or side effects to keep utilities deterministic.

## 3. Dependencies
- Python 3.10+.
- Cryptography or PyCryptodome for AES-256-GCM; ensure consistent backends.
- No cross-layer imports; utils are strictly shared resources.
- Tests live under tests/utils.

## 4. Tasks
- Architect and implement AES-256-GCM primitives with associated tests.
- Expose timing utilities for performance measurements with minimal overhead.
- Extend runtime_diagnostics with stable health checks and metrics.
- Add type hints and docstrings for all public APIs.
- Ensure encryption keys are not logged and are loaded securely.
- Create example usage fixtures for demonstration and testing.

## 5. Design
- Stateless, deterministic utilities with explicit inputs/outputs.
- Encryption follows authenticated encryption to prevent tampering.
- Timing utilities provide wall-clock and monotonic clocks for reliability.
- Diagnostics expose clear pass/fail signals with non-sensitive metadata.
- Embrace simple, readable code to facilitate auditing and maintenance.

## 6. Research
- Review recommended encryption patterns and side-channel protections.
- Explore best practices for timing accuracy and clock skew.
- Assess potential overhead of diagnostics on hot paths.
- Validate integration symmetry with the logging subsystem for tracing.

## 7. Risk
- Misuse of encryption keys or exposure via logs.
- Performance impact if timing utilities are overly granular.
- Incomplete diagnostics could hide latent issues.
- Legacy compatibility concerns when refactoring to newer Python versions.

## 8. Improvements
- Add a public API reference doc and examples for all utilities.
- Introduce regression tests for encryption and timing invariants.
- Centralize configuration for cryptography backends to simplify upgrades.
- Instrument utilities with lightweight telemetry for debugging without leaking data.

## 9. Change Log
- Created AGENTS.md for shared/utils detailing encryption, timing, and diagnostics.
- Documented public APIs, usage expectations, and testing guidance.
- Aligned with the 9-section AGENTS.md template.
