#!/usr/bin/env python3
"""SBOM generator — produces a Software Bill of Materials for the release (T-150).

Generates a CycloneDX-compatible JSON SBOM from installed Python packages.

Usage:
    python scripts/generate_sbom.py [--output PATH] [--format cyclonedx|spdx]

Output:
    reports/sbom.json (default)

Exit codes:
    0  Success
    1  Generation failed
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def _get_installed_packages() -> list[dict]:
    """Return list of installed packages via pip list --format=json."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pip list failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def _get_package_metadata(name: str) -> dict:
    """Return package metadata via pip show."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", name],
        capture_output=True,
        text=True,
        check=False,
    )
    meta: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if ": " in line:
            key, _, value = line.partition(": ")
            meta[key.strip().lower().replace("-", "_")] = value.strip()
    return meta


def _build_cyclonedx(packages: list[dict]) -> dict:
    """Build a minimal CycloneDX JSON SBOM."""
    components = []
    for pkg in packages:
        name = pkg["name"]
        version = pkg["version"]
        meta = _get_package_metadata(name)
        component: dict = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name.lower()}@{version}",
        }
        if meta.get("license"):
            component["licenses"] = [{"license": {"name": meta["license"]}}]
        if meta.get("home_page"):
            component["externalReferences"] = [
                {"type": "website", "url": meta["home_page"]}
            ]
        components.append(component)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:vva-sbom-{int(time.time())}",
        "version": 1,
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "component": {
                "type": "application",
                "name": "voice-vision-assistant",
                "version": "1.0.0",
            },
        },
        "components": components,
    }


def _build_spdx(packages: list[dict]) -> dict:
    """Build a minimal SPDX JSON SBOM."""
    packages_spdx = []
    for pkg in packages:
        name = pkg["name"]
        version = pkg["version"]
        meta = _get_package_metadata(name)
        entry: dict = {
            "SPDXID": f"SPDXRef-{name.replace('.', '-').replace('_', '-')}",
            "name": name,
            "versionInfo": version,
            "downloadLocation": meta.get("home_page", "NOASSERTION"),
            "filesAnalyzed": False,
        }
        if meta.get("license"):
            entry["licenseConcluded"] = meta["license"]
            entry["licenseDeclared"] = meta["license"]
        packages_spdx.append(entry)

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "voice-vision-assistant-1.0.0",
        "documentNamespace": "https://github.com/codingaslu/Envision-AI/sbom-1.0.0",
        "creationInfo": {
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "creators": ["Tool: generate_sbom.py"],
        },
        "packages": packages_spdx,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate Software Bill of Materials")
    p.add_argument(
        "--output",
        default="reports/sbom.json",
        help="Output file path (default: reports/sbom.json)",
    )
    p.add_argument(
        "--format",
        choices=["cyclonedx", "spdx"],
        default="cyclonedx",
        help="SBOM format (default: cyclonedx)",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print package list to stderr",
    )
    return p


def main(argv: list[str] | None = None) -> int:  # noqa: FA100
    args = _build_parser().parse_args(argv)

    print("[generate_sbom] Collecting installed packages ...", file=sys.stderr)
    try:
        packages = _get_installed_packages()
    except RuntimeError as exc:
        print(f"[generate_sbom] ERROR: {exc}", file=sys.stderr)
        return 1

    if args.verbose:
        for pkg in packages:
            print(f"  {pkg['name']}=={pkg['version']}", file=sys.stderr)

    print(f"[generate_sbom] {len(packages)} packages found, building {args.format} SBOM ...", file=sys.stderr)

    if args.format == "cyclonedx":
        sbom = _build_cyclonedx(packages)
    else:
        sbom = _build_spdx(packages)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")

    print(f"[generate_sbom] SBOM written to {out_path} ({out_path.stat().st_size} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
