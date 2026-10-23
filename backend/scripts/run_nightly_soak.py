#!/usr/bin/env python3
"""Item 58 nightly soak entrypoint.

Runs backend/scripts/soak_evaluate.py when that file is present.
Otherwise prints the documented command and exits 0 so CI can land
before the soak script is merged.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_SOAK = _SCRIPTS / "soak_evaluate.py"

DOCUMENTED_COMMAND = "python backend/scripts/soak_evaluate.py"


def main() -> int:
    if not _SOAK.is_file():
        print("SOAK SKIP: backend/scripts/soak_evaluate.py is not present.")
        print(f"Documented command: {DOCUMENTED_COMMAND}")
        print("See backend/scripts/README_soak_metrics.md")
        return 0
    print(f"SOAK RUN: {_SOAK}")
    try:
        runpy.run_path(str(_SOAK), run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return int(code) if not isinstance(code, bool) else int(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
