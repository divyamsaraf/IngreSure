import re
from dataclasses import dataclass

from core.parsing.label_decomposer import decompose_label


@dataclass(frozen=True)
class ParsedAtom:
    """One normalized ingredient atom plus trace / may-contain flags."""
    name: str
    trace: bool = False
    may_contain: bool = False


def parse_atoms(raw: str) -> list[ParsedAtom]:
    """Decompose a label string via the shared label decomposer (bridge parity)."""
    return [
        ParsedAtom(name=item.name, trace=item.trace, may_contain=item.may_contain)
        for item in decompose_label(raw)
    ]


def to_atoms(raw: str) -> list[str]:
    """Sanitize, decompose compounds, split, and normalize a raw ingredient string."""
    return [a.name for a in parse_atoms(raw)]
