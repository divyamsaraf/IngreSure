"""Split ingredient strings by top-level (), [], and {} nesting."""
import re

_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {")": "(", "]": "[", "}": "{"}


def split_by_nesting(text: str) -> list[str]:
    """Flatten nested delimiters; commas inside nesting become separate items."""
    if not text or not text.strip():
        return []
    out: list[str] = []
    depth = 0
    opener = ""
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _OPEN:
            if depth == 0 and i > start:
                chunk = text[start:i].strip()
                if chunk:
                    out.append(chunk)
            if depth == 0:
                opener = ch
            depth += 1
            if depth == 1:
                start = i + 1
            i += 1
        elif ch in _CLOSE and depth > 0 and _CLOSE[ch] == opener:
            depth -= 1
            if depth == 0:
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
    if depth == 0 and start < len(text):
        chunk = text[start:].strip()
        if chunk:
            out.append(chunk)
    return out
