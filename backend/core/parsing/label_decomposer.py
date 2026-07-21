"""Unified label decomposition for legacy bridge and IKE-2 input_layer."""
from dataclasses import dataclass

from core.compound_expansion import expand_compounds
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

    After flatten, compound products with known restricted keywords
    (``egg noodles`` → ``egg``) are expanded so compliance cannot miss them.
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
            expanded, _ = expand_compounds([name])
            for exp_name in expanded or [name]:
                if not exp_name:
                    continue
                existing = by_name.get(exp_name)
                if existing is None:
                    by_name[exp_name] = DecomposedItem(
                        name=exp_name, trace=trace, may_contain=may_contain
                    )
                else:
                    by_name[exp_name] = DecomposedItem(
                        name=exp_name,
                        trace=existing.trace or trace,
                        may_contain=existing.may_contain or may_contain,
                    )
    return list(by_name.values())
