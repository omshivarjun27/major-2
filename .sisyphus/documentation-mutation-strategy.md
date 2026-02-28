# Documentation Mutation Strategy, Continuous Document Evolution for Voice & Vision Assistant

## Section 1: When Documents Must Be Updated
Living documents are not static artifacts. They are active representations of the system's current state and future direction. Stale documentation is worse than no documentation, as it misleads developers and observers. Therefore, specific triggers are defined for each document type to ensure they evolve alongside the codebase. Documentation hygiene is a primary metric for engineering excellence.

### Detailed Core living documents and their update mandates:

**AGENTS.md (50 files)**: These files are the local source of truth for each module. They must be updated whenever a module's core purpose, its primary components, its internal or external dependencies, its pending tasks, or its associated risks undergo a change. If you add a new file to a module, you must update the AGENTS.md file for that directory. If a task listed as pending is completed, it must be moved to the completed section immediately. These files act as a local map for any agent or developer entering the directory. They provide the immediate context needed to understand the module's role in the larger system. When a stub is replaced with a real implementation, the "Stub Inventory" in AGENTS.md must be decreased and the "Completed Tasks" increased to reflect the new capabilities. Each AGENTS.md must also contain a "Local Task History" that tracks the last 5 changes to the module.

**Memory.md (723 lines, 18 sections)**: This is the central repository of architectural knowledge and project history. Updates here are governed by the Section 16 Agent Update Contract. This document is the "brain" of the project and must be kept in sync with every significant change to the system's architecture or state.
- **Section 1 (Project Overview)**: Updated when the project's purpose or phase changes.
- **Section 2 (Global Architecture Map)**: Updated whenever a new module is created or an existing one is removed to maintain a complete system overview.
- **Section 3 (Service Boundaries)**: Updated when dependency flow rules are changed.
- **Section 5 (API Endpoints)**: Updated for every new REST endpoint added to the FastAPI server to ensure all capabilities are discoverable and documented correctly.
- **Section 6 (Configuration)**: Updated for every new environment variable or change in default settings to ensure environment parity and ease of setup.
- **Section 7 (Dependencies)**: Updated for every new external library added to the project to track the security, licensing, and operational footprint.
- **Section 8 (Performance)**: Updated with new benchmark results or changes to SLA targets to maintain our performance-first mindset and hot path requirements.
- **Section 9 (Security)**: Updated when new security measures are implemented or when vulnerabilities are identified and mitigated through patches or configuration changes.
- **Section 10 (Architectural Decisions)**: Updated with a new ADR entry for every major design choice to preserve the reasoning and context for future teams.
- **Section 15 (Issues & Debt)**: Updated to track technical debt, known bugs, and implementation gaps that require future attention and prioritization.
- **Section 18 (Thinking Log)**: Appended to with every major milestone or session to capture the logic and reasoning behind the current state. This preserves the "why" for future audits.
- **Section 19 (Risk Radar)**: Updated whenever a new architectural or operational risk is identified, ensuring that the risk profile of the system is always transparent and managed.
- **Section 20 (Technical Debt Register)**: Updated as new debt is incurred or existing debt is retired, providing a clear roadmap for refactoring and stabilization efforts.

**progress.md**: This document tracks the project's velocity and milestone completion. It is updated when tasks reach a terminal state, when major milestones are achieved, or when the overall completion percentage shifts. It provides a high-level view of the project's health for stakeholders and external observers. It is the pulse of the development effort and must be accurate to within 1% of the actual task state. It includes a burndown chart of remaining tasks and a history of milestone achievements.

**changelog.md**: Every version-worthy change, fix, or enhancement triggers an update here. This file tracks the historical evolution of the system from a user and developer perspective. It is the narrative of the project's growth and maturity over time. It helps users understand what is new and what has changed in each update, providing a clear path from the past to the present. Each entry should include the date, a summary of changes, and the impact on the user experience.

**test-strategy.md**: This document defines how we ensure quality across the 5-layer architecture. Update it when new test layers are added, such as moving from unit tests to integration tests, when coverage targets are adjusted, or when the testing framework itself changes to support new features or improved reliability. It includes the exact commands for running each test layer and the criteria for passing.

**validation-checkpoints.md**: This file tracks the execution and modification of validation gates. It must be updated whenever a checkpoint is reached, redefined, or when the criteria for passing a gate change based on new requirements or lessons learned from production or testing cycles. It records the date and results of every formal validation run.

**benchmarking-protocol.md**: Performance is a core requirement for real-time accessibility tools. Update this file when benchmarks are executed, when the performance targets for the system are revised, or when new hardware profiles are added to the support list for edge deployment on various devices. It details the exact conditions, tools, and scripts used for performance measurement.

**PRD files**: These are the foundation of the project's requirements and vision. They are updated only when the fundamental product scope, user requirements, or target audience evolve significantly. They represent the "what" and "why" of the system's existence and purpose, guiding all development efforts.

**infrastructure-monitoring.md**: This document tracks the health and telemetry strategy for the system. It must be updated whenever new alerts are defined, when monitoring dashboards are modified, or when the threshold for system warnings is adjusted. It ensures that the operations team has a clear understanding of the system's vital signs and the expected response to various failure modes.

**security-policy.md**: Defines the project's stance on data protection, access control, and vulnerability management. Update it when key rotation policies change, when new encryption standards are adopted, or when compliance requirements from external partners are updated. This document is a critical part of our commitment to user privacy and system integrity.

## Section 2: What Triggers Updates
Triggers for documentation mutation are categorized into eight primary types. Each type requires a specific set of updates across the document library to maintain synchronization between the code and its description.

### Trigger Impact Matrix and Requirements
| Trigger Type | Mandatory Document Updates | Secondary Documentation Impact | Expected Documentation Depth |
|:-------------|:---------------------------|:-------------------------------|:-----------------------------|
| **Code Addition** | AGENTS.md, Memory.md (Sec 3, 5), changelog.md, progress.md | test-strategy.md, docs/ | High: Full functional description |
| **Refactoring** | AGENTS.md, Memory.md (Sec 2), test-strategy.md | validation-checkpoints.md | Medium: Structural changes only |
| **Config Change** | Memory.md (Sec 6), AGENTS.md (Dependencies) | .env.example, Dockerfile | High: Security & Setup impact |
| **New Dependency** | Memory.md (Sec 7), AGENTS.md (Dependencies) | requirements.txt, pyproject.toml | High: License & Security scan |
| **Security Fix** | Memory.md (Sec 9), AGENTS.md (Risks), changelog.md | Security audit logs | Very High: Vulnerability details |
| **Performance Opt** | Memory.md (Sec 8), benchmarking-protocol.md | performance/ tests | Medium: Benchmark results |
| **Bug Fix** | changelog.md, Memory.md (Sec 15 cleanup) | integration/ tests | Medium: Issue ID & Fix summary |
| **Infra Change** | infrastructure-monitoring.md, security-policy.md | Dockerfile, CI/CD | High: Operational & Security impact |
| **Schema Change** | Memory.md (Sec 3, 5), AGENTS.md | API clients, frontend | High: Data contract stability |

### Detailed Trigger Categorization and Identification
- **Code Changes**: Any modification that adds, removes, or alters the behavior of a function, class, or module. This is the primary driver of documentation drift and requires immediate attention to the local AGENTS.md file. Any change that alters the flow of data or the responsibility of a component counts as a trigger that must be documented. If the change impacts the user experience, the PRD and changelog are high priority.
- **Config Changes**: Any change to environment variables, YAML settings, or hardcoded constants that affect the system's runtime behavior or setup process. This must be reflected in the configuration documentation to ensure parity across environments. Identification happens through review of `.env`, `config.yaml`, and `settings.py`.
- **Dependency Changes**: The addition of new external libraries or the significant version upgrade of existing ones. This must be reflected in the supply chain documentation and the dependencies section of the relevant AGENTS.md file to manage risk. Identification happens via `pip list` comparison or `requirements.txt` review.
- **Security Events**: Both proactive changes (new encryption) and reactive changes (patching a CVE) must be documented in the security section of Memory.md to maintain the system's security posture and track any known threats or mitigations. Identification happens through security advisories or internal audits.
- **Performance Events**: Results from benchmark runs or the implementation of logic designed to improve speed or reduce memory footprint. This requires updating the performance metrics and benchmarking protocol to understand the system's constraints and the impact of changes over time. Identification happens through benchmark results.
- **Architecture Decisions**: High-level choices about patterns, data flow, or third-party integrations that will have a long-term impact on the system's design. These decisions are the "pivot points" of the project and require a new ADR entry in Memory.md Section 10 to ensure clarity for all team members. Identification happens during design reviews.
- **Infrastructure Events**: Changes to the containerization strategy, CI/CD pipeline modifications, or updates to the local GPU execution environment. These changes impact the "how" of deployment and must be reflected in the operational guides. Identification happens through review of `Dockerfile`, `docker-compose.yml`, and GitHub Actions workflows.
- **Schema Evolutions**: Changes to the core data structures used for inter-module communication or persistence. These are critical "data contracts" that must be documented in the shared schemas section to prevent breakage in downstream consumers. Identification happens through review of `shared/schemas/`.

## Section 3: Automatic vs Manual Mutation
The mutation process is split based on the nature of the information being captured. We aim for maximum efficiency through automation while maintaining high-quality human insight where it provides the most value for the project's longevity. This balance is critical for maintaining accurate and meaningful documentation.

### Automatic Processes and Tools
Automation handles the objective, measurable aspects of the project to ensure accuracy and consistency without human intervention, which can be slow and error-prone for these types of tasks.
- **Changelog Fragments**: Generated for each completed task based on commit messages and pull request descriptions. This ensures the history is always current and provides a clear audit trail. Tools used: Git log parsers and PR decorators.
- **Test Metrics**: Test counts and coverage percentages are updated automatically after every test run via a reporting script that parses the test runner's output and updates the relevant sections in progress.md. Tools used: `pytest --cov`, `coverage-json`.
- **Progress Tracking**: The completion percentage in progress.md is recalculated based on the status of tasks in the tracking system, providing a real-time view of the project's health for all stakeholders. Tools used: Task management APIs or internal task parsers.
- **LOC Analysis**: Lines of code counts for each module are generated by periodic scripts and updated in the architecture map to track growth, identify complexity hotspots, and monitor the system's size over time. Tools used: `cloc`, `wc`.
- **API Spec Export**: Automatically extracting the OpenAPI specification from the FastAPI server and updating the documentation to ensure the REST API interface is always accurately described without manual effort. Tools used: `fastapi.openapi.utils`.
- **Dependency Graph Generation**: Periodically generating visual maps of module dependencies to verify compliance with the 5-layer architecture and detect any unauthorized imports. Tools used: `pydeps`, `import-linter`.

### Manual Processes and Expectations
Human reasoning is required for subjective analysis, strategic decisions, and complex context that automation cannot provide. This is where the developer's insight and experience are most valuable for documentation.
- **Architectural Decision Records**: ADRs in Memory.md Section 10 require deep contextual writing to explain the "why" behind the chosen path and the trade-offs considered during the design process. Expected length: 50-100 lines per ADR.
- **Risk Assessments**: Evaluating the impact of a new feature on the system's safety, privacy, and operational stability. This requires a nuanced understanding of the system's design and operating environment. Expected length: 20-50 lines per assessment.
- **Research Findings**: Qualitative data and observations from model evaluations, hardware tests, or user experience studies. This provides important context that numeric data alone cannot capture. Expected length: Variable based on research scope.
- **Thinking Logs**: Capturing the developer's mindset, logic path, and decisions during the implementation of a complex feature. This helps future maintainers follow the reasoning behind the code. Expected length: 10-20 lines per entry.
- **Integration Scenarios**: Describing complex multi-module workflows, such as the interaction between vision, memory, and speech, which require human narrative to be understandable. Expected length: 30-60 lines per scenario.
- **Security Threat Models**: Analyzing specific attack vectors and the defensive measures implemented to mitigate them. This requires deep domain knowledge and creative thinking. Expected length: 40-80 lines per model.

### Semi-automatic Workflow and Steps
AGENTS.md updates follow a collaborative flow. An agent proposes the changes based on code modifications, and the orchestrator validates and applies them. This maintains consistency while ensuring that the documentation accurately reflects the code's intent and actual implementation without placing an undue burden on the developer. This human-in-the-loop approach ensures the highest documentation quality and prevents errors.
1. **Detection**: Agent detects code change in a specific module.
2. **Drafting**: Agent drafts AGENTS.md update based on the change's impact.
3. **Submission**: Agent submits the documentation update alongside the code.
4. **Validation**: Orchestrator validates the documentation matches the code reality.
5. **Application**: Orchestrator applies the change to the main branch.

### Human Review Cycles and Quality Gates
Documentation is not just written; it is audited. Every month, a senior developer or architect performs a deep-dive review of the document library to ensure consistency, clarity, and relevance. This "documentation sprint" ensures that the long-term narrative of the project remains cohesive even as individual tasks are completed by different agents. This human oversight is the final guard against documentation decay and ensures the library serves its purpose for the entire project lifecycle.

## Section 4: Version Control Discipline
Documentation is treated with the same rigor as source code. It lives in the same repository, follows the same branching strategy, and is subject to the same review process. There is no distinction between "doc work" and "code work" in terms of importance or process. This unified approach is fundamental to our engineering culture.

### The Five Rules of Document Commits and Enforcement
1. **Atoms Only**: All document mutations must be committed atomically with the code change that triggered them. One change, one commit, including its documentation to maintain a clean history. Enforcement: Pre-commit hooks check for doc changes alongside code changes.
2. **No Separation**: Do not separate code and its corresponding documentation into different commits or pull requests. They are two halves of the same whole and must stay together. Enforcement: CI check fails if code changes are detected without corresponding doc changes in the same PR.
3. **Strict Formatting**: Use the format `docs: update [document], [trigger description]` for all documentation-related commits. This makes the git log a readable history for anyone auditing the project. Enforcement: Commit-msg hook validates the format.
4. **No Deferred Docs**: Never commit code without updating its associated documentation. There is no such thing as "docs later" in this project. Documentation debt is not tolerated. Enforcement: Code review rejects any PR with missing documentation.
5. **Review Quality**: Documentation changes are reviewed with the same scrutiny as code changes. Poorly written docs are a reason for a PR rejection, just like poorly written code. Enforcement: Peer review focuses on doc accuracy, clarity, and completeness.

### Documentation as Code (DaC) Principles
We adhere to the principle that documentation is a first-class citizen of the codebase. This means using version control, automated testing for links and formatting, and ensuring that documentation is discoverable through standard developer tools. By treating documentation like code, we use the same powerful tools and workflows that make our software reliable. This includes using linting for markdown files to ensure consistent styling and checking for broken internal links to maintain a consistent navigation experience within the document library. Every document is a module in our information architecture.

## Section 5: Conflict Resolution Logic
As multiple tasks progress in parallel, they may occasionally need to modify the same documentation. We use structured merging and specific design patterns to prevent data loss or corruption during concurrent updates. This process is essential for maintaining a single source of truth in a multi-agent environment.

### Merge Protocol for Concurrent Agents and Humans
1. **Read-Merge-Write**: Always read the entire document before attempting a modification. Never assume you know the current state of the document, especially in a fast-moving project.
2. **Section Locking**: Avoid modifying the same section of a document simultaneously if possible. Work in discrete blocks to minimize the risk of merge conflicts and data loss.
3. **Contextual Awareness**: Use LINE#ID tags or other unique identifiers to locate precise points of change and avoid accidental overwrites of neighboring content. This is a critical safety measure.
4. **Historical Preservation**: When rewriting or updating sections, ensure that historical notes, changelogs, or context are carried forward rather than deleted. Maintaining the history is vital for understanding the evolution of the project.
5. **Conflict Escalation**: If a conflict is too complex for an automated agent to resolve safely, it must be escalated to a human orchestrator immediately. Safety and accuracy are prioritized over speed.

### Structural Conflict Prevention Strategies
To further reduce the likelihood of conflicts, large documents like Memory.md are structured with clearly defined, non-overlapping sections. For highly active areas, we use a "fragment-based" approach where documentation is split into smaller, task-specific files that are later compiled into a master document. This allows multiple agents to work in the same logical area without ever touching the same physical file. This strategy is particularly effective for the changelog and thinking logs, where high-frequency updates are the norm. It provides a scalable way to manage documentation in a high-concurrency environment.

Memory.md minimizes conflicts by using append-only sections for its Thinking Log and Change Tracking. These sections never delete historical data, they only add new entries with timestamps at the end of the section. This structure makes concurrent updates trivial to manage and preserves a perfect audit trail of the project's evolution. It is a resilient pattern for living documentation that ensures data integrity and ease of collaboration.

## Section 6: Drift Detection
Consistency between code and documentation is vital for project health. Documentation that disagrees with the code is a liability that can lead to bugs, confusion, and wasted effort during onboarding or debugging sessions. It is a fundamental principle that wrong documentation is worse than none at all. We take this very seriously and perform regular audits to maintain synchronization.

### Automated Drift Check Logic and Audit Process
After every 10 tasks, a formal drift check must be performed. This involves comparing the actual state of the codebase with the claims made in the documentation. It is a reality check for our records and a quality assurance step for the project's meta-data. This periodic check prevents small errors from accumulating into major inaccuracies that could compromise the project.
- **LOC Count**: Run `cloc --json .` or a similar tool and compare the results against Memory.md Section 2 to ensure the architectural overview matches the actual size of the system.
- **Test Count**: Run `pytest --collect-only` and compare the total count against progress.md to verify that the reported test coverage and numbers are accurate.
- **Endpoint Count**: Parse `apps/api/server.py` and other route files for FastAPI decorators and compare the list against Memory.md Section 5 to identify any undocumented or legacy APIs.
- **Stub Count**: Grep the codebase for comment markers and compare the findings against the AGENTS.md inventories to track implementation gaps accurately.
- **Dependency Check**: Compare the contents of `requirements.txt` and `pyproject.toml` against the list in Memory.md Section 7 to ensure all external dependencies are tracked and licensed correctly.

### Heuristic-Based Drift Analysis
Beyond simple metric counting, we use heuristic analysis to detect subtle drift in technical descriptions. This involves comparing function signatures and class definitions in the code against the descriptions in AGENTS.md. If a function's parameters change but the description remains the same, an alert is triggered. This ensures that the documentation is not just present, but accurate down to the implementation details. This level of precision is necessary for a project of this complexity where small misunderstandings can lead to significant delays and architectural errors. We are committed to a zero-drift policy for all core technical descriptions.

### Agent-Led Documentation Audits
We employ specialized "auditor agents" whose sole purpose is to read the codebase and the documentation library to find discrepancies. These agents use advanced pattern matching and cross-referencing to identify where the code has evolved beyond its description. These audits run as part of the weekly maintenance cycle and provide a detailed report of "documentation debt" that must be addressed. This proactive approach ensures that we never lose sight of our documentation obligations even during intense development phases. It is a key part of our strategy for long-term project sustainability.

Any drift greater than 5% in these metrics is treated as a documentation bug. This requires an immediate fix before any further feature work or refactoring can proceed. Maintaining this tight tolerance ensures that the documentation remains a reliable and trustworthy guide for all current and future contributors. It is a non-negotiable standard for our work that ensures operational excellence and project integrity.

## Section 7: Rollback Strategy
If code changes are reverted, the documentation must stay in sync with the reality of the repository. We do not leave ghosts of deleted features or incorrect descriptions in our guides. A rollback is a full reversal of the task's footprint in the codebase and its meta-data. This is crucial for maintaining a clean and accurate record that reflects only the current state of the system.

### Post-Rollback Documentation Verification Checklist and Steps
1. **AGENTS.md Review**: Ensure all task-associated entries are removed or reverted to their previous state to maintain local accuracy and avoid confusion.
2. **Memory.md Audit**: Check Sections 3, 5, 6, 7, and 10 for any entries that must be removed to maintain global architectural accuracy and prevent misinformation.
3. **Changelog Update**: Ensure the entry for the task is marked as "[REVERTED]" and includes a clear reference to the rollback reasoning and impact.
4. **Progress Correction**: Adjust the completion percentage downward to reflect the loss of completed work and maintain an accurate progress report for all stakeholders.
5. **Thinking Log Entry**: Add a specific entry explaining the rationale behind the revert and any lessons learned or patterns to avoid in future development.

### Post-Mortem Documentation and Learning
Every significant rollback requires a brief post-mortem entry in the thinking log. This entry must capture the root cause of the failure, the impact on the project timeline, and the specific documentation updates that were required to restore the repository's integrity. This practice ensures that every failure contributes to the collective knowledge of the project. It turns a setback into a learning opportunity and helps prevent similar issues from occurring in the future. It is a commitment to continuous improvement and operational excellence.
