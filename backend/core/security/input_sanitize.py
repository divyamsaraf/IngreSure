"""
Input sanitization/validation shared by /chat/grocery and /profile.

Pure functions (no FastAPI/framework dependency) so they're easy to unit test.
"""
from __future__ import annotations

import re
from typing import List, Optional

# Strip NUL and other C0/C1 control chars, but keep \n (0x0A) and \t (0x09).
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Collapse runs of 3+ spaces/tabs into a single space (extreme whitespace padding).
_EXTREME_INLINE_WHITESPACE_RE = re.compile(r"[ \t]{3,}")
# Collapse runs of 4+ newlines (extreme blank-line padding) down to 3 (two blank lines).
_EXTREME_BLANK_LINES_RE = re.compile(r"\n{4,}")

PROFILE_LIST_MAX_ITEMS = 50
PROFILE_LIST_ITEM_MAX_LENGTH = 64


def sanitize_chat_query(text: str) -> str:
    """
    Strip NUL/control characters (keeping \\n and \\t) and collapse extreme
    whitespace/blank-line padding. Does not trim normal spacing or enforce
    length (length is validated separately against MAX_CHAT_MESSAGE_LENGTH).
    """
    if not text:
        return text
    cleaned = _CONTROL_CHARS_RE.sub("", text)
    cleaned = _EXTREME_INLINE_WHITESPACE_RE.sub(" ", cleaned)
    cleaned = _EXTREME_BLANK_LINES_RE.sub("\n\n\n", cleaned)
    return cleaned


def validate_profile_lists(allergens: Optional[List[str]], lifestyle: Optional[List[str]]) -> None:
    """
    Validate allergens/lifestyle: at most PROFILE_LIST_MAX_ITEMS items each,
    and each item at most PROFILE_LIST_ITEM_MAX_LENGTH characters.

    Raises ValueError with a user-facing message when invalid; returns None otherwise.
    """
    for field_name, values in (("allergens", allergens), ("lifestyle", lifestyle)):
        if not values:
            continue
        if len(values) > PROFILE_LIST_MAX_ITEMS:
            raise ValueError(f"{field_name} must have at most {PROFILE_LIST_MAX_ITEMS} items.")
        for item in values:
            if item and len(item) > PROFILE_LIST_ITEM_MAX_LENGTH:
                raise ValueError(
                    f"{field_name} items must be at most {PROFILE_LIST_ITEM_MAX_LENGTH} characters."
                )
