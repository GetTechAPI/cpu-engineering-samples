"""Build a static catalog.json from ES CPU records."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "cpu"
OUT = Path(__file__).resolve().parent / "catalog.json"
HISTORY = Path(__file__).resolve().parent / "history.json"
SUMMARY = Path(__file__).resolve().parent / "summary.json"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def build_history() -> list[dict]:
    """Record count after every commit that touched data/cpu (needs full clone)."""
    points = []
    for line in git("log", "--reverse", "--format=%H %cI", "--", "data/cpu").splitlines():
        sha, date = line.split(" ", 1)
        names = git("ls-tree", "-r", "--name-only", sha, "--", "data/cpu").splitlines()
        points.append({"sha": sha, "date": date, "count": sum(n.endswith(".json") for n in names)})
    return points


def main() -> int:
    records: list[dict] = []
    for path in sorted(DATA.rglob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8-sig"))
        records.append(
            {
                "slug": rec["slug"],
                "name": rec["name"],
                "manufacturer": rec["manufacturer"],
                "sample_class": rec["sample_class"],
                "qspec": rec.get("qspec"),
                "opn": rec.get("opn"),
                "stepping": rec.get("stepping"),
                "architecture": rec.get("architecture"),
                "cores": rec.get("cores"),
                "threads": rec.get("threads"),
                "retail_equivalent": rec.get("retail_equivalent"),
                "first_seen_date": rec.get("first_seen_date"),
                "source_urls": rec.get("source_urls", []),
            }
        )
    OUT.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(records)} ES records)")
    # TechAPI's homepage counts satellites from summary.json rather than by
    # downloading a record listing — game-catalog is ~1M records, so reading
    # a catalog's .length stopped being viable there.
    summary = {
        "count": len(records),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SUMMARY} ({len(records)} records)")
    history = build_history()
    HISTORY.write_text(json.dumps({"points": history}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {HISTORY} ({len(history)} points)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
