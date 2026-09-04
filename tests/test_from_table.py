"""from_table writes ES only and skips QS/retail/unknown."""

from __future__ import annotations

import json
from pathlib import Path

from app.ingest.from_table import ingest_rows, slug_for


def test_slug_from_qspec() -> None:
    assert slug_for({"qspec": "QX7H"}) == "intel-qx7h"


def test_slug_from_opn() -> None:
    assert slug_for({"opn": "100-000000665-21_N"}) == "amd-100-000000665-21-n"


def test_ingest_skips_qs_and_writes_es(monkeypatch) -> None:
    import app.ingest.from_table as mod

    tmp_path = Path("tests/.tmp-from-table")
    if tmp_path.exists():
        import shutil

        shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "DATA", tmp_path)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    rows = [
        {
            "manufacturer": "intel",
            "qspec": "QZZA",
            "stepping": "B0",
            "base_clock_ghz": 1.2,
            "name": "Intel QZZA Engineering Sample",
            "year": 2021,
            "segment": "desktop",
            "architecture": "Alder Lake",
            "cores": 16,
            "threads": 24,
            "source_urls": ["https://example.com/es"],
        },
        {
            "manufacturer": "intel",
            "qspec": "QDF4",
            "stepping": "C0",
            "base_clock_ghz": 3.2,
            "retail_base_clock_ghz": 3.2,
            "name": "i9-14900K QS",
            "source_labels": ["qs"],
            "year": 2023,
            "segment": "desktop",
            "architecture": "Raptor Lake",
            "cores": 24,
            "threads": 32,
            "source_urls": ["https://example.com/qs"],
        },
    ]
    tallies = ingest_rows(rows)
    assert any("intel-qzza" in path for path in tallies["written"])
    assert tallies["skipped-qs"]
    written = tmp_path / "intel" / "2021" / "desktop" / "intel-qzza.json"
    rec = json.loads(written.read_text(encoding="utf-8"))
    assert rec["sample_class"] == "es"
    assert rec["qspec"] == "QZZA"
    import shutil

    shutil.rmtree(tmp_path, ignore_errors=True)
