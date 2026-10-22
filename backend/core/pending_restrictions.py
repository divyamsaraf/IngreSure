"""Session-only pending restrictions.

Asymmetric rule:
- An unconfirmed restriction *tightens* verdicts immediately (session ids).
- Persistence and any *relaxation* wait for confirmation.
- yes / that's right → persist, then clear pending.
- no / nope / cancel → drop pending (never persisted).
- only today / just today / this once → keep session tightening, persist stays false.
- Any other follow-up (including abandonment) leaves tightening in place and does not persist.

This module is in-process. It is not a profile store.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

_LOCK = threading.Lock()
_PENDING: dict[str, "PendingRestriction"] = {}

_YES = re.compile(r"^\s*(yes|y|yeah|yep|confirm|that's right|thats right|ok|okay)\s*[.!]?\s*$", re.I)
_NO = re.compile(r"^\s*(no|n|nope|nah|cancel|never mind|nevermind)\s*[.!]?\s*$", re.I)
_TODAY = re.compile(
    r"^\s*(only today|just today|this once|just for today|today only)\s*[.!]?\s*$",
    re.I,
)


@dataclass
class PendingRestriction:
    restriction_ids: list[str] = field(default_factory=list)
    dietary_preference: str | None = None
    allergens: list[str] = field(default_factory=list)
    persist: bool = False
    confirm_message: str = ""


def get_pending(user_id: str) -> PendingRestriction | None:
    with _LOCK:
        p = _PENDING.get(user_id)
        if p is None:
            return None
        return PendingRestriction(
            restriction_ids=list(p.restriction_ids),
            dietary_preference=p.dietary_preference,
            allergens=list(p.allergens),
            persist=p.persist,
            confirm_message=p.confirm_message,
        )


def set_pending(user_id: str, pending: PendingRestriction) -> None:
    with _LOCK:
        _PENDING[user_id] = pending


def abandon(user_id: str) -> None:
    with _LOCK:
        _PENDING.pop(user_id, None)


def effective_restriction_ids(user_id: str, stored: list[str] | None) -> list[str]:
    ids = list(stored or [])
    pending = get_pending(user_id)
    if not pending:
        return ids
    seen = set(ids)
    for rid in pending.restriction_ids:
        if rid and rid not in seen:
            seen.add(rid)
            ids.append(rid)
    return ids


def classify_confirm(text: str) -> str | None:
    q = text or ""
    if _YES.match(q):
        return "yes"
    if _NO.match(q):
        return "no"
    if _TODAY.match(q):
        return "only-today"
    return None


def apply_confirm(user_id: str, text: str) -> str | None:
    """Return yes / no / only-today when pending exists, else None."""
    if get_pending(user_id) is None:
        return None
    kind = classify_confirm(text)
    if kind == "no":
        abandon(user_id)
        return kind
    if kind == "only-today":
        pending = get_pending(user_id)
        if pending:
            pending.persist = False
            set_pending(user_id, pending)
        return kind
    if kind == "yes":
        return kind
    return None
