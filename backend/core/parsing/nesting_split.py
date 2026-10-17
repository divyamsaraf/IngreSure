"""Split ingredient strings by top-level (), [], and {} nesting."""
import re

_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {")": "(", "]": "[", "}": "{"}


def split_top_level(text: str, seps: str = ",;") -> list[str]:
    """Split on ``seps`` only when not inside (), [], or {}."""
    if not text or not text.strip():
        return []
    out: list[str] = []
    stack: list[str] = []
    start = 0
    for i, ch in enumerate(text):
        if ch in _OPEN:
            stack.append(ch)
        elif ch in _CLOSE and stack and _CLOSE[ch] == stack[-1]:
            stack.pop()
        elif ch in seps and not stack:
            chunk = text[start:i].strip()
            if chunk:
                out.append(chunk)
            start = i + 1
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def split_by_nesting(text: str) -> list[str]:
    """Flatten nested delimiters; commas inside nesting become separate items.

    Uses a stack so mixed ``()`` / ``[]`` / ``{}`` (e.g. vitamin braces inside
    flour parentheticals) do not swallow the outer list.
    """
    if not text or not text.strip():
        return []
    out: list[str] = []
    stack: list[str] = []
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _OPEN:
            if not stack and i > start:
                chunk = text[start:i].strip()
                if chunk:
                    out.append(chunk)
            stack.append(ch)
            if len(stack) == 1:
                start = i + 1
            i += 1
        elif ch in _CLOSE and stack and _CLOSE[ch] == stack[-1]:
            stack.pop()
            if not stack:
                inner = text[start:i].strip()
                if inner:
                    for part in re.split(r"\s*,\s*", inner):
                        part = part.strip()
                        if part:
                            out.extend(split_by_nesting(part))
                start = i + 1
            i += 1
        else:
            i += 1
    if not stack and start < len(text):
        chunk = text[start:].strip()
        if chunk:
            out.append(chunk)
    return out
