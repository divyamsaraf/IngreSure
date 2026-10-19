#!/usr/bin/env python3
"""Rerun Item 44 metrics with the fixed parser on cached OFF texts.

Uses local product cache (no live search). Writes
``backend/.local_reports/item44_rerun_fixed_parser.json``.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "scripts"))

from dotenv import load_dotenv

load_dotenv(_REPO / ".env")
load_dotenv(_BACKEND / ".env")

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.normalization.parser import flatten_ingredients
from item44_label_benchmark import PROFILES, _IDS_PATH, _layer_bucket
from item44_pilot_evidence import (
    _FREQ_PATH,
    _FREQ_PROGRESS,
    _PRODUCT_CACHE,
    _RESOLVE_MEMO,
    _load_product_cache,
    _resolve_atom,
    accumulate_freq_from_ids,
    oos_promotion,
    staples_top40,
)

_OUT = _BACKEND / ".local_reports" / "item44_rerun_fixed_parser.json"
_FREQ_PROGRESS_DUMP = _BACKEND / ".local_reports" / "item44_freq_scan_progress_dump.json"
_AMBIGUOUS = (
    "natural flavors",
    "natural flavour",
    "natural flavouring",
    "artificial flavors",
    "spices",
    "spice",
    "seasoning",
    "seasonings",
    "colors",
    "colours",
    "color",
    "colour",
    "flavor",
    "flavour",
    "flavors",
    "flavours",
)


def _cache_by_code() -> dict[str, dict]:
    _load_product_cache()
    by = {}
    for k, v in _PRODUCT_CACHE.items():
        if not v:
            continue
        code = str(v.get("code") or k.split("|", 1)[0])
        if code and (v.get("ingredients_text") or "").strip():
            by[code] = v
    return by


def _eval_atoms(atoms: list[str], restrictions: dict, *, raw_label: str | None = None) -> str:
    cis = [to_compliance_input(resolve(a, None), query_atom=a) for a in atoms]
    return to_external(
        evaluate(
            cis,
            SimpleNamespace(restrictions=restrictions),
            rules_module.seeded_rules(),
            raw_label=raw_label,
            parsed_atoms=atoms,
        ).verdict
    )


def main() -> int:
    cache.clear()
    _RESOLVE_MEMO.clear()
    by_code = _cache_by_code()
    held = json.loads(_IDS_PATH.read_text(encoding="utf-8"))
    freq_ids = json.loads(_FREQ_PATH.read_text(encoding="utf-8"))
    held_codes = {p["code"] for p in held.get("products") or []}
    freq_codes = {p["code"] for p in freq_ids.get("products") or []}
    overlap = held_codes & freq_codes
    held_with_text = sum(1 for c in held_codes if c in by_code)
    print(
        f"parser=flatten_ingredients(fixed) cache={len(by_code)} "
        f"held={len(held_codes)} held_with_text={held_with_text} "
        f"freq_ids={len(freq_codes)} overlap={len(overlap)}",
        flush=True,
    )

    # --- held-out profile rates + layer shares ---
    profile_counts = {p: Counter() for p in PROFILES}
    layer_by_market = defaultdict(Counter)
    layer_instances = Counter()
    safe_rows = []
    ambiguous_in_safe = []

    for meta in held.get("products") or []:
        prod = by_code.get(meta["code"])
        if not prod:
            continue
        raw = (prod.get("ingredients_text") or "").strip()
        atoms = [a for a in flatten_ingredients(raw) if a]
        if not atoms:
            continue
        layers = {}
        for a in atoms:
            info = _resolve_atom(a)
            layers[a.lower()] = info["layer_bucket"]
            layer_by_market[meta["market"]][info["layer_bucket"]] += 1
            layer_instances[info["layer_bucket"]] += 1
        for pname, restrictions in PROFILES.items():
            v = _eval_atoms(atoms, restrictions, raw_label=raw)
            profile_counts[pname][v] += 1
            if v == "SAFE":
                ambig = []
                for a in atoms:
                    al = a.lower()
                    if any(x in al for x in _AMBIGUOUS) or al in _AMBIGUOUS:
                        info = _resolve_atom(a)
                        # per-profile: re-eval single atom under this profile
                        av = _eval_atoms([a], restrictions)
                        ambig.append(
                            {
                                "atom": a,
                                "layer": info["layer_bucket"],
                                "trusted": info["trusted"],
                                "flags": info["flags"],
                                "atom_verdict": av,
                            }
                        )
                if ambig:
                    ambiguous_in_safe.append(
                        {
                            "code": meta["code"],
                            "market": meta["market"],
                            "profile": pname,
                            "ambiguous": ambig,
                            "all_atoms": atoms,
                        }
                    )
                safe_rows.append(
                    {
                        "code": meta["code"],
                        "market": meta["market"],
                        "profile": pname,
                        "n_atoms": len(atoms),
                        "layers": layers,
                    }
                )

    # --- OOS from dump-based freq progress when present, else legacy ---
    freq_source = None
    if _FREQ_PROGRESS_DUMP.exists():
        freq = Counter(
            json.loads(_FREQ_PROGRESS_DUMP.read_text(encoding="utf-8")).get("freq") or {}
        )
        freq_source = str(_FREQ_PROGRESS_DUMP)
    elif _FREQ_PROGRESS.exists():
        freq = Counter(json.loads(_FREQ_PROGRESS.read_text(encoding="utf-8")).get("freq") or {})
        freq_source = str(_FREQ_PROGRESS)
    else:
        train = [p for p in freq_ids.get("products") or [] if p["code"] not in held_codes]
        freq, _ = accumulate_freq_from_ids(train, resolve_layers=False, progress_path=_FREQ_PROGRESS)
        freq_source = "accumulate_freq_from_ids"

    held_cached = []
    for meta in held.get("products") or []:
        prod = by_code.get(meta["code"])
        if not prod:
            continue
        atoms = [a for a in flatten_ingredients((prod.get("ingredients_text") or "")) if a]
        layers = {a.lower(): _resolve_atom(a)["layer_bucket"] for a in atoms}
        held_cached.append((meta["code"], meta["market"], atoms, layers))

    curves = oos_promotion(freq, held_cached, (50, 100, 200, 339, 500, 1152))
    staples = staples_top40(freq)

    def _rates(counter: Counter) -> dict:
        n = sum(counter.values())
        return {
            "n": n,
            **{k: round(counter[k] / n, 4) if n else 0.0 for k in ("SAFE", "NOT_SAFE", "UNCERTAIN")},
            "counts": dict(counter),
        }

    report = {
        "parser": "flatten_ingredients after composition-percent + nesting conservation fixes",
        "backstops": "raw_label hazard sweep + parse-quality ceiling enabled on list evals",
        "freq_id_source": {
            "path": str(_FREQ_PATH),
            "sampling": freq_ids.get("sampling"),
            "seed": freq_ids.get("seed"),
            "dump_date": freq_ids.get("dump_date"),
            "n_products": freq_ids.get("n_products"),
            "disjoint_from_held_out": freq_ids.get("disjoint_from_held_out"),
            "held_out_excluded": freq_ids.get("held_out_excluded"),
        },
        "held_id_source": {
            "path": str(_IDS_PATH),
            "n_products": len(held.get("products") or []),
            "sampling": held.get("sampling"),
            "dump_date": held.get("dump_date"),
            "with_text": held_with_text,
        },
        "held_freq_overlap_codes": len(overlap),
        "freq_atom_source": freq_source,
        "freq_atom_distinct": len(freq),
        "freq_atom_instances": sum(freq.values()),
        "profile_rates": {p: _rates(c) for p, c in profile_counts.items()},
        "layer_shares_instances": {
            "overall": dict(layer_instances),
            "by_market": {m: dict(c) for m, c in layer_by_market.items()},
            "l3_combined": (
                layer_instances.get("L3", 0)
                + layer_instances.get("L3_trusted", 0)
                + layer_instances.get("L3_untrusted", 0)
            ),
            "l3_share": round(
                (
                    layer_instances.get("L3", 0)
                    + layer_instances.get("L3_trusted", 0)
                    + layer_instances.get("L3_untrusted", 0)
                )
                / max(sum(layer_instances.values()), 1),
                4,
            ),
            "l5_by_market": {
                m: {
                    "L5_unknown": c.get("L5_unknown", 0),
                    "L5_rate": round(
                        c.get("L5_unknown", 0) / max(sum(c.values()), 1), 4
                    ),
                    "L3": c.get("L3", 0)
                    + c.get("L3_trusted", 0)
                    + c.get("L3_untrusted", 0),
                    "n": sum(c.values()),
                }
                for m, c in layer_by_market.items()
            },
        },
        "n_safe_list_evals": len(safe_rows),
        "ambiguous_atoms_in_safe": ambiguous_in_safe,
        "oos_promotion": curves,
        "staples_top40_english": [
            {"atom": s["atom"], "n": s["n"], "layer_bucket": s["layer_bucket"], "trusted": s["trusted"]}
            for s in staples
        ],
        "k339_vs_500": curves.get("_k339_vs_500"),
        "pilot_response_shape": (
            "Default evaluate response should lead with per-ingredient status "
            "(N cleared, K unknown, M hazard), not product-level SAFE. "
            "UK/EU OOS firmness stays ~1.4% at every K — pilot India+US unless Europe in scope."
        ),
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "profile_rates": {
                    p: {k: report["profile_rates"][p][k] for k in ("SAFE", "NOT_SAFE", "UNCERTAIN", "n")}
                    for p in report["profile_rates"]
                },
                "oos_k339": {
                    "no_l5": curves["339"]["no_l5_left"]["rate"],
                    "firm": curves["339"]["firm_verdict"]["rate"],
                    "instance": curves["339"]["instance_coverage"]["rate"],
                },
                "oos_k500": {
                    "no_l5": curves["500"]["no_l5_left"]["rate"],
                    "firm": curves["500"]["firm_verdict"]["rate"],
                    "instance": curves["500"]["instance_coverage"]["rate"],
                },
                "oos_k1152": {
                    "no_l5": curves["1152"]["no_l5_left"]["rate"],
                    "firm": curves["1152"]["firm_verdict"]["rate"],
                    "instance": curves["1152"]["instance_coverage"]["rate"],
                },
                "k339_vs_500": curves.get("_k339_vs_500"),
                "n_ambiguous_safe": len(ambiguous_in_safe),
                "path": str(_OUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
