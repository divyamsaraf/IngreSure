#!/usr/bin/env python3
"""Reproduce production vegan HTTP 500s on the deployed pre-IKE-2 commit.

Loads vegan500_samples.json plus synthetic percent / nested-paren / accent
labels. Runs preprocess + ComplianceEngine.evaluate(vegan) and prints the
first exception + traceback.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# This script is intended to be run with PYTHONPATH pointing at a worktree
# of ca34629^ (870f244). Current main removed ComplianceEngine.
from core.evaluation.compliance_engine import ComplianceEngine  # noqa: E402
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings  # noqa: E402

_HERE = Path(__file__).resolve()
_SAMPLES = _HERE.parent.parent / ".local_reports" / "vegan500_samples.json"

SYNTHETIC = [
    ("percent", "PEANUTS (49.5%), honey, salt"),
    ("min_percent", "wheat flour (min. 62%), water"),
    ("long_paren", "emulsifiers (acacia gum and sunflower lecithin (from sunflower (helianthus annuus))) and flavouring (natural peppermint oil (mentha piperita (leaf)))"),
    ("deep_paren", "a (" * 40 + "x" + ")" * 40),
    ("accents_de", "Reismehl, löslicher Ballaststoff: Oligofructose , Hydroxyprpylmethylcellulose (Kapselhülle)"),
    ("html_entity", 'Omega-3-Algenöl, MCT-ÖI&quot;, Bor retschöl&quot; (long paren nested (a (b (c))))'),
    ("mixed", "Water, diluent (xylitol), cholecalciferol (vitamin D3), emulsifiers (acacia gum and sunflower lecithin), acidity regulator (citric acid)."),
]


def _run_one(engine: ComplianceEngine, label: str, *, api: bool) -> str | None:
    try:
        parsed = preprocess_ingredients_to_strings(label)
    except Exception as e:  # noqa: BLE001
        return f"PARSE {type(e).__name__}: {e}\n{traceback.format_exc()}"
    try:
        engine.evaluate(
            ingredient_strings=parsed,
            restriction_ids=["vegan"],
            use_api_fallback=api,
        )
    except Exception as e:  # noqa: BLE001
        return f"EVAL parsed={parsed[:12]!r} {type(e).__name__}: {e}\n{traceback.format_exc()}"
    return None


def main() -> int:
    samples = []
    if _SAMPLES.exists():
        samples = json.loads(_SAMPLES.read_text(encoding="utf-8"))
    engine = ComplianceEngine()
    cases = [(s["code"], s["text"]) for s in samples] + SYNTHETIC
    print(f"commit probe: {os.getcwd()} api_fallback variants True/False n={len(cases)}")
    found = 0
    for api in (False, True):
        print(f"\n===== use_api_fallback={api} =====")
        for name, text in cases:
            err = _run_one(engine, text, api=api)
            if err:
                found += 1
                print(f"\nFAIL {name} api={api}\n{err}")
                if found >= 3:
                    return 1
            else:
                print(f"ok  {name} api={api} len={len(text)}")
    if found == 0:
        print("\nNo exception raised locally on parser+engine (both api flags).")
    return 0 if found == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
