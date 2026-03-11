"""Tests for Reasoning Engine Suite (T-120 through T-124)."""

from __future__ import annotations

import pytest

from core.reasoning.causal import (
    CausalFactor,
    CausalGraph,
    CausalLink,
    CausalReasoner,
)
from core.reasoning.integration import (
    IntegratedReasoner,
    IntegratedReasoningConfig,
    IntegratedResult,
    create_integrated_reasoner,
)
from core.reasoning.reasoning_foundation import (
    ReasoningCache,
    ReasoningChain,
    ReasoningConfig,
    ReasoningOrchestrator,
    ReasoningStep,
    ReasoningType,
    create_reasoning_orchestrator,
)
from core.reasoning.spatial import (
    SpatialEntity,
    SpatialReasoner,
    SpatialRelation,
    SpatialRelationType,
)
from core.reasoning.temporal import (
    TemporalEvent,
    TemporalReasoner,
    TemporalRelation,
)

# ===========================================================================
# T-120: Reasoning Foundation
# ===========================================================================

class TestReasoningConfig:
    def test_defaults(self):
        cfg = ReasoningConfig()
        assert cfg.max_reasoning_steps == 5
        assert cfg.confidence_threshold == 0.3
        assert cfg.timeout_ms == 300.0
        assert cfg.enable_caching is True
        assert cfg.cache_ttl_s == 60.0


class TestReasoningStep:
    def test_to_dict(self):
        step = ReasoningStep(step_type="analyze", confidence=0.8, latency_ms=10.5)
        d = step.to_dict()
        assert d["step_type"] == "analyze"
        assert d["confidence"] == 0.8
        assert d["latency_ms"] == 10.5


class TestReasoningChain:
    def test_empty_chain(self):
        chain = ReasoningChain()
        assert chain.steps == []
        assert chain.final_answer == ""
        assert chain.total_confidence == 0.0

    def test_add_step(self):
        chain = ReasoningChain()
        chain.add_step(ReasoningStep(step_type="s1", confidence=0.6, latency_ms=5))
        chain.add_step(ReasoningStep(step_type="s2", confidence=0.8, latency_ms=10))
        assert len(chain.steps) == 2
        assert chain.total_latency_ms == 15
        assert chain.total_confidence == pytest.approx(0.7)

    def test_to_dict(self):
        chain = ReasoningChain(final_answer="result", total_confidence=0.75)
        d = chain.to_dict()
        assert d["final_answer"] == "result"
        assert d["step_count"] == 0


class TestReasoningCache:
    def test_set_and_get(self):
        cache = ReasoningCache(ttl_s=10)
        chain = ReasoningChain(final_answer="cached")
        cache.set("key1", chain)
        result = cache.get("key1")
        assert result is not None
        assert result.final_answer == "cached"

    def test_miss(self):
        cache = ReasoningCache()
        assert cache.get("nonexistent") is None

    def test_clear(self):
        cache = ReasoningCache()
        cache.set("k", ReasoningChain())
        cache.clear()
        assert cache.get("k") is None

    def test_stats(self):
        cache = ReasoningCache()
        cache.set("k", ReasoningChain())
        cache.get("k")
        cache.get("missing")
        s = cache.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["size"] == 1


class TestReasoningOrchestrator:
    async def test_no_reasoners(self):
        orch = ReasoningOrchestrator()
        chain = await orch.orchestrate("What?", {})
        assert "No suitable" in chain.final_answer

    async def test_temporal_keyword_routing(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("test", timestamp_ms=1000))
        orch = ReasoningOrchestrator(reasoners=[tr])
        chain = await orch.orchestrate("When did this happen?", {})
        assert chain.metadata.get("reasoner") == "temporal"

    async def test_spatial_keyword_routing(self):
        sr = SpatialReasoner()
        orch = ReasoningOrchestrator(reasoners=[sr])
        entities = [SpatialEntity("e1", "chair", (0, 0, 2))]
        chain = await orch.orchestrate("Where is the chair?", {"entities": entities})
        assert chain.metadata.get("reasoner") == "spatial"

    async def test_factory(self):
        orch = create_reasoning_orchestrator()
        assert isinstance(orch, ReasoningOrchestrator)

    async def test_health(self):
        orch = ReasoningOrchestrator()
        h = orch.health()
        assert "reasoners" in h
        assert h["total_orchestrations"] == 0


# ===========================================================================
# T-121: Temporal Reasoning
# ===========================================================================

class TestTemporalEvent:
    def test_end_ms(self):
        e = TemporalEvent("walk", timestamp_ms=1000, duration_ms=500)
        assert e.end_ms == 1500

    def test_to_dict(self):
        e = TemporalEvent("run", timestamp_ms=2000, confidence=0.9)
        d = e.to_dict()
        assert d["event_type"] == "run"
        assert d["confidence"] == 0.9


class TestTemporalRelation:
    def test_values(self):
        assert TemporalRelation.BEFORE.value == "before"
        assert TemporalRelation.SIMULTANEOUS.value == "simultaneous"


class TestTemporalReasoner:
    def test_reason_type(self):
        tr = TemporalReasoner()
        assert tr.reason_type == ReasoningType.TEMPORAL

    def test_add_event(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("a", timestamp_ms=100))
        tr.add_event(TemporalEvent("b", timestamp_ms=200))
        assert tr.health()["buffer_size"] == 2

    async def test_reason_empty(self):
        tr = TemporalReasoner()
        chain = await tr.reason({})
        assert "No temporal events" in chain.final_answer

    async def test_reason_single_event(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("greeting", timestamp_ms=1000, description="Hello"))
        chain = await tr.reason({})
        assert "Hello" in chain.final_answer

    async def test_reason_multiple_events(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("door_open", timestamp_ms=1000))
        tr.add_event(TemporalEvent("person_enter", timestamp_ms=2000))
        tr.add_event(TemporalEvent("greeting", timestamp_ms=3000))
        chain = await tr.reason({})
        assert len(chain.steps) >= 2
        assert chain.final_answer != ""

    def test_compute_relation_before(self):
        tr = TemporalReasoner()
        e1 = TemporalEvent("a", timestamp_ms=1000, duration_ms=100)
        e2 = TemporalEvent("b", timestamp_ms=2000)
        assert tr._compute_temporal_relation(e1, e2) == TemporalRelation.BEFORE

    def test_compute_relation_simultaneous(self):
        tr = TemporalReasoner()
        e1 = TemporalEvent("a", timestamp_ms=1000)
        e2 = TemporalEvent("b", timestamp_ms=1050)
        assert tr._compute_temporal_relation(e1, e2) == TemporalRelation.SIMULTANEOUS

    def test_compute_relation_overlaps(self):
        tr = TemporalReasoner()
        e1 = TemporalEvent("a", timestamp_ms=1000, duration_ms=2000)
        e2 = TemporalEvent("b", timestamp_ms=2000, duration_ms=2000)
        rel = tr._compute_temporal_relation(e1, e2)
        assert rel == TemporalRelation.OVERLAPS

    async def test_health(self):
        tr = TemporalReasoner()
        h = tr.health()
        assert h["type"] == "temporal"
        assert h["buffer_size"] == 0


# ===========================================================================
# T-122: Spatial Reasoning
# ===========================================================================

class TestSpatialEntity:
    def test_to_dict(self):
        e = SpatialEntity("e1", "chair", (0.3, 0.5, 2.0), "medium", 0.8)
        d = e.to_dict()
        assert d["label"] == "chair"
        assert d["position"] == [0.3, 0.5, 2.0]


class TestSpatialRelationType:
    def test_values(self):
        assert SpatialRelationType.LEFT_OF.value == "left_of"
        assert SpatialRelationType.BLOCKING.value == "blocking"


class TestSpatialRelation:
    def test_describe(self):
        e1 = SpatialEntity("e1", "chair")
        e2 = SpatialEntity("e2", "table")
        r = SpatialRelation(e1, SpatialRelationType.LEFT_OF, e2, 0.8, 1.5)
        desc = r.describe()
        assert "chair" in desc
        assert "left of" in desc
        assert "table" in desc
        assert "1.5m" in desc

    def test_to_dict(self):
        e1 = SpatialEntity("e1", "chair")
        e2 = SpatialEntity("e2", "table")
        r = SpatialRelation(e1, SpatialRelationType.NEAR, e2, 0.7, 0.5)
        d = r.to_dict()
        assert d["relation"] == "near"


class TestSpatialReasoner:
    def test_reason_type(self):
        sr = SpatialReasoner()
        assert sr.reason_type == ReasoningType.SPATIAL

    async def test_reason_empty(self):
        sr = SpatialReasoner()
        chain = await sr.reason({})
        assert "No spatial entities" in chain.final_answer

    async def test_reason_with_entities(self):
        sr = SpatialReasoner()
        entities = [
            SpatialEntity("e1", "chair", (0.2, 0.5, 2.0)),
            SpatialEntity("e2", "table", (0.8, 0.5, 2.0)),
        ]
        chain = await sr.reason({"entities": entities})
        assert "chair" in chain.final_answer
        assert "table" in chain.final_answer
        assert len(chain.steps) >= 2

    def test_compute_relations(self):
        sr = SpatialReasoner()
        entities = [
            SpatialEntity("e1", "a", (0.0, 0.0, 2.0)),
            SpatialEntity("e2", "b", (5.0, 0.0, 2.0)),
        ]
        rels = sr.compute_relations(entities)
        assert len(rels) == 1
        assert rels[0].relation == SpatialRelationType.RIGHT_OF

    def test_infer_left_right(self):
        sr = SpatialReasoner()
        e1 = SpatialEntity("e1", "a", (0.0, 0.0, 2.0))
        e2 = SpatialEntity("e2", "b", (-5.0, 0.0, 2.0))
        assert sr._infer_relation(e1, e2) == SpatialRelationType.LEFT_OF

    def test_infer_in_front(self):
        sr = SpatialReasoner()
        e1 = SpatialEntity("e1", "a", (0.0, 0.0, 5.0))
        e2 = SpatialEntity("e2", "b", (0.0, 0.0, 2.0))
        assert sr._infer_relation(e1, e2) == SpatialRelationType.IN_FRONT

    def test_infer_behind(self):
        sr = SpatialReasoner()
        e1 = SpatialEntity("e1", "a", (0.0, 0.0, 2.0))
        e2 = SpatialEntity("e2", "b", (0.0, 0.0, 5.0))
        assert sr._infer_relation(e1, e2) == SpatialRelationType.BEHIND

    def test_estimate_distance(self):
        sr = SpatialReasoner()
        e1 = SpatialEntity("e1", "a", (0.0, 0.0, 0.0))
        e2 = SpatialEntity("e2", "b", (3.0, 4.0, 0.0))
        assert sr._estimate_distance(e1, e2) == pytest.approx(5.0)

    def test_describe_scene_empty(self):
        sr = SpatialReasoner()
        assert sr.describe_scene([], []) == "Scene is empty."

    async def test_health(self):
        sr = SpatialReasoner()
        h = sr.health()
        assert h["type"] == "spatial"


# ===========================================================================
# T-123: Causal Reasoning
# ===========================================================================

class TestCausalFactor:
    def test_to_dict(self):
        f = CausalFactor("f1", "door opened", "cause", 0.7, ["obs1"])
        d = f.to_dict()
        assert d["factor_id"] == "f1"
        assert d["evidence_count"] == 1


class TestCausalLink:
    def test_to_dict(self):
        c = CausalFactor("c1", "cause")
        e = CausalFactor("e1", "effect")
        link = CausalLink(c, e, 0.6, "temporal", True)
        d = link.to_dict()
        assert d["cause"] == "c1"
        assert d["effect"] == "e1"


class TestCausalGraph:
    def test_add_node_and_edge(self):
        g = CausalGraph()
        c = CausalFactor("c1", "cause factor")
        e = CausalFactor("e1", "effect factor")
        g.add_node(c)
        g.add_node(e)
        g.add_edge(CausalLink(c, e, 0.5))
        assert len(g.nodes) == 2
        assert len(g.edges) == 1

    def test_get_causes(self):
        g = CausalGraph()
        c = CausalFactor("c1", "cause")
        e = CausalFactor("e1", "effect")
        g.add_edge(CausalLink(c, e, 0.5))
        causes = g.get_causes("e1")
        assert len(causes) == 1
        assert causes[0].factor_id == "c1"

    def test_get_effects(self):
        g = CausalGraph()
        c = CausalFactor("c1", "cause")
        e = CausalFactor("e1", "effect")
        g.add_edge(CausalLink(c, e, 0.5))
        effects = g.get_effects("c1")
        assert len(effects) == 1
        assert effects[0].factor_id == "e1"

    def test_to_dict(self):
        g = CausalGraph()
        g.add_node(CausalFactor("n1", "node"))
        d = g.to_dict()
        assert d["node_count"] == 1
        assert d["edge_count"] == 0


class TestCausalReasoner:
    def test_reason_type(self):
        cr = CausalReasoner()
        assert cr.reason_type == ReasoningType.CAUSAL

    async def test_reason_empty(self):
        cr = CausalReasoner()
        chain = await cr.reason({})
        assert "No observations" in chain.final_answer

    async def test_reason_with_observations(self):
        cr = CausalReasoner()
        chain = await cr.reason({
            "observations": [
                {"type": "door_opened", "timestamp_ms": 1000},
                {"type": "person_approaching", "timestamp_ms": 2000},
            ]
        })
        assert chain.final_answer != ""
        assert len(chain.steps) >= 2

    def test_build_causal_graph(self):
        cr = CausalReasoner()
        observations = [
            {"type": "alarm", "confidence": 0.8},
            {"type": "running"},
        ]
        graph = cr.build_causal_graph(observations)
        assert len(graph.nodes) >= 2
        assert len(graph.edges) >= 1

    def test_build_graph_with_templates(self):
        cr = CausalReasoner()
        observations = [{"type": "car_horn"}]
        graph = cr.build_causal_graph(observations)
        # car_horn has template effects
        effects = graph.get_effects("f_0")
        assert len(effects) >= 1

    def test_explain_why(self):
        cr = CausalReasoner()
        g = CausalGraph()
        c = CausalFactor("c1", "door opened", "cause")
        e = CausalFactor("e1", "draft felt", "effect")
        g.add_edge(CausalLink(c, e, 0.5))
        explanation = cr.explain_why(g, "e1")
        assert "door opened" in explanation

    def test_predict_effects(self):
        cr = CausalReasoner()
        g = CausalGraph()
        c = CausalFactor("c1", "alarm")
        e = CausalFactor("e1", "evacuation")
        g.add_edge(CausalLink(c, e, 0.6))
        effects = cr.predict_effects(g, "c1")
        assert len(effects) == 1

    async def test_health(self):
        cr = CausalReasoner()
        h = cr.health()
        assert h["type"] == "causal"


# ===========================================================================
# T-124: Reasoning Integration
# ===========================================================================

class TestIntegratedReasoningConfig:
    def test_defaults(self):
        cfg = IntegratedReasoningConfig()
        assert cfg.temporal_weight == 0.3
        assert cfg.spatial_weight == 0.4
        assert cfg.causal_weight == 0.3
        assert cfg.min_confidence == 0.25


class TestIntegratedResult:
    def test_to_dict(self):
        result = IntegratedResult(
            combined_answer="test answer",
            combined_confidence=0.7,
            reasoning_types_used=["temporal", "spatial"],
        )
        d = result.to_dict()
        assert d["combined_answer"] == "test answer"
        assert len(d["reasoning_types_used"]) == 2

    def test_user_cue(self):
        result = IntegratedResult(combined_answer="Chair ahead")
        assert result.user_cue == "Chair ahead"

    def test_user_cue_empty(self):
        result = IntegratedResult()
        assert result.user_cue == "Analysis complete."


class TestIntegratedReasoner:
    async def test_reason_no_reasoners(self):
        ir = IntegratedReasoner()
        result = await ir.reason("What?", {})
        assert isinstance(result, IntegratedResult)
        assert "No reasoning" in result.combined_answer

    async def test_reason_with_temporal(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("walk", timestamp_ms=1000))
        tr.add_event(TemporalEvent("stop", timestamp_ms=2000))
        ir = IntegratedReasoner(temporal=tr)
        result = await ir.reason("When did things happen?", {})
        assert "temporal" in result.reasoning_types_used

    async def test_reason_with_spatial(self):
        sr = SpatialReasoner()
        ir = IntegratedReasoner(spatial=sr)
        entities = [SpatialEntity("e1", "chair", (0, 0, 2))]
        result = await ir.reason("Where is it?", {"entities": entities})
        assert "spatial" in result.reasoning_types_used

    async def test_reason_with_causal(self):
        cr = CausalReasoner()
        ir = IntegratedReasoner(causal=cr)
        result = await ir.reason("Why?", {"observations": [{"type": "alarm"}]})
        assert "causal" in result.reasoning_types_used

    async def test_reason_all_types(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("a", timestamp_ms=1000))
        sr = SpatialReasoner()
        cr = CausalReasoner()
        ir = IntegratedReasoner(temporal=tr, spatial=sr, causal=cr)
        result = await ir.reason("What is happening?", {
            "entities": [SpatialEntity("e1", "obj", (0, 0, 2))],
            "observations": [{"type": "alarm"}],
        })
        assert len(result.reasoning_types_used) >= 1
        assert result.total_latency_ms >= 0

    async def test_factory(self):
        ir = create_integrated_reasoner()
        assert isinstance(ir, IntegratedReasoner)

    async def test_health(self):
        ir = IntegratedReasoner()
        h = ir.health()
        assert h["total_integrations"] == 0

    async def test_combined_confidence(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("a", timestamp_ms=1000))
        tr.add_event(TemporalEvent("b", timestamp_ms=2000))
        ir = IntegratedReasoner(temporal=tr)
        result = await ir.reason("timeline?", {})
        assert result.combined_confidence >= 0
