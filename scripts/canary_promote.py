#!/usr/bin/env python3
"""Canary promotion CLI — promote or rollback a canary deployment (T-139).

Usage:
    python scripts/canary_promote.py promote [--weight PCT]
    python scripts/canary_promote.py rollback [--reason TEXT]
    python scripts/canary_promote.py status

Exit codes:
    0  Success
    1  Operation failed
    2  Bad arguments
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_STATE_FILE = Path("deployments/canary/state.json")
_DEFAULT_STABLE_WEIGHT = 90
_DEFAULT_CANARY_WEIGHT = 10


def _load_state() -> dict:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    return {
        "phase": "stable",
        "canary_weight": 0,
        "stable_weight": 100,
        "started_at": None,
        "promoted_at": None,
        "rolled_back_at": None,
        "rollback_reason": None,
        "history": [],
    }


def _save_state(state: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def _cmd_status(state: dict) -> int:
    print(json.dumps(state, indent=2))
    return 0


def _cmd_promote(state: dict, weight: int) -> int:
    if weight == 100:  # noqa: PLR2004
        # Full promotion
        state["phase"] = "promoted"
        state["canary_weight"] = 100
        state["stable_weight"] = 0
        state["promoted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        state["history"].append({"event": "promoted", "ts": state["promoted_at"]})
        _save_state(state)
        print(f"[canary_promote] Canary promoted to 100% traffic at {state['promoted_at']}")
        return 0

    # Partial promotion / traffic shift
    state["phase"] = "canary"
    state["canary_weight"] = weight
    state["stable_weight"] = 100 - weight
    if state.get("started_at") is None:
        state["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["history"].append({
        "event": "weight_set",
        "canary_weight": weight,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    _save_state(state)
    print(
        f"[canary_promote] Traffic split set: canary={weight}% / stable={100 - weight}%"
    )
    return 0


def _cmd_rollback(state: dict, reason: str) -> int:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["phase"] = "rolled_back"
    state["canary_weight"] = 0
    state["stable_weight"] = 100
    state["rolled_back_at"] = ts
    state["rollback_reason"] = reason
    state["history"].append({"event": "rollback", "reason": reason, "ts": ts})
    _save_state(state)
    print(f"[canary_promote] Rolled back to stable (100%) — reason: {reason}")
    print(f"[canary_promote] Rollback completed at {ts}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Canary deployment promotion CLI")
    sub = p.add_subparsers(dest="command", required=True)

    # promote
    promo = sub.add_parser("promote", help="Promote canary to given traffic weight (default: 100%)")
    promo.add_argument(
        "--weight",
        type=int,
        default=100,
        metavar="PCT",
        help="Traffic percentage to route to canary (0-100, default: 100)",
    )

    # rollback
    rb = sub.add_parser("rollback", help="Roll back canary to stable")
    rb.add_argument(
        "--reason",
        default="manual rollback",
        help="Reason for rollback (for audit log)",
    )

    # status
    sub.add_parser("status", help="Print current canary state")

    return p


def main(argv: list[str] | None = None) -> int:  # noqa: FA100
    args = _build_parser().parse_args(argv)
    state = _load_state()

    if args.command == "status":
        return _cmd_status(state)
    if args.command == "promote":
        if not (0 <= args.weight <= 100):  # noqa: PLR2004
            print(f"[canary_promote] ERROR: --weight must be 0-100, got {args.weight}", file=sys.stderr)
            return 2
        return _cmd_promote(state, args.weight)
    if args.command == "rollback":
        return _cmd_rollback(state, args.reason)
    return 2


if __name__ == "__main__":
    sys.exit(main())
