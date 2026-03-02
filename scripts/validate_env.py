#!/usr/bin/env python3
"""Environment configuration validator — checks all required env vars (T-142).

Usage:
    python scripts/validate_env.py [--strict]

Exit codes:
    0  All required variables present and valid
    1  One or more required variables missing or invalid
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Variable definitions
# ---------------------------------------------------------------------------

@dataclass
class EnvVar:
    name: str
    required: bool = True
    description: str = ""
    example: str = ""
    validator: object = None  # callable(str) -> bool | None


_REQUIRED_VARS: list[EnvVar] = [
    EnvVar("LIVEKIT_URL", required=True, description="LiveKit server URL",
           example="wss://my-app.livekit.cloud"),
    EnvVar("LIVEKIT_API_KEY", required=True, description="LiveKit API key"),
    EnvVar("LIVEKIT_API_SECRET", required=True, description="LiveKit API secret"),
    EnvVar("DEEPGRAM_API_KEY", required=True, description="Deepgram STT API key"),
    EnvVar("ELEVEN_API_KEY", required=True, description="ElevenLabs TTS API key"),
]

_OPTIONAL_VARS: list[EnvVar] = [
    EnvVar("OLLAMA_API_KEY", required=False, description="Ollama/vision API key"),
    EnvVar("OLLAMA_VL_MODEL_ID", required=False, description="VL model identifier",
           example="qwen3-vl:235b-instruct-cloud"),
    EnvVar("VISION_PROVIDER", required=False, description="Vision backend",
           example="ollama"),
    EnvVar("SPATIAL_PERCEPTION_ENABLED", required=False,
           description="Enable spatial obstacle detection", example="true"),
    EnvVar("ENABLE_QR_SCANNING", required=False, description="Enable QR scanning", example="true"),
    EnvVar("ENABLE_AVATAR", required=False, description="Enable Tavus avatar", example="false"),
    EnvVar("TAVUS_API_KEY", required=False, description="Tavus avatar API key"),
    EnvVar("TAVUS_REPLICA_ID", required=False, description="Tavus replica ID"),
    EnvVar("MEMORY_ENABLED", required=False, description="Enable RAG memory (opt-in)",
           example="false"),
    EnvVar("LOG_LEVEL", required=False, description="Logging level",
           example="INFO"),
]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    passed: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    invalid: list[tuple[str, str]] = field(default_factory=list)  # (name, reason)

    @property
    def ok(self) -> bool:
        return not self.missing_required and not self.invalid


def _validate(strict: bool = False) -> ValidationResult:
    result = ValidationResult()

    for var in _REQUIRED_VARS:
        val = os.environ.get(var.name)
        if not val:
            result.missing_required.append(var.name)
        elif var.validator and not var.validator(val):
            result.invalid.append((var.name, "failed validator"))
        else:
            result.passed.append(var.name)

    for var in _OPTIONAL_VARS:
        val = os.environ.get(var.name)
        if not val:
            result.missing_optional.append(var.name)
        elif var.validator and not var.validator(val):
            if strict:
                result.invalid.append((var.name, "failed validator (strict)"))
            else:
                result.passed.append(var.name)
        else:
            result.passed.append(var.name)

    return result


def _print_report(result: ValidationResult, strict: bool) -> None:
    total = len(_REQUIRED_VARS) + len(_OPTIONAL_VARS)
    print(f"\n{'='*60}")
    print("Environment Validation Report")
    print(f"{'='*60}")
    print(f"  Total variables checked : {total}")
    print(f"  Passed                  : {len(result.passed)}")
    print(f"  Missing (required)      : {len(result.missing_required)}")
    print(f"  Missing (optional)      : {len(result.missing_optional)}")
    print(f"  Invalid                 : {len(result.invalid)}")
    print(f"{'='*60}\n")

    if result.missing_required:
        print("MISSING REQUIRED VARIABLES:")
        for name in result.missing_required:
            var = next(v for v in _REQUIRED_VARS if v.name == name)
            ex = f"  (e.g. {var.example})" if var.example else ""
            print(f"  ✗  {name}{ex}")
            if var.description:
                print(f"       {var.description}")
        print()

    if result.invalid:
        print("INVALID VARIABLES:")
        for name, reason in result.invalid:
            print(f"  ✗  {name} — {reason}")
        print()

    if result.missing_optional:
        print("MISSING OPTIONAL VARIABLES (features may be disabled):")
        for name in result.missing_optional:
            var = next(v for v in _OPTIONAL_VARS if v.name == name)
            ex = f"  (e.g. {var.example})" if var.example else ""
            print(f"  ○  {name}{ex}")
        print()

    if result.ok:
        print("✓  All required environment variables are present.\n")
    else:
        print("✗  Validation FAILED. Set the missing required variables before deploying.\n")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate deployment environment configuration")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Also fail on invalid optional variables",
    )
    p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output; use exit code only",
    )
    return p


def main(argv: list[str] | None = None) -> int:  # noqa: FA100
    args = _build_parser().parse_args(argv)
    result = _validate(strict=args.strict)
    if not args.quiet:
        _print_report(result, strict=args.strict)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
