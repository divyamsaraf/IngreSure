"""Item 2 Prompt 3: expand_compounds retains process identity + flag propagation."""
from core.compound_expansion import (
    expand_compounds,
    member_flags_with_parent_process,
    parent_process_flags,
)
from core.bridge import _run_ike2_compliance, map_ike2_to_compliance_verdict


def test_tempeh_alone_still_passthrough():
    expanded, _, _ = expand_compounds(["tempeh"], role_index={})
    assert expanded == ["tempeh"]


def test_soy_tempeh_retains_tempeh_atom():
    expanded, _, derived = expand_compounds(["soy tempeh"], role_index={})
    assert "soy" in expanded
    assert "tempeh" in expanded
    assert derived.get("tempeh") == "soy tempeh"


def test_soy_miso_koji_natto_retain_process_atoms():
    for phrase, token in (
        ("soy miso", "miso"),
        ("wheat koji", "koji"),
        ("soy natto", "natto"),
    ):
        expanded, _, _ = expand_compounds([phrase], role_index={})
        assert token in expanded, phrase


def test_member_flags_inherit_parent_fungal_via_helper():
    """Configured expand: compositional member gets parent process flags OR'd."""
    parent = "soy tempeh"
    assert parent_process_flags(parent).get("fungal") is True
    member = {"plant_origin": True, "soy_source": True}
    out = member_flags_with_parent_process(parent, member)
    assert out["fungal"] is True
    assert out["soy_source"] is True
    assert "dairy_source" not in out or not out.get("dairy_source")


def test_soy_tempeh_jain_not_safe():
    result, inputs, display = _run_ike2_compliance(["soy tempeh"], ["jain"])
    verdict = map_ike2_to_compliance_verdict(result, inputs, input_display_map=display)
    assert verdict.status.value != "SAFE"


def test_garlic_pasta_still_extracts_garlic():
    expanded, _, _ = expand_compounds(["garlic pasta"], role_index={})
    assert "garlic" in expanded
