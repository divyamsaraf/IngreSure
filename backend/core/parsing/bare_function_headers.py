"""Parse bracket-less AU/NZ Codex function-class headers.

Handles strings such as ``Emulsifier 322`` or ``Emulsifier: soy lecithin``.
``ingredient_parser`` calls this for bracket-less shapes; parenthetical
headers stay in ``parenthetical.classify_parenthetical``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_CLASS_CANON = {
    "acidity regulator": "acidity_regulator",
    "acidity regulators": "acidity_regulator",
    "anticaking agent": "anticaking_agent",
    "anticaking agents": "anticaking_agent",
    "antioxidant": "antioxidant",
    "antioxidants": "antioxidant",
    "bulking agent": "bulking_agent",
    "bulking agents": "bulking_agent",
    "colour": "colour",
    "colours": "colour",
    "color": "colour",
    "colors": "colour",
    "emulsifier": "emulsifier",
    "emulsifiers": "emulsifier",
    "firming agent": "firming_agent",
    "firming agents": "firming_agent",
    "flavour enhancer": "flavour_enhancer",
    "flavour enhancers": "flavour_enhancer",
    "flavor enhancer": "flavour_enhancer",
    "flavor enhancers": "flavour_enhancer",
    "gelling agent": "gelling_agent",
    "gelling agents": "gelling_agent",
    "glazing agent": "glazing_agent",
    "glazing agents": "glazing_agent",
    "humectant": "humectant",
    "humectants": "humectant",
    "preservative": "preservative",
    "preservatives": "preservative",
    "raising agent": "raising_agent",
    "raising agents": "raising_agent",
    "stabiliser": "stabiliser",
    "stabilisers": "stabiliser",
    "stabilizer": "stabiliser",
    "stabilizers": "stabiliser",
    "sweetener": "sweetener",
    "sweeteners": "sweetener",
    "thickener": "thickener",
    "thickeners": "thickener",
}

_CLASS_ALT = "|".join(
    re.escape(name) for name in sorted(_CLASS_CANON, key=len, reverse=True)
)
_CLASS_SPLIT = re.compile(rf"(?i)(?P<cls>{_CLASS_ALT})\b\s*:?\s*")
_CODE = re.compile(r"\b(\d{3,4}[a-z]?)\b", re.IGNORECASE)
_CODE_ONLY = re.compile(r"^(?:\s*,\s*|\s+)?(?:\d{3,4}[a-z]?)(?:\s*,\s*(?:\d{3,4}[a-z]?))*\s*$", re.I)


@dataclass(frozen=True)
class BareFunctionHeader:
    function_class: str
    code: str | None
    substance: str | None
    raw: str


def _clean_substance(text: str) -> str | None:
    t = re.sub(r"\s+", " ", (text or "").strip(" ,;:"))
    return t or None


def _headers_from_clause(cls_raw: str, body: str, raw: str) -> list[BareFunctionHeader]:
    canon = _CLASS_CANON[cls_raw.lower()]
    body = (body or "").strip(" ,;:")
    if not body:
        return [BareFunctionHeader(canon, None, None, raw)]
    if _CODE_ONLY.match(body):
        return [
            BareFunctionHeader(canon, m.group(1).lower() if m.group(1)[-1:].isalpha() else m.group(1), None, raw)
            for m in _CODE.finditer(body)
        ]
    codes = list(_CODE.finditer(body))
    if codes and _CODE.sub("", body).strip(" ,;:") == "":
        return [
            BareFunctionHeader(canon, m.group(1).lower() if m.group(1)[-1:].isalpha() else m.group(1), None, raw)
            for m in codes
        ]
    return [BareFunctionHeader(canon, None, _clean_substance(body), raw)]


def parse_bare_function_headers(text: str) -> list[BareFunctionHeader]:
    """Return every function-class clause in ``text`` (comma-joined lists split)."""
    raw = (text or "").strip()
    if not raw:
        return []
    matches = list(_CLASS_SPLIT.finditer(raw))
    if not matches:
        return []
    out: list[BareFunctionHeader] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[m.end() : end]
        out.extend(_headers_from_clause(m.group("cls"), body, raw[m.start() : end].strip(" ,;")))
    return out


def parse_bare_function_header(text: str) -> BareFunctionHeader | None:
    """Parse a single-clause header, or the first clause of a list."""
    hits = parse_bare_function_headers(text)
    return hits[0] if hits else None
