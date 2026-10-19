from core.knowledge.ike2.coverage_os.induction.pipeline import build_candidates


def test_build_candidates_composes_alias_and_role():
    entries = {
        "broccoli florets": {
            "normalized_key": "broccoli florets",
            "raw_inputs": ["broccoli florets"],
            "frequency": 5,
        }
    }
    ontology = {
        "ingredients": [
            {"canonical_name": "broccoli", "plant_origin": True},
            {"canonical_name": "vinegar", "plant_origin": True},
        ]
    }
    cands = build_candidates(
        entries=entries,
        ontology=ontology,
        alias_table={},
        tear_evidence={"vinegar": "culinary_keep"},
    )
    kinds = {c.proposal_kind for c in cands}
    assert "variant_alias" in kinds
    assert "ontology_role" in kinds
