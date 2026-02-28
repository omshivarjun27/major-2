# Governance Model: Quality Assurance and Compliance Framework

## Overview and Purpose

This document defines the strict engineering standards and operational protocols for the Voice and Vision Assistant for Blind project. With a codebase exceeding 48,000 lines and a 5-layer modular monolith architecture, maintaining system integrity requires total compliance with these rules. Every task in our 150-step execution plan must satisfy these requirements to ensure the reliability and safety of this accessibility platform. 

Compliance with this model is non-negotiable for all team members. The framework ensures that we maintain our 500ms hot path SLA and manage our 8GB VRAM budget effectively. It also protects the modularity of the system, preventing architectural drift over the course of the project.

## Section 1: Task Approval Logic

Every task must pass a pre-flight check before execution starts. This check includes several critical validations that must be documented in the task's initial state. Failure to pass these checks will result in the task being returned to the planning phase.

The validations required for task approval are as follows:
1. Verifying that the dependency graph (DAG) remains acyclic after the proposed changes.
2. Confirming that no circular imports are introduced into the codebase, enforced by the import-linter.
3. Explicitly identifying every file that will be modified or created by the task.
4. Defining a specific test plan before any code modifications occur, including expected outcomes.

Tasks that modify files in shared/schemas/ or shared/config/ carry a system-wide blast radius. These changes require elevated review and exhaustive impact analysis across all downstream layers: core, application, infrastructure, and apps. Phase 0 tasks focus on security and foundational stability. These are high-priority items that you cannot defer under any circumstances. If a task creates a new module, you must immediately generate an AGENTS.md file for the new directory. This ensures our documentation map stays synchronized with the actual codebase structure.

## Section 2: Documentation Compliance Validation

Code changes are incomplete without corresponding documentation updates. We treat documentation as a first-class citizen in this project. Every task must include the following documentation artifacts:
1. An update to the changelog-fragment.md file detailing every functional and structural modification.
2. Updates to any affected AGENTS.md files to reflect functional shifts or new capabilities.
3. Strict compliance with Section 16 of Memory.md, also known as the Agent Update Contract.

A task only reaches completion when all 15 required task folder files are present and contain relevant data. These files include:
- task.md
- reasoning.md
- research.md (for P0, P1, and P2 tasks)
- learnings.md
- issues.md
- decisions.md
- problems.md
- And others defined in the task-template-blueprint.md.

We do not accept empty placeholders or generic templates. If any documentation block is missing or insufficient, the task remains open. This rigorous documentation cycle ensures that the system's internal knowledge base stays accurate for multi-session reasoning and future maintenance by other developers.

## Section 3: Test Compliance Enforcement

We maintain a zero-tolerance policy for untested code. Every functional change requires a comprehensive testing strategy. The requirements are as follows:
1. At least one unit test for every modified function in the task.
2. Integration tests for all cross-module changes, such as core-to-application transitions.
3. Performance tests for any change touching the 500ms hot path or the 8GB VRAM budget.

Our test suite currently contains 840 functions. This number must increase with every task. We treat our test count as a monotonically increasing target. A task that causes the total test count to drop or coverage to decrease is considered a regression. Such tasks will be blocked from completion until the testing gaps are filled and the baseline is restored or improved. High-quality tests are the only way to ensure the long-term stability of an accessibility tool.

## Section 4: Architecture Review Requirement

Our 5-layer hierarchy consists of shared, core, application, infrastructure, and apps. This structure is the foundation of the project's maintainability. Any change that crosses these layer boundaries requires a formal architecture review. We use the import-linter tool to enforce these boundaries during every task execution. 

If you modify any import statement, you must run the linter and ensure it passes without errors. We are also actively reducing technical debt related to large files. The god file at apps/realtime/agent.py currently exceeds 1,900 lines of code. This violates our single responsibility principle. No file may exceed 500 lines after Phase 2 completion. Every task should aim to decompose large modules into smaller, testable units that respect our architectural constraints and reduce cognitive load for developers.

## Section 5: Regression Protection

We protect the system against regression through mandatory before-and-after test comparisons. This process ensures that new features do not break existing functionality. The process includes:
1. Establishing a coverage baseline for all affected modules before starting the work.
2. Running the full test suite after implementation to verify all results.
3. Investigating and fixing any test failures introduced by the changes immediately.

Any failure introduced by your changes blocks the task from completion. We track coverage metrics to ensure we do not lose visibility into critical code paths. If a task introduces unresolvable issues or architectural violations, you must execute the rollback procedure. This involves an atomic reversion of both the source code and the associated documentation files. We do not allow the repository to exist in an inconsistent or broken state.

## Section 6: Model Reasoning Enforcement

Transparency in decision-making is essential for long-term project health. Every task must include a reasoning.md file explaining the logic behind your implementation. The following rules apply:
1. For non-trivial decisions, you must evaluate at least two different alternatives.
2. You must compare trade-offs, performance impact, and architectural alignment for each option.
3. We do not allow shortcuts just because they seem faster or easier in the short term.

Even simple changes require a brief justification to maintain a clear audit trail for the Architecture Council. The depth of your reasoning should scale with the task's risk profile. P0 security tasks require exhaustive analysis and detailed logic. P3 tasks require a concise rationale. This ensures that every line of code in the project has a documented purpose and follows established engineering principles.

## Section 7: Research Depth Requirement

Research is a mandatory prerequisite for implementation on all non-trivial tasks. We use research to validate our approach before writing any code. The requirements are:
1. P0 and P1 tasks require a full research.md file with at least three evaluated options.
2. P2 tasks require a research document with at least two evaluated options.
3. P3 tasks require an inline justification within the task.md file for the selected approach.

All research must reference actual files and models within the repository, such as YOLO v8n, MiDaS v2.1, or Qwen-VL. We do not use hypothetical scenarios or general AI-generated advice. Research must be grounded in the project's current technical reality and measured data points. Findings should be archived in the learnings.md file to prevent repeated investigation and help other team members build on your work.

## Section 8: Anti-Shortcut Enforcement

We are eliminating stubs from the codebase to improve system reliability and predictable behavior. The following rules are strictly enforced:
1. Do not add any new stub implementations. We are systematically replacing the existing 71 stubs.
2. No "pass" or "NotImplementedError" statements are allowed in production code after Phase 1.
3. No "# type: ignore" comments are permitted without a detailed documented justification.
4. No bare "except:" clauses are allowed, as currently flagged in ISSUE-016.

Hardcoded credentials, API keys, or absolute local paths are strictly forbidden. Use the centralized configuration system in shared/config/ and environment variables. All new feature flags must be fully documented in settings.py to ensure they can be managed effectively during deployment and testing. Our goal is a production-ready system that doesn't rely on brittle hacks or undocumented behavior. Every line of code must be reliable and maintainable for the life of the project.

## Compliance and Enforcement Procedures

Any task violating two or more of these governance gates is automatically failed and returned to the task queue. The Architecture Council will then review the task for re-scoping or additional planning. We prioritize the quality of our code and the clarity of our documentation over the speed of execution. This is the only way to build a reliable and safe tool for the blind and visually impaired community.

The following metrics are tracked after every task:
- Test count (must be monotonically increasing)
- Coverage percentage (must not decrease)
- Linting status (must remain clean)
- Documentation completeness (15 files verified)
- Import-linter status (no circular dependencies)

By following these procedures, we ensure that the Voice and Vision Assistant for Blind remains a reliable and high-fidelity accessibility platform. 

*End of Governance Model Document*

