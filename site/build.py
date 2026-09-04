"""Build a static catalog.json from ES CPU records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "cpu"
OUT = Path(__file__).resolve().parent / "catalog.json"


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
