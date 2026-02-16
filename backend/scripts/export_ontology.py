"""
One-time export: map backend/ingredient_ontology.py INGREDIENT_DB to data/ontology.json (new schema).
Run from repo root: python backend/scripts/export_ontology.py
"""
import json
import sys
from pathlib import Path

# Add backend to path so we can import ingredient_ontology
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ingredient_ontology import INGREDIENT_DB

def source_to_origin(source: str, notes: str, key: str) -> dict:
    o = {
        "animal_origin": False,
        "plant_origin": False,
        "synthetic": False,
        "fungal": False,
        "insect_derived": False,
        "animal_species": None,
        "egg_source": False,
        "dairy_source": False,
        "gluten_source": False,
        "nut_source": None,
        "soy_source": False,
        "sesame_source": False,
        "alcohol_content": None,
        "root_vegetable": "root" in notes.lower(),
        "onion_source": "onion" in key and "garlic" not in key,
        "garlic_source": "garlic" in key,
        "fermented": "ferment" in notes.lower(),
        "uncertainty_flags": [],
    }
    if source == "mineral":
        pass
    elif source == "plant":
        o["plant_origin"] = True
    elif source == "animal":
        o["animal_origin"] = True
        if "beef" in notes.lower() or "beef" in key:
            o["animal_species"] = "cow"
        elif "pork" in notes.lower() or "pork" in key or "bacon" in key or "ham" in key or "lard" in key:
            o["animal_species"] = "pig"
        elif "poultry" in notes.lower() or "chicken" in key or "turkey" in key or "duck" in key:
            o["animal_species"] = "chicken"
        elif "meat" in notes.lower() or "lamb" in key or "mutton" in key:
            o["animal_species"] = "lamb"
        elif "goat" in key:
            o["animal_species"] = "goat"
    elif source == "milk":
        o["dairy_source"] = True
        o["animal_origin"] = True
    elif source == "egg":
        o["egg_source"] = True
        o["animal_origin"] = True
    elif source == "fish":
        o["animal_origin"] = True
        o["animal_species"] = "fish"
    elif source == "shellfish":
        o["animal_origin"] = True
        o["animal_species"] = "shellfish"
    elif source == "insect":
        o["insect_derived"] = True
    elif source == "alcohol":
        o["alcohol_content"] = 1.0
    elif source == "synthetic":
        o["synthetic"] = True

    return o

def main():
    ingredients = []
    for key, prop in INGREDIENT_DB.items():
        source, allergens, notes = prop.source, prop.allergens, prop.notes
        o = source_to_origin(source, notes, key)
        if "wheat" in allergens or "gluten" in allergens:
            o["gluten_source"] = True
        if "milk" in allergens:
            o["dairy_source"] = True
        if "egg" in allergens:
            o["egg_source"] = True
        if "peanut" in allergens:
            o["nut_source"] = "peanut"
        if "nut" in allergens:
            o["nut_source"] = o["nut_source"] or "tree_nut"
        if "soy" in allergens:
            o["soy_source"] = True
        if "sesame" in allergens:
            o["sesame_source"] = True
        if "fish" in allergens and not o["animal_species"]:
            o["animal_species"] = "fish"
        if "shellfish" in allergens and not o["animal_species"]:
            o["animal_species"] = "shellfish"

        if key == "natural flavor":
            o["uncertainty_flags"] = ["natural_flavor"]
        if "mono" in key or "glyceride" in key or key in ("glycerin", "glycerol"):
            o["uncertainty_flags"] = o["uncertainty_flags"] or ["mono_diglycerides"]
        if "lecithin" in key and "soy" in str(notes).lower():
            o["uncertainty_flags"] = o["uncertainty_flags"] or ["lecithin_source"]

        ingredients.append({
            "id": key.replace(" ", "_"),
            "canonical_name": key,
            "aliases": [],
            "derived_from": [],
            "contains": [],
            "may_contain": [],
            **o,
            "regions": [],
        })

    data = {"ontology_version": "1.0", "ingredients": ingredients}
    out = Path(__file__).resolve().parent.parent.parent / "data" / "ontology.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Wrote", out, "with", len(ingredients), "ingredients")

if __name__ == "__main__":
    main()
