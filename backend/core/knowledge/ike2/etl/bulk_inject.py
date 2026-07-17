"""Bulk injection CLI for IKE-2 (design §9).

Pipeline per row: ``source adapter -> VALIDATE (CHECK mirror) -> reconcile vs
existing -> upsert into live ike2_* tables``. Rows failing a CHECK are quarantined
to a reject report (never silently dropped); the batch continues. Upserts are
idempotent, keyed by ``canonical_name`` (group), ``(group, normalized_name)``
(ingredient) and ``(normalized_alias, ingredient, region)`` (alias), so re-runs
are safe.

Usage:
    python -m core.knowledge.ike2.etl.bulk_inject data/wikidata_staging.json \
        --source wikidata [--limit N] [--dry-run] [--reject-report rejects.json]
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from types import SimpleNamespace

from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record as map_generic_record
from core.knowledge.ike2.etl.adapt_e_number import map_record as map_e_number_record
from core.knowledge.ike2.etl.reconcile import reconcile
from core.knowledge.ike2.etl.sources import canonical_source, default_knowledge_state
from core.knowledge.ike2.etl.validate import validate_rows


@dataclass
class InjectStats:
    total: int = 0
    inserted: int = 0
    updated: int = 0
    ingredients: int = 0
    aliases: int = 0
    rejected: int = 0
    needs_review: int = 0

    def as_dict(self):
        return asdict(self)


def load_dump(path: str):
    """Return ``(source, records)``. Wrapped dumps carry their own source label;
    bare lists return ``source=None`` (the caller must supply ``--source``)."""
    with open(path) as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return None, data
    return data.get("source"), data.get("ingredients", [])


def inject(records, source: str, writer) -> InjectStats:
    canon = canonical_source(source)
    if canon == "e_number_catalog":
        return _inject_e_number_catalog(records, writer)
    default_state = default_knowledge_state(canon)
    stats = InjectStats()

    for raw in records:
        stats.total += 1
        row, aliases = map_generic_record(raw, canon, default_state)

        ok, rejects = validate_rows([row])
        if rejects:
            writer.quarantine(rejects[0], canon)
            stats.rejected += 1
            continue

        existing = writer.get_group(row["canonical_name"])
        if existing is None:
            gid = writer.insert_group(row)
            stats.inserted += 1
        else:
            incoming = {f: row[f] for f in BOOL_FLAGS}
            result = reconcile(SimpleNamespace(**existing), incoming, canon)
            writer.update_group(existing["id"], result)
            gid = existing["id"]
            stats.updated += 1
            if result.needs_review:
                stats.needs_review += 1

        iid = writer.upsert_ingredient(gid, row["canonical_name"], canon)
        stats.ingredients += 1
        for alias_item in aliases:
            if len(alias_item) == 3:
                normalized_alias, region, alias_type = alias_item
            else:
                normalized_alias, region = alias_item
                alias_type = "common"
            if writer.upsert_alias(normalized_alias, iid, region, canon, alias_type=alias_type):
                stats.aliases += 1

    return stats


def _inject_e_number_catalog(records, writer) -> InjectStats:
    canon = "e_number_catalog"
    stats = InjectStats()
    for raw in records:
        stats.total += 1
        row, aliases = map_e_number_record(raw, canon, default_knowledge_state(canon))
        ok, rejects = validate_rows([row])
        if rejects:
            writer.quarantine(rejects[0], canon)
            stats.rejected += 1
            continue

        existing = writer.get_group(row["canonical_name"])
        if existing is None:
            gid = writer.insert_group(row)
            stats.inserted += 1
        else:
            incoming = {f: row[f] for f in BOOL_FLAGS}
            result = reconcile(SimpleNamespace(**existing), incoming, canon)
            writer.update_group(existing["id"], result)
            gid = existing["id"]
            stats.updated += 1
            if result.needs_review:
                stats.needs_review += 1

        iid = writer.upsert_ingredient(gid, row["canonical_name"], canon)
        stats.ingredients += 1
        for normalized_alias, region, alias_type in aliases:
            if writer.upsert_alias(normalized_alias, iid, region, canon, alias_type=alias_type):
                stats.aliases += 1
    return stats


# Only these columns exist on ike2_ingredient_groups; never POST anything else.
_GROUP_COLUMNS = set(BOOL_FLAGS) | {
    "canonical_name",
    "animal_species",
    "alcohol_content",
    "alcohol_role",
    "uncertainty_flags",
    "knowledge_state",
    "primary_source_url",
    "classification_method",
    "verdict_cap",
}


class SupabaseWriter:
    """Writes to the live (public) ike2_* tables. Rejects are collected and
    flushed to a JSON report file — the ``ike2_staging`` schema is not exposed
    over PostgREST, so quarantine lives outside the REST surface."""

    def __init__(self, client, reject_report: str = "ike2_rejects.json"):
        self.c = client
        self.reject_report = reject_report
        self._rejects = []

    def get_group(self, canonical_name):
        rows = (
            self.c.table("ike2_ingredient_groups")
            .select("*")
            .eq("canonical_name", canonical_name)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def insert_group(self, row):
        payload = {k: v for k, v in row.items() if k in _GROUP_COLUMNS}
        return (
            self.c.table("ike2_ingredient_groups")
            .insert(payload)
            .execute()
            .data[0]["id"]
        )

    def update_group(self, gid, result):
        update = dict(result.merged_flags)
        update["knowledge_state"] = result.knowledge_state
        self.c.table("ike2_ingredient_groups").update(update).eq("id", gid).execute()

    def upsert_ingredient(self, gid, normalized_name, source):
        rows = (
            self.c.table("ike2_ingredients")
            .select("id")
            .eq("group_id", gid)
            .eq("normalized_name", normalized_name)
            .limit(1)
            .execute()
            .data
        )
        if rows:
            return rows[0]["id"]
        return (
            self.c.table("ike2_ingredients")
            .insert({"group_id": gid, "normalized_name": normalized_name, "source": source})
            .execute()
            .data[0]["id"]
        )

    def upsert_alias(self, normalized_alias, ingredient_id, region, source, alias_type="common"):
        q = (
            self.c.table("ike2_aliases")
            .select("id")
            .eq("normalized_alias", normalized_alias)
            .eq("ingredient_id", ingredient_id)
        )
        q = q.is_("region", None) if region is None else q.eq("region", region)
        if q.execute().data:
            return False
        try:
            self.c.table("ike2_aliases").insert(
                {
                    "normalized_alias": normalized_alias,
                    "ingredient_id": ingredient_id,
                    "region": region,
                    "alias_type": alias_type,
                    "source": source,
                }
            ).execute()
            return True
        except Exception:
            # Lost a unique-index race; the alias already exists.
            return False

    def quarantine(self, reject, source):
        self._rejects.append({**reject, "source": source})

    def flush(self):
        if self._rejects:
            with open(self.reject_report, "w") as fh:
                json.dump(self._rejects, fh, indent=2, default=str)


class _CollectWriter:
    """Dry-run / no-DB writer: validates + reconciles fully in memory."""

    def __init__(self):
        self.groups = {}
        self._seq = 0
        self.rejects = []

    def _n(self, p):
        self._seq += 1
        return f"{p}{self._seq}"

    def get_group(self, canonical_name):
        return self.groups.get(canonical_name)

    def insert_group(self, row):
        gid = self._n("g")
        self.groups[row["canonical_name"]] = {**row, "id": gid}
        return gid

    def update_group(self, gid, result):
        for g in self.groups.values():
            if g["id"] == gid:
                g.update(result.merged_flags)
                g["knowledge_state"] = result.knowledge_state
                return

    def upsert_ingredient(self, gid, normalized_name, source):
        return f"i:{gid}:{normalized_name}"

    def upsert_alias(self, normalized_alias, ingredient_id, region, source, alias_type="common"):
        return True

    def quarantine(self, reject, source):
        self.rejects.append(reject)

    def flush(self):
        pass


def _build_writer(dry_run, reject_report):
    if dry_run:
        return _CollectWriter()
    from core.knowledge.ingredient_db import get_supabase_config

    cfg = get_supabase_config()
    if not cfg:
        raise SystemExit("Supabase not configured (need SUPABASE_URL + service role key)")
    from supabase import create_client

    return SupabaseWriter(create_client(cfg.url, cfg.key), reject_report=reject_report)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="bulk_inject", description="Bulk-inject a source dump into IKE-2.")
    parser.add_argument("file", help="path to a source dump (.json)")
    parser.add_argument("--source", help="source label (overrides the dump's own); required for bare-list dumps")
    parser.add_argument("--limit", type=int, default=None, help="process only the first N records")
    parser.add_argument("--dry-run", action="store_true", help="validate + reconcile in memory, write nothing")
    parser.add_argument("--reject-report", default="ike2_rejects.json", help="where to write quarantined rows")
    args = parser.parse_args(argv)

    file_source, records = load_dump(args.file)
    source = args.source or file_source
    if not source:
        parser.error("no source: pass --source for a bare-list dump")
    if args.limit is not None:
        records = records[: args.limit]

    writer = _build_writer(args.dry_run, args.reject_report)
    stats = inject(records, source, writer)
    writer.flush()

    print(json.dumps({"source": canonical_source(source), "dry_run": args.dry_run, **stats.as_dict()}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
