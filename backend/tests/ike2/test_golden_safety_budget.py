import json
import pathlib
from types import SimpleNamespace

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.input_layer import to_atoms
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.verdict import to_external

CORPUS = pathlib.Path(__file__).parent / "golden" / "corpus.jsonl"

# Map a profile restriction -> (rule kind, trigger flag).
_RULE_SPECS = {
    "vegan": ("flag", "animal_origin"),
    "vegetarian": ("flag", "animal_origin"),
    "jain": ("flag", "animal_origin"),
    "peanut": ("flag", "peanut_source"),
    "dairy": ("flag", "dairy_source"),
    "alcohol": ("alcohol", None),
}


def _rules_for(profile):
    rules = []
    for restriction in getattr(profile, "restrictions", {}) or {}:
        spec = _RULE_SPECS.get(restriction)
        if not spec:
            continue
        kind, flag = spec
        rules.append(
            SimpleNamespace(
                restriction=restriction,
                kind=kind,
                trigger_flag=flag,
                min_knowledge_state="UNCLASSIFIED",
            )
        )
    return rules


def _safe_resolve(atom, region):
    # Fail-closed: any resolution error (e.g. store unavailable) -> uncertain,
    # never safe. This keeps the gate deterministic without a live DB.
    try:
        return resolve(atom, region)
    except Exception:
        return SimpleNamespace(group=None, trusted=False, status="uncertain")


def _adapt(r):
    """Flatten a ResolvedIngredient into the shape compliance.evaluate reads."""
    group = getattr(r, "group", None)
    flags = dict(getattr(group, "flags", {}) or {}) if group else {}
    return SimpleNamespace(
        canonical_name=getattr(group, "canonical_name", "?") if group else "?",
        flags=flags,
        knowledge_state=getattr(group, "knowledge_state", "UNCLASSIFIED")
        if group
        else "UNCLASSIFIED",
        trusted=bool(getattr(r, "trusted", False)),
        verdict_cap=getattr(group, "verdict_cap", None) if group else None,
        alcohol_role=flags.get("alcohol_role"),
        trace=False,
    )


def _run_case(case):
    atoms = to_atoms(case["raw_input"])
    resolved = [_adapt(_safe_resolve(a, case.get("region"))) for a in atoms]
    raw_profile = case["profile"]
    restrictions = raw_profile.get("restrictions", raw_profile)
    profile = SimpleNamespace(restrictions=restrictions)
    return to_external(evaluate(resolved, profile, rules=_rules_for(profile)))


def test_zero_false_safe_regressions():
    false_safes = []
    for line in CORPUS.read_text().splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        got = _run_case(case)
        if got == "SAFE" and case["expected_verdict"] == "NOT_SAFE":
            false_safes.append(case["raw_input"])
    assert false_safes == [], f"FALSE-SAFE regressions: {false_safes}"
