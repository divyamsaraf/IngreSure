"""Plain-language echo of what the pipeline understood."""
from __future__ import annotations

_RID_LABEL = {
    "gluten_free": "gluten-free",
    "dairy_free": "dairy-free",
    "vegan": "vegan",
    "peanut_allergy": "peanut allergy",
    "jain": "Jain",
    "halal": "Halal",
    "vegetarian": "vegetarian",
    "egg_free": "egg-free",
}


def compose_understanding_echo(
    *,
    eval_names: list[str],
    unparsed: list[str] | None = None,
    block_kind: str = "label",
    restriction_ids: list[str] | None = None,
) -> str:
    """Return a short echo, or empty string when there is nothing to say."""
    bits: list[str] = []
    if block_kind == "recipe":
        bits.append("Treating this as a recipe, not a packaged label.")
    elif block_kind == "multi_product":
        bits.append("That looks like more than one product.")
    elif block_kind == "product_name":
        bits.append("That looks like a product name, not an ingredient list.")

    names = [n for n in (eval_names or []) if n]
    if names:
        shown = ", ".join(names[:12])
        extra = f" (+{len(names) - 12} more)" if len(names) > 12 else ""
        bits.append(f"I understood: {shown}{extra}.")

    leftover = [u for u in (unparsed or []) if u]
    if leftover:
        bits.append("I could not use: " + "; ".join(leftover[:4]) + ".")

    rids = restriction_ids or []
    if rids:
        labels = [_RID_LABEL.get(r, r.replace("_", " ")) for r in rids]
        bits.append("Checking against: " + ", ".join(labels) + ".")

    return " ".join(bits)
