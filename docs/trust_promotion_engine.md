# Trust & Promotion Engine (operator guide)

**Tracker:** Item **4** · Spec: [`item4_trust_promotion_engine_spec.md`](item4_trust_promotion_engine_spec.md)  
**Human review end-state:** Item **5** = CLI force-human immediate-commit (no UI/pending queue).

IKE-2 compliance (`rules.py` + `compliance.evaluate`) and Coverage OS promote/neutralize/induction are **one engine**: rules decide verdicts; Coverage OS expands identity/alias/role coverage without inventing SAFE.

---

## Operator entry points

| Task | Command / path |
|------|----------------|
| Induction (unknown log → propose → interactive accept/reject) | `cd backend && python scripts/run_induction.py --ontology … --aliases … --ledger … --unknown-log …` (dry-run default; `--no-dry-run` for submit) |
| Phase 2a role seed (batch human-stamped roles) | `python scripts/seed_neutralize_roles.py --ontology … --aliases … --ledger …` |
| Promote ledger | JSONL under `data/coverage_os/` (e.g. `phase2a_role_seed_ledger.jsonl`) |
| Gate / writer code | `backend/core/knowledge/ike2/coverage_os/` (`hybrid_gate`, `promote_writer`, `induction/submit`) |

**Sign-off contract (one pattern):** any human path uses `commit_promotion(..., auto=False, reviewer_id=…, approval_rationale=…)`. Induction always force-human; `seed_neutralize_roles.py` also stamps `auto=False` even when the gate would allow `auto_promote` (more conservative than required — intentional).

---

## L3 mirror — documented no-op

`promote_writer.mirror_l3_inject` **must not write** files or DB. L3 is not a consumer of Coverage OS promotions today; building a write path with no reader is forbidden (Item 4 decision). Promotions apply to **L2 only** (`data/ontology.json`, `data/variant_aliases.json`).

---

## Out of scope here

- Temporal decay of DB `knowledge_state` → Item **4.1** (IKE-2 table rows only; L2/Coverage OS promotions are intentionally outside decay — see `core/knowledge/ike2/decay.py`). Operator CLI: `backend/scripts/ike2_decay_knowledge.py` (dry-run default; `--apply` to write). Spec: [`item4_1_temporal_confidence_decay_spec.md`](item4_1_temporal_confidence_decay_spec.md).
- Unknown-queue triage → Item **18**.
- Enzyme subtype flags → Item **3.1**.
