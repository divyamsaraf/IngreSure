"""
Utility: Print ontology statistics from data/ontology.json.
The legacy ingredient_ontology.py has been removed; data/ontology.json
is now the canonical source of truth.
"""
import json
from pathlib import Path

def main():
    ontology_path = Path(__file__).resolve().parent.parent.parent / "data" / "ontology.json"
    if not ontology_path.exists():
        print(f"Ontology file not found: {ontology_path}")
        return

    with open(ontology_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ingredients = data.get("ingredients", [])
    print(f"Ontology version: {data.get('ontology_version', 'unknown')}")
    print(f"Total ingredients: {len(ingredients)}")

    # Count by origin type
    animal = sum(1 for i in ingredients if i.get("animal_origin"))
    plant = sum(1 for i in ingredients if i.get("plant_origin"))
    synthetic = sum(1 for i in ingredients if i.get("synthetic"))
    print(f"  Animal-origin: {animal}")
    print(f"  Plant-origin:  {plant}")
    print(f"  Synthetic:     {synthetic}")

if __name__ == "__main__":
    main()
