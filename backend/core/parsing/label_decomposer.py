"""Unified label decomposition for legacy bridge and IKE-2 input_layer."""
from dataclasses import dataclass

from core.normalization.parser import flatten_ingredients
from core.parsing.ingredient_parser import preprocess_ingredients


@dataclass(frozen=True)
class DecomposedItem:
    name: str
    trace: bool = False
    may_contain: bool = False


def decompose_label(raw: str) -> list[DecomposedItem]:
    """Parse a label string into normalized atoms with trace flags.

    Mirrors ``bridge.preprocess_ingredient_list`` decomposition so IKE-2 and
    legacy see the same atoms for the same raw paste.
    """
    if not raw or not str(raw).strip():
        return []
    by_name: dict[str, DecomposedItem] = {}
    for item in preprocess_ingredients(str(raw)):
        trace = bool(item.get("trace"))
        may_contain = bool(item.get("may_contain"))
        for name in flatten_ingredients(item["name"]):
            if not name:
                continue
            existing = by_name.get(name)
            if existing is None:
                by_name[name] = DecomposedItem(
                    name=name, trace=trace, may_contain=may_contain
                )
            else:
                by_name[name] = DecomposedItem(
                    name=name,
                    trace=existing.trace or trace,
                    may_contain=existing.may_contain or may_contain,
                )
    return list(by_name.values())
