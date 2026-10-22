"""Split ingredient strings by top-level (), [], and {} nesting."""
import re

_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {")": "(", "]": "[", "}": "{"}
# INS/E codes with sub-letters or roman numerals must stay one atom
# (A34: "INS 322(ii)" is not "INS 322" + "ii").
_ADDITIVE_CODE = re.compile(
    r"\b(?:e|ins)\s*\d{2,4}\s*(?:\([ivxlcdm]+\)|\([a-z]\)|[a-z])?(?!\w)",
    re.IGNORECASE,
)


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


def _restore_additives(text: str, placeholders: dict[str, str]) -> str:
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text


def split_by_nesting(text: str) -> list[str]:
    """Flatten nested delimiters; commas inside nesting become separate items.

    Uses a stack so mixed ``()`` / ``[]`` / ``{}`` (e.g. vitamin braces inside
    flour parentheticals) do not swallow the outer list.

    Unclosed delimiters still flush remaining members (A15) instead of
    dropping them. Additive codes with sub-variants are held intact (A34).
    """
    if not text or not text.strip():
        return []
    placeholders: dict[str, str] = {}

    def _hold(match: re.Match[str]) -> str:
        key = f"\x00ADD{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key

    protected = _ADDITIVE_CODE.sub(_hold, text)
    out = _split_by_nesting_body(protected)
    return [_restore_additives(part, placeholders) for part in out]


def _split_by_nesting_body(text: str) -> list[str]:
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
    if start < len(text):
        leftover = text[start:].strip()
        if leftover:
            if stack:
                for part in re.split(r"\s*,\s*", leftover):
                    part = part.strip()
                    if part:
                        out.extend(split_by_nesting(part))
            else:
                out.append(leftover)
    return out
