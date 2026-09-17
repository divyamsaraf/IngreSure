# Universal Label & Input Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** One label decomposer for legacy + IKE-2; L3 ontology seed; ≥85% shadow match + zero false-Safe on corpus (metric **C**).

**Architecture:** `label_decomposer` → bridge + `input_layer`; L1 staples only; bulk L3 seed via ETL.

**Spec:** `docs/superpowers/specs/2026-06-17-universal-label-input-pipeline-design.md`

## Global Constraints

- Zero false-Safe regressions (`test_golden_safety_budget`).
- TDD: failing test before production code.
- Surgical diffs; no IKE2_MODE=primary wiring in this plan.
- Shadow match target: **≥85%** on label corpus (Phase 4 gate).

---

## Phase 1 — Unified decomposer (P0) — **COMPLETE**

- [x] `nesting_split.py`, `label_decomposer.py`
- [x] `ingredient_parser.py` + `parser.py` wiring
- [x] `input_layer` → decomposer parity
- [x] L1 staples + `tests/fixtures/labels/corpus.json`
- [x] 30 Phase-1 tests green; 198 IKE-2 tests green

## Phase 2 — L3 ontology seed (P0) — **COMPLETE**

- [x] `load_ontology.py` + `scripts/seed_ike2_ontology.py` (547 rows from `data/ontology.json`)
- [x] `ontology` source in ETL (`sources.py`, `reconcile.py`); insect_derived → animal_origin in `adapt.py`
- [x] `tests/ike2/test_ontology_seed.py`, `tests/ike2/test_resolver_ontology_db.py`
- [x] Supabase key resolution (`sb_secret_*` / JWT over `sb_publishable_*`); pytest loads `backend/.env`
- [x] Ontology aliases: extra virgin olive oil, organic grain vinegar; skip structural headers (preservatives)
- [x] Seed: `cd backend && python scripts/seed_ike2_ontology.py` (local Supabase + migrations)

## Phase 3 — May contain (P1) — **COMPLETE**

- [x] `MAY_CONTAIN_PATTERNS` + clause split in `ingredient_parser.py`
- [x] `DecomposedItem.may_contain` / `ParsedAtom.may_contain`
- [x] `ComplianceInput.may_contain` wired through seam, shadow runner, golden runner
- [x] Compliance treats `trace | may_contain` as minor/cross-contact for verdict bucketing
- [x] Fixture class G + golden row for medical `peanut_allergy` + May contain statement

## Phase 4 — Label corpus + shadow gate (P1) — **COMPLETE**

- [x] 200+ labels in `tests/fixtures/labels/corpus.jsonl` (457 rows; generator `scripts/generate_label_corpus.py`)
- [x] `tests/test_label_corpus.py` — parse quality + ≥85% shadow match + zero false-Safe
- [x] `scripts/ike2_label_corpus_shadow.py` — CI/local shadow report (`--fail-below-threshold`)
- [x] CI: corpus drift check + shadow gate in `.github/workflows/ci.yml`

## Phase 5 — Intent & OCR (P2) — **COMPLETE**

- [x] OCR typo table (`OCR_TYPOS`) + label noise fixes (`core/parsing/label_text.py`)
- [x] Multi-block label selection — prefer last `Ingredients:` block / largest comma segment
- [x] Regional name hints in `normalize_ingredient_key` via `regional_ingredient_names.json`
- [x] Junk/chat corpus (`tests/fixtures/intent/junk_corpus.json`) + parametrized intent tests
- [x] `tests/test_label_ocr.py` — OCR, multi-block, regional normalization

---

## Verification (June 2026)

### Test & CI status

| Gate | Result |
|------|--------|
| Backend pytest | **1193** tests collected |
| Label corpus rows | **457** (`tests/fixtures/labels/corpus.jsonl`) |
| Shadow match rate | **≥99.5%** (threshold 85%) |
| False-Safe regressions | **0** on corpus + golden |
| CI workflow | E-number verify, corpus drift, shadow gate, full pytest |

### Stress testing

Long pasted labels with facility warnings, nutrition-facts decoys, lorem ipsum, and 200+ ingredients:

```bash
cd backend
python scripts/stress_test_long_label.py --ingredients 250 --iterations 5
python -m pytest tests/test_stress_long_label.py -v
```

Harness: `tests/fixtures/labels/stress_label.py` — `run_stress_suite()` (label-only) and `run_user_input_stress()` (intent → compliance). Typical: ~235 atoms from 250-ingredient paste; legacy/IKE-2 verdict match; IKE-2 ~15–20% lower latency than legacy on p50.

### Recent fixes (post Phase 5)

| Fix | Files |
|-----|-------|
| Gelatin halal/kosher (`porcine` in species) | `data/restrictions.json`, `ike2/compliance.py` |
| `soy` → soybean alias | `data/ontology.json` |
| External API test mocks | `tests/test_external_apis.py` (`get_with_retries`) |
| Shadow flake / import pollution | Avoid importing check scripts during pytest |

### Production posture

- **Legacy:** User-facing verdicts — production ready.
- **IKE-2 shadow:** Set `IKE2_MODE=shadow` in staging; monitor `ike2_shadow_soak_report.py`.
- **IKE-2 primary:** Not implemented — do not set `IKE2_MODE=primary` until soak gates pass (see IKE-2 spec §8).

---

### Task 1: `split_by_nesting` + tests

**Files:** `backend/core/parsing/nesting_split.py`, `backend/tests/test_label_decomposer.py`

### Task 2: Prefix, clause, semicolon in `ingredient_parser.py`

**Files:** modify `ingredient_parser.py`; tests in `test_label_decomposer.py`

### Task 3: `flatten_ingredients` uses shared split

**Files:** modify `parser.py`; extend `test_parser_and_profile.py`

### Task 4: `label_decomposer.py` + `input_layer` parity

**Files:** `label_decomposer.py`, `input_layer.py`, `tests/ike2/test_input_layer.py`

### Task 5: L1 staples + bread verdict tests

**Files:** `truth_anchor.py`, `tests/ike2/test_bread_label.py`, `tests/fixtures/labels/corpus.json`
