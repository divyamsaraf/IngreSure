# Item 11 — JECFA / INS investigation (report only)

**Date:** 2026-10-06  
**Method:** Codex CXG 36-1989 (2025 amend) PDF text, CXA 6-2025 specs index, WHO/FAO public descriptions, Scientific Data 2024 JECFA portal study, repo comparison against `e_number_catalog` / FSSAI / ontology. No adapter, no registry, no dry-run.  
**Status:** Investigation complete — **do not build** until license and product-slice are explicitly reopened.

---

## 1. What “JECFA / INS” actually means

These are **three related products**, not one dump. Treating them as a single “JECFA source” would smuggle the wrong shape into Layer-1.

| Product | Publisher | What it is | Machine form today |
|---------|-----------|------------|--------------------|
| **WHO JECFA evaluations database** | WHO (with FAO) | Per-chemical evaluation summaries: name, CAS, functional class, ADI/TDI, evaluation history, links to TRS/FAS monographs and specs | Searchable HTML only. **No official API, no bulk CSV/JSON download** (confirmed by WHO portal copy and by Ocagli et al., *Scientific Data* 2024). ~6.5k unique chemicals as of mid-2024 scrape; portal states updates through **102nd JECFA (June 2026)**. ~**72% flavouring agents** in that scrape |
| **FAO JECFA specifications** | FAO (+ WHO on joint pubs) | Identity / purity monographs for additives (and separate flavouring-spec tracks). Codex adopts many of these by reference | Searchable portal + PDF/HTML monographs + Combined Compendium volumes. **CXA 6-2025** is Codex’s adopted-specs **index** (additive table + large flavouring table with JECFA numbers), not a flag table |
| **Codex INS (CXG 36-1989, amended 2025)** | Codex / FAO–WHO | International Numbering System: INS number → name → functional class / technological purpose | Official form is **PDF** (also Open Knowledge Repository). Codex GSFA site exposes a **web food-additives list** (UI), not a documented bulk API |

INS and JECFA are **not the same set**. CXG 36 states explicitly that inclusion in the INS **does not** imply Codex approval for use, and the list **may include** additives **not** evaluated by JECFA and **not** in the GSFA (CXS 192). JECFA ADI holders are pointed to the WHO/FAO portals; Codex-adopted specs are listed in CXA 6.

**Nothing in this family is a composition table** (unlike INFOODS / IFCT / USDA). Nothing here is an EU E-number regulation dump either.

---

## 2. Licensing

| Slice | Licence / terms (as published) | Fits `license_allowlist.json`? |
|-------|--------------------------------|--------------------------------|
| FAO JECFA Compendium / monograph series (sample: 2024 Combined Compendium) | **CC BY-NC-SA 3.0 IGO** — non-commercial; ShareAlike; no FAO/WHO endorsement implied; commercial use → `copyright@fao.org` / licence-request form | **No.** Allowlist is `CC0-1.0`, `CC-BY-4.0`, `ODbL-1.0`, `public-domain`. NC fails closed |
| FAO website / Knowledge Repository default OA | Same default family (**CC BY-NC-SA 3.0 IGO**) for eligible pubs since 2018; commercial republication needs permission | **No** for redistributable Layer-1 without a grant |
| WHO JECFA evaluation DB content | WHO terms: substantial reproduction needs **prior written authorization** | **No** without WHO permission |
| Codex CXG 36 / CXA 6 texts | FAO/WHO copyrighted Codex texts; reuse follows FAO/WHO permissions, not the INFOODS statistical-DB carve-out | **No** as a default CC-BY dump |
| Third-party scrapes (e.g. Scientific Data Figshare index + MIT scraper; commercial aggregator APIs) | May index or quote; **do not** clear FAO/WHO rights for IngreSure to ship a derived Layer-1 corpus | **Not a substitute** for an allowlisted SPDX |

**Contrast with INFOODS (already built):** FAO Statistical Database Terms of Use put **FAO/INFOODS Food Composition Databases** under **CC BY 4.0**. That path is why `infoods` could check in. JECFA specs / Codex additive texts sit in the **publication / NC-IGO** lane, not that statistical-DB carve-out.

**Gate conclusion:** fail closed for any `SourceAdapter` / `license_allowlist` entry today. A future build needs an explicit commercial (or CC-BY/CC0) grant for the **specific** slice, then SPDX check-in — same discipline as produce/animal/infoods, not a scrape around the gate.

---

## 3. Coverage beyond `e_number_catalog` (measured)

### 3.1 What `e_number_catalog` already is

| Fact | Value |
|------|------:|
| Entries | **330** |
| Canonical names / E-codes | 330 / 330 |
| Alias keys (normalized) | 1,217 |
| Default path in registry | **`LOCKED`**, `_SOURCE_TIER` **4** |
| `sources` field on rows | `["e_number_catalog"]` only |
| Stated primary URL | EU additives database (not FAO/WHO JECFA) |
| Ontology rows with `E…` aliases | 329 |
| Ontology rows with `INS…` aliases | **0** |

This is a **hand-curated IKE-2 compliance catalog** (origin/allergen/synthetic flags, uncertainty, verdict caps). It is **not** a JECFA extract and must not be treated as one. Only the e-number adapter path may mint `LOCKED`/`VERIFIED` (`validate.py`).

Flag richness the catalog already carries (examples): `synthetic` true on 181; `plant_origin` 88; `animal_origin` 11; `insect_derived` 3; 50 rows with `uncertainty_flags`. **JECFA/INS publications do not ship these booleans.** ADI, purity assays, and functional class are a different ontology.

### 3.2 Codex INS (CXG 36 numerical list)

From the 2025 CXG 36 PDF text used for this report:

| Metric | Count |
|--------|------:|
| Distinct INS-like numbers in numerical list (cleaned line parse) | **~496–514** |
| Catalog numeric codes present in that INS set | **309 / 330** |
| INS numbers **not** in catalog | **~187** |
| Catalog E-numbers **not** found in that INS parse | **21** (EU-only / naming drift / parse edges — e.g. some lettered or gas codes) |

So INS is a **wider numbering lexicon** than the EU E catalog, but the delta is mostly **additional INS codes and naming variants**, not a parallel universe of compliance-ready ingredient rows.

### 3.3 FSSAI already carries INS

| Metric | Count |
|--------|------:|
| FSSAI Layer-1 rows | 913 |
| Distinct `INS …` aliases on FSSAI | **337** |
| Distinct `E …` aliases on FSSAI | 380 |
| FSSAI INS also in CXG parse | 299 |
| FSSAI INS not in catalog numeric set | **96** |
| FSSAI canon ∩ catalog canon | 153 |
| FSSAI E-codes ∩ catalog E-codes | 264 |

**Honest gap for label resolution:** INS strings are already largely available via **FSSAI** on Indian/regulatory overlap; ontology has almost no INS aliases of its own. The e-number path covers EU `E###` on LOCKED rows. A JECFA/INS inject would mostly **re-alias** or **add INS codes for additives already known under other names**, not open a composition-sized hole like INFOODS’s ~480 new head commodities.

### 3.4 WHO JECFA evaluation corpus

~6.5k chemicals, **majority flavourings**. Flavouring JECFA numbers and long chemical names are a poor fit for grocery-label Layer-1 bulk inject: high noise, weak overlap with `E`/`INS` consumer codes, and **zero** structured origin/allergen flags for IKE-2. Specs monographs are purity/identity narrative + assays — useful for humans and enrichment metadata, not for `synthetic` / `animal_origin` inference without a separate curated mapping (which is exactly what `e_number_catalog` already is).

### 3.5 What would actually be “new” for IKE-2

| Candidate payload | New for compliance? | Notes |
|-------------------|---------------------|-------|
| INS number → additive name lexicon | Mostly **alias / crosswalk** | ~187 INS beyond catalog; FSSAI already holds 337 INS aliases |
| JECFA ADI / evaluation year / CAS | **Metadata**, not verdict flags | No home in current Layer-1 bool model; would be enrichment, not demotion-driving facts |
| Spec purity assays / monograph text | Not Layer-1 | PDF narrative |
| Flavouring agent flood | **Noise** if bulk-injected as ingredients | Dominates WHO DB count |
| Origin / allergen / synthetic flags | **Not published** by JECFA/INS | Would have to be invented or copied from catalog — wrong |

---

## 4. Trust-tier recommendation (argued from this data)

| Field | Recommendation | Why |
|-------|----------------|-----|
| Register source key now? | **No** | License fails allowlist; no official bulk feed |
| Build adapter / Layer-1 dump now? | **No** | Same; also weak coverage ROI vs e_number + FSSAI |
| Inherit `e_number_catalog` **LOCKED / tier 4**? | **No** | LOCKED is reserved for the curated E-catalog path that alone may mint protected states. JECFA/INS do not supply the curated compliance flags that justify that privilege |
| Inherit `fssai` / `fda` **AUTO / tier 4**? | **No** | Those are national regulatory ingest paths already in the registry. JECFA is scientific advice + specs; INS is an open **naming** list that disclaims approval. Tier-4 regulatory weight is the wrong metaphor |
| Inherit `infoods` / `usda` **AUTO / tier 3**? | **No** | Those are composition tables with sheet/category → kingdom inference. JECFA has no analogous structure for origin flags |
| Inherit `animal_catalog` **DISCOVERED / tier 2**? | **No** | Wrong product class (tiny curated seed vs global additive corpus) |
| If license were cleared later for an **INS name↔number crosswalk only** | Likely **`DISCOVERED` or carefully scoped `AUTO_CLASSIFIED` at tier ≤3**, aliases + `uncertainty_flags`, **never LOCKED**, **never** inferred origin/allergen bools from ADI/functional class | Naming enrichment only; asserted_flags only for keys deliberately set (almost none if bools omitted) |
| Best near-term use of JECFA (no inject) | Human / offline reference when curating or reviewing additive rows; optional future **enrichment metadata** after permissions | Keeps scientific authority without contaminating reconcile |

**Bottom line:** JECFA/INS look “nearest” to `e_number_catalog` by domain (additives), but the catalog’s trust posture comes from **curated IKE-2 flags + dedicated LOCKED adapter**, not from FAO/WHO publication authority. On the data’s own characteristics — permission-gated specs, HTML-only evaluations, INS-as-naming-not-approval, flavouring-heavy corpus, and origin flags absent — the honest call is **do not register, do not inject**. Coverage that matters for labels is already split between **LOCKED E-catalog** and **FSSAI INS aliases**; the residual INS/JECFA delta does not clear license or flag-model bars for a bulk source.

---

## 5. Explicit non-actions (this report)

1. No `license_allowlist` entry for `jecfa` / `codex_ins`.  
2. No `_DEFAULT_STATE` / `_SOURCE_TIER` / `_CANONICAL` registration.  
3. No adapter, transform, layer1 dump, or dry-run.  
4. No scrape of WHO/FAO portals into the repo.  
5. Do not “upgrade” `e_number_catalog` provenance to JECFA without a separate curation decision — current primary URL is EU.

---

## 6. If this is ever reopened

Order of proof (same discipline as INFOODS, inverted outcome likely):

1. Written FAO/WHO permission (or a clearly CC-BY/CC0 machine dump) for the **chosen slice**.  
2. Pick **one** slice: CXG INS lexicon **or** adopted-spec index names — not the full flavouring evaluation DB.  
3. Coverage replay against ontology ∪ e_number ∪ FSSAI (alias-only metrics).  
4. Trust check-in argued again from that slice’s fields.  
5. Ontology-seeded dry-run with asserted_flags demotion gate; live only on match.

Until then, Batch 3 / 4 and other Item 11 regional work can proceed without a JECFA dependency.
