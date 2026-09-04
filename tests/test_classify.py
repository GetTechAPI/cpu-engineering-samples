"""Known public identifiers: QXLB=es, QDF4=qs, 12900K=retail, Raphael OPN=es."""

from __future__ import annotations

from app.ingest.classify import classify


def test_intel_qxlb_is_es() -> None:
    result = classify(
        {
            "manufacturer": "intel",
            "qspec": "QXLB",
            "stepping": "B0",
            "base_clock_ghz": 1.2,
            "retail_base_clock_ghz": 3.2,
            "name": "Intel QXLB Engineering Sample",
            "markings": ["Intel Confidential"],
        }
    )
    assert result.sample_class == "es"
    assert result.sample_revision == "es1"


def test_intel_qdf4_is_qs() -> None:
    result = classify(
        {
            "manufacturer": "intel",
            "qspec": "QDF4",
            "stepping": "C0",
            "base_clock_ghz": 3.2,
            "retail_base_clock_ghz": 3.2,
            "name": "i9-14900K QS",
            "source_labels": ["qs"],
        }
    )
    assert result.sample_class == "qs"


def test_intel_s_spec_is_retail() -> None:
    result = classify(
        {
            "manufacturer": "intel",
            "sspec": "SRKNY",
            "name": "Intel Core i9-14900K",
        }
    )
    assert result.sample_class == "retail"


def test_intel_retail_model_without_qspec() -> None:
    result = classify(
        {
            "manufacturer": "intel",
            "name": "Intel Core i9-12900K",
            "slug": "core-i9-12900k",
        }
    )
    assert result.sample_class == "retail"


def test_intel_qspec_without_evidence_is_unknown() -> None:
    result = classify({"manufacturer": "intel", "qspec": "QZZZ"})
    assert result.sample_class == "unknown"


def test_amd_raphael_opn_is_es() -> None:
    result = classify(
        {
            "manufacturer": "amd",
            "opn": "100-000000665-21_N",
            "name": "AMD Eng Sample 100-000000665-21_N",
        }
    )
    assert result.sample_class == "es"


def test_amd_z_prefix_is_qs() -> None:
    result = classify(
        {
            "manufacturer": "amd",
            "opn": "ZS188159TGG54",
            "name": "AMD qualification sample",
        }
    )
    assert result.sample_class == "qs"


def test_amd_historical_es1_prefix() -> None:
    result = classify({"manufacturer": "amd", "opn": "1S160805L4BGC"})
    assert result.sample_class == "es"
    assert result.sample_revision == "es1"


def test_amd_historical_es2_prefix() -> None:
    result = classify({"manufacturer": "amd", "opn": "2S160805L4BGC"})
    assert result.sample_class == "es"
    assert result.sample_revision == "es2"


def test_declared_qs_wins() -> None:
    result = classify(
        {
            "manufacturer": "intel",
            "qspec": "QXLB",
            "sample_class": "qs",
        }
    )
    assert result.sample_class == "qs"


def test_declared_retail_wins() -> None:
    result = classify(
        {
            "manufacturer": "amd",
            "opn": "100-000000665-21_N",
            "sample_class": "retail",
        }
    )
    assert result.sample_class == "retail"


def test_seed_qxlb_file_classifies_es() -> None:
    from pathlib import Path
    import json

    path = Path("data/cpu/intel/2021/desktop/intel-qxlb.json")
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert classify(rec).sample_class == "es"
