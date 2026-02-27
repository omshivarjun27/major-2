# T-082: llm-inference-optimization

> Phase: P4 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Optimize LLM inference latency to meet the <300ms VQA processing target. Focus on Ollama configuration tuning, prompt optimization, response streaming, and KV cache management. Reduce time-to-first-token (TTFT) for better perceived responsiveness.

## Implementation Plan

1. Profile current Ollama inference patterns:
   - Time-to-first-token (TTFT)
   - Tokens per second
   - Total generation time
2. Tune Ollama parameters:
   - Context window size
   - Batch size
   - GPU layers
   - Temperature and sampling
3. Optimize prompts:
   - Minimize prompt length while maintaining quality
   - Use system prompts efficiently
4. Implement streaming response handling:
   - Start TTS on first sentence, not full response
   - Progressive output to user
5. Configure KV cache for conversation continuity.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `infrastructure/llm/ollama/optimizer.py` | Ollama optimization utilities |
| `shared/config/settings.py` | LLM tuning parameters |
| `tests/performance/test_llm_latency.py` | LLM latency tests |

## Acceptance Criteria

- [ ] TTFT measured and optimized
- [ ] Ollama parameters tuned for target hardware
- [ ] Prompt templates optimized for minimal tokens
- [ ] Streaming response integrated with TTS
- [ ] VQA processing <300ms achieved
- [ ] Configuration documented

## Upstream Dependencies

T-074 (hot path profiling)

## Downstream Unblocks

T-084 (end-to-end latency validation)

## Estimated Scope

Medium. Configuration and optimization, ~150-200 lines of code.
