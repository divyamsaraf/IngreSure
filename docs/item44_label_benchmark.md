# Item 44 — Real-label coverage benchmark

**Status:** ready to run  
**Goal:** measure clearance vs Avoid power on real labels (not row counts), with a
sample that reflects the product’s target markets.

## Why per-list SAFE looks terrible

A product verdict is only as clear as its **weakest ingredient**. Only ontology /
L1 / human / e-number groups can firm-SAFE; one unknown on a 20-item list makes
the whole list UNCERTAIN. Report **both**:

- **Per-list** SAFE / UNCERTAIN / NOT_SAFE (product-level, weakest link)
- **Per-ingredient** resolution rates (what drives the promotion queue)

## Profiles (six mechanisms + one combined)

| # | Profile | Mechanism exercised |
|---|---------|---------------------|
| 1 | `vegan` | animal origin |
| 2 | `jain` | root vegetables, fungal |
| 3 | `halal` | alcohol, gelatin, animal-derived uncertainty |
| 4 | `gluten_free` | medical; oat/malt traps |
| 5 | `peanut_allergy` | may-contain handling |
| 6 | `dairy_free` | dairy |
| 7 | `combined_vegan_peanut_gluten` | Item 10.1 multi-restriction |

## Sample (~200 lists)

Stratify by **market** (India, US, UK/EU) and **category** (snacks,
sauces/condiments, bakery, dairy alternatives, ready meals, supplements).

- Fix random seed; commit **product IDs** (not ingredient text) under
  `data/item44_off_product_ids.json` with ODbL attribution.
- Unparseable / garbled lists: count separately; **exclude from rates**.

Target cell size ≈ 200 / (3 markets × 6 categories) when OFF allows; document
shortfalls per cell.

## Metrics

Existing:

1. SAFE / UNCERTAIN / NOT_SAFE rates (overall + per profile) — **per-list**
2. Top 50 UNCERTAIN ingredients by frequency
3. Top 50 derive-only NOT_SAFE ingredients by frequency

Additional:

4. **Per-ingredient resolution distribution** (L1 / L2 / L3 trusted /
   L3 untrusted / L5 unknown), overall and per market
5. **Per-list verdict + weakest-link ingredient** (the atom that caused
   UNCERTAIN or NOT_SAFE)
6. Any NOT_SAFE caused by **derive alone**, listed with the **source phrase**

## Gate (pre-pilot)

Any derive-only NOT_SAFE that is a **false Avoid on a pantry staple** → golden
+ `flag_derive` fix before pilot.

## Deliverables

- `data/item44_off_product_ids.json` — seeded stratified product IDs + ODbL note
- `backend/scripts/item44_label_benchmark.py`
- `docs/item44_benchmark_report.json` + `docs/item44_benchmark_report.md`

## Non-goals

- Not a substitute for Item 12 live audits
- Not automatic promotion into ontology / truth anchor
