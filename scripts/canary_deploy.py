"""Canary deployment CLI for Voice-Vision Assistant (T-139).

Manages traffic splitting between stable and canary releases.

Usage:
    python scripts/canary_deploy.py deploy --image v2.1.0 --traffic 10
    python scripts/canary_deploy.py promote
    python scripts/canary_deploy.py rollback
    python scripts/canary_deploy.py status
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("canary-deploy")

STATE_FILE = Path(".canary-state.json")
DEFAULT_CANARY_TRAFFIC_PCT = 10
ANALYSIS_INTERVAL_S = 120  # 2-minute analysis window
PROMOTION_WINDOW_S = 7200  # 2-hour promotion window


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state() -> Dict[str, Any]:
    """Load current canary state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Could not load canary state: %s", exc)
    return {"active": False, "canary_image": None, "stable_image": None,
            "traffic_pct": 0, "deployed_at": None}


def _save_state(state: Dict[str, Any]) -> None:
    """Persist canary state to disk."""
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except IOError as exc:
        logger.error("Could not save canary state: %s", exc)


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------

def _run_compose(
    compose_file: str,
    *args: str,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """Run a docker-compose command."""
    cmd = ["docker", "compose", "-f", compose_file, *args]
    logger.debug("Running: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True,
        timeout=120,
    )


def _update_nginx_weights(canary_pct: int, compose_file: str) -> None:
    """Update Nginx upstream weights for traffic splitting.

    In a real environment this would update the nginx.conf and reload.
    For this implementation we write the weight to an env file consumed by nginx.
    """
    stable_pct = 100 - canary_pct
    weights_env = Path("deployments/canary/.nginx-weights.env")
    weights_env.parent.mkdir(parents=True, exist_ok=True)
    weights_env.write_text(
        f"CANARY_WEIGHT={canary_pct}\nSTABLE_WEIGHT={stable_pct}\n",
        encoding="utf-8",
    )
    logger.info("Traffic split: stable=%d%% canary=%d%%", stable_pct, canary_pct)


# ---------------------------------------------------------------------------
# Subcommand: deploy
# ---------------------------------------------------------------------------

def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy a canary release with specified traffic percentage."""
    state = _load_state()
    if state.get("active"):
        logger.error("A canary is already active (image=%s). Rollback first.", state["canary_image"])
        return 1

    compose_file = args.compose_file
    canary_image = args.image
    traffic_pct = args.traffic

    logger.info("Deploying canary image=%s traffic=%d%%", canary_image, traffic_pct)

    # Write canary image tag to env file
    env_file = Path("deployments/canary/.canary.env")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(f"CANARY_IMAGE={canary_image}\n", encoding="utf-8")

    try:
        _run_compose(compose_file, "up", "-d", "app-canary")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.error("Failed to start canary service: %s", exc)
        return 1

    _update_nginx_weights(traffic_pct, compose_file)

    state.update({
        "active": True,
        "canary_image": canary_image,
        "stable_image": args.stable_image,
        "traffic_pct": traffic_pct,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_state(state)

    logger.info("Canary deployed successfully. Monitor with: canary_deploy.py status")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: promote
# ---------------------------------------------------------------------------

def cmd_promote(args: argparse.Namespace) -> int:
    """Promote canary to 100% traffic and retire stable."""
    state = _load_state()
    if not state.get("active"):
        logger.error("No active canary to promote.")
        return 1

    compose_file = args.compose_file
    canary_image = state["canary_image"]

    logger.info("Promoting canary image=%s to 100%% traffic", canary_image)

    # Shift all traffic to canary
    _update_nginx_weights(100, compose_file)

    # Stop stable service
    try:
        _run_compose(compose_file, "stop", "app-stable", check=False)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Could not stop stable service: %s", exc)

    state.update({
        "active": False,
        "stable_image": canary_image,
        "canary_image": None,
        "traffic_pct": 0,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_state(state)

    logger.info("Canary promoted. New stable image: %s", canary_image)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: rollback
# ---------------------------------------------------------------------------

def cmd_rollback(args: argparse.Namespace) -> int:
    """Roll back traffic to stable and remove canary."""
    state = _load_state()
    if not state.get("active"):
        logger.warning("No active canary. Nothing to roll back.")
        return 0

    compose_file = args.compose_file

    logger.info("Rolling back canary image=%s", state.get("canary_image"))

    # Shift all traffic back to stable
    _update_nginx_weights(0, compose_file)

    # Stop canary service
    try:
        _run_compose(compose_file, "stop", "app-canary", check=False)
        _run_compose(compose_file, "rm", "-f", "app-canary", check=False)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Could not fully remove canary service: %s", exc)

    state.update({
        "active": False,
        "canary_image": None,
        "traffic_pct": 0,
        "rolled_back_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_state(state)

    logger.info("Rollback complete. Traffic restored to stable.")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    """Show current canary deployment status."""
    state = _load_state()

    if not state.get("active"):
        print("No active canary deployment.")
        if state.get("stable_image"):
            print(f"Current stable image: {state['stable_image']}")
        return 0

    print(json.dumps({
        "status": "active",
        "canary_image": state.get("canary_image"),
        "stable_image": state.get("stable_image"),
        "traffic_pct": state.get("traffic_pct"),
        "deployed_at": state.get("deployed_at"),
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: auto-analyze (for CI use)
# ---------------------------------------------------------------------------

def cmd_auto_analyze(args: argparse.Namespace) -> int:
    """Run automated canary analysis and rollback if needed."""
    state = _load_state()
    if not state.get("active"):
        logger.info("No active canary to analyze.")
        return 0

    try:
        from scripts.canary_analysis import collect_metrics, compare_metrics, should_rollback
    except ImportError:
        logger.warning("canary_analysis module not available — skipping auto-analysis")
        return 0

    stable_metrics = collect_metrics("app-stable")
    canary_metrics = collect_metrics("app-canary")
    comparison = compare_metrics(stable_metrics, canary_metrics)

    if should_rollback(comparison):
        logger.warning("Canary analysis: degradation detected. Initiating rollback.")
        return cmd_rollback(args)

    logger.info("Canary analysis: metrics healthy. No action needed.")
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Canary deployment manager for Voice-Vision Assistant"
    )
    parser.add_argument(
        "--compose-file",
        default="deployments/canary/docker-compose.canary.yml",
        help="Path to canary docker-compose file",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # deploy
    deploy_p = sub.add_parser("deploy", help="Deploy a canary release")
    deploy_p.add_argument("--image", required=True, help="Canary image tag")
    deploy_p.add_argument("--stable-image", default="latest", help="Current stable image tag")
    deploy_p.add_argument(
        "--traffic", type=int, default=DEFAULT_CANARY_TRAFFIC_PCT,
        help=f"Canary traffic percentage (default: {DEFAULT_CANARY_TRAFFIC_PCT})"
    )

    # promote
    sub.add_parser("promote", help="Promote canary to 100% traffic")

    # rollback
    sub.add_parser("rollback", help="Roll back to stable")

    # status
    sub.add_parser("status", help="Show current canary status")

    # auto-analyze
    sub.add_parser("auto-analyze", help="Run automated metrics analysis")

    return parser


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "deploy": cmd_deploy,
        "promote": cmd_promote,
        "rollback": cmd_rollback,
        "status": cmd_status,
        "auto-analyze": cmd_auto_analyze,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
