"""
Voice Router Module
===================

Handles intent detection and routing of voice queries
to appropriate handlers (VQA, spatial, or general LLM).
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("voice-router")


# ============================================================================
# Intent Types
# ============================================================================

class IntentType(Enum):
    """Types of detected intents."""
    
    # Visual/VQA intents
    VISUAL_DESCRIBE = auto()     # "What do you see?"
    VISUAL_IDENTIFY = auto()     # "What is this?"
    VISUAL_READ = auto()         # "Read this text"
    VISUAL_COLOR = auto()        # "What color is this?"
    
    # Spatial/Navigation intents
    SPATIAL_OBSTACLE = auto()    # "Any obstacles?"
    SPATIAL_PATH = auto()        # "Is the path clear?"
    SPATIAL_DISTANCE = auto()    # "How far is...?"
    SPATIAL_DIRECTION = auto()   # "Which way to...?"
    SPATIAL_HAZARD = auto()      # "Any hazards?"
    
    # Priority/Urgent intents
    PRIORITY_SCAN = auto()       # "Quick scan" / priority mode

    # QR / AR scanning (explicit request only)
    QR_SCAN = auto()             # "Scan QR", "read this code"

    # Navigation routing
    NAVIGATION_ROUTE = auto()    # "Take me to", "help me exit"

    # Mode toggle
    TOGGLE_MODE = auto()         # "Enable always-on", "disable proactive"
    
    # General conversation
    GENERAL_CHAT = auto()        # Normal conversation
    GENERAL_HELP = auto()        # Help requests
    GENERAL_COMMAND = auto()     # System commands
    
    # Unknown/Fallback
    UNKNOWN = auto()


# ============================================================================
# Route Result
# ============================================================================

@dataclass
class RouteResult:
    """Result of intent routing."""
    
    intent: IntentType
    confidence: float
    handler: str  # "vqa", "spatial", "priority", "llm"
    query: str
    processed_query: str
    mode: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Voice Router
# ============================================================================

class VoiceRouter:
    """
    Routes voice queries to appropriate handlers based on intent.
    
    Uses pattern matching and keyword detection to classify
    queries into visual, spatial, or general categories.
    """
    
    # Pattern definitions
    VISUAL_PATTERNS = [
        (r"\b(what|who|which)\b.*\b(see|look|watch|view|spot)\b", IntentType.VISUAL_DESCRIBE),
        (r"\b(describe|tell me about|explain)\b.*\b(see|front|view|scene)\b", IntentType.VISUAL_DESCRIBE),
        (r"\bwhat('s|s| is) (this|that|it)\b", IntentType.VISUAL_IDENTIFY),
        (r"\b(identify|recognize|detect)\b", IntentType.VISUAL_IDENTIFY),
        (r"\b(read|text|sign|label|writing)\b", IntentType.VISUAL_READ),
        (r"\b(color|colour)\b", IntentType.VISUAL_COLOR),
        (r"\b(look|see|vision|image|camera|picture|photo)\b", IntentType.VISUAL_DESCRIBE),
    ]
    
    SPATIAL_PATTERNS = [
        (r"\b(obstacles?|blocks?|blocking|blocked)\b", IntentType.SPATIAL_OBSTACLE),
        (r"\b(path|way|route)\b.*\b(clear|free|open)\b", IntentType.SPATIAL_PATH),
        (r"\b(clear|open)\b.*\b(path|way|ahead)\b", IntentType.SPATIAL_PATH),
        (r"\b(how far|distance|close|near|away)\b", IntentType.SPATIAL_DISTANCE),
        (r"\b(where|which way|direction|left|right|ahead|behind)\b", IntentType.SPATIAL_DIRECTION),
        (r"\b(hazards?|dangers?|unsafe|careful|watch out)\b", IntentType.SPATIAL_HAZARD),
        (r"\b(navigate|navigation|walk|step|move)\b", IntentType.SPATIAL_DIRECTION),
    ]
    
    PRIORITY_PATTERNS = [
        (r"\b(quick scan|priority|urgent|emergency|alert)\b", IntentType.PRIORITY_SCAN),
        (r"\b(top|main|important|critical)\b.*\b(hazards?|dangers?|obstacles?)\b", IntentType.PRIORITY_SCAN),
        (r"\b(safety|safe)\b.*\b(check|scan)\b", IntentType.PRIORITY_SCAN),
    ]

    QR_PATTERNS = [
        (r"\b(scan|read)\b.*\b(qr|code|tag|barcode)\b", IntentType.QR_SCAN),
        (r"\bqr\b", IntentType.QR_SCAN),
        (r"\b(what does)\b.*\b(code|tag)\b.*\b(say|mean|contain)\b", IntentType.QR_SCAN),
    ]

    NAVIGATION_ROUTE_PATTERNS = [
        (r"\b(take me|guide me|help me)\b.*\b(to|exit|out|through)\b", IntentType.NAVIGATION_ROUTE),
        (r"\b(find|get to|reach)\b.*\b(exit|door|entrance|room|stairs)\b", IntentType.NAVIGATION_ROUTE),
    ]

    TOGGLE_PATTERNS = [
        (r"\b(enable|disable|turn on|turn off|activate|deactivate)\b.*\b(always.?on|proactive|priority|continuous)\b", IntentType.TOGGLE_MODE),
    ]
    
    HELP_PATTERNS = [
        (r"\b(help|assist|how do|how to|can you)\b", IntentType.GENERAL_HELP),
    ]
    
    COMMAND_PATTERNS = [
        (r"\b(stop|start|pause|resume|quit|exit|cancel)\b", IntentType.GENERAL_COMMAND),
        (r"\b(settings|configure|setup|mode)\b", IntentType.GENERAL_COMMAND),
    ]
    
    def __init__(self):
        self._compiled_patterns = self._compile_patterns()
        
        # Stats
        self._total_routes = 0
        self._route_counts: Dict[IntentType, int] = {i: 0 for i in IntentType}
    
    def _compile_patterns(self) -> List[Tuple[re.Pattern, IntentType]]:
        """Compile all regex patterns.  Order determines precedence on ties."""
        all_patterns = (
            self.PRIORITY_PATTERNS +       # Highest precedence
            self.QR_PATTERNS +             # Explicit QR before spatial/visual
            self.TOGGLE_PATTERNS +         # Mode toggles
            self.NAVIGATION_ROUTE_PATTERNS +  # Guided navigation
            self.SPATIAL_PATTERNS +
            self.VISUAL_PATTERNS +
            self.HELP_PATTERNS +
            self.COMMAND_PATTERNS
        )
        return [(re.compile(p, re.IGNORECASE), intent) for p, intent in all_patterns]
    
    def route(self, query: str) -> RouteResult:
        """
        Route a query to the appropriate handler.
        
        Args:
            query: The transcribed voice query
            
        Returns:
            RouteResult with intent, handler, and metadata
        """
        start_time = time.time()
        
        # Clean query
        clean_query = query.strip().lower()
        processed_query = self._preprocess_query(query)
        
        # Detect intent using preprocessed query (fillers removed)
        intent, confidence = self._detect_intent(processed_query.lower())
        
        # Determine handler
        handler, mode = self._select_handler(intent)
        
        # Update stats
        self._total_routes += 1
        self._route_counts[intent] += 1
        
        latency_ms = (time.time() - start_time) * 1000
        
        result = RouteResult(
            intent=intent,
            confidence=confidence,
            handler=handler,
            query=query,
            processed_query=processed_query,
            mode=mode,
            metadata={
                "routing_latency_ms": round(latency_ms, 2),
            }
        )
        
        logger.debug(
            f"Routed '{query[:30]}...' to {handler} "
            f"(intent={intent.name}, conf={confidence:.2f})"
        )
        
        return result
    
    def _preprocess_query(self, query: str) -> str:
        """Preprocess query for handler."""
        # Remove filler words
        fillers = [
            "um", "uh", "like", "you know", "basically", "actually",
            "please", "could you", "can you", "will you",
        ]
        processed = query
        for filler in fillers:
            processed = re.sub(rf"\b{filler}\b", "", processed, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        processed = re.sub(r'\s+', ' ', processed).strip()
        
        return processed
    
    def _detect_intent(self, query: str) -> Tuple[IntentType, float]:
        """Detect intent from query using pattern matching with precedence."""
        best_intent = IntentType.GENERAL_CHAT
        best_confidence = 0.3  # Default confidence for fallback
        
        total_patterns = len(self._compiled_patterns)
        for idx, (pattern, intent) in enumerate(self._compiled_patterns):
            match = pattern.search(query)
            if match:
                # Calculate confidence based on match quality
                match_len = match.end() - match.start()
                query_len = len(query)
                confidence = min(0.5 + (match_len / query_len) * 0.5, 0.95)
                
                # Add precedence bonus: earlier patterns (priority > spatial >
                # visual > help) get a small boost to win confidence ties.
                precedence_bonus = (total_patterns - idx) / total_patterns * 0.05
                confidence += precedence_bonus
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent
        
        return best_intent, min(best_confidence, 0.99)
    
    def _select_handler(self, intent: IntentType) -> Tuple[str, Optional[str]]:
        """Select handler and mode based on intent."""
        handler_map = {
            # VQA handlers
            IntentType.VISUAL_DESCRIBE: ("vqa", "describe"),
            IntentType.VISUAL_IDENTIFY: ("vqa", "identify"),
            IntentType.VISUAL_READ: ("vqa", "read"),
            IntentType.VISUAL_COLOR: ("vqa", "color"),
            
            # Spatial handlers
            IntentType.SPATIAL_OBSTACLE: ("spatial", "obstacles"),
            IntentType.SPATIAL_PATH: ("spatial", "path_check"),
            IntentType.SPATIAL_DISTANCE: ("spatial", "distance"),
            IntentType.SPATIAL_DIRECTION: ("spatial", "direction"),
            IntentType.SPATIAL_HAZARD: ("spatial", "hazards"),
            
            # Priority handler
            IntentType.PRIORITY_SCAN: ("priority", "top3"),

            # QR / AR handler (explicit request only)
            IntentType.QR_SCAN: ("qr", "scan"),

            # Guided navigation
            IntentType.NAVIGATION_ROUTE: ("spatial", "navigation"),

            # Mode toggle
            IntentType.TOGGLE_MODE: ("command", "toggle"),
            
            # General handlers
            IntentType.GENERAL_CHAT: ("llm", None),
            IntentType.GENERAL_HELP: ("llm", "help"),
            IntentType.GENERAL_COMMAND: ("command", None),
            IntentType.UNKNOWN: ("llm", None),
        }
        
        return handler_map.get(intent, ("llm", None))
    
    def is_visual_intent(self, intent: IntentType) -> bool:
        """Check if intent requires visual processing (camera frame)."""
        return intent in {
            IntentType.VISUAL_DESCRIBE,
            IntentType.VISUAL_IDENTIFY,
            IntentType.VISUAL_READ,
            IntentType.VISUAL_COLOR,
            IntentType.SPATIAL_OBSTACLE,
            IntentType.SPATIAL_PATH,
            IntentType.SPATIAL_DISTANCE,
            IntentType.SPATIAL_HAZARD,
            IntentType.PRIORITY_SCAN,
            IntentType.QR_SCAN,
            IntentType.NAVIGATION_ROUTE,
        }
    
    def is_priority_intent(self, intent: IntentType) -> bool:
        """Check if intent requires priority mode."""
        return intent == IntentType.PRIORITY_SCAN

    def is_qr_intent(self, intent: IntentType) -> bool:
        """Check if intent is an explicit QR/AR scan request."""
        return intent == IntentType.QR_SCAN

    def is_toggle_intent(self, intent: IntentType) -> bool:
        """Check if intent is a mode toggle (proactive on/off)."""
        return intent == IntentType.TOGGLE_MODE
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            "total_routes": self._total_routes,
            "routes_by_intent": {
                i.name: self._route_counts[i]
                for i in IntentType
                if self._route_counts[i] > 0
            },
        }


# ============================================================================
# Quick Intent Helpers
# ============================================================================

def quick_classify(query: str) -> str:
    """Quick classification for simple routing."""
    router = VoiceRouter()
    result = router.route(query)
    return result.handler


def needs_vision(query: str) -> bool:
    """Check if query needs visual processing."""
    router = VoiceRouter()
    result = router.route(query)
    return router.is_visual_intent(result.intent)
