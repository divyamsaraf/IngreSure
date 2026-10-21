#!/usr/bin/env python3
"""Item 29: local dry-run count + in-memory replay for FDA GRAS, NIN, FoodEx2.

Never injects. Never opens a remote / production Supabase project.
Writes ``docs/item29/reports/l3_dry_run.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
os.chdir(_BACKEND)

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")
load_dotenv(_REPO / ".env")

from core.knowledge.ike2.etl.adapt import BOOL_FLAGS
from core.knowledge.ike2.etl.bulk_inject import _CollectWriter, inject, load_dump
from core.knowledge.ike2.etl.load_ontology import load_ontology_records
from core.knowledge.ike2.etl.sources import canonical_source
from core.knowledge.ingredient_db import get_supabase_config

_EXPECTED = {
    "fda_gras": {
        "expected_count": 1414,
        "dump": _REPO / "data" / "layer1_fda_gras.json",
        "cli_source": "fda_gras",
    },
    "nin": {
        "expected_count": 82,
        "dump": _REPO / "data" / "layer1_nin.json",
        "cli_source": "nin",
    },
    "foodex2": {
        "expected_count": 1258,
        "dump": _REPO / "data" / "layer1_foodex2.json",
        "cli_source": "foodex2",
    },
}

# Higher-trust local artifacts used as a live-shaped proxy when no local DB.
_LIVE_SHAPED_DUMPS = (
    ("e_number_catalog", _REPO / "data" / "layer1_e_numbers.json"),
    ("fssai", _REPO / "data" / "layer1_fssai.json"),
    ("ifct", _REPO / "data" / "layer1_ifct.json"),
    ("produce_catalog", _REPO / "data" / "layer1_produce_catalog.json"),
    ("animal_catalog", _REPO / "data" / "layer1_animal_catalog.json"),
)

_OUT = _REPO / "docs" / "item29" / "reports" / "l3_dry_run.json"


def _dump_count(path: Path) -> int:
    if not path.is_file():
        return -1
    _, records = load_dump(str(path))
    return len(records)


def _url_is_local(url: str) -> bool:
    u = (url or "").strip().lower()
    return "127.0.0.1" in u or "localhost" in u


def _flag_snapshot(writer: _CollectWriter) -> dict[str, dict[str, bool]]:
    return {
        name: {f: bool(row.get(f)) for f in BOOL_FLAGS}
        for name, row in writer.groups.items()
    }


def _cleared_hazards(before: dict[str, dict[str, bool]], after: _CollectWriter) -> list[dict]:
    cleared: list[dict] = []
    for name, flags in before.items():
        row = after.groups.get(name)
        if not row:
            continue
        for flag, was in flags.items():
            if was and not row.get(flag):
                cleared.append({"canonical_name": name, "flag": flag})
    return cleared


def _seed_ontology(writer: _CollectWriter) -> dict:
    records = load_ontology_records()
    stats = inject(records, "ontology", writer)
    return {"seeded": len(writer.groups), "stats": stats.as_dict()}


def _seed_live_shaped(writer: _CollectWriter) -> dict:
    ont = _seed_ontology(writer)
    extra = []
    for source, path in _LIVE_SHAPED_DUMPS:
        if not path.is_file():
            extra.append({"source": source, "skipped": "missing_dump"})
            continue
        _, records = load_dump(str(path))
        stats = inject(records, source, writer)
        extra.append({"source": source, "n": len(records), "stats": stats.as_dict()})
    return {"ontology": ont, "extra": extra, "seeded": len(writer.groups), "mode": "repo_proxy"}


def _try_local_live_rows() -> tuple[list[dict] | None, str]:
    cfg = get_supabase_config()
    if not cfg:
        return None, "no_local_supabase_env"
    if not _url_is_local(cfg.url):
        return None, f"refused_non_local_supabase_host"
    from supabase import create_client

    client = create_client(cfg.url, cfg.key)
    out: list[dict] = []
    start = 0
    page = 1000
    while True:
        rows = (
            client.table("ike2_ingredient_groups")
            .select("*")
            .range(start, start + page - 1)
            .execute()
            .data
            or []
        )
        out.extend(rows)
        if len(rows) < page:
            break
        start += page
    return out, "localhost_ike2_ingredient_groups"


def _seed_live(writer: _CollectWriter) -> dict:
    rows, mode = _try_local_live_rows()
    if rows is None:
        shaped = _seed_live_shaped(writer)
        shaped["live_db"] = mode
        return shaped
    for row in rows:
        name = row.get("canonical_name")
        if not name:
            continue
        writer.insert_group(dict(row))
    return {"seeded": len(writer.groups), "mode": mode, "live_db": mode}


def _replay(seed_fn, source: str, records: list[dict]) -> dict:
    writer = _CollectWriter()
    seed_info = seed_fn(writer)
    before = _flag_snapshot(writer)
    before_disc = writer.list_discovered_names()
    first = inject(records, source, writer)
    cleared = _cleared_hazards(before, writer)
    reject_rows = [
        {
            "canonical_name": r.get("canonical_name"),
            "violated_constraint": r.get("violated_constraint"),
        }
        for r in writer.rejects
        if isinstance(r, dict)
    ]
    second = inject(records, source, writer)
    after_disc = writer.list_discovered_names()
    new_disc = sorted(after_disc - before_disc)
    return {
        "seed": seed_info,
        "first_pass": first.as_dict(),
        "second_pass": second.as_dict(),
        "replay_idempotent": second.inserted == 0,
        "new_discovered_sample": new_disc[:25],
        "new_discovered_n": len(new_disc),
        "rejects": reject_rows,
        "cleared_hazards": cleared,
        "cleared_hazard_n": len(cleared),
        "groups_after": len(writer.groups),
    }


def _transform_replay() -> dict:
    from scripts.transform_fda_gras_bulk import transform_fda_gras_bulk
    from scripts.transform_foodex2_bulk import transform_foodex2_bulk
    from scripts.transform_nin_bulk import transform_nin_bulk

    scogs = _REPO / "data" / "raw" / "fda" / "scogs.xls"
    gras = _REPO / "data" / "raw" / "fda" / "gras_notices.xls"
    manual = _REPO / "data" / "fda_gras_manual_us.json"
    nin_in = _REPO / "data" / "nin_indian_ingredients.json"
    foodex_in = _REPO / "data" / "raw" / "foodex2" / "foodex2.csv"

    fda_rows = transform_fda_gras_bulk(scogs, gras, manual)
    nin_rows = transform_nin_bulk(nin_in) if nin_in.is_file() else []
    foodex_rows = transform_foodex2_bulk(foodex_in)

    return {
        "fda_gras": {
            "transform_n": len(fda_rows),
            "raw_scogs": scogs.is_file(),
            "raw_gras_notices": gras.is_file(),
            "manual": manual.is_file(),
            "complete": scogs.is_file() and gras.is_file(),
            "note": (
                "Committed layer1_fda_gras.json is the count of record (1,414). "
                "data/raw/ is gitignored; without SCOGS + GRAS Notices the "
                "in-memory transform only sees the 16-row manual US list."
            ),
        },
        "nin": {
            "transform_n": len(nin_rows),
            "input": nin_in.is_file(),
            "complete": nin_in.is_file(),
            "matches_expected": len(nin_rows) == _EXPECTED["nin"]["expected_count"],
        },
        "foodex2": {
            "transform_n": len(foodex_rows),
            "raw_csv": foodex_in.is_file(),
            "complete": foodex_in.is_file(),
            "note": (
                "Committed layer1_foodex2.json is the count of record (1,258). "
                "Re-run ./scripts/download_sources_5_6.sh then "
                "python backend/scripts/transform_foodex2_bulk.py to replay "
                "the adapter; this run has no raw CSV."
            ),
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Item 29 local L3 dry-run (no inject)")
    parser.add_argument(
        "--out",
        type=Path,
        default=_OUT,
        help="JSON report path",
    )
    args = parser.parse_args(argv)

    count_checks = {}
    for key, meta in _EXPECTED.items():
        n = _dump_count(meta["dump"])
        count_checks[key] = {
            "path": str(meta["dump"].relative_to(_REPO)),
            "count": n,
            "expected": meta["expected_count"],
            "ok": n == meta["expected_count"],
        }

    transforms = _transform_replay()
    replays = {}
    for key, meta in _EXPECTED.items():
        _, records = load_dump(str(meta["dump"]))
        source = canonical_source(meta["cli_source"])
        replays[key] = {
            "cli_source": meta["cli_source"],
            "canonical_source": source,
            "dump_n": len(records),
            "ontology_seeded": _replay(_seed_ontology, source, records),
            "live_seeded": _replay(_seed_live, source, records),
        }

    report = {
        "dry_run": True,
        "injected": False,
        "remote_db": False,
        "count_checks": count_checks,
        "count_checks_ok": all(v["ok"] for v in count_checks.values()),
        "transform_replay": transforms,
        "replays": replays,
        "invariants": {
            "bulk_adds_hazard_never_clearance": all(
                replay[mode]["cleared_hazard_n"] == 0
                for replay in replays.values()
                for mode in ("ontology_seeded", "live_seeded")
            ),
            "second_pass_inserts_zero": all(
                replay[mode]["replay_idempotent"]
                for replay in replays.values()
                for mode in ("ontology_seeded", "live_seeded")
            ),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {
        "out": str(args.out),
        "count_checks": {k: v["count"] for k, v in count_checks.items()},
        "count_checks_ok": report["count_checks_ok"],
        "invariants": report["invariants"],
        "ontology_seeded_inserts": {
            k: v["ontology_seeded"]["first_pass"]["inserted"] for k, v in replays.items()
        },
        "live_seeded_inserts": {
            k: v["live_seeded"]["first_pass"]["inserted"] for k, v in replays.items()
        },
        "cleared_hazards": {
            k: {
                "ontology_seeded": v["ontology_seeded"]["cleared_hazard_n"],
                "live_seeded": v["live_seeded"]["cleared_hazard_n"],
            }
            for k, v in replays.items()
        },
    }
    print(json.dumps(summary, indent=2))
    if not report["count_checks_ok"]:
        return 1
    if not report["invariants"]["bulk_adds_hazard_never_clearance"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
