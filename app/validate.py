"""Validate engineering-sample CPU JSON.

Hard rule: this catalog accepts ``sample_class == "es"`` only.
QS, retail, and production records must fail. Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cpu"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YEAR_RE = re.compile(r"^\d{4}$")

ALLOWED_SAMPLE_CLASS = {"es"}
FORBIDDEN_SAMPLE_CLASS = {
    "qs",
    "qualification",
    "retail",
    "production",
    "qs-retail",
    "qs_retail",
    "engineering-and-qs",
}
MANUFACTURERS = {"intel", "amd"}
SEGMENTS = {"desktop", "laptop", "hedt", "server"}
SAMPLE_REVISIONS = {"es1", "es2"}

REQUIRED = {
    "slug",
    "name",
    "manufacturer",
    "sample_class",
    "architecture",
    "cores",
    "threads",
    "source_urls",
}


def _load() -> list[tuple[str, dict[str, Any]]]:
    if not DATA_DIR.exists():
        return []
    records: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(DATA_DIR.rglob("*.json")):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        records.append((rel, json.loads(path.read_text(encoding="utf-8-sig"))))
    return records


def _check_required(name: str, record: dict[str, Any], errors: list[str]) -> None:
    missing = REQUIRED - record.keys()
    if missing:
        errors.append(f"{name}: missing required fields {sorted(missing)}")


def _check_slug(name: str, slug: object, errors: list[str]) -> None:
    if not isinstance(slug, str) or not SLUG_RE.match(slug):
        errors.append(f"{name}: invalid slug '{slug}' (must be kebab-case)")


def _check_date(name: str, field: str, value: object, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not DATE_RE.match(value):
        errors.append(f"{name}: {field} '{value}' is not YYYY-MM-DD")


def _check_range(
    name: str, field: str, value: object, lo: float, hi: float, errors: list[str]
) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{name}: {field} must be a number")
        return
    if value < lo or value > hi:
        errors.append(f"{name}: {field} {value} out of range {lo}..{hi}")


def _check_source_urls(name: str, record: dict[str, Any], errors: list[str]) -> None:
    urls = record.get("source_urls")
    if not isinstance(urls, list) or not urls:
        errors.append(f"{name}: source_urls must be a non-empty list")
        return
    for url in urls:
        if not isinstance(url, str) or not url.startswith("http"):
            errors.append(f"{name}: invalid source url '{url}'")


def _check_sample_class(name: str, record: dict[str, Any], errors: list[str]) -> None:
    sample_class = record.get("sample_class")
    if not isinstance(sample_class, str):
        errors.append(f"{name}: sample_class is required and must be 'es'")
        return
    lowered = sample_class.strip().lower()
    if lowered in FORBIDDEN_SAMPLE_CLASS:
        errors.append(
            f"{name}: sample_class '{sample_class}' is forbidden "
            "(QS / retail / production belong in TechAPI, not here)"
        )
        return
    if lowered not in ALLOWED_SAMPLE_CLASS:
        errors.append(f"{name}: sample_class '{sample_class}' must be 'es'")


def _check_identifiers(name: str, record: dict[str, Any], errors: list[str]) -> None:
    qspec = record.get("qspec")
    opn = record.get("opn")
    has_qspec = isinstance(qspec, str) and qspec.strip()
    has_opn = isinstance(opn, str) and opn.strip()
    if not has_qspec and not has_opn:
        errors.append(f"{name}: need qspec (Intel) and/or opn (AMD)")


def _check_path(name: str, record: dict[str, Any], errors: list[str]) -> None:
    # data/cpu/<manufacturer>/<year>/<segment>/<slug>.json
    parts = name.split("/")
    if len(parts) != 6 or parts[0] != "data" or parts[1] != "cpu":
        errors.append(
            f"{name}: path must be data/cpu/<manufacturer>/<year>/<segment>/<slug>.json"
        )
        return
    _, _, manufacturer, year, segment, filename = parts
    slug = record.get("slug")
    if filename != f"{slug}.json":
        errors.append(f"{name}: filename does not match slug '{slug}'")
    if manufacturer != record.get("manufacturer"):
        errors.append(f"{name}: folder manufacturer does not match record")
    if not YEAR_RE.match(year):
        errors.append(f"{name}: year folder '{year}' is not YYYY")
    if segment != record.get("segment"):
        errors.append(f"{name}: folder segment does not match record")


def validate(records: list[tuple[str, dict[str, Any]]] | None = None) -> list[str]:
    records = _load() if records is None else records
    errors: list[str] = []
    slugs: dict[str, str] = {}

    if not records:
        errors.append("no ES CPU records found under data/cpu/")
        return errors

    for name, rec in records:
        if not isinstance(rec, dict):
            errors.append(f"{name}: JSON root must be an object")
            continue
        _check_required(name, rec, errors)
        _check_slug(name, rec.get("slug"), errors)
        _check_sample_class(name, rec, errors)
        _check_identifiers(name, rec, errors)
        _check_source_urls(name, rec, errors)
        _check_path(name, rec, errors)
        _check_date(name, "first_seen_date", rec.get("first_seen_date"), errors)
        _check_date(name, "release_date", rec.get("release_date"), errors)
        _check_range(name, "cores", rec.get("cores"), 1, 512, errors)
        _check_range(name, "threads", rec.get("threads"), 1, 1024, errors)
        _check_range(name, "base_clock_ghz", rec.get("base_clock_ghz"), 0.1, 8, errors)
        _check_range(name, "boost_clock_ghz", rec.get("boost_clock_ghz"), 0.1, 10, errors)
        _check_range(name, "tdp_w", rec.get("tdp_w"), 1, 3000, errors)

        manufacturer = rec.get("manufacturer")
        if manufacturer not in MANUFACTURERS:
            errors.append(
                f"{name}: manufacturer '{manufacturer}' not in {sorted(MANUFACTURERS)}"
            )
        segment = rec.get("segment")
        if segment not in SEGMENTS:
            errors.append(f"{name}: segment '{segment}' not in {sorted(SEGMENTS)}")
        revision = rec.get("sample_revision")
        if revision is not None and revision not in SAMPLE_REVISIONS:
            errors.append(
                f"{name}: sample_revision '{revision}' not in {sorted(SAMPLE_REVISIONS)}"
            )

        slug = rec.get("slug")
        if isinstance(slug, str):
            if slug in slugs:
                errors.append(f"{name}: duplicate slug '{slug}' (also {slugs[slug]})")
            else:
                slugs[slug] = name

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"{len(errors)} validation error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("OK: all ES CPU records passed (QS/retail excluded by schema).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
