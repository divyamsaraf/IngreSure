"""E-number catalog adapter for IKE-2 bulk injection."""

from core.knowledge.ike2.e_number_catalog import entry_to_ike2_row, normalize_e_code
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, _regions_to_values
from core.normalization.normalizer import normalize_ingredient_key


def map_record(raw: dict, canonical_source: str, default_state: str):
    """Map a layer1_e_numbers record -> (group row, alias tuples with types)."""
    row = entry_to_ike2_row(raw, tier=raw.get("ike2_tier"))
    if raw.get("knowledge_state"):
        row["knowledge_state"] = raw["knowledge_state"]
    row["classification_method"] = f"bulk:{canonical_source}"

    aliases: list[tuple[str, str | None, str]] = []
    seen: set[tuple[str, str | None]] = set()
    regions = _regions_to_values(raw.get("regions"))

    def add(alias: str, alias_type: str) -> None:
        norm = normalize_e_code(alias) if alias_type == "e_number" else normalize_ingredient_key(alias)
        if not norm:
            return
        for region in regions:
            key = (norm, region)
            if key in seen:
                continue
            seen.add(key)
            aliases.append((norm, region, alias_type))

    add(row["canonical_name"], "common")
    for meta in raw.get("aliases_meta") or []:
        add(meta["normalized_alias"], meta.get("alias_type", "common"))
    for alias in raw.get("aliases") or []:
        add(alias, "common")
    for alias in raw.get("e_number_aliases") or []:
        add(alias, "e_number")

    return row, aliases
