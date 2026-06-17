from core.knowledge.ike2.etl.validate import validate_rows


def test_reject_row_quarantined_batch_continues():
    rows = [
        {"canonical_name": "ok_milk", "animal_origin": True, "dairy_source": True},
        {"canonical_name": "bad", "animal_origin": False, "insect_derived": True},
    ]
    ok, rejects = validate_rows(rows)
    assert [r["canonical_name"] for r in ok] == ["ok_milk"]
    assert rejects[0]["violated_constraint"] == "insect_implies_animal"
