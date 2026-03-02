# T-119: Audio Event Detection Enhancement

**Status**: completed
**Priority**: P6
**Created**: 2026-03-02

## Description
Enhance audio event detection with multi-channel support, temporal event correlation, adaptive thresholding, and ambient noise estimation.

## Deliverables
- `core/audio/enhanced_detector.py` — EnhancedAudioConfig, AudioEventCorrelation, EnhancedAudioResult, EnhancedAudioDetector, factory
- `tests/unit/test_enhanced_audio.py` — 30+ tests covering config, detection, correlation, ambient noise, adaptive threshold, edge cases

## Key Decisions
- Multi-channel audio averaged to mono for base detector compatibility
- Correlation window defaults to 2000ms; events beyond window are uncorrelated
- Adaptive threshold: events must be 10dB above ambient (critical events exempt)
- Event density computed over the correlation window (events/second)
- Graceful degradation: exceptions return empty result with noise floor defaults
