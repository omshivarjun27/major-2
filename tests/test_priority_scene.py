"""
Tests for Priority Scene Module
================================

Tests for hazard ranking and prioritization.
"""

import pytest
import time


# ============================================================================
# Test Priority Scene Analyzer
# ============================================================================

class TestPrioritySceneAnalyzer:
    """Tests for hazard analysis and ranking."""
    
    def test_import(self):
        """Test module imports successfully."""
        from core.vqa import PrioritySceneAnalyzer, HazardSeverity
        assert PrioritySceneAnalyzer is not None
    
    def test_analyzer_creation(self):
        """Test analyzer instantiation."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        assert analyzer is not None
        assert analyzer.walking_speed_ms == 1.4
        assert analyzer.critical_distance_m == 1.5
    
    def test_empty_detections(self):
        """Test analysis with no detections."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        result = analyzer.analyze([])
        
        assert result.total_detected == 0
        assert len(result.top_hazards) == 0
        assert result.path_clear
    
    def test_single_detection(self):
        """Test analysis with single detection."""
        from core.vqa import PrioritySceneAnalyzer, HazardSeverity
        
        analyzer = PrioritySceneAnalyzer()
        
        detections = [{
            "class": "chair",
            "confidence": 0.95,
            "bbox": [0.4, 0.5, 0.6, 0.8],  # Center of image
            "depth": 2.0,
        }]
        
        result = analyzer.analyze(detections)
        
        assert result.total_detected == 1
        assert len(result.top_hazards) == 1
        assert result.top_hazards[0].class_name == "chair"
        assert result.top_hazards[0].distance_m == 2.0
    
    def test_multiple_detections_priority(self):
        """Test that closer obstacles rank higher."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        detections = [
            {"class": "table", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.7], "depth": 5.0},
            {"class": "chair", "confidence": 0.95, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 1.0},
            {"class": "person", "confidence": 0.85, "bbox": [0.3, 0.4, 0.5, 0.7], "depth": 3.0},
        ]
        
        result = analyzer.analyze(detections, top_n=3)
        
        assert result.total_detected == 3
        assert len(result.top_hazards) == 3
        
        # Closest object should be first (chair at 1m)
        assert result.top_hazards[0].class_name == "chair"
        assert result.top_hazards[0].distance_m == 1.0
    
    def test_direction_affects_priority(self):
        """Test that center obstacles rank higher than peripheral."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        # Same distance, different positions
        detections = [
            {"class": "chair", "confidence": 0.9, "bbox": [0.0, 0.5, 0.1, 0.7], "depth": 2.0},  # Far left
            {"class": "table", "confidence": 0.9, "bbox": [0.45, 0.5, 0.55, 0.7], "depth": 2.0},  # Center
        ]
        
        result = analyzer.analyze(detections, top_n=2)
        
        # Center obstacle should rank higher
        assert result.top_hazards[0].class_name == "table"
    
    def test_severity_levels(self):
        """Test severity assignment based on distance."""
        from core.vqa import PrioritySceneAnalyzer, HazardSeverity
        
        analyzer = PrioritySceneAnalyzer()
        
        detections = [
            {"class": "obstacle", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 1.0},  # Critical
            {"class": "obstacle", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 2.5},  # High
            {"class": "obstacle", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 4.5},  # Medium
            {"class": "obstacle", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 8.0},  # Low
        ]
        
        result = analyzer.analyze(detections)
        
        # Verify severities are assigned
        severities = [h.severity for h in result.all_hazards]
        assert any(s == HazardSeverity.CRITICAL for s in severities[:2])  # Close ones should be critical/high
    
    def test_path_clear_detection(self):
        """Test path clear status."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        # Obstacle off to the side
        detections = [{
            "class": "chair",
            "confidence": 0.9,
            "bbox": [0.0, 0.5, 0.15, 0.8],  # Far left
            "depth": 5.0,
        }]
        
        result = analyzer.analyze(detections)
        assert result.path_clear
        
        # Obstacle in center
        detections = [{
            "class": "chair",
            "confidence": 0.9,
            "bbox": [0.4, 0.5, 0.6, 0.8],  # Center
            "depth": 2.0,
        }]
        
        result = analyzer.analyze(detections)
        assert not result.path_clear
    
    def test_short_cue_format(self):
        """Test short cue generation for TTS."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        detections = [{
            "class": "person",
            "confidence": 0.95,
            "bbox": [0.45, 0.5, 0.55, 0.8],
            "depth": 3.5,
        }]
        
        result = analyzer.analyze(detections)
        hazard = result.top_hazards[0]
        
        assert hazard.short_cue
        assert "person" in hazard.short_cue.lower()
        assert "3.5" in hazard.short_cue or "meters" in hazard.short_cue
    
    def test_navigation_cue_generation(self):
        """Test navigation cue generation."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        # Critical hazard ahead
        detections = [{
            "class": "person",
            "confidence": 0.9,
            "bbox": [0.45, 0.5, 0.55, 0.8],
            "depth": 0.8,  # Very close
        }]
        
        result = analyzer.analyze(detections)
        
        assert result.navigation_cue
        assert "stop" in result.navigation_cue.lower() or "caution" in result.navigation_cue.lower()
    
    def test_top_n_limit(self):
        """Test top_n parameter limits results."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        # Create 10 detections
        detections = [
            {"class": f"obj{i}", "confidence": 0.9, "bbox": [0.1*i, 0.5, 0.1*i+0.1, 0.8], "depth": float(i+1)}
            for i in range(10)
        ]
        
        result = analyzer.analyze(detections, top_n=3)
        
        assert len(result.top_hazards) == 3
        assert result.total_detected == 10
    
    def test_hazard_to_dict(self):
        """Test hazard serialization."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        detections = [{
            "class": "chair",
            "confidence": 0.95,
            "bbox": [0.4, 0.5, 0.6, 0.8],
            "depth": 2.5,
        }]
        
        result = analyzer.analyze(detections)
        hazard_dict = result.top_hazards[0].to_dict()
        
        assert "id" in hazard_dict
        assert "name" in hazard_dict
        assert "distance_m" in hazard_dict
        assert "direction" in hazard_dict
        assert "confidence" in hazard_dict
        assert "risk_score" in hazard_dict
        assert "severity" in hazard_dict
        assert "short_cue" in hazard_dict
    
    def test_result_to_dict(self):
        """Test result serialization."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        detections = [{
            "class": "table",
            "confidence": 0.9,
            "bbox": [0.3, 0.4, 0.7, 0.9],
            "depth": 3.0,
        }]
        
        result = analyzer.analyze(detections)
        result_dict = result.to_dict()
        
        assert "top_hazards" in result_dict
        assert "total_detected" in result_dict
        assert "highest_severity" in result_dict
        assert "path_clear" in result_dict
        assert "navigation_cue" in result_dict
        assert "processing_time_ms" in result_dict
    
    def test_stats_tracking(self):
        """Test statistics tracking."""
        from core.vqa import PrioritySceneAnalyzer
        
        analyzer = PrioritySceneAnalyzer()
        
        # Run a few analyses
        for _ in range(5):
            analyzer.analyze([{"class": "obj", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 2.0}])
        
        stats = analyzer.get_stats()
        
        assert stats["total_analyses"] == 5
        assert "avg_processing_ms" in stats


# ============================================================================
# Test Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_analyze_priority_scene(self):
        """Test analyze_priority_scene function."""
        from core.vqa import analyze_priority_scene
        
        detections = [
            {"class": "chair", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 2.0},
        ]
        
        result = analyze_priority_scene(detections)
        
        assert isinstance(result, dict)
        assert "top_hazards" in result
    
    def test_get_top_hazards(self):
        """Test get_top_hazards function."""
        from core.vqa import get_top_hazards
        
        detections = [
            {"class": "chair", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 2.0},
            {"class": "table", "confidence": 0.9, "bbox": [0.4, 0.5, 0.6, 0.8], "depth": 3.0},
        ]
        
        hazards = get_top_hazards(detections)
        
        assert isinstance(hazards, list)
        assert len(hazards) <= 3


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
