"""
Strict contract for canonical ingredient representation.
No free-text metadata; all fields are structured for deterministic evaluation.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Ingredient:
    id: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    contains: list[str] = field(default_factory=list)
    may_contain: list[str] = field(default_factory=list)
    # Origin flags
    animal_origin: bool = False
    plant_origin: bool = False
    synthetic: bool = False
    fungal: bool = False
    insect_derived: bool = False
    # Species (when animal_origin True): cow, goat, pig, chicken, fish, shellfish, etc.
    animal_species: Optional[str] = None
    # Allergen / dietary source flags
    egg_source: bool = False
    dairy_source: bool = False
    gluten_source: bool = False
    nut_source: Optional[str] = None  # e.g. "tree_nut", "peanut", "coconut"
    soy_source: bool = False
    # Allergen: sesame, mustard, etc. (nut_source covers nut; separate for sesame/mustard)
    sesame_source: bool = False
    # Alcohol: 0 = none, >0 = present (e.g. 1.0 for "contains alcohol")
    alcohol_content: Optional[float] = None
    # Jain / no_onion_no_garlic / onion or garlic as allergen
    root_vegetable: bool = False
    onion_source: bool = False
    garlic_source: bool = False
    fermented: bool = False
    # Uncertainty: e.g. "natural_flavor", "mono_diglycerides"
    uncertainty_flags: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)

    @property
    def meat_fish_derived(self) -> bool:
        """True if animal-derived but not dairy/egg/insect (meat, fish, shellfish, gelatin, etc.).
        Excludes insect-derived items (honey, beeswax, carmine, shellac) which are
        handled separately by the insect_derived flag."""
        return (
            self.animal_origin
            and not self.dairy_source
            and not self.egg_source
            and not self.insect_derived
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "canonical_name": self.canonical_name,
            "aliases": list(self.aliases),
            "derived_from": list(self.derived_from),
            "contains": list(self.contains),
            "may_contain": list(self.may_contain),
            "animal_origin": self.animal_origin,
            "plant_origin": self.plant_origin,
            "synthetic": self.synthetic,
            "fungal": self.fungal,
            "insect_derived": self.insect_derived,
            "animal_species": self.animal_species,
            "egg_source": self.egg_source,
            "dairy_source": self.dairy_source,
            "gluten_source": self.gluten_source,
            "nut_source": self.nut_source,
            "soy_source": self.soy_source,
            "sesame_source": self.sesame_source,
            "alcohol_content": self.alcohol_content,
            "root_vegetable": self.root_vegetable,
            "onion_source": self.onion_source,
            "garlic_source": self.garlic_source,
            "fermented": self.fermented,
            "uncertainty_flags": list(self.uncertainty_flags),
            "regions": list(self.regions),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Ingredient":
        return cls(
            id=d["id"],
            canonical_name=d["canonical_name"],
            aliases=d.get("aliases", []) or [],
            derived_from=d.get("derived_from", []) or [],
            contains=d.get("contains", []) or [],
            may_contain=d.get("may_contain", []) or [],
            animal_origin=d.get("animal_origin", False),
            plant_origin=d.get("plant_origin", False),
            synthetic=d.get("synthetic", False),
            fungal=d.get("fungal", False),
            insect_derived=d.get("insect_derived", False),
            animal_species=d.get("animal_species"),
            egg_source=d.get("egg_source", False),
            dairy_source=d.get("dairy_source", False),
            gluten_source=d.get("gluten_source", False),
            nut_source=d.get("nut_source"),
            soy_source=d.get("soy_source", False),
            sesame_source=d.get("sesame_source", False),
            alcohol_content=d.get("alcohol_content"),
            root_vegetable=d.get("root_vegetable", False),
            onion_source=d.get("onion_source", False),
            garlic_source=d.get("garlic_source", False),
            fermented=d.get("fermented", False),
            uncertainty_flags=d.get("uncertainty_flags", []) or [],
            regions=d.get("regions", []) or [],
        )
