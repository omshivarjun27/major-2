# Phase 4 Learnings

## Issue Registry Generation
 26 issues extracted from 10 artifacts: 18 from architecture_risks.md (R1-R18), 4 from ci_summary/security_scan, 4 from data_flows gap analysis
 Severity distribution: 4 critical, 6 high, 11 medium, 5 low
 7 GPU-related issues, 6 cloud-related issues
 JSON validation essential — used node.js since python not on PATH in this env

## Architecture Observations
 Hybrid architecture is well-separated: cloud (LLM/STT/TTS) vs local GPU (vision/embedding/OCR)
 Local GPU pipeline well-designed: ~3.1GB of 8GB VRAM, all models have CPU fallback
 Cloud side fragile: no retry/backoff, no circuit breakers, no fallback providers
 OllamaEmbedder sync blocking is the most impactful async boundary violation
 Security is the top blocker: 7 API keys in git, Docker root, .env in image
