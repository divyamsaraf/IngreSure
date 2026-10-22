"""A31–A34: bilingual blocks, slash translations, qualifiers, INS/E sub-variants."""
from core.parsing.ingredient_block import extract_ingredient_block
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings


def test_a31_bilingual_blocks_are_one_product():
    block = extract_ingredient_block(
        "Ingredients: Sugar, milk. Ingredients (FR): Sucre, lait. Zutaten: Zucker, Milch"
    )
    assert block.kind != "multi_product"
    blob = " ".join(block.atoms).lower()
    assert "sugar" in blob
    assert "milk" in blob
    # Language blocks are joined, not last-wins.
    assert "sucre" in blob or "lait" in blob
    assert "zucker" in blob or "milch" in blob


def test_a32_slash_translation_is_one_atom_not_alternatives():
    atoms = preprocess_ingredients_to_strings("Sugar/Sucre, milk/lait, water/eau")
    blob = " ".join(atoms).lower()
    assert "sugar" in blob or "sucre" in blob
    assert "milk" in blob or "lait" in blob
    # Must not invent a third unknown glued token, or drop milk.
    assert not any(a.lower() in {"ii", "a", "d"} for a in atoms)


def test_a33_qualifiers_attach_to_parent():
    atoms = preprocess_ingredients_to_strings(
        "citric acid (to preserve freshness), annatto (color), "
        "cocoa processed with alkali, natural and artificial flavors, color added"
    )
    blob = " ".join(atoms).lower()
    assert "citric" in blob or "acid" in blob
    assert "annatto" in blob
    assert "cocoa" in blob
    assert "flavor" in blob or "flavour" in blob
    # Qualifier words must not stand as blocking unknown atoms.
    bare = {a.lower().strip() for a in atoms}
    assert "alkali" not in bare
    assert "color" not in bare
    assert "colour" not in bare
    assert "natural" not in bare


def test_a34_ins_e_subvariant_is_one_atom():
    atoms = preprocess_ingredients_to_strings("INS 322(ii), E 150 d, ins 330, E471(a)")
    blob = " ".join(a.lower() for a in atoms)
    assert "ii" not in {a.lower().strip() for a in atoms}
    assert "a" not in {a.lower().strip() for a in atoms}
    assert "d" not in {a.lower().strip() for a in atoms}
    assert "322" in blob or "e322" in blob.replace(" ", "")
    assert "150" in blob or "e150" in blob.replace(" ", "")
    assert "330" in blob or "e330" in blob.replace(" ", "")
    assert "471" in blob or "e471" in blob.replace(" ", "")
