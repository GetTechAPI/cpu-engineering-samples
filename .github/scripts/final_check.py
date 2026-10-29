"""Render TechEngineBot's final-check comment for a PR.

Reads the validator / test outcomes from the environment and summarises the
ES records the PR touches. Prints Markdown to stdout. Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKER = "<!-- techenginebot:final-check -->"
ICON = {"success": "✅", "failure": "❌", "skipped": "⏭️", "cancelled": "⏹️"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def changed_records(base: str, head: str) -> list[tuple[str, str]]:
    """(status, path) for every data/cpu JSON the PR adds, modifies, or removes."""
    out = git("diff", "--name-status", "--no-renames", f"{base}...{head}", "--", "data/cpu")
    rows = []
    for line in out.splitlines():
        status, path = line.split("\t", 1)
        if path.endswith(".json"):
            rows.append((status[0], path))
    return rows


def describe(path: str) -> str:
    try:
        rec = json.loads((ROOT / path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return f"`{path}` (unreadable: {exc})"
    ident = rec.get("qspec") or rec.get("opn") or "—"
    sources = len(rec.get("source_urls") or [])
    return (
        f"`{rec.get('slug')}` · {ident} · {rec.get('architecture')} · "
        f"{rec.get('cores')}C/{rec.get('threads')}T · class `{rec.get('sample_class')}` · "
        f"{sources} source(s)"
    )


def main() -> int:
    validate = os.environ.get("VALIDATE_OUTCOME", "skipped")
    tests = os.environ.get("TESTS_OUTCOME", "skipped")
    base = os.environ["BASE_SHA"]
    head = os.environ["HEAD_SHA"]
    passed = validate == "success" and tests == "success"

    rows = changed_records(base, head)
    added = [p for s, p in rows if s == "A"]
    modified = [p for s, p in rows if s == "M"]
    removed = [p for s, p in rows if s == "D"]

    lines = [
        MARKER,
        "## Final check",
        "",
        "**✅ Ready to merge**" if passed else "**❌ Not ready — fix the failing checks below**",
        "",
        f"- {ICON.get(validate, '❔')} `python -m app.validate`",
        f"- {ICON.get(tests, '❔')} `python -m pytest -q`",
        "",
        f"**Records:** +{len(added)} added · ~{len(modified)} modified · −{len(removed)} removed",
    ]
    for title, paths in (("Added", added), ("Modified", modified)):
        if paths:
            lines += ["", f"<details><summary>{title} ({len(paths)})</summary>", ""]
            lines += [f"- {describe(p)}" for p in paths]
            lines += ["", "</details>"]
    if removed:
        lines += ["", f"<details><summary>Removed ({len(removed)})</summary>", ""]
        lines += [f"- `{p}`" for p in removed]
        lines += ["", "</details>"]
    lines += ["", f"<sub>Checked at {head[:7]}. This comment is updated in place on every push.</sub>"]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
