# Zero False-Safe Trust Architecture — Design Spec

**Status:** Draft for review — structural P0 items need explicit sign-off before implementation  
**Date:** 2026-07-20  
**Authors:** Engineering + principal-engineer review panel (safety-critical allergen systems + food/religious diet domain)  
**Scope:** How IngreSure earns user trust for Safe/Avoid/Depends without claiming the impossible

---

## 1. Honest framing

**“Not even 1 wrong Safe, forever, on every label in the world” is not a provable property** of an open-world ingredient reader (OCR errors, mislabeling, reformulation, novel additives, manufacturing aids not printed on labels).

What *is* achievable — and what we commit to:

> Every **Safe** verdict is earned under a closed, testable set of preconditions. Anything outside that set is **Depends**, never silent Safe. False Avoid is acceptable; false Safe is a P0 incident.

Trust without doubt means: **no unacknowledged uncertainty**, not the absence of uncertainty.

---

## 2. Safety invariants (must hold by construction)

| ID | Invariant |
|----|-----------|
| INV-1 | Worst-case aggregation: one Avoid/Depends beats any number of Safes |
| INV-2 | Untrusted resolution → never Safe or Avoid (only Depends) |
| INV-3 | Species/origin unknown on species-gated rules → Depends |
| INV-4 | Compound/umbrella terms (`natural flavors`, spices, …) → never firm Safe |
| INV-5 | Medical “may contain” → Avoid (not Safe) |
| INV-6 | Missing/NULL safety flag ≠ verified-false (must not default to Safe) |
| INV-7 | Tier-1 LOCKED facts heal under-flagged Tier-2/DB rows |
| INV-8 | Determinism: same inputs + rules version → same verdict |
| INV-9 | `must_never_be_safe` corpus: zero SAFE allowed (CI merge blocker) |

---

## 3. What we shipped now (this change)

1. **Dedicated golden corpus** `backend/tests/ike2/golden/must_never_be_safe.jsonl`  
   - Severity tiers: **M** medical, **R** religious, **P** preference  
   - Ambiguity classes: allergen_core, may_contain, religious, lifestyle, ambiguity, compound_expand, …  
2. **Hard CI gate** `test_must_never_be_safe.py`  
   - Zero SAFE on corpus (legacy + new)  
   - Degraded Tier-2/3 row stress for curated canons (under-flagged DISCOVERED must not clear)  
3. Existing `test_golden_safety_budget.py` remains as legacy companion

---

## 4. Principal-engineer recommendations (team consensus)

### P0 — before marketing “trust without doubt” for anaphylaxis-class use

1. **NULL vs False on safety flags** — missing flag must be Depends, not “not triggered → Safe”  
2. **Shadow `false_safe_regression` as release blocker** (not log-only)  
3. **Dual-control on LOCKED / RULE_SEED** — domain steward + verdict-delta PR report  
4. **Property-based tests** for INV-1…INV-8 on every PR touching compliance/resolver/rules/truth_anchor  
5. **UI confidence tiering** — “Safe · verified (LOCKED)” ≠ identical green badge to lower-tier clears  
6. **Scoped copy** — Safe means *“no disqualifying ingredients found on this label for your restrictions”*, never *“this product is safe for you to eat”*

### P1 — hardening

7. Mutation testing on SAFE-producing branches  
8. Adversarial/OCR/homoglyph fuzz corpus (any SAFE = P0)  
9. Metamorphic tests (reorder, casing, synonyms → same verdict)  
10. Verdict receipts (hashed facts + rules version) for incident forensics  
11. Independent “dumb keyword scanner” cross-check in shadow pipeline  

### P2 — maturity

12. Auto kill-switch: demote a restriction category to Depends-only if false-Safe rate spikes  
13. Queryable governance ledger for migrations + LOCKED edits  
14. External red-team / clinical-regulatory review of allergy + religious rule sets  

### Product claims we must never make as firm Safe without certification

- Whole-product Halal / Kosher / Certified Vegan / Peanut-free facility  
- Regulated “gluten-free” at ppm (vs “no gluten ingredients declared”)  
- Cooking “burns off alcohol” assumptions  
- Inference from brand reputation or “most natural flavors are plant”

---

## 5. Policy defaults (domain panel)

| Class | Default |
|-------|---------|
| Gelatin (species unstated) | Depends (Avoid for vegan/veg/Jain; species diets Depends) |
| Natural flavors / spices / enzymes / colors | Depends (hard cap) |
| Mono/diglycerides, E471, E910 | Depends unless source known |
| May contain (medical allergy) | Avoid |
| May contain (religious/preference) | Depends + strong reason |
| Honey | Safe Halal/Kosher/Hindu/Vegetarian; Avoid Vegan/Jain |
| Carmine/shellac | Avoid veg-style + Halal/Kosher/Jain/Vegan |
| Unknown atom | Depends |

---

## 6. Team model (ongoing)

| Role | Responsibility |
|------|----------------|
| Safety / compliance PE | Invariants, NULL-vs-false, aggregation, CI gates |
| Food allergen / labeling PE | Medical severity, may-contain, certification boundaries |
| Religious diet reviewer (as needed) | Halal/Kosher/Jain/Hindu policy sign-off |
| Data steward (≥2 person dual control) | LOCKED facts, source citations |
| Product | Scoped Safe copy, confidence UI, Depends as “system working” |

---

## 7. Success metrics

- **False-Safe count on `must_never_be_safe` = 0** (CI, every PR)  
- Shadow false-Safe regressions = 0 before release  
- Corpus coverage: every Tier-M/R restriction has ≥1 must-never-safe row  
- Incident → permanent corpus entry within 24h  

---

## 8. Approval needed before next implementation

Please approve which P0 items to implement next:

- **A)** NULL-vs-false flag semantics in compliance (largest latent false-Safe vector)  
- **B)** Property-based invariant suite  
- **C)** UI scoped Safe copy + confidence tiering  
- **D)** Shadow false-Safe as hard release gate  

Recommend starting with **A + B** (engine), then **C** (trust UX), then **D** (ops).

---

## 9. Bugs found by principal panel + root fixes (2026-07-20)

| Bug | Evidence | Root fix shipped |
|-----|----------|------------------|
| Uncertainty ceiling **allowlist fail-open** (glycerin `mono_diglycerides` → Safe for Jain/Halal) | Live chat Safe | Deny-by-default: any origin uncertainty caps vegan/religious/dairy-egg to WARN |
| Typo `no_insect` vs `no_insect_derived` in ceiling set | Dead branch | Fixed id |
| `map_record` dropped `verdict_cap` | Tier-2 never got caps | Pass through `verdict_cap` |
| Explicit **NULL** flag = Safe | `peanut_source: None` → SAFE | NULL → UNCERTAIN (cautious) |
| DB rule typo never fires | Unvalidated `field` | `load_rules` drops unknown fields |
| Pescatarian only 5 species | turkey/duck relied on wrong species aliases | `meat_land_derived` composite |
| Regressions | — | `test_false_safe_root_fixes.py` + glycerin in must-never-Safe corpus |

Remaining P0 from §8 still open: property tests, UI copy, shadow release gate.