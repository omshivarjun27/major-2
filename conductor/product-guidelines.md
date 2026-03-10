# Product Guidelines: Voice & Vision Assistant for Blind

## Tone and Voice
- **Dynamic Adaptability:** The tone should adapt based on the scenario:
  - **Empathetic & Clear:** When guiding the user or dealing with sensitive information.
  - **Technical & Direct:** For rapid micro-navigation and critical obstacle warnings.
  - **Casual & Friendly:** During general conversation and relaxed interactions.

## Accessibility Principles
- **Voice-First Design:** The core interaction model relies primarily on speech input and output.
- **Verbose & Granular Descriptions:** Ensuring users receive thorough details of their environment when requested.
- **Screen Reader Ready:** Software interfaces must strictly adhere to WCAG and screen reader standards.
- **Inclusive Design:** Adhere to universal design principles to cater to users across the spectrum of visual impairment.

## Error Handling UX
- **Informative Spoken Errors:** In case of connection drops, missing API keys, or unrecognizable objects, the system must provide clear, concise spoken explanations of the issue and suggest actionable next steps (e.g., fallback options like 3-tier OCR).

## Interaction and Feedback Model
- **Continuous Streaming & Passive Alerts:** The system must proactively provide critical event-driven alerts (e.g., obstacle detection) and stream continuous feedback without requiring user prompting.
- **On-Demand Assistance:** Users can interrupt or query the system at any time for specific tasks (e.g., "Read this sign," "Find my keys"), overriding or layering upon the passive alert system.