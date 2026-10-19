# backend/tests/ike2/test_commodity_head_culinary_keep.py
from core.knowledge.ike2.commodity_head import facet_reduction_candidates


def test_facet_does_not_strip_wine_vinegar_when_culinary_keep():
    roles = {"vinegar": "culinary_keep"}
    cands = facet_reduction_candidates("wine vinegar", role_index=roles)
    # Must not offer a reduction that tears culinary-kept wholes (e.g. to "wine").
    assert "wine" not in cands
    assert cands == []
