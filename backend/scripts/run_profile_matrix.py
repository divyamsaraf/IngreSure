"""CLI: paste × profiles → Safe/Avoid/Depends + evidence chains."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python backend/scripts/run_profile_matrix.py` from repo root.
_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.coverage_os.profile_matrix import run_matrix, write_matrix_csv
from core.knowledge.ike2.rules import SUPPORTED_RESTRICTIONS


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Coverage OS multi-profile matrix")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--paste", help="Raw ingredient paste string")
    src.add_argument("--file", type=Path, help="Path to paste text file")
    p.add_argument(
        "--restrictions",
        nargs="*",
        default=None,
        help="Restriction ids (default: all SUPPORTED_RESTRICTIONS)",
    )
    p.add_argument("--csv", type=Path, default=None, help="Optional CSV output path")
    p.add_argument("--json", type=Path, default=None, help="Optional JSON output path")
    p.add_argument(
        "--no-clear-caches",
        action="store_true",
        help="Skip L2 cache reset (default is clear at start of each run)",
    )
    args = p.parse_args(argv)

    raw = args.paste if args.paste is not None else Path(args.file).read_text(encoding="utf-8")
    restriction_ids = args.restrictions
    if restriction_ids is None:
        restriction_ids = sorted(SUPPORTED_RESTRICTIONS)

    rows = run_matrix(
        raw,
        restriction_ids=restriction_ids,
        clear_caches=not args.no_clear_caches,
    )
    if args.csv:
        write_matrix_csv(rows, args.csv)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    else:
        # Default: compact stdout lines for analyst scanning.
        for r in rows:
            print(f"{r['ingredient']}\t{r['profile']}\t{r['bucket']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
