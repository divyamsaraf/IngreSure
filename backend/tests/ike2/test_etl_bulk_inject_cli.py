import json

from core.knowledge.ike2.etl import bulk_inject


def test_cli_dry_run_reports_stats_without_db(tmp_path, capsys):
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps({
        "source": "wikidata",
        "ingredients": [
            {"canonical_name": "Kale", "aliases": ["Kale"], "plant_origin": True, "regions": ["Global"]},
            {"canonical_name": "Beet", "aliases": ["Beet"], "plant_origin": True, "regions": ["Global"]},
        ],
    }))

    rc = bulk_inject.main([str(dump), "--dry-run"])
    assert rc == 0

    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["source"] == "wikidata"
    assert out["inserted"] == 2
    assert out["total"] == 2


def test_cli_requires_source_for_bare_list(tmp_path):
    dump = tmp_path / "bare.json"
    dump.write_text(json.dumps([{"canonical_name": "Kale", "plant_origin": True}]))

    try:
        bulk_inject.main([str(dump), "--dry-run"])
        assert False, "expected SystemExit for missing --source"
    except SystemExit as e:
        assert e.code != 0


def test_cli_limit_caps_records(tmp_path, capsys):
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps({
        "source": "wikidata",
        "ingredients": [
            {"canonical_name": f"veg {i}", "aliases": [f"veg {i}"], "plant_origin": True, "regions": ["Global"]}
            for i in range(5)
        ],
    }))

    bulk_inject.main([str(dump), "--limit", "2", "--dry-run"])
    out = json.loads(capsys.readouterr().out)
    assert out["total"] == 2
