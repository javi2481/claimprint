#!/usr/bin/env python3
"""Write HITL review HTML from kernel claims. No RAGFlow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schemas.review import load_verdicts, write_review_pack
from schemas.store import load_claims


def main() -> int:
    parser = argparse.ArgumentParser(description="Paquete HTML de revisión HITL")
    parser.add_argument(
        "--verdicts",
        type=Path,
        default=None,
        help="JSON de veredictos (omitido = todo accept)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "review" / "index.html",
        help="HTML de salida (assets/ queda al lado)",
    )
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    claims, _cached = load_claims(force=args.refresh)
    verdicts = load_verdicts(args.verdicts)
    path = write_review_pack(args.out, claims, verdicts=verdicts)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
