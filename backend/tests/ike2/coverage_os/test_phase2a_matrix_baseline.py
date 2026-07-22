# backend/tests/ike2/coverage_os/test_phase2a_matrix_baseline.py
"""Guard: expand baseline was captured against seeded ontology, not passthrough."""
import json
from pathlib import Path

from core.compound_expansion import clear_role_index_cache, expand_compounds

_BASELINE = Path(__file__).parent / "fixtures" / "phase2a_matrix_baseline.json"


def test_seeded_expand_matches_committed_baseline():
    clear_role_index_cache()
    data = json.loads(_BASELINE.read_text(encoding="utf-8"))
    assert data.get("ontology_seed") == "phase2a_role_seed"
    for phrase, expected in data["expand"].items():
        atoms, _dmap, derived = expand_compounds([phrase])
        assert atoms == expected["atoms"], phrase
        assert derived == expected["derived_from"], phrase


def test_baseline_regression_phrases_not_passthrough_tears():
    """Live regression table must stay closed after seed."""
    clear_role_index_cache()
    cases = {
        "almond yogurt": (["almond yogurt", "almond"], {"almond": "almond yogurt"}),
        "coconut milk": (["coconut milk", "coconut"], {"coconut": "coconut milk"}),
        "plant yogurt": (["plant yogurt", "plant"], {"plant": "plant yogurt"}),
        "yogurt goat": (["yogurt goat"], {}),
        "mechanically separated chicken": (
            ["mechanically separated chicken", "chicken"],
            {"chicken": "mechanically separated chicken"},
        ),
    }
    for phrase, (atoms, derived) in cases.items():
        got_atoms, _, got_der = expand_compounds([phrase])
        assert got_atoms == atoms, phrase
        assert got_der == derived, phrase
        assert "yogurt" not in got_atoms or phrase == "yogurt goat"
        assert "milk" not in got_atoms
