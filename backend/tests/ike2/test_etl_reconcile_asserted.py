from core.knowledge.ike2.etl.reconcile import ReconcileResult, reconcile


def test_reconcile_result_exposes_merged_asserted_flags():
    # Smoke: attribute exists after call (implementation detail checked by behavior tests).
    assert "merged_asserted_flags" in ReconcileResult.__dataclass_fields__
