"""
Memory Engine - RAG Reasoner Module
=====================================

Conversational RAG flow using retrieved memories and qwen3-vl.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from .config import get_memory_config, MemoryConfig
from .api_schema import (
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryCitation,
    MemoryHit,
    QueryMode,
)
from .retriever import MemoryRetriever
from .api_schema import MemorySearchRequest

logger = logging.getLogger("memory-rag")


# Template-based answers for common memory queries
ANSWER_TEMPLATES = {
    "location": "Based on my memory from {timestamp}, you {action}.",
    "object": "I remember seeing {object} {location} around {timestamp}.",
    "event": "Around {timestamp}, {event}.",
    "unknown": "I don't have clear memories about that. {fallback}",
}

# System prompt for qwen3-vl RAG reasoning
RAG_SYSTEM_PROMPT = """You are a helpful memory assistant for a blind user.

Your task is to answer questions about past events using ONLY the provided memory context.

RULES:
1. ONLY use information from the provided memories. Do not make up or assume information.
2. If the memories don't contain relevant information, say "I don't recall that" or "I don't have that in my recent memories."
3. Always cite which memory you're using by mentioning the timestamp.
4. Keep answers concise and helpful.
5. For location questions, be specific about where objects were seen.
6. Never hallucinate or guess. If unsure, express uncertainty.

MEMORY CONTEXT:
{context}

USER QUESTION: {question}

Provide a helpful, accurate answer based only on the memories above."""


class RAGReasoner:
    """Conversational RAG for memory-based Q&A.
    
    Pipeline:
    1. Retrieve relevant memories
    2. Build context from summaries + scene graphs
    3. For "short" mode: try template-based answer
    4. For "verbose" mode or if templates fail: use LLM
    5. Return answer with citations
    
    Usage:
        reasoner = RAGReasoner(retriever=retriever, llm_client=ollama_client)
        response = await reasoner.query(MemoryQueryRequest(query="Where are my keys?"))
    """
    
    def __init__(
        self,
        retriever: MemoryRetriever,
        llm_client: Optional[Any] = None,
        model_name: str = "qwen3.5:397b-cloud",
        config: Optional[MemoryConfig] = None,
    ):
        self._retriever = retriever
        self._llm_client = llm_client
        self._model_name = model_name
        self._config = config or get_memory_config()
        
        # Telemetry
        self._query_count = 0
        self._total_retrieval_time_ms = 0.0
        self._total_reasoning_time_ms = 0.0
    
    async def query(
        self,
        request: MemoryQueryRequest,
    ) -> MemoryQueryResponse:
        """Answer a natural language query using retrieved memories.
        
        Args:
            request: Query request with question and mode
            
        Returns:
            MemoryQueryResponse with answer and citations
        """
        start_time = time.time()
        
        # Step 1: Retrieve relevant memories
        retrieval_start = time.time()
        search_request = MemorySearchRequest(
            query=request.query,
            k=request.k,
            time_window_days=request.time_window_days,
            include_scene_graph=True,
        )
        search_response = await self._retriever.search(search_request)
        retrieval_time_ms = (time.time() - retrieval_start) * 1000
        
        memories = search_response.results
        
        # No memories found
        if not memories:
            return MemoryQueryResponse(
                answer="I don't have any relevant memories about that.",
                confidence=0.0,
                has_evidence=False,
                citations=[],
                retrieval_time_ms=retrieval_time_ms,
                reasoning_time_ms=0,
            )
        
        # Step 2: Build context
        context = self._build_context(memories)
        citations = self._build_citations(memories)
        
        # Step 3: Generate answer
        reasoning_start = time.time()
        
        if request.mode == QueryMode.SHORT:
            # Try template-based answer first
            answer, confidence = self._try_template_answer(request.query, memories)
            
            if answer and confidence >= 0.6:
                reasoning_time_ms = (time.time() - reasoning_start) * 1000
                self._update_telemetry(retrieval_time_ms, reasoning_time_ms)
                
                return MemoryQueryResponse(
                    answer=answer,
                    confidence=confidence,
                    has_evidence=True,
                    citations=citations,
                    retrieval_time_ms=retrieval_time_ms,
                    reasoning_time_ms=reasoning_time_ms,
                )
        
        # Fall back to LLM reasoning
        answer, confidence, reasoning = await self._llm_reason(
            query=request.query,
            context=context,
            verbose=(request.mode == QueryMode.VERBOSE),
        )
        
        reasoning_time_ms = (time.time() - reasoning_start) * 1000
        self._update_telemetry(retrieval_time_ms, reasoning_time_ms)
        
        return MemoryQueryResponse(
            answer=answer,
            confidence=confidence,
            has_evidence=bool(memories),
            citations=citations,
            reasoning=reasoning if request.mode == QueryMode.VERBOSE else None,
            retrieval_time_ms=retrieval_time_ms,
            reasoning_time_ms=reasoning_time_ms,
        )
    
    def _build_context(self, memories: List[MemoryHit]) -> str:
        """Build context string from retrieved memories."""
        context_parts = []
        
        for i, mem in enumerate(memories, 1):
            # Format timestamp
            try:
                ts = mem.timestamp.replace("T", " ").replace("Z", "")[:19]
            except:
                ts = mem.timestamp
            
            part = f"[Memory {i}] ({ts}):\n  {mem.summary}"
            
            if mem.user_label:
                part += f"\n  Label: {mem.user_label}"
            
            if mem.scene_graph:
                # Extract key info from scene graph
                objects = mem.scene_graph.get("objects", [])
                if objects:
                    obj_names = []
                    for obj in objects[:5]:
                        if isinstance(obj, dict):
                            obj_names.append(obj.get("class", obj.get("name", "")))
                        else:
                            obj_names.append(str(obj))
                    if obj_names:
                        part += f"\n  Objects seen: {', '.join(filter(None, obj_names))}"
            
            context_parts.append(part)
        
        return "\n\n".join(context_parts)
    
    def _build_citations(self, memories: List[MemoryHit]) -> List[MemoryCitation]:
        """Build citation list from memories."""
        citations = []
        
        for mem in memories:
            citations.append(MemoryCitation(
                memory_id=mem.id,
                timestamp=mem.timestamp,
                relevance_score=mem.score,
                excerpt=mem.summary[:100] if mem.summary else None,
            ))
        
        return citations
    
    def _try_template_answer(
        self,
        query: str,
        memories: List[MemoryHit],
    ) -> tuple:
        """Try to answer using templates (fast, no LLM).
        
        Returns:
            Tuple of (answer, confidence) or (None, 0) if templates don't apply
        """
        query_lower = query.lower()
        
        if not memories:
            return None, 0.0
        
        top_memory = memories[0]
        
        # Format timestamp nicely
        try:
            ts = top_memory.timestamp.replace("T", " ").replace("Z", "")[:16]
        except:
            ts = "recently"
        
        # Location queries: "where did I put X", "where is X", "where are my X"
        location_patterns = [
            r"where (?:did i put|is|are|was|were) (?:my |the )?(.+?)[\?]?$",
            r"where did i (?:leave|place|set) (?:my |the )?(.+?)[\?]?$",
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                object_name = match.group(1).strip()
                
                # Check if the memory mentions this object
                summary_lower = top_memory.summary.lower()
                if object_name in summary_lower or self._fuzzy_match(object_name, summary_lower):
                    answer = f"Based on my memory from {ts}: {top_memory.summary}"
                    return answer, min(0.9, top_memory.score + 0.2)
        
        # "What did I..." queries
        what_patterns = [
            r"what did i (?:have|hold|see|put|place|touch) (.+?)[\?]?$",
            r"what was (?:in|on|near) (?:my |the )?(.+?)[\?]?$",
        ]
        
        for pattern in what_patterns:
            match = re.search(pattern, query_lower)
            if match:
                answer = f"Around {ts}: {top_memory.summary}"
                return answer, top_memory.score
        
        # "Do I have..." queries
        have_patterns = [
            r"do i have (?:any )?(.+?)[\?]?$",
            r"did i (?:buy|get|have) (?:any )?(.+?)[\?]?$",
        ]
        
        for pattern in have_patterns:
            match = re.search(pattern, query_lower)
            if match:
                item = match.group(1).strip()
                summary_lower = top_memory.summary.lower()
                
                if item in summary_lower:
                    answer = f"Based on my memory from {ts}: {top_memory.summary}"
                    return answer, min(0.85, top_memory.score + 0.15)
                else:
                    # Item not mentioned in top memory
                    return f"I don't recall seeing {item} in my recent memories.", 0.6
        
        # Generic fallback for high-confidence matches
        if top_memory.score >= 0.7:
            answer = f"From my memory ({ts}): {top_memory.summary}"
            return answer, top_memory.score
        
        return None, 0.0
    
    def _fuzzy_match(self, query_term: str, text: str) -> bool:
        """Simple fuzzy matching for object names."""
        # Handle plurals
        if query_term.endswith("s"):
            singular = query_term[:-1]
            if singular in text:
                return True
        else:
            if query_term + "s" in text:
                return True
        
        # Handle common variations
        variations = {
            "keys": ["key", "keychain"],
            "glasses": ["spectacles", "eyeglasses"],
            "phone": ["mobile", "cellphone", "smartphone"],
            "wallet": ["purse", "billfold"],
            "bag": ["backpack", "handbag", "purse"],
        }
        
        for base, alts in variations.items():
            if query_term == base or query_term in alts:
                for alt in [base] + alts:
                    if alt in text:
                        return True
        
        return False
    
    async def _llm_reason(
        self,
        query: str,
        context: str,
        verbose: bool = False,
    ) -> tuple:
        """Use LLM for reasoning when templates don't suffice.
        
        Returns:
            Tuple of (answer, confidence, reasoning_text)
        """
        if self._llm_client is None:
            # No LLM available, return context-based fallback
            answer = f"Based on my memories: {context[:200]}..."
            return answer, 0.5, None
        
        try:
            # Build prompt
            prompt = RAG_SYSTEM_PROMPT.format(
                context=context,
                question=query,
            )
            
            # Call LLM
            response = await self._call_llm(prompt, max_tokens=200 if not verbose else 500)
            
            answer = response.strip()
            
            # Estimate confidence based on answer content
            confidence = 0.7
            if "don't recall" in answer.lower() or "don't have" in answer.lower():
                confidence = 0.4
            elif "remember" in answer.lower() or "memory" in answer.lower():
                confidence = 0.8
            
            reasoning = f"Retrieved {len(context.split('[Memory'))-1} memories. " if verbose else None
            
            return answer, confidence, reasoning
            
        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            return "I'm having trouble accessing my memories right now.", 0.3, None
    
    async def _call_llm(self, prompt: str, max_tokens: int = 200) -> str:
        """Call the LLM client."""
        if self._llm_client is None:
            raise ValueError("No LLM client configured")
        
        try:
            # Try OpenAI-compatible API
            if hasattr(self._llm_client, "chat"):
                response = await self._llm_client.chat.completions.create(
                    model=self._model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3,
                )
                return response.choices[0].message.content
            
            # Try Ollama-style API
            if hasattr(self._llm_client, "generate"):
                response = await self._llm_client.generate(
                    model=self._model_name,
                    prompt=prompt,
                    options={"num_predict": max_tokens},
                )
                return response.get("response", "")
            
            raise ValueError("Unsupported LLM client type")
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _update_telemetry(self, retrieval_ms: float, reasoning_ms: float):
        """Update telemetry counters."""
        self._query_count += 1
        self._total_retrieval_time_ms += retrieval_ms
        self._total_reasoning_time_ms += reasoning_ms
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG statistics."""
        avg_retrieval = (
            self._total_retrieval_time_ms / self._query_count
            if self._query_count > 0 else 0
        )
        avg_reasoning = (
            self._total_reasoning_time_ms / self._query_count
            if self._query_count > 0 else 0
        )
        
        return {
            "total_queries": self._query_count,
            "avg_retrieval_time_ms": round(avg_retrieval, 2),
            "avg_reasoning_time_ms": round(avg_reasoning, 2),
            "llm_available": self._llm_client is not None,
        }
