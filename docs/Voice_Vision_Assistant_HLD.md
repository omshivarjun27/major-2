# Voice & Vision Assistant for Blind
## Comprehensive Technical Documentation
### Workflow | Dataflow | Architecture | High-Level Design (HLD)

> **Changelog**: Phase 16 — Unified shared types, orchestration layer, OCR pipeline, debug/session endpoints, 277 tests passing (2026-02-09)
> **Changelog**: Added QR/AR tag scanning with contextual deep linking and offline cache (2026-02-07)
> **Changelog**: Added spatial perception: object detection + edge-aware segmentation + depth estimation (2026-02-03)

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [High-Level Design (HLD)](#3-high-level-design-hld)
4. [Component Architecture](#4-component-architecture)
5. [Workflow Diagrams](#5-workflow-diagrams)
6. [Dataflow Diagrams](#6-dataflow-diagrams)
7. [Technology Stack](#7-technology-stack)
8. [API Integration Details](#8-api-integration-details)
9. [Sequence Diagrams](#9-sequence-diagrams)
10. [Deployment Architecture](#10-deployment-architecture)

---

# 1. Executive Summary

## 1.1 Project Overview
The **Voice & Vision Assistant for Blind** is an AI-powered accessibility solution designed specifically for blind and visually impaired users. It combines cutting-edge speech recognition, natural language processing, and computer vision to create an intuitive assistant that helps users understand their surroundings and interact with the world more confidently.

## 1.2 Key Objectives
- **Real-time Voice Interaction**: Seamless speech-to-text and text-to-speech processing
- **Visual Scene Analysis**: AI-powered image understanding and description
- **Spatial Perception & Micro-Navigation**: Object detection, depth estimation, and obstacle warnings for safe navigation
- **Multi-Tool Integration**: Calendar, email, contacts, places, and internet search
- **Low Latency**: Streaming responses for natural conversational flow
- **Privacy-Aware**: Thoughtful handling of visual content with people

## 1.3 Target Users
- Blind individuals
- Visually impaired users
- People with low vision
- Accessibility-focused applications

---

# 2. System Architecture Diagram

## 2.1 High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ALLY VISION ASSISTANT                                 │
│                              Voice & Vision System Architecture                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                         ┌─────────────┐
                                         │    USER     │
                                         │  (Blind/VI) │
                                         └──────┬──────┘
                                                │
                        ┌───────────────────────┼───────────────────────┐
                        │                       │                       │
                        ▼                       ▼                       ▼
                ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
                │  Voice Input  │       │ Camera Input  │       │ Audio Output  │
                │  (Microphone) │       │   (WebRTC)    │       │  (Speakers)   │
                └───────┬───────┘       └───────┬───────┘       └───────▲───────┘
                        │                       │                       │
┌───────────────────────┼───────────────────────┼───────────────────────┼───────────────────┐
│                       │     LIVEKIT CLOUD     │                       │                   │
│                       │  Real-time Transport  │                       │                   │
│                       ▼                       ▼                       │                   │
│               ┌───────────────┐       ┌───────────────┐               │                   │
│               │  Audio Track  │       │  Video Track  │               │                   │
│               │  Subscription │       │  Subscription │               │                   │
│               └───────┬───────┘       └───────┬───────┘               │                   │
└───────────────────────┼───────────────────────┼───────────────────────┼───────────────────┘
                        │                       │                       │
                        ▼                       ▼                       │
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                              LIVEKIT AGENTS FRAMEWORK                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              AgentSession Controller                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │  │
│  │  │  Silero VAD │  │ Deepgram    │  │ Ollama LLM  │  │ ElevenLabs  │                 │  │
│  │  │  (Voice     │──│    STT      │──│   (qwen3-vl │──│    TTS      │─────────────────┼──┘
│  │  │  Activity)  │  │  (nova-3)   │  │   :235b)    │  │(multilingual)│                │
│  │  └─────────────┘  └─────────────┘  └──────┬──────┘  └─────────────┘                 │
│  │                                           │                                          │
│  │                                           ▼                                          │
│  │                              ┌─────────────────────────┐                             │
│  │                              │   AllyVisionAgent       │                             │
│  │                              │   (Custom Agent Class)  │                             │
│  │                              └───────────┬─────────────┘                             │
│  │                                          │                                           │
│  └──────────────────────────────────────────┼───────────────────────────────────────────┘
│                                             │                                            │
│  ┌──────────────────────────────────────────┼───────────────────────────────────────────┐
│  │                              FUNCTION TOOLS LAYER                                     │
│  │                                          │                                            │
│  │    ┌──────────────┬──────────────┬───────┴───────┬──────────────┬──────────────┐     │
│  │    ▼              ▼              ▼               ▼              ▼              ▼     │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ │ analyze  │ │ search   │ │ search       │ │ manage   │ │ manage   │ │ search   │   │
│  │ │ _vision  │ │ _internet│ │ _places      │ │_calendar │ │_communic │ │ _general │   │
│  │ └────┬─────┘ └────┬─────┘ └──────┬───────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
│  │      │            │              │              │            │            │          │
│  └──────┼────────────┼──────────────┼──────────────┼────────────┼────────────┼──────────┘
└─────────┼────────────┼──────────────┼──────────────┼────────────┼────────────┼──────────┘
          │            │              │              │            │            │
          ▼            ▼              ▼              ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   EXTERNAL SERVICES                                      │
│                                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   OLLAMA    │  │ DuckDuckGo  │  │ OpenStreet  │  │   Local     │  │ IMAP/SMTP   │   │
│  │   Server    │  │   Search    │  │   Map       │  │  Calendar   │  │   Email     │   │
│  │ (Vision LLM)│  │    API      │  │  Nominatim  │  │  (JSON)     │  │             │   │
│  │             │  │             │  │             │  │             │  │             │   │
│  │ qwen3-vl    │  │             │  │             │  │             │  │             │   │
│  │ :235b-cloud │  │             │  │             │  │             │  │             │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                           COMPONENT INTERACTION MAP                                 │
└────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
    │   app.py    │────────▶│   src/      │────────▶│   main.py   │
    │  (Entry)    │         │  __init__.py│         │  (Agent)    │
    └─────────────┘         └─────────────┘         └──────┬──────┘
                                   │                       │
                                   ▼                       │
                            ┌─────────────┐                │
                            │  config.py  │◀───────────────┤
                            │ (Settings)  │                │
                            └─────────────┘                │
                                                           │
              ┌────────────────────────────────────────────┼────────────────────────┐
              │                                            │                        │
              ▼                                            ▼                        ▼
    ┌─────────────────┐                          ┌─────────────────┐      ┌─────────────────┐
    │   tools/        │                          │   tools/        │      │   tools/        │
    │   visual.py     │                          │ ollama_handler  │      │ internet_search │
    │ (VisualProcessor)│                         │   .py           │      │      .py        │
    └────────┬────────┘                          └────────┬────────┘      └────────┬────────┘
             │                                            │                        │
             │         ┌─────────────────┐                │                        │
             │         │   tools/        │                │                        │
             │         │ google_places.py│◀───────────────┤                        │
             │         │ (PlacesSearch)  │                │                        │
             │         └─────────────────┘                │                        │
             │                                            │                        │
             │         ┌─────────────────┐                │                        │
             │         │   tools/        │◀───────────────┼────────────────────────┤
             │         │  calendar.py    │                │                        │
             │         │ (CalendarTool)  │                │                        │
             │         └─────────────────┘                │                        │
             │                                            │                        │
             │         ┌─────────────────┐                │                        │
             │         │   tools/        │◀───────────────┘                        │
             │         │ communication.py│                                         │
             │         │(CommunicationTool)                                        │
             │         └─────────────────┘                                         │
             │                                                                     │
             │         ┌─────────────────┐                                         │
             └────────▶│   tools/        │◀────────────────────────────────────────┘
                       │   timing.py     │
                       │(PipelineProfiler)
                       └─────────────────┘
```

---

# 3. High-Level Design (HLD)

## 3.1 Design Overview

### 3.1.1 Design Principles
| Principle | Description |
|-----------|-------------|
| **Accessibility First** | All interactions optimized for blind/VI users |
| **Real-time Processing** | Streaming responses for minimal latency |
| **Modular Architecture** | Loosely coupled components for maintainability |
| **Privacy Aware** | Thoughtful handling of visual data with people |
| **Fault Tolerant** | Graceful degradation when services unavailable |

### 3.1.2 System Layers

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LAYER ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: PRESENTATION LAYER                                                     │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────────┐ │
│  │   Voice Interface   │ │   Video Interface   │ │   WebRTC Connection         │ │
│  │   (Microphone/      │ │   (Camera Feed)     │ │   (LiveKit Cloud)           │ │
│  │    Speaker)         │ │                     │ │                             │ │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: PROCESSING LAYER                                                       │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────────┐ │
│  │   Speech-to-Text    │ │   Language Model    │ │   Text-to-Speech            │ │
│  │   (Deepgram Nova-3) │ │   (Ollama qwen3-vl) │ │   (ElevenLabs)              │ │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────────────┘ │
│  ┌─────────────────────┐ ┌─────────────────────┐                                 │
│  │   Voice Activity    │ │   Vision Processing │                                 │
│  │   Detection (Silero)│ │   (VisualProcessor) │                                 │
│  └─────────────────────┘ └─────────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: BUSINESS LOGIC LAYER                                                   │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────────┐ │
│  │   AllyVisionAgent   │ │   Function Router   │ │   Tool Orchestrator         │ │
│  │   (Main Agent)      │ │   (Query Classifier)│ │   (Tool Execution)          │ │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: INTEGRATION LAYER                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │ Visual Tool │ │ Search Tool │ │ Places Tool │ │Calendar Tool│ │ Comm Tool   ││
│  │             │ │             │ │             │ │             │ │             ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 5: EXTERNAL SERVICES LAYER                                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Ollama    │ │ DuckDuckGo  │ │ OpenStreet  │ │   Local     │ │ IMAP/SMTP   ││
│  │   Cloud     │ │   Search    │ │   Map       │ │  Calendar   │ │   Email     ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1.3 Spatial Perception: Obstacle Detection & Micro-Navigation

**Goal:** Detect objects, produce edge-aware segmentation masks, and estimate per-pixel depth to provide precise spatial descriptions and real-time micro-navigation cues (e.g., "obstacle 1.5 m ahead, slightly left").

**Features**
- **Object detection** → class, bounding box, detection confidence
- **Edge-aware segmentation** → crisp object contours and boundary confidence to better localize obstacles and walkable space
- **Depth estimation** → per-pixel depth map (metric or relative) to calculate distances to objects and scene geometry
- **Spatial fusion** → fuse detections, segmentation masks, and depth to produce concise navigation cues: distance (meters), direction (left/center/right + angle), obstacle size, and suggested action

**Output Modes:**
| Mode | Description | Example |
|------|-------------|---------|
| **Speech Cue** | Short spoken message for immediate TTS | "Obstacle 1.5 m ahead, slightly left — step right" |
| **Verbose Description** | Detailed narration on request | "A chair is 1.5 meters ahead and slightly left of center..." |
| **Structured Telemetry** | JSON for downstream modules | `{id, class, bbox, distance_m, direction_deg, confidence, action}` |

**Priority Thresholds:**
| Distance | Priority | Action |
|----------|----------|--------|
| < 1.0 m | 🔴 Critical | Immediate stop/alert |
| 1.0–2.0 m | 🟠 Near hazard | Urgent audio cue |
| 2.0–5.0 m | 🟡 Far hazard | Cautionary mention |

**Research Value:** Precise spatial descriptions for micro-navigation and fine-grained user guidance (useful for indoor navigation and last-meter micro-avoidance).

**Feasibility:** Medium — achievable using optimized depth models and compact detection/segmentation networks (quantization, pruning, or on-device mobile models). Consider offloading heavy LLM summarization to a cloud/edge server while keeping detection + depth on-device for low-latency hazard warnings.

## 3.2 Key Components Description

### 3.2.1 Core Components

| Component | File | Description | Key Responsibilities |
|-----------|------|-------------|---------------------|
| **App Entry** | `app.py` | Application entry point | Initialize logging, start LiveKit CLI |
| **Agent Core** | `src/main.py` | Main agent implementation | Handle user messages, route to tools, manage state |
| **Config Manager** | `src/config.py` | Configuration management | Load environment variables, manage settings |
| **Utils** | `src/utils.py` | Utility functions | Credential management, date/time helpers |

### 3.2.2 Tool Components

| Tool | File | Purpose | External API |
|------|------|---------|--------------|
| **VisualProcessor** | `tools/visual.py` | Camera frame capture | LiveKit WebRTC |
| **SpatialProcessor** | `tools/spatial.py` | Object detection, segmentation, depth | YOLO/MiDaS/Local |
| **OllamaHandler** | `tools/ollama_handler.py` | Vision LLM processing | Ollama API |
| **InternetSearch** | `tools/internet_search.py` | Web search | DuckDuckGo |
| **PlacesSearch** | `tools/google_places.py` | Location search | OpenStreetMap Nominatim |
| **CalendarTool** | `tools/calendar.py` | Calendar management | Local JSON store |
| **CommunicationTool** | `tools/communication.py` | Email/Contacts | IMAP/SMTP + Local JSON |
| **PipelineProfiler** | `tools/timing.py` | Latency measurement | Internal |

---

# 4. Component Architecture

## 4.1 AllyVisionAgent Class Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AllyVisionAgent                                        │
│                    (extends livekit.agents.voice.Agent)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ATTRIBUTES:                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  instructions: str        # System prompt for LLM behavior              │    │
│  │  session: AgentSession    # Reference to current session                │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  LIFECYCLE METHODS:                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  __init__()               # Initialize agent with instructions          │    │
│  │  on_enter()               # Called when agent starts                    │    │
│  │  on_message(text)         # Handle incoming user message                │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  CORE METHODS:                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  llm_node(chat_ctx, tools, model_settings)                              │    │
│  │      → Override LLM processing, stream responses                        │    │
│  │                                                                         │    │
│  │  _process_stream(chat_ctx, tools, userdata)                             │    │
│  │      → Process and stream LLM responses                                 │    │
│  │                                                                         │    │
│  │  _run_ollama_analysis(userdata, analysis_llm, visual_ctx)               │    │
│  │      → Execute vision analysis with streaming                           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  FUNCTION TOOLS:                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  @function_tool() analyze_vision(context, query)                        │    │
│  │      → Capture frame and analyze with vision LLM                        │    │
│  │                                                                         │    │
│  │  @function_tool() search_places(context, query)                         │    │
│  │      → Search OpenStreetMap Nominatim for locations                      │    │
│  │                                                                         │    │
│  │  @function_tool() search_internet(context, query)                       │    │
│  │      → Search DuckDuckGo for information                                │    │
│  │                                                                         │    │
│  │  @function_tool() manage_calendar(context, action, ...)                 │    │
│  │      → Add/view calendar events                                         │    │
│  │                                                                         │    │
│  │  @function_tool() manage_communication(context, action, ...)            │    │
│  │      → Find contacts, read/send emails                                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 4.2 UserData State Class

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              UserData (dataclass)                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  CORE STATE:                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  current_tool: str = "general"     # Active tool mode                   │    │
│  │  last_query: str = ""              # Last user query                    │    │
│  │  last_response: str = ""           # Last agent response                │    │
│  │  room_ctx: JobContext = None       # LiveKit room context               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  TOOL INSTANCES:                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  visual_processor: VisualProcessor     # Camera/frame handling          │    │
│  │  internet_search: InternetSearch       # Web search handler             │    │
│  │  ollama_handler: OllamaHandler         # Vision LLM handler             │    │
│  │  places_search: PlacesSearch           # OSM Nominatim handler          │    │
│  │  calendar_tool: CalendarTool           # Calendar management            │    │
│  │  communication_tool: CommunicationTool # Email/contacts handler         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  VISION PROCESSING STATE:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  _model_choice: str = None         # Selected vision model              │    │
│  │  _ollama_analysis: str = None      # Ollama analysis result             │    │
│  │  _ollama_chunks: List[str] = []    # Streaming chunks buffer            │    │
│  │  _analysis_complete: bool = False  # Analysis completion flag           │    │
│  │  _add_chunk_callback = None        # Callback for chunk streaming       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  SPATIAL PERCEPTION STATE:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  spatial_processor: SpatialProcessor  # Detection/depth/segmentation   │    │
│  │  _obstacle_records: List[dict] = []   # Fused obstacle records         │    │
│  │  _nav_cue: str = None                 # Current navigation cue         │    │
│  │  _depth_map: np.ndarray = None        # Latest depth estimation        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 4.3 SpatialProcessor Architecture (Spatial Perception)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SpatialProcessor                                       │
│                    (tools/spatial.py - NEW)                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SUBCOMPONENTS:                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ObjectDetector       # Detection model (YOLOv8/Detectron2/ONNX)        │    │
│  │  EdgeAwareSegmenter   # Boundary refinement + mask generation           │    │
│  │  DepthEstimator       # MiDaS/DPT or mobile depth model                 │    │
│  │  SpatialFuser         # Combines detections + masks + depth             │    │
│  │  MicroNavFormatter    # Generates audio cues + JSON telemetry           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  CORE METHODS:                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  detect_objects(frame) → List[Detection]                               │    │
│  │      → Run object detection, return {id, class, bbox, score}           │    │
│  │                                                                         │    │
│  │  segment_with_edges(frame, detections) → List[Mask]                    │    │
│  │      → Edge-aware segmentation with boundary confidence                 │    │
│  │                                                                         │    │
│  │  estimate_depth(frame) → DepthMap                                      │    │
│  │      → Per-pixel depth estimation (metric or relative)                 │    │
│  │                                                                         │    │
│  │  fuse_spatial(detections, masks, depth) → List[ObstacleRecord]         │    │
│  │      → Compute distance, direction, size for each obstacle             │    │
│  │                                                                         │    │
│  │  format_nav_cue(obstacles) → NavOutput                                 │    │
│  │      → Generate: short_cue, verbose, JSON telemetry                    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  OUTPUT STRUCTURE (ObstacleRecord):                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  {                                                                       │    │
│  │    "id": "o1",                                                           │    │
│  │    "class": "chair",                                                     │    │
│  │    "bbox": [100, 40, 210, 300],                                         │    │
│  │    "centroid_px": [155, 170],                                           │    │
│  │    "distance_m": 1.52,                                                   │    │
│  │    "direction_deg": -12,                                                 │    │
│  │    "mask_confidence": 0.92,                                              │    │
│  │    "detection_score": 0.96,                                              │    │
│  │    "action_recommendation": "step right"                                 │    │
│  │  }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. Workflow Diagrams

## 5.1 Main Application Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          MAIN APPLICATION WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────────────────┘

    START
      │
      ▼
┌─────────────────┐
│  1. app.py      │
│  Initialize     │
│  logging        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Load src/   │
│  __init__.py    │
│  (env vars)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. cli.run_app │
│  with Worker    │
│  Options        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Connect to  │
│  LiveKit Cloud  │
│  (WebSocket)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Initialize  │
│  UserData with  │
│  all tools      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. Create      │
│  AgentSession   │
│  (STT/LLM/TTS)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  7. Start Agent │
│  Session with   │
│  Room I/O       │
└────────┬────────┘
         │
         ▼
    LISTENING
    FOR USER
    INPUT...
```

## 5.2 Voice Interaction Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VOICE INTERACTION WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────────────────┘

User Speaks
    │
    ▼
┌──────────────────┐
│ 1. SILERO VAD    │───▶ Detects voice activity
│ (Voice Activity) │     Filters silence/noise
└────────┬─────────┘
         │ Audio Frames
         ▼
┌──────────────────┐
│ 2. DEEPGRAM STT  │───▶ Converts speech to text
│ (Nova-3 Model)   │     Real-time transcription
└────────┬─────────┘
         │ Transcribed Text
         ▼
┌──────────────────┐
│ 3. on_message()  │───▶ Logs query
│ Method Called    │     Sets up profiling
└────────┬─────────┘
         │ User Query
         ▼
┌──────────────────┐
│ 4. OLLAMA LLM    │───▶ Processes query
│ (qwen3-vl:235b)  │     Selects appropriate tool
└────────┬─────────┘
         │ Tool Selection
         ▼
┌──────────────────┐
│ 5. TOOL          │───▶ Executes selected tool
│ EXECUTION        │     Returns results
└────────┬─────────┘
         │ Response Text
         ▼
┌──────────────────┐
│ 6. ELEVENLABS    │───▶ Converts text to speech
│ TTS              │     Natural voice output
└────────┬─────────┘
         │ Audio Stream
         ▼
User Hears Response
```

## 5.3 Vision Analysis Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VISION ANALYSIS WORKFLOW                                 │
│                    (with Spatial Perception Pipeline)                            │
└─────────────────────────────────────────────────────────────────────────────────┘

User: "What do you see?" / "Any obstacles?"
         │
         ▼
┌──────────────────┐
│ 1. analyze_vision│───▶ Tool triggered by LLM
│ @function_tool   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. FRAME CAPTURE │───▶ Get video track from room
│ visual_processor │     Capture 5 frames buffer
│ .capture_frame() │     Return latest frame
└────────┬─────────┘
         │ Image (PIL)
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SPATIAL PERCEPTION PIPELINE (NEW)                          │
├──────────────────────────────────────────────────────────────────────────────┤
│         │                                                                     │
│         ▼                                                                     │
│  ┌──────────────────┐                                                         │
│  │ 2a. OBJECT       │───▶ Run ObjectDetector (YOLO/Detectron2)               │
│  │ DETECTION        │     Output: {id, class, bbox, score}                   │
│  └────────┬─────────┘                                                         │
│           │ Detections                                                        │
│           ▼                                                                   │
│  ┌──────────────────┐                                                         │
│  │ 2b. EDGE-AWARE   │───▶ Run EdgeAwareSegmenter                             │
│  │ SEGMENTATION     │     Refine masks with boundary confidence              │
│  └────────┬─────────┘     Preserve sharp object contours                      │
│           │ Masks + Confidence                                                │
│           ▼                                                                   │
│  ┌──────────────────┐                                                         │
│  │ 2c. DEPTH        │───▶ Run DepthEstimator (MiDaS/DPT)                     │
│  │ ESTIMATION       │     Per-pixel depth map                                 │
│  └────────┬─────────┘     Camera-to-ground plane (if available)               │
│           │ Depth Map                                                         │
│           ▼                                                                   │
│  ┌──────────────────┐                                                         │
│  │ 2d. SPATIAL      │───▶ Fuse detections + masks + depth                    │
│  │ FUSION           │     Compute: distance_m, direction_deg                  │
│  │ (SpatialFuser)   │     Apply thresholds, filter by confidence              │
│  └────────┬─────────┘                                                         │
│           │ ObstacleRecords[]                                                 │
│           ▼                                                                   │
│  ┌──────────────────┐                                                         │
│  │ 2e. MICRO-NAV    │───▶ Generate navigation outputs:                       │
│  │ FORMATTER        │     • Short cue: "Obstacle 1.5m left"                  │
│  │                  │     • Verbose: detailed description                     │
│  └────────┬─────────┘     • JSON telemetry for downstream                    │
│           │                                                                   │
├───────────┼─────────────────────────────────────┬─────────────────────────────┤
│           │                                     │                             │
│           ▼                                     ▼                             │
│  ┌──────────────────┐               ┌──────────────────┐                     │
│  │ IMMEDIATE TTS    │               │ ATTACH TO        │                     │
│  │ (short_cue)      │               │ VISUAL CONTEXT   │                     │
│  │ Low-latency path │               │ For LLM narration│                     │
│  └──────────────────┘               └────────┬─────────┘                     │
│                                              │                                │
└──────────────────────────────────────────────┼────────────────────────────────┘
         │                                     │
         ▼                                     ▼
┌──────────────────┐               ┌──────────────────┐
│ 3. CREATE VISUAL │───▶ Build ChatContext with:
│ CONTEXT          │     • System prompt
│                  │     • Image + query
│                  │     • Spatial telemetry summary
└────────┬─────────┘
         │ ChatContext + SpatialData
         ▼
┌──────────────────┐
│ 4. START ASYNC   │───▶ Non-blocking LLM call
│ LLM ANALYSIS     │     Stream chunks to queue
│ create_task()    │     LLM can reference obstacle data
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. STREAM        │───▶ Yield chunks as received
│ PROCESSING       │     Build full response
│ _process_stream()│     Handle timeouts
└────────┬─────────┘
         │ Response Chunks
         ▼
┌──────────────────┐
│ 6. TTS OUTPUT    │───▶ Convert to speech
│ Real-time        │     Stream audio to user
└────────┬─────────┘
         │
         ▼
User Hears Description + Navigation Cues
```

**Pipeline Summary:** `FRAME → DETECT → SEGMENT (edge-aware) → DEPTH → FUSE → FORMAT → [TTS + LLM]`

---

# 6. Dataflow Diagrams

## 6.1 Complete System Dataflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            SYSTEM DATAFLOW DIAGRAM                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────┐                                                            ┌─────────┐
│  USER   │                                                            │  USER   │
│ (Input) │                                                            │(Output) │
└────┬────┘                                                            └────▲────┘
     │                                                                      │
     │ Voice/Camera                                                   Audio │
     ▼                                                                      │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LIVEKIT CLOUD                                       │
│  ┌────────────┐                                        ┌────────────┐           │
│  │ Audio Track│──────┐                          ┌─────▶│Audio Track │           │
│  │ (WebRTC)   │      │                          │      │ (WebRTC)   │           │
│  └────────────┘      │                          │      └────────────┘           │
│  ┌────────────┐      │                          │                               │
│  │Video Track │──────┼──────────────────────────┼───────────────────────────────│
│  │ (WebRTC)   │      │                          │                               │
│  └────────────┘      │                          │                               │
└──────────────────────┼──────────────────────────┼───────────────────────────────┘
                       │                          │
                       ▼                          │
┌─────────────────────────────────────────────────┼───────────────────────────────┐
│                      LIVEKIT AGENTS FRAMEWORK   │                               │
│                                                 │                               │
│  ┌───────────────┐   ┌───────────────┐   ┌─────┴───────┐   ┌───────────────┐   │
│  │   SILERO VAD  │──▶│  DEEPGRAM STT │──▶│ OLLAMA LLM  │──▶│ ELEVENLABS TTS│   │
│  │               │   │               │   │             │   │               │   │
│  │  Audio Frames │   │  Text Output  │   │  Response   │   │ Audio Stream  │   │
│  └───────────────┘   └───────────────┘   └──────┬──────┘   └───────────────┘   │
│                                                 │                               │
│                                                 ▼                               │
│                                     ┌─────────────────────┐                     │
│                                     │   AllyVisionAgent   │                     │
│                                     │   Tool Selection    │                     │
│                                     └──────────┬──────────┘                     │
│                                                │                                │
└────────────────────────────────────────────────┼────────────────────────────────┘
                                                 │
         ┌───────────────┬───────────────┬───────┼───────┬───────────────┐
         │               │               │       │       │               │
         ▼               ▼               ▼       ▼       ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐┌─────────┐┌─────────┐┌─────────┐
    │ Visual  │    │Internet │    │ Places  ││Calendar ││ Comm    ││ General │
    │ Query   │    │ Search  │    │ Search  ││  Mgmt   ││  Mgmt   ││ Query   │
    └────┬────┘    └────┬────┘    └────┬────┘└────┬────┘└────┬────┘└────┬────┘
         │              │              │          │          │          │
         ▼              ▼              ▼          ▼          ▼          │
    ┌─────────┐    ┌─────────┐    ┌─────────┐┌─────────┐┌─────────┐    │
    │ OLLAMA  │    │DuckDuck │    │   OSM   ││  Local  ││ IMAP/   │    │
    │ Vision  │    │  Go     │    │Nominatim││Calendar ││  SMTP   │    │
    │ API     │    │  API    │    │         ││ (JSON)  ││  Email  │    │
    └────┬────┘    └────┬────┘    └────┬────┘└────┬────┘└────┬────┘    │
         │              │              │          │          │          │
         └──────────────┴──────────────┴──────────┴──────────┴──────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   Tool Result   │
                              │  (Text Response)│
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  Back to LLM    │
                              │  for Response   │
                              │  Generation     │
                              └─────────────────┘
```

## 6.2 Vision Processing Dataflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VISION PROCESSING DATAFLOW                               │
│                    (with Spatial Perception Pipeline)                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Camera    │      │  LiveKit    │      │   Visual    │      │   Frame     │
│   Device    │─────▶│  WebRTC     │─────▶│  Processor  │─────▶│   Buffer    │
│             │      │  Track      │      │             │      │  (5 frames) │
└─────────────┘      └─────────────┘      └─────────────┘      └──────┬──────┘
                                                                      │
                        Video Frame                        Best Frame │
                        Stream                                        │
                                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      SPATIAL PERCEPTION PIPELINE                                 │
│                                                                                  │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │  Object     │      │ Edge-Aware  │      │   Depth     │      │  Spatial    │ │
│  │  Detector   │─────▶│ Segmenter   │─────▶│ Estimator   │─────▶│   Fuser     │ │
│  │ (YOLO/Det2) │      │ (Boundary)  │      │ (MiDaS/DPT) │      │             │ │
│  └─────────────┘      └─────────────┘      └─────────────┘      └──────┬──────┘ │
│        │                    │                    │                     │        │
│   Detections             Masks              Depth Map          ObstacleRecords  │
│   {class,bbox,           +boundary            per-pixel          {distance_m,   │
│    score}               confidence                              direction_deg, │
│                                                                  action}        │
└────────────────────────────────────────────────────────────────────┬────────────┘
                                                                     │
                                              ┌──────────────────────┴───────────┐
                                              │                                  │
                                              ▼                                  ▼
                                    ┌─────────────────┐               ┌─────────────────┐
                                    │  MicroNav       │               │   Base64        │
                                    │  Formatter      │               │   Encode        │
                                    │ (short_cue,     │               │   Image +       │
                                    │  verbose, JSON) │               │  Spatial Data   │
                                    └────────┬────────┘               └────────┬────────┘
                                             │                                  │
              ┌──────────────────────────────┘                                  │
              │                                                                 │
              ▼                                                                 ▼
┌─────────────────────┐                                              ┌─────────────────┐
│   IMMEDIATE TTS     │                                              │   Ollama        │
│   (Low Latency)     │                                              │   Handler       │
│   "Obstacle 1.5m    │                                              │   (LLM Vision)  │
│    ahead, left"     │                                              └────────┬────────┘
└──────────┬──────────┘                                                       │
           │                                              ┌───────────────────┘
           │                                              │
           ▼                                              ▼
┌─────────────────────┐                        ┌─────────────────┐
│   Audio Stream      │                        │   LLM Response  │
│   to User           │◀───────────────────────│   Stream        │
│   (hazard cue)      │                        │   (narration)   │
└─────────────────────┘                        └─────────────────┘
```

**Dual Output Paths:**
1. **Low-latency path**: `SpatialFuser → MicroNavFormatter → TTS` (immediate hazard warnings)
2. **Rich narration path**: `SpatialFuser → Ollama LLM → TTS` (detailed descriptions)

## 6.3 Data Format Specifications

### 6.3.1 Input Data Formats

| Source | Format | Description |
|--------|--------|-------------|
| Audio Input | PCM 16-bit, 16kHz | Voice from microphone |
| Video Input | YUV420 frames | Camera via WebRTC |
| STT Output | UTF-8 text | Transcribed speech |

### 6.3.2 Internal Data Formats

| Component | Format | Example |
|-----------|--------|---------|
| Frame Buffer | PIL.Image | RGB image object |
| Chat Context | ChatContext | Messages + ImageContent |
| LLM Chunks | ChatChunk | Delta content streaming |
| Tool Results | String | Formatted response text |

### 6.3.3 Output Data Formats

| Destination | Format | Description |
|-------------|--------|-------------|
| TTS Input | UTF-8 text | Response to speak |
| Audio Output | PCM stream | Voice synthesis |
| Logs | JSON/text | Timing & debug info |

---

# 7. Technology Stack

## 7.1 Complete Technology Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            TECHNOLOGY STACK                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  RUNTIME & LANGUAGE                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Python 3.11+        │  Primary language with async/await support       │    │
│  │  asyncio             │  Asynchronous I/O framework                      │    │
│  │  dataclasses         │  Structured data management                      │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  LIVEKIT ECOSYSTEM                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  livekit-agents 1.3.12  │  Agent framework for voice AI                 │    │
│  │  livekit-plugins-deepgram │  Deepgram STT integration                   │    │
│  │  livekit-plugins-openai   │  OpenAI-compatible LLM integration          │    │
│  │  livekit-plugins-elevenlabs │  ElevenLabs TTS integration               │    │
│  │  livekit-plugins-silero   │  Silero VAD integration                     │    │
│  │  livekit-plugins-tavus    │  Optional avatar integration                │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  AI/ML SERVICES                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Ollama (local)     │  Vision LLM hosting (qwen3-vl:235b-instruct-cloud)│    │
│  │  Deepgram Nova-3    │  Speech-to-text (cloud)                           │    │
│  │  ElevenLabs         │  Text-to-speech (eleven_multilingual_v2)          │    │
│  │  Silero VAD         │  Voice activity detection (local)                 │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  SPATIAL PERCEPTION MODELS (NEW)                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Object Detection:                                                       │    │
│  │    • YOLOv8 / YOLOv7-tiny    │  Fast object detection                   │    │
│  │    • Detectron2              │  Accurate detection (heavier)            │    │
│  │    • ONNX exported models    │  Cross-platform inference                │    │
│  │                                                                         │    │
│  │  Edge-Aware Segmentation:                                               │    │
│  │    • HED + mask refinement   │  Boundary-aware segmentation             │    │
│  │    • CRF post-processing     │  Sharp object contours                   │    │
│  │    • Lightweight seg heads   │  Mobile-optimized                        │    │
│  │                                                                         │    │
│  │  Depth Estimation:                                                      │    │
│  │    • MiDaS / DPT             │  High accuracy monocular depth           │    │
│  │    • ZoeDepth Mobile         │  Optimized for on-device                 │    │
│  │    • Distilled depth models  │  Fast inference                          │    │
│  │                                                                         │    │
│  │  Acceleration:                                                          │    │
│  │    • ONNX Runtime            │  Quantization support                    │    │
│  │    • TensorRT                │  NVIDIA GPU acceleration                 │    │
│  │    • TFLite / CoreML         │  Mobile device acceleration              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL APIs                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  DuckDuckGo Search  │  Internet search (via langchain)                  │    │
│  │  OSM Nominatim      │  Location/business search (geopy)                 │    │
│  │  Local Calendar     │  Calendar event management (JSON file)            │    │
│  │  IMAP/SMTP          │  Email reading and sending                        │    │
│  │  Local Contacts     │  Contact management (JSON file)                   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  KEY LIBRARIES                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  httpx              │  Async HTTP client for API calls                  │    │
│  │  Pillow (PIL)       │  Image processing and manipulation                │    │
│  │  pydantic           │  Data validation and settings                     │    │
│  │  langchain-community│  LangChain tools for search                       │    │
│  │  geopy              │  OpenStreetMap Nominatim places search             │    │
│  │  python-dotenv      │  Environment variable management                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Environment Configuration

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ENVIRONMENT VARIABLES                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Ollama Configuration
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OLLAMA_VL_MODEL_ID=qwen3-vl:235b-instruct-cloud

# STT Configuration
DEEPGRAM_API_KEY=your_deepgram_key

# TTS Configuration
ELEVEN_API_KEY=your_elevenlabs_key

# Email (IMAP/SMTP)
GMAIL_MAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465

# Optional: Avatar
ENABLE_AVATAR=false
TAVUS_API_KEY=your_tavus_key
TAVUS_REPLICA_ID=your_replica_id
TAVUS_PERSONA_ID=your_persona_id
```

---

# 8. API Integration Details

## 8.1 Ollama Vision API

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          OLLAMA VISION API INTEGRATION                           │
└─────────────────────────────────────────────────────────────────────────────────┘

ENDPOINT: http://localhost:11434/v1/chat/completions

REQUEST FORMAT:
┌─────────────────────────────────────────────────────────────────────────────────┐
│  {                                                                               │
│    "model": "qwen3-vl:235b-instruct-cloud",                                     │
│    "messages": [                                                                 │
│      {                                                                           │
│        "role": "system",                                                         │
│        "content": "You are Ally, a vision assistant..."                         │
│      },                                                                          │
│      {                                                                           │
│        "role": "user",                                                           │
│        "content": [                                                              │
│          {"type": "text", "text": "What do you see?"},                          │
│          {"type": "image_url", "image_url": {"url": "data:image/..."}}          │
│        ]                                                                         │
│      }                                                                           │
│    ],                                                                            │
│    "stream": true,                                                               │
│    "max_tokens": 500,                                                            │
│    "temperature": 0.7                                                            │
│  }                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘

RESPONSE FORMAT (Streaming):
┌─────────────────────────────────────────────────────────────────────────────────┐
│  data: {"choices":[{"delta":{"content":"The"}}]}                                │
│  data: {"choices":[{"delta":{"content":" scene"}}]}                             │
│  data: {"choices":[{"delta":{"content":" shows"}}]}                             │
│  ...                                                                             │
│  data: [DONE]                                                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 8.2 Deepgram STT API

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DEEPGRAM STT CONFIGURATION                              │
└─────────────────────────────────────────────────────────────────────────────────┘

CONFIGURATION:
┌─────────────────────────────────────────────────────────────────────────────────┐
│  deepgram.STT(                                                                   │
│      model="nova-3",        # Latest Nova model for best accuracy               │
│      language="en"          # English language                                   │
│  )                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘

FEATURES:
  • Real-time streaming transcription
  • Punctuation and formatting
  • Low latency (~300ms)
  • High accuracy for natural speech
```

## 8.3 ElevenLabs TTS API

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ELEVENLABS TTS CONFIGURATION                            │
└─────────────────────────────────────────────────────────────────────────────────┘

CONFIGURATION:
┌─────────────────────────────────────────────────────────────────────────────────┐
│  elevenlabs.TTS(                                                                 │
│      model="eleven_multilingual_v2"   # High-quality multilingual model         │
│  )                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘

FEATURES:
  • Natural human-like voice synthesis
  • Streaming audio output
  • Emotional expression
  • Multiple language support
```

---

# 9. Sequence Diagrams

## 9.1 Complete Voice Interaction Sequence

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      VOICE INTERACTION SEQUENCE DIAGRAM                          │
└─────────────────────────────────────────────────────────────────────────────────┘

  User        LiveKit       VAD      Deepgram     Agent       LLM         TTS
   │            │           │           │           │          │           │
   │──Voice────▶│           │           │           │          │           │
   │            │──Audio───▶│           │           │          │           │
   │            │           │──Detect──▶│           │          │           │
   │            │           │           │           │          │           │
   │            │           │    ┌──────┴──────┐    │          │           │
   │            │           │    │ Transcribe  │    │          │           │
   │            │           │    └──────┬──────┘    │          │           │
   │            │           │           │           │          │           │
   │            │           │           │───Text───▶│          │           │
   │            │           │           │           │          │           │
   │            │           │           │    ┌──────┴──────┐   │           │
   │            │           │           │    │ on_message()│   │           │
   │            │           │           │    │ Route Query │   │           │
   │            │           │           │    └──────┬──────┘   │           │
   │            │           │           │           │          │           │
   │            │           │           │           │──Query──▶│           │
   │            │           │           │           │          │           │
   │            │           │           │           │    ┌─────┴─────┐     │
   │            │           │           │           │    │ Process   │     │
   │            │           │           │           │    │ & Select  │     │
   │            │           │           │           │    │ Tool      │     │
   │            │           │           │           │    └─────┬─────┘     │
   │            │           │           │           │          │           │
   │            │           │           │           │◀─Stream──│           │
   │            │           │           │           │          │           │
   │            │           │           │           │───Text──────────────▶│
   │            │           │           │           │          │           │
   │            │           │           │           │          │    ┌──────┴──────┐
   │            │           │           │           │          │    │ Synthesize  │
   │            │           │           │           │          │    │ Speech      │
   │            │           │           │           │          │    └──────┬──────┘
   │            │           │           │           │          │           │
   │◀───────────┼───────────┼───────────┼───────────┼──────────┼───Audio───│
   │            │           │           │           │          │           │
```

## 9.2 Vision Analysis Sequence

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        VISION ANALYSIS SEQUENCE DIAGRAM                          │
└─────────────────────────────────────────────────────────────────────────────────┘

  User     Agent    VisualProc   Camera    Ollama     Queue       TTS
   │         │          │          │          │          │          │
   │"What    │          │          │          │          │          │
   │do you   │          │          │          │          │          │
   │see?"    │          │          │          │          │          │
   │────────▶│          │          │          │          │          │
   │         │          │          │          │          │          │
   │         │──analyze_vision()──▶│          │          │          │
   │         │          │          │          │          │          │
   │         │          │──capture_frame()───▶│          │          │
   │         │          │          │          │          │          │
   │         │          │◀─────frames────────│          │          │
   │         │          │          │          │          │          │
   │         │◀──image──│          │          │          │          │
   │         │          │          │          │          │          │
   │         │──create_task(_run_ollama_analysis)──────▶│          │
   │         │          │          │          │          │          │
   │         │          │          │          │──chunk──▶│          │
   │         │          │          │          │──chunk──▶│          │
   │         │          │          │          │──chunk──▶│          │
   │         │          │          │          │          │          │
   │         │◀─────────┼──────────┼─────get_chunk──────│          │
   │         │          │          │          │          │          │
   │         │──────────┼──────────┼──────────┼──────────┼─stream──▶│
   │         │          │          │          │          │          │
   │◀────────┼──────────┼──────────┼──────────┼──────────┼──audio───│
   │         │          │          │          │          │          │
```

---

# 10. Deployment Architecture

## 10.1 Local Development Setup

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        LOCAL DEVELOPMENT ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DEVELOPER MACHINE                                   │
│                                                                                  │
│  ┌─────────────────────┐     ┌─────────────────────┐                            │
│  │    Python 3.11      │     │     Ollama Server   │                            │
│  │    Virtual Env      │     │  localhost:11434    │                            │
│  │    (.venv/)         │     │                     │                            │
│  │                     │     │  qwen3-vl:235b      │                            │
│  │  ┌───────────────┐  │     │  -instruct-cloud    │                            │
│  │  │   app.py      │  │────▶│                     │                            │
│  │  │   src/main.py │  │     └─────────────────────┘                            │
│  │  │   src/tools/* │  │                                                        │
│  │  └───────────────┘  │                                                        │
│  └──────────┬──────────┘                                                        │
│             │                                                                    │
│             │ WebSocket                                                          │
└─────────────┼────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD SERVICES                                      │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   LiveKit Cloud │  │    Deepgram     │  │   ElevenLabs    │                  │
│  │                 │  │   Cloud API     │  │   Cloud API     │                  │
│  │  Real-time      │  │                 │  │                 │                  │
│  │  WebRTC         │  │  STT Service    │  │  TTS Service    │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  OSM Nominatim  │  │ Local Calendar  │  │  IMAP/SMTP      │                  │
│  │   (Places)      │  │   (JSON file)   │  │   (Email)       │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 10.2 Production Deployment

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION DEPLOYMENT ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│    Users    │
│  (Clients)  │
└──────┬──────┘
       │
       │ WebRTC/HTTPS
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LIVEKIT CLOUD                                       │
│                         (Real-time Media Server)                                 │
│                                                                                  │
│  • Audio/Video routing                                                          │
│  • WebRTC signaling                                                             │
│  • Room management                                                              │
│  • Agent dispatch                                                               │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
                                   │ gRPC/WebSocket
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AGENT WORKER CLUSTER                                   │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Worker 1      │  │   Worker 2      │  │   Worker N      │                  │
│  │   (Agent Pod)   │  │   (Agent Pod)   │  │   (Agent Pod)   │                  │
│  │                 │  │                 │  │                 │                  │
│  │  Python Runtime │  │  Python Runtime │  │  Python Runtime │                  │
│  │  AllyVision     │  │  AllyVision     │  │  AllyVision     │                  │
│  │  Agent          │  │  Agent          │  │  Agent          │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│                                                                                  │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
                                   │ HTTPS/API Calls
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL SERVICES                                     │
│                                                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│  │   Ollama   │ │  Deepgram  │ │ ElevenLabs │ │   Local    │ │ DuckDuckGo │    │
│  │   Cloud    │ │    API     │ │    API     │ │   APIs     │ │   Search   │    │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 11. Performance & Timing

## 11.1 Pipeline Latency Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          LATENCY BREAKDOWN (TYPICAL)                             │
└─────────────────────────────────────────────────────────────────────────────────┘

Component                        | Time (ms)  | Status
─────────────────────────────────┼────────────┼─────────
VAD Detection                    |   10-50    |   🟢
STT (Deepgram)                   |  200-400   |   🟡
LLM First Token                  |  300-800   |   🟡
LLM Complete Response            |  500-2000  |   🟠
Vision Frame Capture             |   50-100   |   🟢
Vision LLM First Token           |  500-1500  |   🟠
Vision LLM Complete              | 1000-3000  |   🔴
TTS Synthesis Start              |  100-300   |   🟡
─────────────────────────────────┼────────────┼─────────
TOTAL (Text Query)               | 1000-2500  |   🟠
TOTAL (Vision Query)             | 2000-5000  |   🔴

Legend:
  🟢 < 100ms (Fast)
  🟡 100-500ms (Moderate)
  🟠 500-1000ms (Slow)
  🔴 > 1000ms (Very Slow)
```

## 11.2 Timing Profiler Integration

The system includes a built-in `PipelineProfiler` class in `tools/timing.py` that measures:

- `frame_capture` - Camera frame acquisition time
- `vision_llm_first_token` - Time to first token from vision model
- `vision_llm_complete` - Total vision analysis time
- `llm_first_token` - Time to first token from text LLM

---

# 12. Phase 16 — Architectural Consolidation (2026-02-09)

## 12.1 Summary

Phase 16 is a comprehensive architectural overhaul that addresses 10 identified issues
and introduces 5 new subsystems. All changes maintain full backward compatibility.

## 12.2 New Modules

| Module | Purpose |
|--------|---------|
| `shared/__init__.py` | **Single source of truth** for all data types: `BoundingBox`, `Detection`, `SegmentationMask`, `DepthMap`, `PerceptionResult`, `ObstacleRecord`, `NavigationOutput`, enums (`Priority`, `Direction`, `SizeCategory`, `SpatialRelation`), and ABCs (`ObjectDetector`, `Segmenter`, `DepthEstimator`). |
| `vqa_engine/orchestrator.py` | `PerceptionOrchestrator` — runs detection, segmentation, and depth estimation **concurrently** via `asyncio.gather` with per-stage configurable timeouts (default 100/100/100 ms, pipeline 300 ms). Never raises. |
| `debug_tools/session_logger.py` | `SessionLogger` — ring-buffer (default 500 events) structured JSON logging with optional JSONL disk flush per session. |
| `ocr_engine/__init__.py` | `OCRPipeline` — preprocessing (CLAHE → bilateral denoise → Hough deskew) with auto-selected EasyOCR or Tesseract backend. All heavy work via `run_in_executor`. |

## 12.3 Key Changes to Existing Files

| File | Change |
|------|--------|
| `src/main.py` | Replaced 7 hard-coded model names with `LLM_MODEL` from config; wired `VoiceRouter`, `OCRPipeline`, `SessionLogger`; added `read_text` OCR tool. |
| `src/tools/spatial.py` | Removed ~200 lines of duplicate type definitions; imports from `shared`; `detection_score` → `detection_confidence`. |
| `vqa_engine/perception.py` | Removed local type definitions, imports from `shared`. |
| `vqa_engine/scene_graph.py` | Imports from `shared`; fixed `_format_distance` to use module-level function. |
| `vqa_engine/spatial_fuser.py` | Imports from `shared`. |
| `vqa_engine/vqa_reasoner.py` | Imports from `shared`. |
| `api_server.py` | Added 4 REST endpoints: `POST /debug/perception_frame`, `GET /logs/sessions`, `GET /logs/session/{id}`, `POST /logs/session`. |

## 12.4 Breaking Changes

| Change | Migration |
|--------|-----------|
| `DepthMap.get_region_depth()` now returns `(min, median, max)` | Was `(min, max, mean)`. Update unpacking. |
| `Direction.CENTER` value = `"ahead"` | Was `"center"`. Update string comparisons. |
| `Detection.to_dict()["bbox"]` returns `to_xywh()` format | Was `to_list()` (x1,y1,x2,y2). Update consumers. |
| `ObstacleRecord` canonical field is `detection_confidence` | `detection_score` still works via property alias. |

## 12.5 Test Coverage

| Test File | Tests | Covers |
|-----------|-------|--------|
| `tests/test_shared_types.py` | 35 | BoundingBox, Detection, DepthMap, enums, ABCs |
| `tests/test_orchestrator.py` | 14 | Concurrent execution, timeouts, errors, fallbacks, stats |
| `tests/test_session_logger.py` | 14 | Ring-buffer, disk flush, filtering, CRUD |
| `tests/test_ocr_pipeline.py` | 14 | Preprocessing, mock backends, confidence filtering, error handling |
| *Existing test_spatial.py* | 52 | Updated for shared types, new field names |
| **Total** | **277 passed, 0 failed** | |
- `llm_complete` - Total LLM generation time
- `total_message_processing` - End-to-end latency

## 11.3 Spatial Perception Latency & Feasibility

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    SPATIAL PERCEPTION LATENCY TARGETS                            │
└─────────────────────────────────────────────────────────────────────────────────┘

Component                        | Time (ms)  | Status    | Notes
─────────────────────────────────┼────────────┼───────────┼─────────────────────
Object Detection (YOLO)          |   20-80    |   🟢      | Quantized/TensorRT
Object Detection (Detectron2)    |  100-300   |   🟡      | Full precision
Edge-Aware Segmentation          |   30-100   |   🟢      | Lightweight head
Depth Estimation (MiDaS mobile)  |   50-150   |   🟢      | Optimized model
Depth Estimation (DPT full)      |  200-500   |   🟡      | High accuracy
Spatial Fusion                   |    5-20    |   🟢      | CPU only
MicroNav Formatting              |    1-5     |   🟢      | String ops
─────────────────────────────────┼────────────┼───────────┼─────────────────────
TOTAL (optimized pipeline)       |  100-350   |   🟢      | On-device hazard
TOTAL (with LLM narration)       | 1000-3000  |   🔴      | Streamed response

Legend:
  🟢 < 200ms (Suitable for real-time hazard warnings)
  🟡 200-500ms (Acceptable with streaming)
  🔴 > 500ms (Use only for detailed narration)
```

### Optimization Strategies

| Strategy | Description | Impact |
|----------|-------------|--------|
| **Model Quantization** | INT8 quantization for detection/depth | 2-4x speedup |
| **Hardware Acceleration** | TensorRT/CoreML/NNAPI | 3-10x speedup |
| **Temporal Smoothing** | Multi-frame averaging for depth | Reduces jitter |
| **Dual-Path Output** | Immediate TTS for hazards, LLM for details | Low-latency warnings |
| **Selective Processing** | Skip depth if no obstacles detected | Conditional speedup |

### Failure Modes & Mitigation

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| Low light / blur | Low confidence scores | Fallback: "Possible obstacle ahead" |
| Depth scale uncertainty | High variance in depth samples | Report distance ranges |
| False positives | Edge bleeding, shadows | Edge-aware masks + confidence threshold |
| Model timeout | Inference > 500ms | Use cached previous frame data |

---

# 11.5 QR / AR Tag Scanning Engine

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  QR / AR Engine                      │
│                                                      │
│  Camera Frame ──►  QRScanner (pyzbar / cv2)          │
│                    ARTagHandler (ArUco)               │
│                        │                             │
│                        ▼                             │
│                   QRDecoder                          │
│         (classify: URL, transport, location,         │
│          product, contact, WiFi, text, custom)       │
│                        │                             │
│              ┌─────────┴──────────┐                  │
│              ▼                    ▼                   │
│        CacheManager          Online Fetch            │
│    (offline-first JSON)     (optional enrichment)    │
│              │                    │                   │
│              └─────────┬──────────┘                  │
│                        ▼                             │
│               Contextual Message                     │
│           (spoken via TTS pipeline)                  │
│                                                      │
│  REST API:                                           │
│   POST /qr/scan    – scan image for QR/AR           │
│   POST /qr/cache   – manually add cache entry       │
│   GET  /qr/history  – recent scan results           │
│   POST /qr/debug   – developer diagnostics          │
└──────────────────────────────────────────────────────┘
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| pyzbar primary, cv2 fallback | pyzbar is faster and supports more QR/barcode formats |
| Offline-first cache | Blind users may lose connectivity; cached results must always work |
| SHA-256 content key | Deterministic, collision-resistant key for any QR payload |
| JSON file cache | Simple, inspectable, no database dependency |
| TTL-based expiry | Stale data is auto-purged; manual refresh supported |
| Content classification | Enables tailored spoken messages per QR type |
| Navigation offer | Location/transport QR codes automatically offer guidance |

---

# 12. Summary

## 12.1 Key Takeaways

| Aspect | Description |
|--------|-------------|
| **Architecture** | Multi-layer, modular design with clear separation of concerns |
| **Real-time** | Streaming architecture for low-latency voice interaction |
| **Vision** | Integrated camera capture and AI-powered scene analysis |
| **QR/AR Scanning** | QR code / ArUco marker detection with contextual deep linking & offline cache |
| **Tools** | Eight function tools for comprehensive assistance |
| **Accessibility** | Designed specifically for blind/VI users |
| **Scalability** | Cloud-native with distributed agent workers |

## 12.2 File Structure Summary

```
Voice-Vision-Assistant-for-Blind/
├── app.py                    # Entry point
├── api_server.py             # REST API server (QR + VQA endpoints)
├── requirements.txt          # Dependencies
├── .env                      # Environment config
├── src/
│   ├── __init__.py          # Package init, env loading
│   ├── config.py            # Configuration management
│   ├── main.py              # AllyVisionAgent implementation
│   ├── utils.py             # Utility functions
│   └── tools/
│       ├── visual.py        # VisualProcessor
│       ├── spatial.py       # SpatialProcessor (detection/depth/segmentation)
│       ├── ollama_handler.py # OllamaHandler
│       ├── internet_search.py # InternetSearch
│       ├── google_places.py  # PlacesSearch (OpenStreetMap Nominatim)
│       ├── calendar.py      # CalendarTool (local JSON)
│       ├── communication.py # CommunicationTool (local JSON + IMAP/SMTP)
│       └── timing.py        # PipelineProfiler
├── qr_engine/                # QR/AR Tag Scanning Engine (NEW)
│   ├── __init__.py          # Package exports
│   ├── qr_scanner.py        # QR code detection (pyzbar / OpenCV)
│   ├── qr_decoder.py        # Content classification & context builder
│   ├── ar_tag_handler.py    # ArUco marker detection
│   ├── cache_manager.py     # Offline-first JSON file cache
│   └── qr_api.py            # FastAPI router (/qr/*)
└── docs/
    └── Voice_Vision_Assistant_HLD.md  # This document
```

---

**Document Version**: 1.3  
**Last Updated**: February 9, 2026  
**Author**: Generated by GitHub Copilot  
**Changes**: QR/AR tag scanning (2026-02-07); Spatial perception (2026-02-03)

---
