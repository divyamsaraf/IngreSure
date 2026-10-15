# Item 7 follow-up — Sodium sulfite / E220–E228 under-flag (investigation)

**Date:** 2026-10-07  
**Trigger:** Item 7 never-SAFE expansion found `sodium sulfite` → SAFE under `sulfite_sensitive`; initially noted as “skipped,” then reopened as a named finding.  
**Method:** Resolve + seam + evaluate locally; ontology / `e_number_catalog` / truth-anchor inspection. Live Supabase not configured in this environment — L1 truth-anchor path is the active resolve surface for these canons.

---

## 0. CI signal

Started as **`xfail(strict=True)`** naming this finding; after the same-day fix it is a real gate: `test_sulfite_family_never_safe_for_sulfite_sensitive` plus never-SAFE corpus rows for sodium sulfite / E220 / E221 / E223.

---

## 1. What `sodium sulfite` resolves to today

| Field | Value |
|-------|--------|
| Input | `sodium sulfite` |
| Layer | **`L1_truth_anchor`** |
| Source | **`truth_anchor`** (generated **e-number** anchor, not the hand sulphite cluster) |
| Canonical | `sodium sulphite` |
| `knowledge_state` | **`LOCKED`** |
| `sulphite_source` | **`False`** |
| Other true flags | `synthetic=True`, `alcohol_role=none` |
| Verdict (`sulfite_sensitive` / medical) | **`SAFE`** |

**Provenance:** Not created or modified by Item 11 USDA / FSSAI / IFCT / INFOODS injects. The living path is the **e_number_catalog → `truth_anchor_e_numbers.json`** LOCKED map. `ontology.json` `e221` mirrors the same under-flag (`sulphite_source` absent / not true; only `synthetic` asserted). Hand Tier-1 has a sulphite cluster (`sulfite` / `sulphite` / `sodium metabisulfite` / `potassium metabisulfite` → `sulphite_source=True`), but **`sodium sulfite` / `sodium sulphite` are not in that alias list**, so lookup falls through to the generated E221 anchor.

**Spelling trap:** `sodium metabisulfite` (no “ph”) hits the **hand** sulphite cluster → NOT_SAFE. `sodium metabisulphite` (British) hits the **e-number** E223 anchor → SAFE.

---

## 2. Why `derive_identity_flags` did not catch it

`flag_derive.py` has **no sulfite / sulphite / bisulfite / metabisulfite / sulfur dioxide stems at all**. Covered families today: peanut, gluten/wheat, sesame, soy, egg, fungal, animal enzyme, tree-nut (+ species→fish/shellfish).  

Resolve path for this row: L1 e-number anchor → `to_compliance_input` → `_with_derived_flags` → derive returns `{}` extras → `sulphite_source` stays false → rule never fires → SAFE.

Even if derive were fixed alone, a LOCKED catalog false would still be wrong for any consumer that trusts stored flags without re-derive; fix both catalog and derive.

---

## 3. Exposure — sulfite stems with `sulphite_source≠true`

### Ontology (authoritative file scan)

**10** rows with sulfite-family name/alias stem and `sulphite_source` not true:

| Canonical | `sulfite_sensitive` verdict today |
|-----------|-----------------------------------|
| caramel colours | UNCERTAIN (not false-SAFE; umbrella/WARN path) |
| sulphur dioxide (E220) | **SAFE** |
| sodium sulphite (E221) | **SAFE** |
| sodium hydrogen sulphite (E222) | **SAFE** |
| sodium metabisulphite (E223) | **SAFE** |
| potassium metabisulphite (E224) | **SAFE** |
| potassium sulphite (E225) | **SAFE** |
| calcium sulphite (E226) | **SAFE** |
| calcium hydrogen sulphite (E227) | **SAFE** |
| potassium hydrogen sulphite (E228) | **SAFE** |

**9 / 10 are false-SAFE** under a sulfite-restricted medical profile. Same shape as the oat finding: a real regulated allergen family clearing as Safe.

`e_number_catalog` / `layer1_e_numbers.json`: same E220–E228 set with explicit `sulphite_source: false`. FSSAI layer1 has additional noisy stem hits (junk heads carrying E22x aliases); USDA/IFCT/INFOODS dumps: 0 stem∩underflag for this family.

**Live Supabase:** not configured here — could not count `ike2_ingredient_groups` rows. Any prior e-number catalog inject would have written the same LOCKED falses; treat L1 SAFE matrix above as production-path exposure.

**Urgency:** **oat-class / same-day** — multiple SAFE hits on `sulfite_sensitive`.

---

## 4. Generalized stem∩missing-flag scan (ontology)

Heuristic name-stem scan vs stored flag (with light exclusions for plant milks, eggplant, buckwheat, coconut/nutmeg, etc.). Counts = ontology rows where stem matches and flag is not true. SAFE column = among up to 30 evaluated misses, how many resolve SAFE for the matching restriction today (noisy stems inflate some families).

| Flag | Stem∩≠true | SAFE among evaluated | Notes |
|------|-----------:|---------------------:|-------|
| fish_source | 95 | 30/30 (first 30) | Noisy regional fish names + false friends; needs curated pass, not same-day bulk |
| shellfish_source | 25 | 19/25 | Includes clear misses (`crustaceans`, `mollusks`) + noise (`mushroom`, `crabapples`) |
| dairy_source | 21 | 20/21 | Heavy false friends (`hemp milk`, `milk fish`, `kokum butter`) |
| gluten_source | 13 | 13/13 | Real gaps (`einkorn`, `khorasan`, barley forms) + derive cover holes |
| **sulphite_source** | **10** | **9 SAFE** | **Only family with a clean regulated E-number block all false-SAFE** |
| mustard_source | 9 | 7/9 | Greens/oil vs seed allergen ambiguity |
| lupin_source | 4 | 4/4 | Real gaps (`lupini`, etc.) — derive lacks lupin |
| celery_source | 3 | 2/3 | `celery` may resolve elsewhere; stalk/gap |
| sesame_source | 2 | 1/2 | `tahini paste` SAFE gap |
| egg_source | 1 | 0 | `lecithin` (ambiguous — not a clear false-SAFE) |
| soy_source | 1 | 0 | bare `soy` likely covered by resolve/derive elsewhere |
| tree_nut_source | 1 | 0 | `macadamia` |
| peanut_source | 0 | 0 | Clean |

**Verdict:** Sulfite is **not** the only stem∩missing-flag family, but it is the only one in this scan that is a **tight, regulated additive block (E220–E228) delivering systematic SAFE**. Other families need triage (noise vs real) as a follow-up; they do not dilute the sulfite same-day fix.

---

## 5. Root cause (one paragraph)

`e_number_catalog` marks E220–E228 as `sulphite_source: false` while shipping LOCKED Tier-1 anchors for every common alias. Hand sulphite anchors cover only a thin alias set, so British/EU names and E-codes prefer the wrong generated fact. `derive_identity_flags` never learned sulfite stems, so the seam cannot OR the flag back on. Result: sulfite-sensitive profiles get **SAFE** for sulfur dioxide and the common sodium/potassium/calcium sulfites.

---

## 6. Fix applied (same-day, 2026-10-07)

1. **`e_number_catalog.json`:** `sulphite_source: true` on **E220–E228 only** (sulphates / acesulfame untouched).  
2. Regenerated `truth_anchor_e_numbers.json` / `layer1_e_numbers.json`.  
3. **`derive_identity_flags`:** sulfite/sulphite/bisulfite/metabisulfite/disulfite/pyrosulfite tokens + sulfur/sulphur dioxide phrases + `e220`–`e228`; sulfate/sulphate/acesulfame do not match.  
4. **Hand sulphite Tier-1 aliases** expanded to cover the E220–E228 name/E-code set (hand wins over generated anchors on collision).  
5. **`ontology.json`:** e220–e228 rows set `sulphite_source` true + asserted.  
6. Never-SAFE goldens + parametrized regression test for sodium sulfite / E220 / E221 / E223 family (xfail removed after fix).  

**Live closeout (2026-10-07):** local Supabase E220–E228 groups backfilled via reconcile/inject (true-only asserted); L3-bypass matrix **0 SAFE**. Stem triage + derive extensions + orthographic gate: see `docs/item37_part_abc_closeout.md`.
