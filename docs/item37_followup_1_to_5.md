# Item 37 follow-up (Items 1–5) — 2026-10-08

Companion to `docs/item37_part_abc_closeout.md`.

## 1. Re-pollution tripwire + DISCOVERED baseline

**Preventive guard** in `validate_rows`: constraint `asserted_flags_false_pollution` quarantines any row whose `asserted_flags` holds **more than 3** false-valued names, unless `curated_asserted_negatives=True` (stem-triage deliberate-negative path).

Tests: `tests/ike2/test_asserted_false_pollution_guard.py`
- `entry_to_ike2_row` → true-only asserted, validates
- ontology row with curated `asserted_flags` → no false pollution
- raw full-boolean dump through `adapt` → quarantined
- curated-negative escape hatch allows a full false block

**Live DISCOVERED**

| Checkpoint | Count |
|------------|------:|
| INFOODS closeout baseline | 89 |
| After stem-triage (pre-restore) | 93 |
| After restoring hyphen-normalization residues (`salt-preserved fish` ↔ `salt preserved fish`, `probiotic milk-like drinks` ↔ `probiotic milk like drinks`) | **91** |

Delta vs baseline: **+2**. Stem-triage dump names are **not** among the 91 (demotion restore held). Breakdown of the 91: ~80 `synthetic=true` (Phase-1 FSSAI demotion pattern) + 11 nonsynthetic including pre-existing `oat`/`parsnip`/`pepsin`/`rennet` and others (`caviar`, `cuttlefish`, `ghee`, `honey`, …). Several of those nonsynthetic rows still show **full-block asserted pollution** on live — pre-existing / reintroduced, not new stem-triage demotions. The validate tripwire stops the next writer; a live strip pass remains a separate cleanup if desired.

---

## 2. Regional fish

Starting remainder after earlier curated fish flips: **57 SAFE** under `fish_allergy`.

| Bucket | Count |
|--------|------:|
| Matched to live INFOODS fish groups (alias / local / scientific) and flipped | **13** |
| Human-review (no match) | **44** |
| Post-flip: matched set still SAFE | **0** |

Matches (evidence in `uncertainty_flags` as `matched_infoods:<target>`): allathi→ladyfish, aluva→black pomfret, betki→giant perch, kulam paarai→yellow spotted trevally, pambada→savalai hair tail, parava→false trevally, parcus→indian tiny turbot, rani/sangada→pink perch, shelavu→barracuda, valava→white fin wolf herring, vanjaram→spanish mackerel, xiphinis→swordfish.

Human-review list (still SAFE, no INFOODS/IFCT match): see `docs/item37_regional_fish_triage.json` (`human_review`). Includes collagen (ambiguous) and vernacular IFCT names without a live scientific/alias bridge.

IFCT contributed **0** additional `fish_source=true` groups beyond INFOODS in this environment (311 INFOODS fish groups indexed).

---

## 3. Sulfured / sulphured / sulfited

Direct check (before fix): `apples dried sulfured uncooked` / `apricots…` were **SAFE** under `sulfite_sensitive` — oat-class. Bare `sulfured`/`sulphured` were unknown.

**Fix**
- `derive_identity_flags`: tokens `sulfured` / `sulphured` / `sulfited` / `sulphited` (not sulfate/sulphate/sulfated/acesulfame)
- Seam: OR derive from `query_atom` (label kept when head is plain `apples`)
- Seam: L5 unknown with label-derived hazard is trusted enough for Avoid

**After**

| Label | Verdict |
|-------|---------|
| dried sulfured/sulphured fruit | NOT_SAFE |
| apples/apricots dried sulfured/sulphured uncooked | NOT_SAFE |
| sulfured / sulphured / sulfited / sulphited | NOT_SAFE |

Mistaken ontology patch that set `sulphite_source` on fruit **heads** (apples/apricots/peaches/pears) was **reverted**.

---

## 4. Orthographic gate widened

`test_orthographic_verdict_parity` now parametrizes **every** pair from `generate_orthographic_pairs()` (61 pairs × 15 restrictions). Firm **SAFE vs NOT_SAFE** fails. SAFE↔UNCERTAIN must appear on the reviewed list in `orthographic_reviewed_safe_uncertain.json` (528 entries). Current firm splits: **0**.

---

## 5. Lecithins / lactates / nisin (today)

| Name | dairy_free | egg_free | soy_allergy |
|------|------------|----------|-------------|
| lecithin / lecithins / e322 | UNCERTAIN | UNCERTAIN | UNCERTAIN |
| sunflower lecithin | UNCERTAIN | UNCERTAIN | UNCERTAIN |
| soy lecithin | SAFE | SAFE | **NOT_SAFE** |
| lactic acid / e270 | UNCERTAIN | UNCERTAIN | UNCERTAIN |
| sodium/potassium/calcium lactate, e325 | **SAFE** | SAFE | SAFE |
| nisin / e234 | **SAFE** | SAFE | SAFE |

**SAFE for dairy on lactates and nisin is the sulfite-class gap** — WARN would be an acceptable interim; today they clear. Soy lecithin correctly fails soy. Undecided lecithin/E322 stay UNCERTAIN (acceptable interim).
