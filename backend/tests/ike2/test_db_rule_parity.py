"""Item 7 Prompt 2: never-SAFE verdicts identical under seed vs migration-replayed rules.

Production evaluate uses ``load_rules()`` (DB). Goldens historically used
``seeded_rules()`` only. Column parity is already covered in ``test_rules``;
this gate checks that the never-SAFE corpus cannot diverge when rules are
built from the migration-replayed table shape.
"""
from __future__ import annotations

import json
import pathlib

from core.knowledge.ike2 import rules as rules_module
from tests.ike2.golden_runner import run_case
from tests.ike2.test_rules import _migration_rule_rows

CORPUS = pathlib.Path(__file__).parent / "golden" / "must_never_be_safe.jsonl"
LEGACY = pathlib.Path(__file__).parent / "golden" / "corpus.jsonl"


def _load(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _must_never_cases() -> list[dict]:
    cases = [c for c in _load(CORPUS) if c.get("must_not_be_safe", True)]
    for c in _load(LEGACY):
        if c.get("must_not_be_safe") is True:
            cases.append(c)
    return cases


def _rules_from_migration_replay():
    rows = _migration_rule_rows()
    out = [rules_module._to_rule(rec) for rec in rows.values()]
    assert out, "migration replay produced no restriction rules"
    return out


def test_never_safe_verdicts_match_seed_and_migration_rules():
    seed = rules_module.seeded_rules()
    migrated = _rules_from_migration_replay()
    assert {r.restriction for r in seed} == {r.restriction for r in migrated}

    mismatches = []
    for case in _must_never_cases():
        seed_v = run_case(case, rules=seed)
        mig_v = run_case(case, rules=migrated)
        if seed_v != mig_v:
            mismatches.append(
                f"{case.get('raw_input')!r} tier={case.get('severity_tier')} "
                f"seed={seed_v} migration={mig_v}"
            )
    assert not mismatches, "seed vs migration rule drift:\n" + "\n".join(mismatches[:40])
