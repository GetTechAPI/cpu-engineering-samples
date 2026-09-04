"""Offline ES / QS / retail classifier.

No network. A candidate must be ``es`` before the ingest pipeline may write JSON.
QS and retail belong in TechAPI or nowhere; ``unknown`` goes to a review issue.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CLASS_ES = "es"
CLASS_QS = "qs"
CLASS_RETAIL = "retail"
CLASS_UNKNOWN = "unknown"

# Intel production S-spec: 5 letters starting with S (e.g. SRKNY).
_SSPEC_RE = re.compile(r"^S[A-Z0-9]{4}$")
# Intel sample QDF / Q-spec: 4–6 letters starting with Q (e.g. QXLB, QDF4).
_QSPEC_RE = re.compile(r"^Q[A-Z0-9]{3,5}$")
# Zen 4+ engineering OPN, e.g. 100-000000665-21_N
_AMD_MODERN_OPN_RE = re.compile(
    r"^100-0+\d+(?:-\d+)?(?:_[A-Z0-9]+)?$", re.IGNORECASE
)

_ES_STEPPINGS = {"A0", "B0", "G0"}
_QS_STEPPINGS = {"C0", "H0"}

_QS_PHRASES = (
    "qualification sample",
    "qualification-sample",
    " qs ",
    "(qs)",
    "[qs]",
)
_ES_PHRASES = (
    "engineering sample",
    "eng sample",
    "eng. sample",
    "intel confidential",
)
_RETAIL_PHRASES = ("retail", "production sku", "production part")


@dataclass(frozen=True)
class Classification:
    """Result of classifying one candidate. ``sample_class`` is never empty."""

    sample_class: str
    reasons: tuple[str, ...]
    sample_revision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _upper(value: object) -> str:
    return _norm(value).upper()


def _blob(candidate: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "slug", "notes", "sample_class"):
        parts.append(_norm(candidate.get(key)))
    markings = candidate.get("markings")
    if isinstance(markings, list):
        parts.extend(_norm(m) for m in markings)
    labels = candidate.get("source_labels")
    if isinstance(labels, list):
        parts.extend(_norm(label) for label in labels)
    return " ".join(parts).lower()


def _has_phrase(blob: str, phrases: tuple[str, ...]) -> str | None:
    padded = f" {blob} "
    for phrase in phrases:
        if phrase in padded or phrase.strip() in blob:
            return phrase.strip()
    return None


def _intel_qspec(candidate: dict[str, Any]) -> str:
    qspec = _upper(candidate.get("qspec"))
    if _QSPEC_RE.match(qspec):
        return qspec
    return ""


def _intel_sspec(candidate: dict[str, Any]) -> str:
    for key in ("sspec", "s_spec"):
        sspec = _upper(candidate.get(key))
        if _SSPEC_RE.match(sspec):
            return sspec
    return ""


def _amd_opn(candidate: dict[str, Any]) -> str:
    return _norm(candidate.get("opn")).replace(" ", "")


def _clock_far_below_retail(candidate: dict[str, Any]) -> bool:
    base = candidate.get("base_clock_ghz")
    retail = candidate.get("retail_base_clock_ghz")
    if not isinstance(base, (int, float)) or isinstance(base, bool):
        return False
    if isinstance(retail, (int, float)) and not isinstance(retail, bool):
        return base <= retail * 0.6
    # Early Intel ES desktop parts often ship a ~1.x GHz fuse default.
    return base <= 1.5


def _clocks_match_retail(candidate: dict[str, Any]) -> bool:
    base = candidate.get("base_clock_ghz")
    retail = candidate.get("retail_base_clock_ghz")
    if not isinstance(base, (int, float)) or not isinstance(retail, (int, float)):
        return False
    if isinstance(base, bool) or isinstance(retail, bool):
        return False
    return abs(base - retail) <= 0.15


def _classify_intel(candidate: dict[str, Any], blob: str) -> Classification:
    sspec = _intel_sspec(candidate)
    if sspec:
        return Classification(
            CLASS_RETAIL, (f"Intel S-spec {sspec} is a production part",)
        )

    qspec = _intel_qspec(candidate)
    qs_phrase = _has_phrase(blob, _QS_PHRASES)
    es_phrase = _has_phrase(blob, _ES_PHRASES)
    stepping = _upper(candidate.get("stepping"))

    if not qspec:
        if _has_phrase(blob, _RETAIL_PHRASES) or (
            "core i" in blob and "sample" not in blob
        ):
            return Classification(
                CLASS_RETAIL, ("Intel retail model name with no Q-spec",)
            )
        return Classification(CLASS_UNKNOWN, ("Intel candidate has no Q-spec or S-spec",))

    reasons: list[str] = [f"Intel Q-spec {qspec}"]
    es_hits = 0
    qs_hits = 0

    if stepping in _ES_STEPPINGS:
        es_hits += 1
        reasons.append(f"early stepping {stepping}")
    if stepping in _QS_STEPPINGS:
        qs_hits += 1
        reasons.append(f"mature stepping {stepping}")
    if _clock_far_below_retail(candidate):
        es_hits += 1
        reasons.append("base clock far below retail")
    if _clocks_match_retail(candidate):
        qs_hits += 1
        reasons.append("clocks match retail equivalent")
    if es_phrase:
        es_hits += 1
        reasons.append(f"source text {es_phrase!r}")
    if qs_phrase:
        qs_hits += 1
        reasons.append(f"source text {qs_phrase!r}")

    if qs_hits > es_hits:
        return Classification(CLASS_QS, tuple(reasons))
    if es_hits > 0 and es_hits >= qs_hits:
        return Classification(CLASS_ES, tuple(reasons), sample_revision="es1")
    return Classification(
        CLASS_UNKNOWN,
        tuple(reasons + ["not enough ES/QS evidence"]),
    )


def _classify_amd(candidate: dict[str, Any], blob: str) -> Classification:
    opn = _amd_opn(candidate)
    qs_phrase = _has_phrase(blob, _QS_PHRASES)
    es_phrase = _has_phrase(blob, _ES_PHRASES)

    if qs_phrase:
        return Classification(
            CLASS_QS, (f"source text {qs_phrase!r}", f"opn={opn or 'n/a'}")
        )

    if opn:
        compact = opn.replace("_", "-")
        if _AMD_MODERN_OPN_RE.match(opn):
            reasons = [f"AMD modern OPN {opn}"]
            if es_phrase:
                reasons.append(f"source text {es_phrase!r}")
            return Classification(CLASS_ES, tuple(reasons), sample_revision="es1")
        prefix = compact[:1].upper()
        if prefix == "Z":
            return Classification(CLASS_QS, (f"AMD OPN prefix Z ({opn})",))
        if prefix == "1":
            return Classification(
                CLASS_ES, (f"AMD historical ES1 OPN {opn}",), sample_revision="es1"
            )
        if prefix == "2":
            return Classification(
                CLASS_ES, (f"AMD historical ES2 OPN {opn}",), sample_revision="es2"
            )

    if es_phrase:
        return Classification(
            CLASS_ES, (f"source text {es_phrase!r}",), sample_revision="es1"
        )
    if opn:
        return Classification(CLASS_UNKNOWN, (f"AMD OPN {opn} has no ES/QS evidence",))
    return Classification(CLASS_UNKNOWN, ("AMD candidate has no OPN",))


def classify(candidate: dict[str, Any]) -> Classification:
    """Return es / qs / retail / unknown for one candidate dict."""
    blob = _blob(candidate)
    manufacturer = _norm(candidate.get("manufacturer")).lower()

    declared = _norm(candidate.get("sample_class")).lower()
    if declared in {CLASS_QS, "qualification"}:
        return Classification(CLASS_QS, ("declared sample_class is qs",))
    if declared in {CLASS_RETAIL, "production"}:
        return Classification(CLASS_RETAIL, ("declared sample_class is retail/production",))

    if manufacturer == "intel":
        return _classify_intel(candidate, blob)
    if manufacturer == "amd":
        return _classify_amd(candidate, blob)

    if _has_phrase(blob, _QS_PHRASES):
        return Classification(CLASS_QS, ("source text indicates QS",))
    if _has_phrase(blob, _ES_PHRASES):
        return Classification(CLASS_ES, ("source text indicates ES",), sample_revision="es1")
    return Classification(
        CLASS_UNKNOWN, (f"unsupported manufacturer '{manufacturer or 'missing'}'",)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify a CPU candidate as es, qs, retail, or unknown."
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="JSON file (object or list of objects). Reads stdin if omitted.",
    )
    args = parser.parse_args(argv)

    if args.path:
        raw = Path(args.path).read_text(encoding="utf-8-sig")
    else:
        raw = sys.stdin.read()
    payload: Any = json.loads(raw)
    items = payload if isinstance(payload, list) else [payload]
    results = [classify(item).to_dict() for item in items]
    json.dump(results if isinstance(payload, list) else results[0], sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
