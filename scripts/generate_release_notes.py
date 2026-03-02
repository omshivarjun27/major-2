#!/usr/bin/env python3
"""Release notes generator — parses conventional commits and produces CHANGELOG markdown (T-140).

Usage:
    python scripts/generate_release_notes.py [--from REF] [--to REF] [--version VERSION]

Output:
    Prints formatted changelog to stdout; optionally writes to CHANGELOG.md.

Exit codes:
    0  Success
    1  Git error or no commits found
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Conventional commit categories
# ---------------------------------------------------------------------------
_TYPE_LABELS: dict[str, str] = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "test": "Tests",
    "docs": "Documentation",
    "ci": "CI / DevOps",
    "chore": "Chores",
    "build": "Build",
    "style": "Style",
    "revert": "Reverts",
}

# Task ID pattern — e.g. T-042, T-137
_TASK_RE = re.compile(r"\bT-\d{3}\b")
# Conventional commit pattern: type(scope): description
_CONV_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$"
)


class CommitEntry(NamedTuple):
    sha: str
    type_: str
    scope: str
    breaking: bool
    description: str
    task_ids: list[str]
    raw: str


def _git(*args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _parse_commits(from_ref: str, to_ref: str) -> list[CommitEntry]:
    """Return parsed CommitEntry list from git log between two refs."""
    sep = "\x1f"
    fmt = f"%H{sep}%s"
    try:
        log = _git("log", f"{from_ref}..{to_ref}", f"--pretty=format:{fmt}")
    except RuntimeError as exc:
        print(f"[generate_release_notes] WARNING: {exc}", file=sys.stderr)
        return []

    entries: list[CommitEntry] = []
    for line in log.splitlines():
        if not line.strip():
            continue
        parts = line.split(sep, 1)
        if len(parts) != 2:  # noqa: PLR2004
            continue
        sha, subject = parts
        m = _CONV_RE.match(subject.strip())
        if m:
            task_ids = _TASK_RE.findall(subject)
            entries.append(CommitEntry(
                sha=sha[:8],
                type_=m.group("type"),
                scope=m.group("scope") or "",
                breaking=bool(m.group("breaking")),
                description=m.group("desc").strip(),
                task_ids=task_ids,
                raw=subject,
            ))
        else:
            # Non-conventional commit — file under "chore" so it isn't lost
            task_ids = _TASK_RE.findall(subject)
            entries.append(CommitEntry(
                sha=sha[:8],
                type_="chore",
                scope="",
                breaking=False,
                description=subject.strip(),
                task_ids=task_ids,
                raw=subject,
            ))
    return entries


def _render_changelog(version: str, entries: list[CommitEntry]) -> str:
    """Render entries as Markdown changelog section."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = [
        f"## [{version}] — {today}",
        "",
    ]

    breaking = [e for e in entries if e.breaking]
    if breaking:
        lines += ["### ⚠️  Breaking Changes", ""]
        for e in breaking:
            _append_entry(lines, e)
        lines.append("")

    by_type: dict[str, list[CommitEntry]] = defaultdict(list)
    for e in entries:
        by_type[e.type_].append(e)

    for type_key, label in _TYPE_LABELS.items():
        bucket = by_type.get(type_key, [])
        if not bucket:
            continue
        lines += [f"### {label}", ""]
        for e in bucket:
            _append_entry(lines, e)
        lines.append("")

    # Any unknown types
    known = set(_TYPE_LABELS.keys())
    for type_key, bucket in by_type.items():
        if type_key in known:
            continue
        lines += [f"### {type_key.capitalize()}", ""]
        for e in bucket:
            _append_entry(lines, e)
        lines.append("")

    return "\n".join(lines)


def _append_entry(lines: list[str], e: CommitEntry) -> None:
    scope_str = f"**{e.scope}**: " if e.scope else ""
    task_str = " ".join(f"`{t}`" for t in e.task_ids)
    suffix = f" {task_str}" if task_str else ""
    lines.append(f"- {scope_str}{e.description} ({e.sha}){suffix}")


def _latest_tag() -> str:
    """Return the most recent git tag, or the first commit if no tags exist."""
    try:
        return _git("describe", "--tags", "--abbrev=0")
    except RuntimeError:
        # Fall back to first commit
        try:
            return _git("rev-list", "--max-parents=0", "HEAD")
        except RuntimeError:
            return "HEAD~1"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate release notes from conventional commits")
    p.add_argument("--from", dest="from_ref", default=None, help="Start ref (default: latest tag)")
    p.add_argument("--to", dest="to_ref", default="HEAD", help="End ref (default: HEAD)")
    p.add_argument("--version", default="next", help="Release version label (default: next)")
    p.add_argument(
        "--output",
        default=None,
        help="Write changelog to this file (prepends if it already exists)",
    )
    return p


def main(argv: list[str] | None = None) -> int:  # noqa: FA100
    args = _build_parser().parse_args(argv)

    from_ref = args.from_ref or _latest_tag()
    print(f"[generate_release_notes] {from_ref}..{args.to_ref} → {args.version}", file=sys.stderr)

    entries = _parse_commits(from_ref, args.to_ref)
    if not entries:
        print("[generate_release_notes] No commits found in range.", file=sys.stderr)
        return 1

    changelog = _render_changelog(args.version, entries)
    print(changelog)

    if args.output:
        out_path = Path(args.output)
        existing = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        out_path.write_text(changelog + "\n\n" + existing, encoding="utf-8")
        print(f"[generate_release_notes] Written to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
