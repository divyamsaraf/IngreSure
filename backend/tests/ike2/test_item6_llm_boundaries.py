"""Item 6 Prompt 3: LLM stay out of IKE-2 compliance; classify cannot mint LOCKED."""
from __future__ import annotations

import ast
from pathlib import Path

from core.config import LLM_CLASSIFY_TIMEOUT, LLM_ENGLISH_HINT_TIMEOUT
from core.knowledge.ike2.etl.sources import default_knowledge_state
from core.knowledge.llm_classify import apply_classification_to_ingredient
from core.ontology.ingredient_schema import Ingredient

_IKE2_ROOT = Path(__file__).resolve().parents[2] / "core" / "knowledge" / "ike2"

_FORBIDDEN_LLM_MODULES = frozenset(
    {
        "core.llm_intent",
        "core.llm_response",
        "core.knowledge.llm_classify",
    }
)


def _imported_modules(py_path: Path) -> set[str]:
    tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_ike2_modules_do_not_import_llm_touchpoints():
    offenders: list[str] = []
    for path in _IKE2_ROOT.rglob("*.py"):
        imported = _imported_modules(path)
        bad = imported & _FORBIDDEN_LLM_MODULES
        # Also catch `from core.knowledge import llm_classify` style via module prefix.
        bad |= {
            m
            for m in imported
            if m.startswith("core.llm_") or m.endswith(".llm_classify") or m == "llm_classify"
        }
        if bad:
            offenders.append(f"{path.relative_to(_IKE2_ROOT.parent.parent.parent)}: {sorted(bad)}")
    assert not offenders, "IKE-2 must not import LLM modules:\n" + "\n".join(offenders)


def test_enrichment_api_default_state_is_discovered():
    assert default_knowledge_state("enrichment_api") == "DISCOVERED"


def test_apply_classification_adds_llm_classified_uncertainty():
    base = Ingredient(id="t1", canonical_name="mystery additive", aliases=[])
    out = apply_classification_to_ingredient(
        base,
        {"animal_origin": True, "origin_type": "animal", "animal_species": "insect"},
    )
    assert "llm_classified" in (out.uncertainty_flags or [])
    assert out.animal_origin is True
    # Ingredient rows do not carry knowledge_state; protected states are a group concern.
    assert not hasattr(out, "knowledge_state")


def test_llm_timeouts_are_config_named():
    assert LLM_CLASSIFY_TIMEOUT == 15
    assert LLM_ENGLISH_HINT_TIMEOUT == 5


def test_dead_profile_update_llm_helper_removed():
    import core.llm_response as mod

    assert not hasattr(mod, "llm_compose_profile_update")
