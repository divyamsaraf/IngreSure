# L5 Staples — complete-record spec

**Status:** SPEC ONLY. This document defines the staple complete-record, license gates, generation/validation rules, and Wave 1 review process.

**This PR does not ingest.** It does not write ontology JSON, IKE-2 DB groups, aliases, or Layer-1 dumps. No adapter run. No bulk inject. No promotion.

**Authority for later build:** this spec. Serving and ingest code stay unchanged until a later, explicit ingest PR.

---

## 0. What a staple is

A **staple** is a commonly eaten commodity or commodity-equivalent name that people expect a region-aware diet/allergen engine to already know: a vegetable, fruit, grain, pulse, spice, oil, dairy cut, meat cut, fish, fungus, beverage, or common additive — plus the local names that resolve to it.

A staple is **not** a branded SKU, a restaurant dish, or an unresolved compound umbrella (`spices`, `vegetable oil`, `natural flavors`). Those stay outside L5 until they have their own complete records.

Wave 1 ships a **global core** plus **India** and **USA** overlays. Counts below are estimates, not targets that authorize thinning review.

---

## 1. Complete-record schema

Every staple that may later be ingested must be representable as one **complete record**. Incomplete records stay `DISCOVERED` and cannot drive firm SAFE.

### 1.1 Identity

| Field | Required | Rule |
|---|---|---|
| `canonical_name` | yes | English display name, title-case for UI, stored as given. One preferred name per staple. |
| `normalized_key` | yes | Output of `normalize_ingredient_key` (`backend/core/normalization/normalizer.py`). Lookup key. |
| `region` | yes | ISO-like code used elsewhere in-repo: `IN`, `US`, `GLOBAL`, later `AE`, `JP`, … |
| `language` | yes | BCP-47 / existing label-language codes (`en`, `hi`, `ar`, …). |
| `staple_id` | yes | Stable UUID (or ULID) for the *concept*. Shared across region+language rows of the same food. |
| `local_names` | yes if any | Extra surface forms for this region+language. Each form is also normalized. |
| `taxon` | yes for biological foods | Scientific name when the staple is a plant, fungus, or animal. Optional for pure additives. |
| `category` | yes | One of §6. |

**Uniqueness:** `(region, language, normalized_key)` is unique. Two staples must not share that triple. The same `staple_id` may appear once per region+language (India `en` + India `hi` + USA `en` + global `en`).

A local name that normalizes to another staple’s key is an **alias of that staple**, not a new row. Collisions are review-by-exception (§4), not silent overwrite.

### 1.2 Asserted allergen and diet flags

Flags reuse the IKE-2 columns already enforced in `backend/core/knowledge/ike2/rules.py` (`VALID_FLAG_COLUMNS`) and `data/restrictions.json`. L5 does not invent a parallel flag set.

**Always present on a complete record (boolean, never implicit false-as-asserted):**

Allergen / medical:

- `peanut_source`, `tree_nut_source`, `soy_source`, `sesame_source`
- `fish_source`, `shellfish_source`
- `mustard_source`, `lupin_source`, `celery_source`
- `onion_source`, `garlic_source`
- `gluten_source`, `dairy_source`, `egg_source`, `sulphite_source`

Diet / religious (Jain and neighbors):

- `animal_origin`, `plant_origin`, `synthetic`
- `root_vegetable` — Jain underground / root-tuber class (potato, carrot, onion, garlic, hing as underground resin, etc.)
- `fungal` — yeast, mushroom, koji, tempeh, mycoprotein
- `fermented` — fermentation class (Jain WARN today; still asserted when true)
- `insect_derived`, `bee_product`
- `enzyme_animal_source`, `enzyme_microbial_source`

Alcohol:

- `alcohol_role` — `none` / `ingredient` / process role, same as IKE-2
- `alcohol_content` — numeric or null; null means unevaluated, not zero

Identity helpers (when applicable):

- `animal_species` — `pig`, `cow`, `bird`, `fish`, `shellfish`, …; required when `animal_origin` is true
- `meat_fish_derived` is **derived** at evaluate time (`compliance.py`); do not store a conflicting asserted value

### 1.3 True-only asserted flags

`asserted_flags` is a list of flag **names whose stored value is true**.

- A stored `true` may be listed. That is the only honest assertion.
- A stored `false` is **not** asserted. Absence of a name means “not asserted true,” not “reviewed false.”
- Inventing asserted falses is forbidden. This matches `backend/core/knowledge/ike2/etl/backfill_asserted_flags.py` and the `asserted_flags_unreviewed_negative` / `asserted_flags_false_pollution` checks in `backend/core/knowledge/ike2/etl/validate.py`.
- Deliberate negatives stay on the reviewed-negatives registry (`data/ike2_reviewed_negatives.json`) and are out of Wave 1 staple minting unless a human adds them there first.

### 1.4 Provenance

| Field | Required on complete record | Rule |
|---|---|---|
| `primary_source` | yes | Canonical source key from `backend/core/knowledge/ike2/etl/sources.py` (or a new key added to the allowlist first). |
| `primary_source_url` | yes for `VERIFIED` / `LOCKED` | Same invariant as `verified_requires_source` in `validate.py`. |
| `license_spdx` | yes | Must pass `license_check` against `backend/core/knowledge/ike2/etl/license_allowlist.json`. |
| `reviewer` | yes for `VERIFIED` / `LOCKED` | Human id. Not an LLM name. |
| `trust_timestamp` | yes | Maps to IKE-2 `trust_refreshed_at`. UTC instant. Decay clock (`backend/core/knowledge/ike2/decay.py`) uses this, not `updated_at`. |
| `knowledge_state` | yes | One of §3.2. |
| `class_trusted` | yes (boolean) | Owner-approved class exemption for firm SAFE. Default `false`. |
| `verified` | yes (boolean) | `true` only when `knowledge_state` is `VERIFIED` or `LOCKED` **and** the region is allowed to verify (§7). |
| `uncertainty_flags` | when needed | Non-empty when origin is dual or process is ambiguous. Dual `animal_origin` + `plant_origin` **requires** uncertainty (`dual_origin_requires_uncertainty`). |

---

## 2. License-checked sources (cite only; do not ingest)

All future staple generation must call `license_check` (`backend/core/knowledge/ike2/etl/license_check.py`) with the source id and SPDX. Fail-closed: missing SPDX or unknown license is a deny.

Allowlist file (already in repo):

- `backend/core/knowledge/ike2/etl/license_allowlist.json`

Allowed SPDX in that file today: `CC0-1.0`, `CC-BY-4.0`, `ODbL-1.0`, `public-domain`, `OGL-UK-3.0`, `OGL-Canada-2.0`.

Per-source pins in the same file:

- `produce_catalog` → `CC0-1.0`, `public-domain`
- `animal_catalog` → `CC0-1.0`, `public-domain`
- `infoods` → `CC-BY-4.0`
- `cofid` → `OGL-UK-3.0`
- `canadian_nutrient_file` → `OGL-Canada-2.0`

### 2.1 India first — files already in repo

Use these as **name and alias evidence** when a later ingest PR runs. This spec does not load them.

| Source key | License / notes | Files already in repo |
|---|---|---|
| `nin` | Curated India composition names already checked in. Default state `AUTO_CLASSIFIED` in `sources.py`. | `data/layer1_nin.json`, `data/nin_indian_ingredients.json` |
| `ifct` | IFCT 2017 names / vernacular aliases. Default `AUTO_CLASSIFIED`. | `data/layer1_ifct.json` |
| `fssai` | Additive / permitted-substance names. Default `AUTO_CLASSIFIED`. | `data/layer1_fssai.json`, `data/fssai_prohibited_substances.json` |
| `produce_catalog` | **CC0-1.0** (allowlisted). Curated plant seed, not scraped. | `backend/core/knowledge/ike2/etl/adapters/seeds/produce_catalog_seed.json`, `data/layer1_produce_catalog.json` |
| `animal_catalog` | **CC0-1.0** (allowlisted). Lands `DISCOVERED` today. | `backend/core/knowledge/ike2/etl/adapters/seeds/animal_catalog_seed.json`, `data/layer1_animal_catalog.json` |
| local names | Project-owned maps, not a licensed dump. | `data/regional_ingredient_names.json`, `backend/data/india_ingredients_catalog.json` |

India Wave 1 may cite NIN / IFCT / FSSAI / produce / regional maps. It must not treat crowd taxonomies as truth.

### 2.2 USA first — files already in repo

| Source key | License / notes | Files already in repo |
|---|---|---|
| `usda` | USDA FDC dump already transformed (`usda_fdc` → `usda`). Default `AUTO_CLASSIFIED`. | `data/layer1_usda_fdc.json`, `data/usda_reviewed_asserted_clears.json` |
| `fda` | FDA GRAS names (`fda_gras` → `fda`). Default `AUTO_CLASSIFIED`. | `data/layer1_fda_gras.json`, `data/fda_gras_manual_us.json` |
| `infoods` | **CC-BY-4.0** (allowlisted). FAO/INFOODS AnFooD. | `data/layer1_infoods_anfood.json` |
| `produce_catalog` / `animal_catalog` | **CC0-1.0** as above. | same seed / layer1 files |
| `e_number_catalog` | Dedicated LOCKED path only. Not a staple mint shortcut. | `data/layer1_e_numbers.json`, `backend/core/knowledge/ike2/truth_anchor_e_numbers.json` |

### 2.3 Allowlisted but blocked until the owner confirms OGL

These keys are already in `license_allowlist.json` and `test_license_check.py` accepts them. **There is no Layer-1 file for them in this repo. Do not ingest.**

| Source key | SPDX in allowlist | Covers | Owner gate |
|---|---|---|---|
| `cofid` | `OGL-UK-3.0` | CoFID (McCance and Widdowson) | Owner must confirm the Open Government Licence still covers the intended extract and attribution text. |
| `canadian_nutrient_file` | `OGL-Canada-2.0` | Canadian Nutrient File | Owner must confirm OGL-Canada still covers the intended extract and attribution text. |

Confirmation is a written owner decision, not an LLM guess. Until that note exists, CoFID/CNF are **license-known, ingest-forbidden**.

### 2.4 Sources that must not mint Wave 1 staples

Default `DISCOVERED` in `sources.py` — useful for later discovery, **not** staple truth:

- `data/layer1_off_taxonomy.json` (`openfoodfacts`)
- `data/layer1_wikidata.json`, `data/layer1_chebi.json`, `data/layer1_pubchem.json`, `data/layer1_foodex2.json`
- `enrichment_api`

Crowd or inferred rows may appear as **signals** in review-by-exception (§4). They cannot be `primary_source` for a `VERIFIED` staple.

---

## 3. Generation and validation

### 3.1 How a draft is generated (later PR only)

1. Collect candidate names from license-checked files in §2 for `GLOBAL`, `IN`, and `US`.
2. Normalize each name. Deduplicate on `(region, language, normalized_key)`.
3. Attach taxon when the source already carries a scientific name (IFCT / USDA aliases often do).
4. Propose flags from **identity**, not from an LLM:
   - systemic derive in `backend/core/knowledge/ike2/flag_derive.py` (peanut / tree-nut / gluten / dairy / egg / fungal / sulphite / …)
   - Jain `root_vegetable` / `onion_source` / `garlic_source` from produce seed and known underground class
   - implication CHECKs in §3.3
5. Leave `asserted_flags` true-only.
6. Start `knowledge_state = DISCOVERED` unless the source’s default in `sources.py` is higher **and** the class is eligible for `AUTO_CLASSIFIED`.
7. Never write the draft to ontology or DB from this spec PR.

### 3.2 Knowledge ladder

Same ranks as `compliance._KS_RANK` / `decay.py`, minus serving-only `UNCLASSIFIED` / `CLASSIFIED` leftovers:

| State | Meaning for a staple | May drive firm SAFE? |
|---|---|---|
| `DISCOVERED` | Seen, not class-reviewed. Crowd or first draft. | **No.** Serving already caps clean-pass to WARN. |
| `AUTO_CLASSIFIED` | License-checked source + derive + CHECKs. No human on this row. | **Only if `class_trusted = true`.** |
| `VERIFIED` | Human reviewer signed the complete record. `primary_source_url` + `trust_timestamp` set. | **Yes.** |
| `LOCKED` | Frozen truth (e-number catalog path today). Staples almost never start here. | **Yes.** |

Promotion is one step at a time. Decay is one step down (`VERIFIED` → `AUTO_CLASSIFIED` after 180 days; `AUTO_CLASSIFIED` → `DISCOVERED` after 90 days; `LOCKED` never decays). A later ingest must set `trust_timestamp` so decay has a clock.

**Firm SAFE rule (L5 staples):** a staple may participate in a firm SAFE verdict only when:

- `knowledge_state` is `VERIFIED` or `LOCKED`, **or**
- `knowledge_state` is `AUTO_CLASSIFIED` **and** `class_trusted` is true for that category (owner-approved class, e.g. fresh whole produce from the CC0 produce catalog).

`DISCOVERED`, `UNCLASSIFIED`, UAE rows, and Japan rows before G4 CAA confirmation cannot be firm SAFE. Positive hazard FAILs still stand regardless of state (existing Item 34 asymmetry).

`class_trusted` is not a shortcut around missing flags, failed CHECKs, or a disagreeing-signal queue item. It only answers the SAFE-floor question for an otherwise complete, non-conflicting `AUTO_CLASSIFIED` row.

### 3.3 Implication CHECKs

A staple draft is invalid if any existing IKE-2 CHECK in `validate.py` fails. Reuse the same names:

| Constraint | Predicate |
|---|---|
| `insect_implies_animal` | `insect_derived` ⇒ `animal_origin` |
| `egg_implies_animal` | `egg_source` ⇒ `animal_origin` |
| `dairy_implies_animal` | `dairy_source` ⇒ `animal_origin` |
| `fish_implies_animal` | `fish_source` ⇒ `animal_origin` |
| `shellfish_implies_animal` | `shellfish_source` ⇒ `animal_origin` |
| `enzyme_animal_implies_animal` | `enzyme_animal_source` ⇒ `animal_origin` |
| `enzyme_origin_not_both` | not both enzyme animal and microbial |
| `verified_requires_source` | `VERIFIED` / `LOCKED` ⇒ `primary_source_url` |
| `dual_origin_requires_uncertainty` | animal+plant ⇒ `uncertainty_flags` non-empty |
| `asserted_flags_unreviewed_negative` | no unreviewed asserted false |
| `asserted_flags_false_pollution` | ≤3 asserted falses unless curated escape hatch |

L5 adds staple-specific CHECKs (validate in the later ingest PR; do not implement here):

| Constraint | Predicate |
|---|---|
| `complete_requires_identity` | `canonical_name`, `normalized_key`, `region`, `language`, `staple_id`, `category` present |
| `complete_requires_taxon_if_biological` | category in vegetables/fruits/herbs/grains/pulses/nuts/dairy/eggs/meat/fish/fungi ⇒ `taxon` present |
| `animal_requires_species` | `animal_origin` ⇒ `animal_species` set |
| `jain_root_consistency` | `onion_source` or `garlic_source` ⇒ `root_vegetable` |
| `fungal_not_plant_xor` | `fungal` true does not require `plant_origin`; do not force plant on yeast/mushroom |
| `alcohol_role_none_if_no_content` | `alcohol_role = none` ⇔ (`alcohol_content` is null or 0) |
| `unique_region_language_key` | no duplicate `(region, language, normalized_key)` |
| `true_only_asserted` | every name in `asserted_flags` has stored value `true` |
| `uae_not_verified` | `region = AE` ⇒ `verified = false` and state ≠ `VERIFIED`/`LOCKED` |
| `japan_unverified_until_g4` | `region = JP` ⇒ `UNVERIFIED` / not `verified` until G4 CAA confirmation is recorded |

### 3.4 Completeness gate

A record is **complete** only when all of the following hold:

1. Identity fields in §1.1 are filled (taxon rule included).
2. Every flag in §1.2 is **present as a key** (true, false, or null). Null means unevaluated — the row is then *not* complete.
3. `asserted_flags` is true-only and matches the true keys.
4. All implication CHECKs pass.
5. Provenance fields for the claimed `knowledge_state` are filled.
6. Region gates in §7 pass.
7. License check passes for `primary_source` + `license_spdx`.

The completeness gate is a hard fail: incomplete rows cannot be batched as `VERIFIED`, cannot be `class_trusted`, and cannot enter the Wave 1 “done” set. They may sit in `DISCOVERED` for later review.

---

## 4. Review-by-exception

Humans do not re-label every carrot. They see **disagreements**, ranked by how often the name appears.

### 4.1 What is a disagreeing signal

A staple candidate goes to a human when any of these fire:

- Two license-checked sources disagree on a hazard or diet flag (e.g. USDA plant vs IFCT animal; NIN missing `root_vegetable` on potato).
- Derive (`flag_derive.py`) disagrees with a source-asserted true.
- Dual origin without an uncertainty flag.
- Normalized-key collision across two `staple_id`s in the same region+language.
- Crowd/OFF/Wikidata signal contradicts a license-checked source (crowd loses; human confirms the keep).
- Jain class ambiguity (is X a root? is yeast fungal? is idli batter fermented?).
- Alcohol role unclear.

Agreeing, complete, class-trusted produce can stay `AUTO_CLASSIFIED` without a human row review.

### 4.2 Ranking and batches

1. Count frequency from existing unknown-queue / label-corpus / regional-name hits (`normalized_key` frequency). Higher frequency first.
2. Present to humans in **batches of 200** queue items.
3. Each item: canonical, local names, proposed flags, source snippets, the disagreeing signals, and the implied restrictions (`data/restrictions.json` / Jain rules).
4. Human sets or confirms trues, leaves falses unasserted, sets `reviewer` + `trust_timestamp`, and may promote to `VERIFIED`.

### 4.3 Audit sample — zero wrong hazard flags

Every wave, after the exception queue for that wave is empty (or deferred with reason):

- Draw an **audit sample of 300** complete records from the wave set (global core + IN + US for Wave 1). Stratify across §6 categories; do not audit only produce.
- A **wrong hazard flag** is a missed true or a false true on any allergen/diet flag that can FAIL a profile (peanut, tree nut, soy, sesame, fish, shellfish, gluten, dairy, egg, sulphite, insect, bee, root vegetable, onion, garlic, fungal, alcohol, animal origin / species). Jain `fermented` WARN misses count as audit defects too.
- **Pass bar: ZERO wrong hazard flags in the 300.**
- Any single miss → **redo the wave** (re-derive, re-queue disagreements, new 300-sample). Do not ship a partial pass.

This audit is human. An LLM may not grade the sample.

---

## 5. LLM role — draft offline only

- An LLM **may** draft candidate lists, alias clusters, or taxon guesses **offline**, off the serving path, off CI, off evaluate/resolve.
- LLM output is **never truth**. It is not `primary_source`. It cannot set `verified`, `class_trusted`, `knowledge_state`, or `asserted_flags`.
- LLM output must not be imported onto a staple row without a human or a deterministic derive+CHECK path replacing it.
- The serving path (`compliance.evaluate`, resolver, chat, `/api/v1/evaluate-*`) must not call an LLM to classify staples.
- If an offline draft and a license-checked source disagree, the disagreement is a §4 queue item. The LLM side has no weight.

---

## 6. Wave 1 categories and size

Wave 1 = **global core + India + USA**.

**Estimate: 1,000–1,500 complete records per region, including the shared global core.** The same potato counted in GLOBAL and IN is one `staple_id` and two region rows; do not treat 1,500×3 as 4,500 distinct foods. The range is an estimate for planning review batches, not a quota and not a reason to skip audit.

### Categories (required coverage)

Every category must appear in the Wave 1 estimate and in the 300-audit stratification:

| Category | Examples (illustrative, not an ingest list) |
|---|---|
| vegetables | spinach, tomato, bitter gourd, bottle gourd |
| fruits | apple, banana, mango |
| herbs/spices | turmeric, cumin, hing, mustard seed |
| grains/flours | rice, wheat, atta, maida, ragi, bajra |
| pulses | chickpea, masoor, toor, urad, moong |
| nuts/seeds | almond, peanut, sesame, kaju |
| oils | sunflower oil, mustard oil, ghee (ghee is also dairy) |
| sweeteners | sugar, jaggery, honey (bee_product) |
| dairy | milk, paneer, dahi, khoa |
| eggs | chicken egg |
| meat | chicken, goat, pork (species required) |
| fish/seafood | salmon, shrimp, pomfret |
| fungi | mushroom, yeast |
| beverages | tea, coffee, lassi |
| common additives | e-number staples only via the existing LOCKED catalog path; do not mint new LOCKED additives here |
| local names | `data/regional_ingredient_names.json` forms (bajra, palak, gajar, doodh, …) attached to the staple they normalize to |

A category hole (zero complete records) fails the completeness gate for the wave.

---

## 7. Region gates (UAE, Japan)

`backend/core/region_profile.py` onboarding order is India, USA, Canada, UK, AU/NZ, EU, UAE. Japan is not in Wave 1.

### 7.1 UAE (`AE`)

- `verified = false` on every UAE staple row.
- `knowledge_state` must not be `VERIFIED` or `LOCKED`.
- UAE may hold `DISCOVERED` drafts only. No class-trusted UAE set in Wave 1.
- Do not mint a UAE Wave 1 overlay.

### 7.2 Japan (`JP`)

- Japan staples are **UNVERIFIED** until **G4 CAA** (Consumer Affairs Agency) confirmations exist and are recorded as the primary regulatory source.
- Until that confirmation: `verified = false`; state is not `VERIFIED` / `LOCKED`; `class_trusted = false`.
- Do not mint a Japan Wave 1 overlay.
- A later G4 PR may lift this gate; this spec does not.

### 7.3 Wave 1 regions only

`GLOBAL`, `IN`, `US`. No `AE`, no `JP`, no `CA`/`GB` CoFID-or-CNF overlay until the owner confirms OGL (§2.3).

---

## 8. Out of scope (this PR and Wave 1 ingest)

- Any write to `data/ontology.json`, `data/dynamic_ontology.json`, `ike2_ingredient_groups`, or Layer-1 JSON.
- Running adapters, `bulk_inject`, or Coverage OS promotion.
- Treating CoFID or CNF as confirmed.
- Serving-path changes. Today `AUTO_CLASSIFIED` can still be firm SAFE in `compliance.py`; L5 staples **policy** is the stricter VERIFIED-or-class-trusted rule above. A later serving PR must implement that floor for staple rows. This spec does not change evaluate.
- LLM on the hot path.

---

## 9. Acceptance for a future ingest PR (not this one)

A later PR may ingest Wave 1 only if:

1. License check passes for every `primary_source`.
2. Owner OGL confirmation is on file before any CoFID/CNF row (none expected in Wave 1).
3. Completeness gate + implication CHECKs pass for every claimed-complete row.
4. Exception queue was reviewed in batches of 200, frequency-ranked.
5. Audit sample of 300 shows **zero** wrong hazard flags (else redo).
6. UAE `verified=false`; Japan UNVERIFIED pending G4 CAA.
7. No LLM-authored flag is stored as truth.
8. Firm SAFE eligibility is `VERIFIED`/`LOCKED` or `class_trusted` `AUTO_CLASSIFIED` only.
