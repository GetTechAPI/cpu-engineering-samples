"""Write ES JSON from a local table (JSON/JSONL). No network.

Rows that classify as qs/retail/unknown are skipped. Existing slugs are skipped.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from app.ingest.classify import CLASS_ES, classify

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "cpu"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

RECORD_KEYS = (
    "slug",
    "name",
    "manufacturer",
    "sample_class",
    "qspec",
    "opn",
    "stepping",
    "cpuid",
    "sample_revision",
    "retail_equivalent",
    "first_seen_date",
    "release_date",
    "segment",
    "architecture",
    "socket",
    "process_node",
    "cores",
    "threads",
    "p_cores",
    "e_cores",
    "base_clock_ghz",
    "boost_clock_ghz",
    "l3_cache_mb",
    "tdp_w",
    "max_tdp_w",
    "integrated_graphics",
    "memory_support",
    "msrp_usd",
    "verified",
    "markings",
    "notes",
    "source_urls",
)


def _kebab(value: str) -> str:
    text = value.strip().lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


def slug_for(row: dict[str, Any]) -> str:
    if isinstance(row.get("slug"), str) and row["slug"].strip():
        return _kebab(row["slug"])
    qspec = row.get("qspec")
    if isinstance(qspec, str) and qspec.strip():
        return "intel-" + _kebab(qspec)
    opn = row.get("opn")
    if isinstance(opn, str) and opn.strip():
        return "amd-" + _kebab(opn)
    raise ValueError("row needs slug, qspec, or opn")


def existing_slugs() -> set[str]:
    found: set[str] = set()
    if not DATA.exists():
        return found
    for path in DATA.rglob("*.json"):
        found.add(path.stem)
    return found


def load_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if path.suffix == ".jsonl" or text[:1] != "[":
        rows: list[dict[str, Any]] = []
        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_no} is not an object")
            rows.append(item)
        return rows
    payload = json.loads(text)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must be a JSON array or JSONL")
    return [item for item in payload if isinstance(item, dict)]


def _record(row: dict[str, Any], slug: str) -> dict[str, Any]:
    manufacturer = str(row.get("manufacturer") or "").strip().lower()
    name = str(row.get("name") or "").strip()
    if not name:
        ident = row.get("qspec") or row.get("opn") or slug
        brand = "Intel" if manufacturer == "intel" else "AMD"
        name = f"{brand} {ident} Engineering Sample"
    rec: dict[str, Any] = {key: row.get(key) for key in RECORD_KEYS}
    rec["slug"] = slug
    rec["name"] = name
    rec["manufacturer"] = manufacturer
    rec["sample_class"] = CLASS_ES
    rec["segment"] = str(row.get("segment") or "desktop").strip().lower()
    rec["verified"] = bool(row.get("verified", False))
    rec["source_urls"] = list(row.get("source_urls") or [])
    rec["markings"] = list(row.get("markings") or [])
    if manufacturer == "intel" and "Intel Confidential" not in rec["markings"]:
        rec["markings"].append("Intel Confidential")
    if manufacturer == "amd" and "AMD Eng Sample" not in rec["markings"]:
        rec["markings"].append("AMD Eng Sample")
    if rec.get("qspec") == "":
        rec["qspec"] = None
    if rec.get("opn") == "":
        rec["opn"] = None
    return rec


def output_path(rec: dict[str, Any], year: int) -> Path:
    return DATA / rec["manufacturer"] / str(year) / rec["segment"] / f"{rec['slug']}.json"


def ingest_rows(
    rows: list[dict[str, Any]],
    *,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    tallies: dict[str, list[str]] = {
        "written": [],
        "duplicate": [],
        "skipped-qs": [],
        "skipped-retail": [],
        "unknown": [],
        "invalid": [],
    }
    seen = existing_slugs()
    for row in rows:
        try:
            slug = slug_for(row)
        except ValueError as exc:
            tallies["invalid"].append(str(exc))
            continue
        if not SLUG_RE.match(slug):
            tallies["invalid"].append(f"{slug}: bad slug")
            continue
        if slug in seen:
            tallies["duplicate"].append(slug)
            continue
        manufacturer = str(row.get("manufacturer") or "").strip().lower()
        if manufacturer == "intel" and not row.get("qspec"):
            row = {**row, "qspec": slug.removeprefix("intel-").upper()}
        candidate = {
            **row,
            "slug": slug,
            "name": row.get("name") or f"{slug} engineering sample",
            "sample_class": "es",
        }
        result = classify(candidate)
        if result.sample_class != CLASS_ES:
            key = {
                "qs": "skipped-qs",
                "retail": "skipped-retail",
            }.get(result.sample_class, "unknown")
            tallies[key].append(f"{slug}:{result.sample_class}")
            continue
        year = int(row.get("year") or str(row.get("first_seen_date") or "1970")[:4])
        rec = _record(row, slug)
        if result.sample_revision and not rec.get("sample_revision"):
            rec["sample_revision"] = result.sample_revision
        path = output_path(rec, year)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        seen.add(slug)
        tallies["written"].append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return tallies


def print_summary(tallies: dict[str, list[str]]) -> None:
    for key in (
        "written",
        "duplicate",
        "skipped-qs",
        "skipped-retail",
        "unknown",
        "invalid",
    ):
        items = tallies[key]
        print(f"{key}: {len(items)}")
        for item in items[:30]:
            print(f"  {item}")
        if len(items) > 30:
            print(f"  … {len(items) - 30} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest ES rows from a local JSON/JSONL table.")
    parser.add_argument("table", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    rows = load_rows(args.table)
    tallies = ingest_rows(rows, dry_run=args.dry_run)
    print_summary(tallies)
    return 0 if not tallies["invalid"] else 1


if __name__ == "__main__":
    sys.exit(main())
