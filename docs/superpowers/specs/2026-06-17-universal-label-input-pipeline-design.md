# Universal Label & Input Pipeline — Design Spec

**Status:** Approved — **implemented** (Phases 1–5 complete, June 2026)  
**Date:** 2026-06-17  
**Supersedes scope of:** `2026-06-17-label-parser-ike2-bread-fix-design.md` (bread becomes Phase 1 example, not the whole program)  
**Related:** `2026-06-16-ike2-design.md`, intent_detector, bulk_inject ETL

---

## 1. Problem

Users paste **many input shapes**, not one bread label:

| Class | Examples | Current gaps |
|-------|----------|--------------|
| **A. Simple lists** | `milk, gelatin, E471` | Mostly works |
| **B. Parenthesis labels** | `Enriched Flour (Wheat, Niacin)` | Works |
| **C. Bracket labels** | `Flour [Wheat, Barley]` | **Broken** — brackets not nested |
| **D. Trace / minor %** | `Contains 2% or less of: …` | Partial — fails after `.` sentence break |
| **E. Prefix / boilerplate** | `Ingredients:`, `INGREDIENTS -` | **Broken** — prefix leaks into tokens |
| **F. Semicolon lists** | EU-style `;` separators | IKE-2 `input_layer` weak vs bridge |
| **G. May contain** | `May contain: peanuts` | Separate from `<2%` trace; policy differs |
| **H. Conversational** | `Can I eat this if I'm vegan? eggs, milk` | Intent extracts subset |
| **Junk / chat** | `hi`, `what's the weather` | Intent should block — not IKE-2's job |
| **I. OCR noise** | broken commas, `l .` `Ingred1ents` | Limited normalization |
| **J. Regional / IN labels** | Hindi transliterations, FSSAI names | L3 coverage + region aliases |
| **K. Long multi-block** | nutrition facts + ingredients + allergen stmt | Intent may take wrong block |

Bread label is **class C + D + E** combined — fixing only that string without generalizing leaves the same bugs on every similar label.

---

## 2. Goals / Non-goals

### Goals

1. **One decomposition pipeline** shared by legacy bridge and IKE-2 `input_layer` (same atoms, same trace flags).
2. **Pattern-class coverage** — every class A–G above has golden tests; fixes apply to the class, not one product.
3. **IKE-2 resolution coverage** — L3 seeded from ontology; L1 stays safety-critical + E-numbers only.
4. **Intent boundary** — junk/chat never enters compliance; meta-phrases rejected.
5. **Measurable quality** — label corpus (200+ real labels) + shadow soak metrics.

### Non-goals

- 100% correctness on arbitrary English sentences (impossible; see §7).
- LLM in resolution/verdict hot path.
- Replacing OCR/barcode pipelines.
- Hand-maintaining 500+ items in `truth_anchor.py`.

---

## 3. Correctness contract (unchanged from IKE-2)

| Promise | Target |
|---------|--------|
| **Zero false-Safe** on labeled allergens | Required |
| **Exact verdict on all inputs** | Not promised |
| **Fail-closed on unknown** | Required (Depends, not Safe) |
| **Label parse → stable atoms** | Required for classes A–G in corpus |

---

## 4. Architecture

```
                    ┌─────────────────────┐
  User text ───────►│ intent_detector     │──► [] → chat / ask for list
                    │ (junk, questions,   │
                    │  extract list)      │
                    └──────────┬──────────┘
                               │ List[str] raw segments
                    ┌──────────▼──────────┐
                    │ label_decomposer    │  ◄── NEW unified module
                    │ (prefix, nesting,   │      (wraps + extends
                    │  trace, may_contain)│       ingredient_parser)
                    └──────────┬──────────┘
                               │ List[Atom{name, trace, may_contain}]
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        bridge/legacy    IKE-2 input_layer   audit display
              │                │
              ▼                ▼
        ComplianceEngine   IKE-2 resolver (L1→L3→L5)
```

**Key decision:** Extract `label_decomposer` (or extend `ingredient_parser` as single entry) so bridge and IKE-2 cannot drift.

---

## 5. Pattern-class specifications

### 5.1 Nesting delimiters (classes B, C)

Treat `()`, `[]`, `{}` as equivalent nesting for decomposition.

- Shared `split_by_nesting()` used by `preprocess_ingredients` and `flatten_ingredients`.
- Comma-split regex respects all bracket types: `,(?![^(\[\{]*[\)\]\}])`.

### 5.2 Label prefix & boilerplate (class E)

Strip before parse:

- `^\s*ingredients?\s*[:;\-]\s*`
- Optional `^\s*composition\s*:\s*` (EU)
- Trim duplicate `Ingredients:` blocks (intent already does; decomposer idempotent)

### 5.3 Sentence & clause breaks (class D)

Split major clauses before comma pass:

- `\.\s+(?=contains\s+2%|<\s*2%|less than\s+2%)`
- `;\s*(?=contains\s+2%)` (semicolon + trace)

Trace introducers (existing `TRACE_PATTERNS` + extend):

- `contains 2% or less of each of the following`
- `less than 2% of the following`

### 5.4 Semicolons (class F)

EU labels use `;` as top-level separator. Decomposer splits on `;` at nesting depth 0 (same as comma).

IKE-2 `input_layer` must use decomposer — not `re.split(r"[,;]", …)` alone without nesting.

### 5.5 May contain (class G)

Distinct from `<2%` trace (FDA minor ingredient):

| Marker | Semantics | Compliance |
|--------|-----------|------------|
| `<2%` / `contains 2% or less` | Product composition, minor | `trace=True` → may_contain rules |
| `May contain` / `Produced in a facility` | Cross-contact warning | `may_contain=True` → stricter for medical allergies |

Decomposer emits `ParsedAtom(trace=…, may_contain=…)`. Compliance already supports `matched_may_contain` in IKE-2.

### 5.6 Conversational & junk (classes H, junk)

**No change inside IKE-2.** Expand `intent_detector` tests:

- Greetings → no ingredients
- `check these ingredients for gluten` → no list (ask user)
- `eggs and milk` without list signal → extract or prompt
- Profile-only updates → no compliance run

### 5.7 Resolution coverage (classes A–J)

| Layer | Responsibility | Size |
|-------|----------------|------|
| **L1 truth anchor** | Allergens, animal, alcohol, Jain, E-numbers, ~20 staple aliases (water, salt, yeast) | ~150 hand + generated E-codes |
| **L3 Supabase** | Full ontology + aliases + region | Thousands (ETL) |
| **L5** | Unknown queue | Fail-closed |

**Top 500 by frequency** → seed **L3 only**, optional in-process LRU cache. **Not** L1.

---

## 6. Phased delivery

### Phase 1 — Unified decomposer + IKE-2 alignment (P0)

*Bread label is the acceptance test for this phase, not the only test.*

- Shared nesting split (brackets + parens)
- Prefix strip, period/trace split, semicolon at depth 0
- `input_layer.parse_atoms` → decomposer (same as bridge)
- Minimal L1 staples: water, salt, yeast, wheat flour, wheat gluten, malted barley flour
- Golden: `tests/fixtures/labels/` with ≥15 label files covering classes A–G

### Phase 2 — L3 ontology seed (P0)

- Run existing `bulk_inject` / merge pipeline into `ike2_*` tables
- Verify local + CI with seeded DB fixture
- Shadow match rate should jump on simple multi-ingredient lists

### Phase 3 — May contain + allergen statements (P1)

- Decomposer recognizes `May contain:` blocks
- Wire `may_contain` flag through IKE-2 seam/compliance
- Golden rows for peanut allergy + may contain

### Phase 4 — Label corpus expansion (P1)

- 200+ real labels (US FDA, EU, IN/FSSAI, OFF samples)
- `test_label_corpus.py` — parse assertions (no bracket junk, atom count bounds) + IKE-2 verdict on subset
- Shadow soak gate: ≥85% legacy match on parsed labels (configurable)

### Phase 5 — Intent & OCR hardening (P2)

- OCR typo table (limited, high-confidence)
- Multi-block label: prefer last `Ingredients:` block or largest list segment
- Regional name hints via existing `regional_ingredient_names.json`

---

## 7. What “handle all inputs” honestly means

| User expectation | System response |
|----------------|-----------------|
| Any English sentence → perfect verdict | **No** — intent asks for clarification or Depends |
| Any grocery label format → sensible atoms | **Target ~90%** after Phases 1–4 on corpus |
| Any ingredient ever named → resolved | **No** — unknown → Depends |
| Never wrong Safe on allergens | **Yes** — IKE-2 invariant |

---

## 8. Performance

| Change | Latency impact |
|--------|----------------|
| L1 grow to 500 hand entries | Negligible (dict lookup) |
| L3 seed 5k–15k aliases | Fewer L5 misses; more DB hits unless cached |
| In-process LRU for hot L3 rows | **Recommended** — cuts repeated Supabase RTT |
| Unified decomposer | Negligible vs current parse |

Bottleneck is **per-atom L3 network**, not truth anchor size. Seed + cache beats bloating L1.

---

## 9. Testing strategy

| Layer | Test file | What |
|-------|-----------|------|
| Decomposer | `tests/test_label_decomposer.py` | Class A–G fixtures |
| Bridge parity | `tests/ike2/test_input_layer.py` | IKE-2 atoms == bridge atoms |
| IKE-2 verdict | `tests/ike2/golden/corpus.jsonl` + label corpus | Safety + selected verdicts |
| Intent | `tests/test_intent_detector.py` | Junk rejection |
| Shadow | soak report + `ike2_label_corpus_shadow.py` | match %, false_safe % |
| Stress | `tests/test_stress_long_label.py`, `stress_test_long_label.py` | 200+ atoms, junk paste, latency |

TDD mandatory per phase. No production change without failing test first.

---

## 10. Success criteria (program complete)

- [x] Bridge and IKE-2 produce identical atom sets for all fixtures in `tests/fixtures/labels/`
- [x] Zero false-Safe on IKE-2 golden + label corpus safety rows
- [x] ≥85% shadow verdict match on label corpus (current: ~99.5% on 457 rows)
- [x] Intent tests: 0 compliance runs on junk/greeting corpus (`tests/fixtures/intent/junk_corpus.json`)
- [x] L3 seeded; staples resolve via truth anchor + ontology (`scripts/seed_ike2_ontology.py`)

**Post-completion (June 2026):** Long-label stress harness (`stress_test_long_label.py`, `test_stress_long_label.py`), gelatin halal/kosher species matching, soy alias parity. See implementation plan verification section.

---

## 11. Recommendation summary

| Question | Answer |
|----------|--------|
| Bread only? | **No** — fix **pattern classes**; bread is Phase 1 proof |
| Truth anchor 500? | **No** — keep L1 small; seed **L3** |
| Supabase for top 500? | **Yes** — correct layer |
| 100% all inputs? | **No** — 100% **safe** + high **parse/resolve** on corpus |
| Complicated? | **Less** if one decomposer + one DB ontology |

---

## 12. Approval

After approval, invoke **writing-plans** for phased implementation plan (replaces narrow bread-only plan as master plan).
