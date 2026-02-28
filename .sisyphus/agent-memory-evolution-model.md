# Agent Memory Evolution Model — Knowledge Persistence and Growth Strategy

**Voice & Vision Assistant for Blind — Autonomous Agent Intelligence Layer**

---

## 1. How AGENTS.md Grows

Currently, the project maintains 50 AGENTS.md files distributed across all directories, each following a consistent 9-section template:

1. Purpose — Module goal and scope
2. Components — Key files and subsystems
3. Dependencies — Module imports and relationships
4. Tasks — Pending, in-progress, and completed work items
5. Design — Architectural decisions and patterns
6. Research — Technology evaluations and trade-offs
7. Risk — Threat assessment and mitigation strategies
8. Improvements — Refactoring and optimization opportunities
9. Changelog — Historical record of modifications

**Growth triggers** that mandate AGENTS.md creation or updates:

- **New directory created**: A new AGENTS.md is immediately generated for the directory following the 9-section template. If parent AGENTS.md exists, a reference link is added to the parent's Components section.
- **Module purpose changes**: The Purpose section is updated to reflect the new scope. Parent module is notified if organizational hierarchy is affected.
- **New risks discovered**: The Risk section receives a new entry with severity, likelihood, and mitigation. Existing risks are NOT removed, only marked as "mitigated" or "closed."
- **Task completion**: The Changelog section receives a dated entry under Section 9. Task details are added to the Completed Tasks table in Section 4 (Global Task Intelligence).
- **Architecture evolution**: The Design section is rewritten to reflect current decisions. Previous design rationale is preserved in a "Previous Design" subsection for historical reference.

**Critical growth rule**: Never delete sections or purge historical content. All sections persist; new content is appended or updates are annotated with dates and reasoning.

---

## 2. How Memory.md Evolves

Memory.md currently contains 723 lines organized into 18 sections at the project root. Evolution of this master knowledge store is governed by strict append-only and mutation rules:

**Append-only sections** (historical records, immutable after creation):

- **Section 12 (Thinking Log)**: Architectural reasoning and strategic decisions are appended with timestamps. No edits to existing entries.
- **Section 13 (Change Tracking)**: All modifications to the system are logged with date, author, and rationale. Historical entries remain visible.
- **Section 15 (Open Issues)**: New issues are appended with status. Resolved issues are marked "closed" with resolution date, but records persist for auditing.
- **Section 13.1 (Git History)**: Immutable historical fact. Cannot be retroactively modified.
- **Section 18.2 (Version History)**: Append-only version log. Each release version is recorded once and never removed.

**Rewrite-allowed sections** (reflect current state, mutable):

- **Section 2 (System Identity)**: Metrics including LOC counts, test counts, file counts, completion percentage, and phase status. These are refreshed to match current codebase reality after every 5 tasks or phase boundary.
- **Section 14 (Context Compression)**: Summary views at 4 levels (20-line, 10-line, 5-line, 1-line). Compression is refreshed every 10 tasks or when metrics in Section 2 change by >5%.
- **Section 8 (Performance Memory)**: Performance benchmarks, latency targets, and resource usage statistics. Updated after any performance-impacting code change.

**Section count evolution rule**: The number of sections may increase (new sections appended at the end). The number of sections must NEVER decrease. Deprecated sections are marked "archived" but remain in the document.

---

## 3. What Must NEVER Be Mutated

Four critical sections represent immutable historical records and must be protected from modification or deletion:

- **Section 10 (Decision Memory)**: Architecture Decision Records (ADRs) are recorded with date, context, decision, and rationale. Once an ADR is accepted and dated, it is immutable. Superseded decisions receive a "superseded on [date]" annotation but the original record remains. This preserves architectural lineage and rationale.
- **Section 13.1 (Git History)**: Historical commits and blame information constitute factual history. Retroactive rewriting violates audit trail integrity.
- **Section 18.2 (Version History)**: Release version records are immutable. Each release is tagged once with version, date, and release notes. Historical versions cannot be deleted or modified.
- **Section 12 (Thinking Log)**: All reasoning entries are time-stamped and represent the state of knowledge at that moment. Entries reflect authentic decision-making context and must not be revised for narrative consistency.

**Governance violation**: Any deletion, purging, or retroactive modification of these sections constitutes a documentation integrity violation and triggers a P1 remediation task.

---

## 4. What Must ALWAYS Be Mutated

Four critical sections must be maintained in synchronization with the actual system state and are subject to mandatory updates:

- **Section 2 (System Identity)**: LOC counts (by module), test coverage (lines and percentage), file inventory, completion percentage, and phase status are the single source of truth for system metrics. These must reflect codebase reality after every 5 completed tasks. Drift detection occurs every 10 tasks and mismatches trigger a documentation bug.
- **Section 14 (Context Compression)**: Summary views provide rapid context loading for new tasks. Compression is refreshed every 10 tasks or when Section 2 metrics change by more than 5%. Stale summaries degrade agent efficiency.
- **Section 15 (Open Issues)**: Issues are marked resolved with closure date and impact. New issues discovered during tasks are added with discovery date and severity. The open issues list represents the current state of known problems.
- **Section 8 (Performance Memory)**: Performance targets (latency budgets, throughput SLAs, resource caps) and actual measurements are reconciled after any code change affecting hot paths. If measured performance deviates from target by >10%, the section is updated with drift analysis and root cause.

**Update cadence**: These sections are refreshed in batch after every 5 completed tasks, at phase boundaries, or immediately if a critical metric becomes stale (>2 phases old).

---

## 5. Memory Compression Strategy

Context Compression (Section 14) provides four hierarchical summary levels enabling rapid knowledge reconstruction:

- **20-line summary**: Current phase goal, top 3 architectural risks, top 5 open blockers, completion percentage, next 3 high-priority tasks. Sufficient for orientation during task pickup.
- **10-line summary**: Phase goal, critical path blocker, top 2 risks, completion %, next task. Enables rapid context loading within same session.
- **5-line summary**: Current goal, blocker, completion %, next task. Emergency context for context-exhausted continuations.
- **1-line summary**: One-sentence current focus for ultra-compressed handoff.

**Refresh cadence**:

- Full compression refresh every 10 completed tasks.
- Incremental updates after every 2 completed tasks (1-line and 5-line only).
- Emergency re-compression at phase boundaries or when critical metrics change.

**Compression rules**:

- **Preserve critical metrics**: LOC, test count, completion %, architectural health score.
- **Preserve risk posture**: Top 3 active risks by severity × likelihood, mitigation status.
- **Preserve architectural decisions**: Core ADRs and design rationale from Section 10.
- **Remove stale details**: Resolved issues, superseded tasks, completed research, experimental results no longer applicable.
- **Emphasize blocker chain**: Explicitly surface dependencies and critical path obstacles.

---

## 6. Context Overflow Prevention

Memory.md has a soft cap of 1,500 lines. If the document approaches this threshold, compression and archival procedures activate:

**Soft cap procedures** (1,450–1,500 lines):

- Enable aggressive compression (refresh all summaries, drop verbose tables, consolidate redundant entries).
- Archive resolved issues (move entries >2 phases old to Issues-archive.md with a summary reference).
- Consolidate duplicate entries across sections.

**Hard cap threshold** (2,000 lines):

- Beyond 2,000 lines, Memory.md must be split into two documents: Memory.md (current state) and Memory-archive.md (historical records).
- Memory.md retains Sections 1–8, 12, 14–16 (active knowledge).
- Memory-archive.md retains Sections 9–11, 13, 17–18 (historical records).
- A navigation index at the top of Memory.md references the archive and provides search guidance.

**Archive trigger logic**:

- Resolved issues older than 2 phases and no longer actively referenced.
- Completed task details that provide no forward-looking insight.
- Superseded research with no learning value for current phase.
- Deprecated components no longer in active use.

---

## 7. State Synchronization Rules

Three critical synchronization points ensure knowledge consistency across the documentation ecosystem:

**Memory.md ↔ Codebase**:

- Section 2 (System Identity) metrics must match actual codebase state. Drift detection occurs every 10 completed tasks via LOC counts, test coverage measurement, and file inventory verification. Acceptable drift: <2%. Beyond 2% triggers a P1 documentation bug.

**Memory.md ↔ AGENTS.md Files**:

- Memory.md Section 4 (Global Task Intelligence) task listings must align with corresponding task sections in module-level AGENTS.md files. When a task is completed, it is marked "completed" in both locations. Duplicate records are permitted (cross-referencing), but contradictory states are P1 bugs.

**Memory.md ↔ changelog.md**:

- All completed tasks must appear in changelog.md with date, module, and summary. Entries in Memory.md Changelog are mirrored to changelog.md. One-way sync from Memory.md to changelog.md (changelog.md is derivative).

**Desynchronization resolution**:

- Any detected inconsistency is logged as a P1 documentation bug.
- Resolution procedure: Memory.md Section 2 is the authoritative source for metrics. AGENTS.md is secondary. changelog.md is derivative. In case of conflict, memory.md wins.
- Sync check is performed at phase boundaries and every 10 completed tasks.

---

## 8. Historical Knowledge Preservation Model

The documentation system preserves knowledge across three tiers, each with distinct lifecycle rules:

**Tier 1: Immutable Records** (permanent preservation):

- Architectural Decision Records (Section 10, Memory.md): Decisions with date, context, rationale, status. Once accepted, immutable. Superseded decisions receive annotation but are never deleted.
- Git history (Section 13.1, Memory.md): Commit records, blame information, blame history. Factual audit trail, never retroactively modified.
- Version history (Section 18.2, Memory.md): Release tags, version numbers, date, release notes. Each release recorded once, never removed.
- Thinking log (Section 12, Memory.md): Timestamped reasoning entries representing authentic decision-making moments. Preserved as-is for accountability and pattern learning.

**Tier 2: Evolving Records** (mutable for accuracy):

- System metrics (Section 2, Memory.md): LOC, test coverage, file counts, completion %. Refreshed to match reality every 5 tasks.
- Open issues (Section 15, Memory.md): Issues marked resolved with closure date. Resolved records persist but are distinguished from active issues.
- Compression summaries (Section 14, Memory.md): Refreshed every 10 tasks to reflect current state without losing historical insight.
- Performance data (Section 8, Memory.md): Benchmarks updated after performance-affecting changes.

**Tier 3: Archivable Records** (eligible for archival):

- Resolved issue details: Issues closed >2 phases ago and not referenced in active work.
- Completed task details: Task records providing no forward-looking architectural insight.
- Superseded research: Research conclusions no longer applicable to current codebase state.
- Deprecated components: Subsystems removed or replaced, with migration complete.

**Archive lifecycle**:

- Archive trigger: Tier 3 record older than 2 phases and no active references.
- Archive action: Record moved to Memory-archive.md with a summary reference (e.g., "Issue #42 archived — see Memory-archive.md § 11.3").
- Retrieval: Archive remains searchable and queryable; no knowledge is lost, only moved to cold storage.
- Retention: Archive is permanent. Records are never purged from the system.

---

**Document Status**: Active | Last Updated: 2026-02-24 | Version: 1.0

