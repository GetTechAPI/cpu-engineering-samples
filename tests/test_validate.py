"""Validator accepts ES records and rejects QS / retail."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from app import validate

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "data" / "cpu" / "intel" / "2021" / "desktop" / "intel-qxlb.json"


def _seed() -> dict:
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_seed_catalog_passes() -> None:
    errors = validate.validate()
    assert errors == []


def test_qs_sample_class_rejected() -> None:
    rec = _seed()
    rec["sample_class"] = "qs"
    rec["qspec"] = "QDF4"
    rec["slug"] = "intel-qdf4"
    errors = validate.validate([("data/cpu/intel/2023/desktop/intel-qdf4.json", rec)])
    assert any("forbidden" in err or "qs" in err.lower() for err in errors)


def test_retail_sample_class_rejected() -> None:
    rec = _seed()
    rec["sample_class"] = "retail"
    rec["slug"] = "core-i9-12900k"
    rec["name"] = "Intel Core i9-12900K"
    errors = validate.validate(
        [("data/cpu/intel/2021/desktop/core-i9-12900k.json", rec)]
    )
    assert any("forbidden" in err or "retail" in err.lower() for err in errors)


def test_production_sample_class_rejected() -> None:
    rec = _seed()
    rec["sample_class"] = "production"
    errors = validate.validate([("data/cpu/intel/2021/desktop/intel-qxlb.json", rec)])
    assert any("forbidden" in err for err in errors)


def test_missing_sample_class_rejected() -> None:
    rec = _seed()
    del rec["sample_class"]
    errors = validate.validate([("data/cpu/intel/2021/desktop/intel-qxlb.json", rec)])
    assert any("sample_class" in err for err in errors)


def test_missing_identifier_rejected() -> None:
    rec = _seed()
    rec["qspec"] = None
    rec["opn"] = None
    errors = validate.validate([("data/cpu/intel/2021/desktop/intel-qxlb.json", rec)])
    assert any("qspec" in err and "opn" in err for err in errors)


def test_unknown_manufacturer_rejected() -> None:
    rec = copy.deepcopy(_seed())
    rec["manufacturer"] = "contoso"
    errors = validate.validate(
        [("data/cpu/contoso/2021/desktop/intel-qxlb.json", rec)]
    )
    assert any("manufacturer" in err for err in errors)
