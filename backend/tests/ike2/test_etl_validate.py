from core.knowledge.ike2.etl.validate import validate_rows


def test_reject_row_quarantined_batch_continues():
    rows = [
        {"canonical_name": "ok_milk", "animal_origin": True, "dairy_source": True},
        {"canonical_name": "bad", "animal_origin": False, "insect_derived": True},
    ]
    ok, rejects = validate_rows(rows)
    assert [r["canonical_name"] for r in ok] == ["ok_milk"]
    assert rejects[0]["violated_constraint"] == "insect_implies_animal"


def test_enzyme_animal_implies_animal_origin():
    ok, rejects = validate_rows([
        {"canonical_name": "rennet", "animal_origin": True, "enzyme_animal_source": True},
        {"canonical_name": "bad_enzyme", "animal_origin": False, "enzyme_animal_source": True},
    ])
    assert [r["canonical_name"] for r in ok] == ["rennet"]
    assert rejects[0]["violated_constraint"] == "enzyme_animal_implies_animal"


def test_enzyme_origin_not_both():
    ok, rejects = validate_rows([
        {
            "canonical_name": "confused",
            "animal_origin": True,
            "enzyme_animal_source": True,
            "enzyme_microbial_source": True,
        },
    ])
    assert ok == []
    assert rejects[0]["violated_constraint"] == "enzyme_origin_not_both"


def test_non_enumber_locked_hard_rejected():
    ok, rejects = validate_rows([
        {
            "canonical_name": "fake_locked",
            "knowledge_state": "LOCKED",
            "primary_source_url": "https://example.com",
            "classification_method": "bulk:usda",
        },
    ])
    assert ok == []
    assert rejects[0]["violated_constraint"] == "bulk_locked_verified_requires_e_number_catalog"


def test_non_enumber_verified_hard_rejected():
    ok, rejects = validate_rows([
        {
            "canonical_name": "fake_verified",
            "knowledge_state": "VERIFIED",
            "primary_source_url": "https://example.com",
            "classification_method": "bulk:openfoodfacts",
        },
    ])
    assert ok == []
    assert rejects[0]["violated_constraint"] == "bulk_locked_verified_requires_e_number_catalog"


def test_enumber_catalog_locked_allowed():
    ok, rejects = validate_rows([
        {
            "canonical_name": "e120",
            "knowledge_state": "LOCKED",
            "primary_source_url": "https://example.com/e120",
            "classification_method": "bulk:e_number_catalog",
            "insect_derived": True,
            "animal_origin": True,
        },
    ])
    assert rejects == []
    assert [r["canonical_name"] for r in ok] == ["e120"]
