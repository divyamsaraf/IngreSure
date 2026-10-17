"""Item 33 Prompt 2: IKE-2 resolve → ResolvedIngredientResponse adapter (no routes)."""
from types import SimpleNamespace

from core.knowledge.ike2.resolution_cache import ResolvedIngredient
from core.knowledge.ike2.resolve_response import map_ike2_to_resolved_response
from core.knowledge.ike2.truth_anchor import TruthAnchorFact

# Flags Ingredient.to_dict() cannot carry — the Prompt 1 under-flag catch.
_IKE2_ONLY_FLAGS = (
    "peanut_source",
    "tree_nut_source",
    "fish_source",
    "shellfish_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
    "enzyme_animal_source",
    "enzyme_microbial_source",
)


def _resolved(**overrides):
    base = dict(
        group=None,
        source="unknown_queue",
        confidence_band="none",
        trusted=False,
        resolution_layer="L5_unknown_queue",
        status="uncertain",
    )
    base.update(overrides)
    return ResolvedIngredient(**base)


def test_uncertain_is_null_ingredient_unclassified_never_api():
    out = map_ike2_to_resolved_response(_resolved())
    assert out["ingredient"] is None
    assert out["source_layer"] == "unknown"
    assert out["confidence_band"] is None
    assert out["knowledge_state"] == "UNCLASSIFIED"
    assert out["knowledge_source"] == "unknown_queue"
    assert out["source_layer"] != "api"


def test_db_error_and_ambiguous_are_unknown_not_dynamic():
    for layer in ("L3_db_error", "L3_db_malformed", "L3_db_alias"):
        # L3_db_alias with group None is still a miss (ambiguous path returns uncertain).
        out = map_ike2_to_resolved_response(
            _resolved(resolution_layer=layer, source="db", status="uncertain")
        )
        assert out["ingredient"] is None
        assert out["source_layer"] == "unknown"
        assert out["knowledge_state"] == "UNCLASSIFIED"


def test_truth_anchor_maps_static_high_and_keeps_state():
    fact = TruthAnchorFact(
        canonical_name="gelatin",
        flags={"animal_origin": True, "verdict_cap": "WARN"},
        knowledge_state="LOCKED",
    )
    out = map_ike2_to_resolved_response(
        _resolved(
            group=fact,
            source="truth_anchor",
            confidence_band="exact",
            trusted=True,
            resolution_layer="L1_truth_anchor",
            status="resolved",
        )
    )
    assert out["source_layer"] == "static"
    assert out["confidence_band"] == "high"
    assert out["knowledge_state"] == "LOCKED"
    assert out["knowledge_source"] == "truth_anchor"
    ing = out["ingredient"]
    assert ing["canonical_name"] == "gelatin"
    assert ing["animal_origin"] is True
    assert ing["verdict_cap"] == "WARN"
    assert ing["id"] == "gelatin"


def test_local_ontology_layer_is_static():
    fact = TruthAnchorFact(canonical_name="oat", flags={"plant_origin": True}, knowledge_state="AUTO_CLASSIFIED")
    out = map_ike2_to_resolved_response(
        _resolved(
            group=fact,
            source="local_ontology",
            confidence_band="high",
            trusted=True,
            resolution_layer="L2_local_ontology",
            status="resolved",
        )
    )
    assert out["source_layer"] == "static"
    assert out["knowledge_state"] == "AUTO_CLASSIFIED"


def test_group_row_keeps_ike2_allergen_flags_to_dict_would_drop():
    group = SimpleNamespace(
        id="g-shrimp",
        canonical_name="xqz blend",
        knowledge_state="DISCOVERED",
        peanut_source=True,
        tree_nut_source=True,
        fish_source=True,
        shellfish_source=True,
        mustard_source=True,
        celery_source=True,
        lupin_source=True,
        sulphite_source=True,
        enzyme_animal_source=True,
        enzyme_microbial_source=True,
        animal_origin=True,
        plant_origin=False,
    )
    out = map_ike2_to_resolved_response(
        _resolved(
            group=group,
            source="db",
            confidence_band="high",
            trusted=False,
            resolution_layer="L3_db_alias",
            status="resolved",
        )
    )
    assert out["source_layer"] == "dynamic"
    assert out["knowledge_state"] == "DISCOVERED"
    assert out["knowledge_source"] == "db"
    ing = out["ingredient"]
    assert ing["id"] == "g-shrimp"
    for flag in _IKE2_ONLY_FLAGS:
        assert ing[flag] is True, flag
    assert ing["nut_source"] == "peanut,tree_nut"


def test_nut_source_compat_single_flags():
    def _one(**flags):
        group = SimpleNamespace(id="g", canonical_name="xqz nut", knowledge_state="AUTO_CLASSIFIED", **flags)
        return map_ike2_to_resolved_response(
            _resolved(
                group=group,
                source="db",
                confidence_band="high",
                trusted=True,
                resolution_layer="L3_db_alias",
                status="resolved",
            )
        )["ingredient"]["nut_source"]

    assert _one(peanut_source=True) == "peanut"
    assert _one(tree_nut_source=True) == "tree_nut"
    assert _one(plant_origin=True) is None


def test_adapter_does_not_enqueue(monkeypatch):
    from core.knowledge.ike2 import unknown_queue as uq

    calls = []
    monkeypatch.setattr(uq, "record_miss", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(uq, "enqueue_unknown", lambda *a, **k: calls.append(a))
    map_ike2_to_resolved_response(_resolved())
    assert calls == []
