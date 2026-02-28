## 1. Purpose
- Define the data schema layer contracts for the base platform.
- Include 52 data models across dataclasses, Pydantic, enums, and ABCs.
- Establish serialization/deserialization rules and validation semantics.
- Provide a stable foundation for inter-layer data exchange while preserving type safety.
- Document governance around model usage and evolution to minimize breaking changes.

## 2. Components
- 22 dataclasses describing domain entities.
- 20 Pydantic models for runtime validation and API contracts.
- 10 enums used for constrained value spaces and semantic rigor.
- 3 abstract base classes (ABCs) for extensible interfaces and mocks.
- Central registry of models and factories for dependency injection in tests.
- Helper validators and custom types shared across models.

## 3. Dependencies
- Python 3.10+ for typing enhancements and dataclass support.
- Pydantic for runtime validation and parsing.
- The shared layer must not import from higher layers; schemas should be dependency catalogs.
- Codegen or manual maintenance tooling should generate broad tests for models.
- Tests reside in tests/schemas.

## 4. Tasks
- Implement 52 models with consistent naming conventions and field typing.
- Create validators for cross-field constraints where needed.
- Build a central schema registry with controlled exposure.
- Write unit tests for edge cases (nullability, invalid enum values, etc.).
- Document serialization formats and error shapes for each model.
- Create sample fixtures for common flows (create/read/update/delete).

## 5. Design
- Clear separation between domain models (business layer) and API contracts.
- Use union types and Optional where appropriate to reflect real-world data.
- Prefer strict validation on deserialization to catch mistakes early.
- Enums provide explicit value spaces to minimize drift.
- ABCs enable easy test doubles and plugin-based extensions.
- Models should be serializable to JSON without loss of fidelity.

## 6. Research
- Align with common Python data modeling patterns in large codebases.
- Investigate performance implications of complex validators and nested schemas.
- Review security implications of sensitive fields and ensure no leakage through reprs.
- Evaluate compatibility with existing codegen and schema evolution strategies.

## 7. Risk
- Breaking API contracts if fields are renamed or removed without migrations.
- Inconsistent validation rules across modules causing data leaks or UI errors.
- Over-strong typing causing friction with external inputs; balance with flexibility.
- Difficulty mocking ABCs in tests.
- Reflection-based operations may complicate serialization.

## 8. Improvements
- Add automatic schema versioning and migrations.
- Provide tooling to diff schema changes and generate migration notes.
- Create synthetic data generators for test coverage.
- Integrate with the memory layer to ensure consistent vector-typed data.
- Document error shapes for all models in developer docs.

## 9. Change Log
- Created AGENTS.md for shared/schemas with 52 data models broken into 4 categories.
- Added governance around model evolution and API compatibility.
- Established serialization norms and validation expectations.
- Ensured alignment with the 9-section AGENTS.md template.
