"""Build long noisy label pastes for legacy vs IKE-2 stress comparison."""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from core.config import get_ontology_path
from core.knowledge.ike2 import input_layer, resolver
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.shadow.comparator import compare
from core.knowledge.ike2.verdict import to_external
from core.parsing.label_decomposer import decompose_label
from core.parsing.label_text import fix_ocr_label_noise, select_ingredient_label_text
from core.bridge import run_new_engine_chat
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ONTOLOGY_PATH = get_ontology_path()

JUNK_BLOCKS = [
    "Manufactured in a facility that also handles peanuts, tree nuts, and sesame.",
    "Phase 3 clinical trial formulation notes — internal R&D only, not for consumer labeling.",
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Random paragraph noise.",
    "Analyze this for me please. What's the weather today?",
    "Best before: see cap. Store in a cool, dry place away from direct sunlight.",
    "Nutrition Facts Serving size 30g Calories 150 Total Fat 8g — not an ingredient list.",
    "Tell me about gelatin and whether vegans can eat it.",
]

# Separate tiny block for OCR / multi-header tests (must NOT be last in a stress paste).
OCR_DECOY_HEADER = "1ngredients: water, salt, sugar."

STRESS_PROFILES: list[dict[str, Any]] = [
    {"id": "vegan", "restriction_ids": ["vegan"]},
    {"id": "halal", "restriction_ids": ["halal"]},
    {"id": "jain", "restriction_ids": ["jain"]},
    {"id": "peanut_medical", "restriction_ids": ["peanut_allergy"]},
    {"id": "vegan_peanut", "restriction_ids": ["vegan", "peanut_allergy"]},
    {"id": "gluten_free", "restriction_ids": ["gluten_free"]},
]


def load_ontology_names(limit: int = 220) -> list[str]:
    path = _ONTOLOGY_PATH if _ONTOLOGY_PATH.is_file() else _REPO_ROOT / "data" / "ontology.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ingredients = data.get("ingredients") or []
    names = [row["canonical_name"] for row in ingredients if row.get("canonical_name")]
    if len(names) < limit:
        raise ValueError(f"ontology has {len(names)} names, need {limit}")
    return names[:limit]


def build_stress_label(ingredient_count: int = 240) -> str:
    """Comma-separated label with 200+ real ingredients plus junk paragraphs.

    Junk precedes the real list; the **last** ``Ingredients:`` block is the
  220+ item paste (matches ``select_ingredient_label_text`` multi-block rules).
    """
    names = load_ontology_names(ingredient_count)
    leading_junk = "\n\n".join(JUNK_BLOCKS + [OCR_DECOY_HEADER])
    core = "Ingredients: " + ", ".join(names)
    # Known allergens / diet triggers sprinkled in
    core += ", peanut, gelatin, milk, wheat flour, shrimp, wine"
    core += ". May contain: soy, traces of tree nuts."
    core += ". Contains less than 2% of: salt, yeast."
    return f"{leading_junk}\n\n{core}"


def _profile(restriction_ids: list[str]) -> SimpleNamespace:
    return SimpleNamespace(restrictions={rid: "medical" for rid in restriction_ids})


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def time_legacy_pipeline(raw: str, restriction_ids: list[str]) -> dict[str, Any]:
    from core.intent_detector import detect_intent
    from core.parsing.label_decomposer import DecomposedItem
    from core.parsing.chat_ingredients import prepare_chat_ingredients

    t0 = time.perf_counter()
    t_parse = time.perf_counter()
    parsed = detect_intent(raw)
    prepared = prepare_chat_ingredients(raw, parsed)
    items = prepared.decomposed or [DecomposedItem(name=n) for n in prepared.eval_names]
    parse_ms = (time.perf_counter() - t_parse) * 1000

    t_comp = time.perf_counter()
    verdict = run_new_engine_chat(
        prepared.eval_names,
        restriction_ids=restriction_ids,
        use_api_fallback=False,
        prepared_decomposed=prepared.decomposed,
    )
    comp_ms = (time.perf_counter() - t_comp) * 1000
    total_ms = (time.perf_counter() - t0) * 1000

    return {
        "atom_count": len(items),
        "verdict": verdict.status.value,
        "triggered_restrictions": list(verdict.triggered_restrictions or []),
        "triggered_ingredients": list(verdict.triggered_ingredients or []),
        "uncertain_count": len(verdict.uncertain_ingredients or []),
        "confidence": verdict.confidence_score,
        "latency_ms": {
            "select_and_decompose": round(parse_ms, 2),
            "compliance_total": round(comp_ms, 2),
            "end_to_end": round(total_ms, 2),
        },
    }


def time_ike2_pipeline(
    raw: str,
    restriction_ids: list[str],
    *,
    use_seeded_rules: bool = False,
) -> dict[str, Any]:
    rules = rules_module.seeded_rules() if use_seeded_rules else rules_module.load_rules()
    profile = _profile(restriction_ids)
    cleaned = select_ingredient_label_text(fix_ocr_label_noise(raw))

    t0 = time.perf_counter()
    t_parse = time.perf_counter()
    atoms = list(input_layer.parse_atoms(cleaned))
    parse_ms = (time.perf_counter() - t_parse) * 1000

    t_resolve = time.perf_counter()
    inputs = []
    for atom in atoms:
        resolved = resolver.resolve(atom.name, None)
        inputs.append(
            to_compliance_input(resolved, trace=atom.trace, may_contain=atom.may_contain)
        )
    resolve_ms = (time.perf_counter() - t_resolve) * 1000

    t_comp = time.perf_counter()
    result = evaluate(inputs, profile, rules)
    verdict = to_external(result.verdict)
    comp_ms = (time.perf_counter() - t_comp) * 1000
    total_ms = (time.perf_counter() - t0) * 1000

    return {
        "atom_count": len(atoms),
        "verdict": verdict,
        "matched_contains": list(result.matched_contains),
        "matched_may_contain": list(result.matched_may_contain),
        "caution_reasons": list(result.caution_reasons)[:20],
        "latency_ms": {
            "parse_atoms": round(parse_ms, 2),
            "resolve_all": round(resolve_ms, 2),
            "compliance": round(comp_ms, 2),
            "end_to_end": round(total_ms, 2),
        },
    }


def compare_profile(
    raw: str,
    profile: dict[str, Any],
    *,
    use_seeded_rules: bool = False,
) -> dict[str, Any]:
    rids = profile["restriction_ids"]
    legacy = time_legacy_pipeline(raw, rids)
    ike2 = time_ike2_pipeline(raw, rids, use_seeded_rules=use_seeded_rules)
    diff = compare(legacy["verdict"], ike2["verdict"], raw[:500])
    return {
        "profile_id": profile["id"],
        "restriction_ids": rids,
        "legacy": legacy,
        "ike2": ike2,
        "atom_parity": legacy["atom_count"] == ike2["atom_count"],
        "verdict_match": diff["match"],
        "false_safe_regression": diff["false_safe_regression"],
        "latency_delta_ms": round(
            ike2["latency_ms"]["end_to_end"] - legacy["latency_ms"]["end_to_end"],
            2,
        ),
    }


def run_user_input_stress(
    *,
    ingredient_count: int = 240,
    use_seeded_rules: bool = False,
) -> dict[str, Any]:
    """End-to-end via intent detector + chat bridge (simulates pasted user messages)."""
    from core.intent_detector import detect_intent
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
    from core.models.user_profile import UserProfile
    from core.parsing.chat_ingredients import prepare_chat_ingredients

    raw = build_stress_label(ingredient_count)
    # Use the real ingredient block (after junk); full paste often mis-detects diet from junk lines.
    core_label = raw.split("Ingredients:")[-1]
    core_label = "Ingredients:" + core_label if core_label else raw

    scenarios = [
        {
            "id": "check_for_vegan",
            "query": f"Check these ingredients for vegan:\n{core_label}",
            "profile_diet": "Vegan",
        },
        {
            "id": "halal_label_paste",
            "query": f"I follow halal. Is this ok?\n{core_label}",
            "profile_diet": "Halal",
        },
        {
            "id": "raw_ingredients_only",
            "query": core_label,
            "profile_diet": "Jain",
        },
        {
            "id": "junk_only_weather",
            "query": "what's the weather today analyze this for me",
            "profile_diet": None,
        },
        {
            "id": "complex_nested_only",
            "query": (
                "Ingredients: mono- and diglycerides of fatty acids (E471), "
                "natural flavors, gelatin (bovine), carmine (E120), "
                "sodium caseinate, l-cysteine, shellac, isinglass, rennet, "
                "wine vinegar, shrimp powder, wheat flour, peanut oil. "
                "May contain: tree nuts, soy."
            ),
            "profile_diet": "Vegan",
        },
    ]

    results: list[dict[str, Any]] = []
    for sc in scenarios:
        t0 = time.perf_counter()
        parsed = detect_intent(sc["query"])
        intent_ms = (time.perf_counter() - t0) * 1000

        profile = UserProfile(user_id="stress")
        if sc["profile_diet"]:
            profile.update_merge(dietary_preference=sc["profile_diet"])
        elif parsed.profile_updates.get("dietary_preference"):
            profile.update_merge(
                dietary_preference=str(parsed.profile_updates["dietary_preference"])
            )
        rids = user_profile_model_to_restriction_ids(profile)

        t1 = time.perf_counter()
        legacy_verdict = None
        ike2_verdict = None
        if parsed.ingredients and parsed.intent not in ("GREETING", "GENERAL_QUESTION"):
            prepared = prepare_chat_ingredients(sc["query"], parsed)
            legacy_verdict = run_new_engine_chat(
                prepared.eval_names,
                user_profile=profile,
                restriction_ids=rids,
                use_api_fallback=False,
                prepared_decomposed=prepared.decomposed,
            )
            ike2_verdict = time_ike2_pipeline(
                prepared.label_text or sc["query"],
                rids,
                use_seeded_rules=use_seeded_rules,
            )["verdict"]
        compliance_ms = (time.perf_counter() - t1) * 1000

        diff = None
        if legacy_verdict and ike2_verdict:
            diff = compare(legacy_verdict.status.value, ike2_verdict, sc["query"][:200])

        results.append(
            {
                "scenario_id": sc["id"],
                "intent": parsed.intent,
                "ingredient_count": len(parsed.ingredients),
                "profile_diet": sc["profile_diet"] or parsed.profile_updates.get("dietary_preference"),
                "legacy_verdict": legacy_verdict.status.value if legacy_verdict else None,
                "ike2_verdict": ike2_verdict,
                "verdict_match": diff["match"] if diff else None,
                "false_safe_regression": diff["false_safe_regression"] if diff else False,
                "latency_ms": {
                    "intent": round(intent_ms, 2),
                    "compliance": round(compliance_ms, 2),
                    "total": round(intent_ms + compliance_ms, 2),
                },
            }
        )

    compared = [r for r in results if r["verdict_match"] is not None]
    return {
        "scenarios": results,
        "summary": {
            "verdict_match_rate": (
                sum(1 for r in compared if r["verdict_match"]) / len(compared) if compared else 1.0
            ),
            "false_safe_regressions": sum(1 for r in results if r["false_safe_regression"]),
        },
    }


def run_stress_suite(
    *,
    ingredient_count: int = 240,
    iterations: int = 3,
    use_seeded_rules: bool = False,
) -> dict[str, Any]:
    raw = build_stress_label(ingredient_count)
    cleaned = select_ingredient_label_text(fix_ocr_label_noise(raw))
    decomposed = decompose_label(cleaned)

    profile_results = [
        compare_profile(raw, p, use_seeded_rules=use_seeded_rules) for p in STRESS_PROFILES
    ]

    # Latency distribution on vegan profile (representative hot path)
    legacy_runs: list[float] = []
    ike2_runs: list[float] = []
    vegan = STRESS_PROFILES[0]
    for _ in range(iterations):
        legacy_runs.append(time_legacy_pipeline(raw, vegan["restriction_ids"])["latency_ms"]["end_to_end"])
        ike2_runs.append(
            time_ike2_pipeline(
                raw, vegan["restriction_ids"], use_seeded_rules=use_seeded_rules
            )["latency_ms"]["end_to_end"]
        )

    mismatches = [r for r in profile_results if not r["verdict_match"]]
    false_safe = [r for r in profile_results if r["false_safe_regression"]]

    return {
        "label_chars": len(raw),
        "ingredient_target": ingredient_count,
        "decomposed_atoms": len(decomposed),
        "iterations": iterations,
        "profiles": profile_results,
        "summary": {
            "verdict_match_rate": (
                sum(1 for r in profile_results if r["verdict_match"]) / len(profile_results)
            ),
            "false_safe_regressions": len(false_safe),
            "atom_parity_all_profiles": all(r["atom_parity"] for r in profile_results),
            "mismatch_profiles": [m["profile_id"] for m in mismatches],
        },
        "latency": {
            "legacy_ms": {
                "p50": round(_percentile(legacy_runs, 50), 2),
                "p95": round(_percentile(legacy_runs, 95), 2),
                "mean": round(statistics.mean(legacy_runs), 2),
                "runs": legacy_runs,
            },
            "ike2_ms": {
                "p50": round(_percentile(ike2_runs, 50), 2),
                "p95": round(_percentile(ike2_runs, 95), 2),
                "mean": round(statistics.mean(ike2_runs), 2),
                "runs": ike2_runs,
            },
        },
        "false_safe_details": false_safe,
        "mismatch_details": mismatches,
    }
