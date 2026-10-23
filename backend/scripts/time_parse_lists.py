"""p50/p99/max per-list parse time over item44 (9,181) + regional dumps."""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from core.parsing.ingredient_parser import preprocess_ingredients_to_strings

_REPORTS = _BACKEND / ".local_reports"
_ITEM44 = _REPORTS / "item44_dump_ingredients.jsonl"
_REGION = _REPORTS / "region_dump_ingredients.jsonl"


def _texts(path: Path) -> list[str]:
    out = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = row.get("ingredients_text") or ""
        if text.strip():
            out.append(text)
    return out


def _pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(round((p / 100) * (len(xs) - 1)))))
    return xs[i]


def main() -> None:
    groups = {
        "item44": _texts(_ITEM44),
        "regional": _texts(_REGION),
    }
    print(f"{'set':10} {'n':>6} {'p50_ms':>8} {'p99_ms':>8} {'max_ms':>8}")
    all_ms: list[float] = []
    over: list[tuple[str, float, str]] = []
    for name, texts in groups.items():
        times = []
        for text in texts:
            t0 = time.perf_counter()
            preprocess_ingredients_to_strings(text)
            dt = (time.perf_counter() - t0) * 1000
            times.append(dt)
            if dt > 2000:
                over.append((name, dt, text[:80]))
        all_ms.extend(times)
        if times:
            print(
                f"{name:10} {len(times):6} {_pct(times,50):8.2f} "
                f"{_pct(times,99):8.2f} {max(times):8.2f}"
            )
        else:
            print(f"{name:10} {0:6} missing")
    if all_ms:
        print(
            f"{'all':10} {len(all_ms):6} {_pct(all_ms,50):8.2f} "
            f"{_pct(all_ms,99):8.2f} {max(all_ms):8.2f}  "
            f"mean={statistics.fmean(all_ms):.2f}"
        )
    if over:
        print(f"{len(over)} lists over 2s:")
        for name, dt, snippet in over[:10]:
            print(f"  {name} {dt:.0f}ms {snippet!r}")


if __name__ == "__main__":
    main()
