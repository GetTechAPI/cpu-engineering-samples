"""ES intake: classify public identifiers before any JSON is written."""

from app.ingest.classify import Classification, classify

__all__ = ["Classification", "classify"]
