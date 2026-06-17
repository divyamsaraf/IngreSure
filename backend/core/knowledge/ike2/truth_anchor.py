from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TruthAnchorFact:
    canonical_name: str
    flags: dict
    knowledge_state: str = "LOCKED"


def _f(**kw):
    return kw


_ANCHORS: dict[str, TruthAnchorFact] = {}


def _add(keys, canonical, flags):
    fact = TruthAnchorFact(canonical_name=canonical, flags=flags)
    for k in keys:
        _ANCHORS[k] = fact


_add(["gelatin", "gelatine"], "gelatin", _f(animal_origin=True))
_add(["carmine", "e120", "cochineal", "carminic acid"], "carmine",
     _f(animal_origin=True, insect_derived=True))
_add(["lard", "tallow"], "animal_fat", _f(animal_origin=True, animal_species="pig"))
_add(["isinglass"], "isinglass", _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["shellac", "e904"], "shellac", _f(animal_origin=True, insect_derived=True))
_add(["ethanol", "ethyl alcohol"], "ethanol", _f(alcohol_content=1.0))


def lookup(normalized_key: str) -> Optional[TruthAnchorFact]:
    return _ANCHORS.get(normalized_key)
