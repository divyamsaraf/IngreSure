"""True-only derive write-back: real gaps applied; false friends skipped."""
import json
import subprocess
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "scripts"))

from item44_derive_true_only_writeback import (  # noqa: E402
    _apply_trues,
    _classify,
    _gaps_for_name,
)


def test_classify_rejects_milk_of_magnesia():
    assert _classify("milk of magnesia", "dairy_source") == "false_friend"
    assert _classify("bean curd", "dairy_source") == "false_friend"


def test_classify_accepts_whey_and_egg_lecithin():
    assert _classify("whey protein concentrate", "dairy_source") == "real_gap"
    assert _classify("egg lecithin", "egg_source") == "real_gap"


def test_apply_trues_is_true_only_and_sets_asserted():
    row = {
        "canonical_name": "egg lecithin",
        "egg_source": False,
        "dairy_source": False,
        "asserted_flags": [],
    }
    gaps = _gaps_for_name("egg lecithin", row)
    assert "egg_source" in gaps
    out = _apply_trues(row, ["egg_source"])
    assert out["egg_source"] is True
    assert "egg_source" in (out.get("asserted_flags") or [])
    row2 = {
        "canonical_name": "x",
        "dairy_source": True,
        "asserted_flags": ["dairy_source"],
    }
    out2 = _apply_trues(row2, ["egg_source"])
    assert out2["dairy_source"] is True


def test_dry_run_script_writes_proof(tmp_path):
    ont = {
        "ontology_version": "test",
        "ingredients": [
            {
                "canonical_name": "egg lecithin",
                "aliases": [],
                "egg_source": False,
                "dairy_source": False,
                "asserted_flags": [],
            },
            {
                "canonical_name": "magnesium hydroxide",
                "aliases": ["milk of magnesia"],
                "dairy_source": False,
                "asserted_flags": [],
            },
        ],
    }
    path = tmp_path / "ontology.json"
    path.write_text(json.dumps(ont), encoding="utf-8")
    script = _BACKEND / "scripts" / "item44_derive_true_only_writeback.py"
    # Script writes proof under backend/.local_reports — run and check stdout counts.
    proc = subprocess.run(
        [sys.executable, str(script), "--ontology", str(path)],
        cwd=_BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert '"write": false' in proc.stdout or '"write": false' in proc.stdout.replace(
        " ", ""
    )
    # ontology unchanged
    after = json.loads(path.read_text())
    assert after["ingredients"][0]["egg_source"] is False
