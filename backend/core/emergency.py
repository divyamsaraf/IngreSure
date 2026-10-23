"""Emergency intent: guidance first, no verdict flow.

Numbers verified 2026-10-20 against primary sources listed on each row.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Retrieval date for the citations below.
RETRIEVED = "2026-10-21"

# region code -> (number, citation)
NUMBERS: dict[str, tuple[str, str]] = {
    "US": ("911", "https://www.fcc.gov/general/9-1-1-and-e9-1-1-services"),
    "CA": ("911", "https://crtc.gc.ca/eng/phone/911/can.htm"),
    "GB": ("999", "https://www.gov.uk/guidance/999-and-112-the-uks-national-emergency-numbers"),
    "UK": ("999", "https://www.gov.uk/guidance/999-and-112-the-uks-national-emergency-numbers"),
    "EU": ("112", "https://europa.eu/youreurope/citizens/travel/security-and-emergencies/emergency/index_en.htm"),
    "AU": ("000", "https://www.triplezero.gov.au/"),
    "NZ": ("111", "https://www.police.govt.nz/call-111"),
    "AE": ("998", "https://u.ae/en/information-and-services/justice-safety-and-the-law/handling-emergencies/medical-emergencies"),
    "IN": ("112", "https://www.mha.gov.in/en/commoncontent/emergency-response-support-system-erss"),
}

_GENERIC_NUMBERS = (
    ("911", "US/Canada"),
    ("999", "UK"),
    ("112", "EU/India"),
    ("000", "Australia"),
    ("111", "New Zealand"),
    ("998", "UAE"),
)


@dataclass(frozen=True)
class EmergencyHit:
    kind: str = "emergency"
    region: str = "US"
    number: str = "911"


_PATTERNS = (
    re.compile(r"\b(?:call|dial)\s*(?:911|999|112|000|111|998)\b", re.IGNORECASE),
    re.compile(r"\b911\b"),
    re.compile(r"\bcan(?:'|’)t\s+breathe\b", re.IGNORECASE),
    re.compile(r"\bcannot\s+breathe\b", re.IGNORECASE),
    re.compile(r"\banaphylax", re.IGNORECASE),
    re.compile(r"\b(?:having|had)\s+a\s+reaction\b", re.IGNORECASE),
    re.compile(r"\ballergic\s+reaction\b", re.IGNORECASE),
    re.compile(r"\bthroat\s+(?:is\s+)?(?:closing|swelling|closing\s+up)\b", re.IGNORECASE),
    re.compile(r"\bepipen\b|\bepi-pen\b", re.IGNORECASE),
    re.compile(r"\bcall\s+emergency\b", re.IGNORECASE),
)


def number_for_region(region: str | None) -> str | None:
    """Return a verified emergency number, or None when the region is unknown.

    Unknown region must not silently apply one country's number (R01).
    """
    code = (region or "").strip().upper()
    if not code:
        return None
    if code in NUMBERS:
        return NUMBERS[code][0]
    if code in {"FR", "DE", "IT", "ES", "NL", "IE", "PT", "SE", "PL", "BE"}:
        return NUMBERS["EU"][0]
    return None


def generic_guidance() -> str:
    listed = ", ".join(f"{num} ({place})" for num, place in _GENERIC_NUMBERS)
    return (
        "If this is a medical emergency, stop using this app and call your local "
        f"emergency number now: {listed}. I am not emergency services and I will "
        "not evaluate ingredients while you may need urgent care."
    )


def detect_emergency(text: str, *, region: str | None = None) -> EmergencyHit | None:
    q = text or ""
    if not any(p.search(q) for p in _PATTERNS):
        return None
    code = (region or "").strip().upper()
    if code in {"FR", "DE", "IT", "ES", "NL", "IE", "PT", "SE", "PL", "BE"}:
        code = "EU"
    number = number_for_region(code) or ""
    return EmergencyHit(region=code, number=number)


def guidance(hit: EmergencyHit) -> str:
    if not hit.number:
        return generic_guidance()
    return (
        f"If this is a medical emergency, stop using this app and call {hit.number} "
        "now (or your local emergency number). I am not emergency services and I will "
        "not evaluate ingredients while you may need urgent care."
    )
