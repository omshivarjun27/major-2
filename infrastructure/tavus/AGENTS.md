1. Folder Purpose
- The Tavus folder houses the virtual avatar adapter which can render an on-call avatar during interactions.
- It is optional and feature-flag controlled; current priority is low but documented for future use.
- The folder documents how avatars would integrate with the REST/LiveKit pathways.

2. Contained Components
- Tavus avatar service stub (avatar rendering surface)
- Client-facing API hooks to integrate avatar state into responses
- Shared config and logging helpers reused by other adapters

3. Dependency Graph
- Inbound: speech/text outputs from core; outbound: avatar stream to UI or clients
- Depends on shared config/logging and infrastructure layer for secure transport
- No external providers required at this stage

4. Task Tracking
- Provide a minimal, testable Tavus stub that can be toggled via feature flag
- Wire API surface with the existing speech layer to demonstrate end-to-end flow
- Add a small health indicator and a soft-stop flag for graceful degradation

5. Design Thinking
- Treat Tavus as an optional, low-risk extension that can be stubbed easily without impacting core latency
- Ensure the avatar state is decoupled from the main perception pipeline
- Document clear opt-in/opt-out semantics for production use

6. Research Notes
- Avatar integration often requires UI-side hooks; keep server-side contracts stable regardless of UI changes
- Plan for avatar personalization in future iterations when requirements mature

7. Risk Assessment
- Low current risk; potential drift if UI contracts change without server changes
- Risk of feature creep; keep MVP minimal and flag-gated
- Accessibility considerations should be revisited as we evolve UI bindings

8. Improvement Suggestions
- Add a lightweight test harness to simulate avatar state changes
- Draft a simple protocol for avatar-video pairing with minimal bandwidth overhead
- Prepare a rollback plan for Tavus feature flag changes

9. Folder Change Log
- Created infrastructure/tavus/AGENTS.md with nine-section structure.
- Documented optional nature and MVP-oriented approach.
- Noted future UI bindings and feature-flag strategy.
