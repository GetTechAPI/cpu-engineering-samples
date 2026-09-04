"""``python -m app.ingest`` classifies JSON on stdin or a file path."""

from __future__ import annotations

import sys

from app.ingest.classify import main

if __name__ == "__main__":
    sys.exit(main())
