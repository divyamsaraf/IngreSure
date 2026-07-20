# IKE-2 Resolution & Compliance Fix — Design Spec

**Status:** Approved 2026-07-17 — implementation plan next; **no production code until execute is requested**  
**Date:** 2026-07-17  
**Scope:** Root-cause fixes to intent → resolve → compliance → audit mapping → explanation copy  
**Out of scope:** Novel ingredients absent from all knowledge tiers; inventing bone-char from bare “Sugar”; manufacturer labeling errors; shipping a “strict processing” preference (future)

---

## 1. Context

Break-testing produced **89 issue signals** across diets. They collapse into a small set of structural bugs in:

```
parse → resolve → rules → compliance.evaluate()
  → map_ike2_to_compliance_verdict()
  → compose_verdict_explanation() / build_ingredient_audit_payload()
  → audit cards
```

Symptom fixes (special-casing sugar or egg) would leave the same failures for collagen, rennet, flour, chicken, `2+2`, etc. This design fixes the **contracts** so unknown-but-structurally-similar cases inherit correct behavior.

A second requirement emerged in review: **correctness for known ingredients must not depend on Supabase being reachable.** Today, anything not in the in-process truth anchor fails closed to untrusted/Depends when DB throws — including staples that already exist in `data/ontology.json` (ETL-only, not runtime).

---

## 2. Locked policy decisions

### 2.1 Policy A — Depends meaning

| Bucket | When |
|--------|------|
| **Avoid** | A rule returned **FAIL** for this ingredient under the active profile |
| **Depends** | Genuine ambiguity: unknown species/source for a diet that cares; compound/umbrella terms (`verdict_cap=WARN`); real processing uncertainty flags; unresolved after all knowledge tiers |
| **Safe** | Rules returned **SAFE** at sufficient knowledge, and the item is not capped as compound/WARN |
| **No audit** | Non-food / nonsense / pure conversation — never enters compliance |

Known-safe plant staples (e.g. plain sugar, beet sugar, organic cane sugar) → **Safe** when resolved with plant-safe flags.

### 2.2 Plain “Sugar” (including Vegan)

- Default: **Safe** on every diet, including Vegan.
- Bone-char refining is **not inferable** from the word “Sugar” and must not be invented.
- Explicit safer labels (`beet sugar`, organic cane, “not bone-char filtered”) → **Safe**.
- Future opt-in “strict processing” preference may reintroduce Depends for bone-char-sensitive users — **not part of this fix**.

### 2.3 Certainty constraint (non-negotiable)

The system must never claim or imply certainty it does not have.

- Unresolved / ambiguous / outside all knowledge tiers → **Depends** (or a dedicated Unknown presentation if UI later splits it) — **never** forced Safe or Avoid to make cards look complete.
- Avoid requires FAIL. Safe requires SAFE without WARN cap. Depends is the honest middle.

---

## 3. Corrected mapper contract

### 3.1 Problem today

`compliance.evaluate` appends to `matched_contains` whenever `triggered=True`, including species-unknown caution paths that return **UNCERTAIN**.  

`map_ike2_to_compliance_verdict` then copies **all** of `matched_contains` into `triggered_ingredients`, which the audit UI renders as **Avoid**.

Result: egg on Hindu Non-Vegetarian → Avoid (“animal-derived”) though no cow/pig rule FAILed.

### 3.2 New contract

For each resolved ingredient under the active profile, derive a **single per-ingredient verdict** = worst (`max`) of all rule outcomes for that ingredient:

| Per-ingredient verdict | Audit status | `triggered_ingredients` | `uncertain_ingredients` |
|------------------------|--------------|-------------------------|-------------------------|
| `FAIL` | Avoid | include | exclude (unless also separately unresolved) |
| `WARN` | Depends | exclude | include |
| `UNCERTAIN` | Depends | exclude | include |
| `SAFE` | Safe | exclude | exclude |

**Species/source unknown:**

- May raise the per-ingredient verdict to UNCERTAIN/WARN (aggregate caution).
- Must **not** place the ingredient in Avoid unless some rule’s outcome for that ingredient is FAIL.
- Implementation implication: either stop putting non-FAIL triggers into `matched_contains`, or ignore `matched_contains` for Avoid and build Avoid exclusively from breakdown entries where verdict == FAIL.

**Recommended implementation:** Prefer breakdown (after §4 fix) as the source of truth for Avoid/Depends; treat `matched_contains` as diagnostic/legacy or redefine it as “FAIL-only matches.”

### 3.3 Aggregate status

Unchanged severity ladder: `SAFE < UNCERTAIN < WARN < FAIL`.  

External mapping stays: FAIL → NOT_SAFE; WARN/UNCERTAIN → UNCERTAIN; SAFE → SAFE.

Headline status remains `max` over all per-rule (or per-ingredient) verdicts — mapper changes must not invent firm SAFE when any ingredient is Depends.

---

## 4. Breakdown key collision fix

### 4.1 Problem today

```text
breakdown[(name, restriction)] = verdict   # last write wins
```

Multiple rules share one restriction (e.g. `hindu_vegetarian`: meat_fish_derived, egg_source, insect_derived). A later SAFE overwrites an earlier FAIL → `triggered_restrictions` can be empty while Avoid still lists the ingredient (from `matched_contains`).

### 4.2 Required behavior

For each `(canonical_name, restriction_id)`:

```text
breakdown[key] = max(existing, new_verdict)
```

Using the same IntEnum order as `Verdict` (`SAFE=0 … FAIL=3`).

### 4.3 Downstream effects

- `triggered_restrictions`: include a restriction if **any** ingredient has breakdown FAIL (or, if keeping WARN for informational lists, document separately — for Avoid attribution, FAIL is required).
- Explanation and allergen/diet attribution (§7) use the **worst** restriction outcomes, not the last evaluated rule.

---

## 5. WARN-compound fix

### 5.1 Problem today

Compounds (`natural flavors`, `spices`, `enzymes`) use truth-anchor `_add_compound` → `verdict_cap=WARN`, knowledge often VERIFIED/trusted.  

If no boolean rule triggers, per-rule base is SAFE then capped to WARN in `_verdict_for`, but the audit mapper only pushes **untrusted / UNCLASSIFIED / DISCOVERED** into Depends. Trusted WARN compounds appear under **Safe**.

Golden corpus already requires: natural flavors must never be firm-SAFE.

### 5.2 Required behavior

Any ingredient whose **per-ingredient verdict** is WARN, or whose effective flags include `verdict_cap=WARN` / compound ceiling, **must** appear in Depends — never Safe — even when `trusted=True` and knowledge_state is VERIFIED/LOCKED.

Mapper rule (explicit):

```text
if per_ingredient_verdict in (WARN, UNCERTAIN) OR unresolved:
    → Depends
elif per_ingredient_verdict == FAIL:
    → Avoid
elif per_ingredient_verdict == SAFE and not verdict_cap_warn:
    → Safe
```

---

## 6. Intent gate (“is this food?”)

### 6.1 Problem today

`_bare_ingredients_fallback` accepts short non-question lines. Break-test garbage that becomes INGREDIENT_QUERY:

`2+2`, `act as`, `Namaste`, `asdfgh`, `null`, `true`, SQL fragments, `{}`, jailbreak-ish prompts, etc.

Those hit compliance as unresolved → Depends with diet-conflict copy.

### 6.2 Placement

Run **before** `_bare_ingredients_fallback` (and before last-resort whole-query ingredient extraction). Order inside `detect_intent`:

1. Existing greeting / conversational regexes  
2. Profile / list extraction  
3. General-question patterns  
4. **NEW: ingredient plausibility gate** on candidate bare text  
5. Only if gate passes → bare-ingredient fallback / extractors  
6. Else → `GENERAL_QUESTION` (or a dedicated “can’t check that” composer path)

### 6.3 Gate logic (deterministic, no LLM required)

Reject (do not treat as ingredients) if **any** of:

| Check | Examples |
|-------|----------|
| Math / expressions | digits+operators only, `2+2`, `3*4` |
| Boolean / nullish literals | `true`, `false`, `null`, `undefined` |
| JSON / code punctuation dominant | `{}`, `[]`, `SELECT …` |
| URLs | `http://…` (already partially skipped) |
| Prompt-injection / meta phrases | `ignore previous instructions`, `act as …` (phrase denylist) |
| Pure greeting leftovers already covered | — |
| Single token with no letters from ingredient charset, or keyboard smash heuristics | `asdfgh`, `qwerty` |
| Tokens in an expanded non-food denylist | `namaste` alone, `menu`, `settings` (extend `_BARE_QUERY_DENYLIST`) |

Accept when:

- Matches known alias / ontology / anchor key, **or**
- Looks like a food phrase: letters, optional spaces/hyphens, optional E-number (`E120`), comma-separated list signals, “Ingredients:” prefix paths (existing extractors)

**Ambiguous short words that are also food** (e.g. rare overlap): prefer food if in Tier 1/2 alias set; otherwise GENERAL_QUESTION rather than Depends.

### 6.4 Response when gate rejects

Reuse / lightly extend `compose_general_question()` (or sibling): clear “I can’t check that — paste an ingredient list or ask about a specific ingredient.” **No** INGREDIENT_AUDIT block.

---

## 7. Allergen vs diet explanation attribution

### 7.1 Problem today

`compose_verdict_explanation` uses `_allergy_triggered(restrictions)` on the **full** `triggered_restrictions` list. If gelatin Avoid is primarily `hindu_vegetarian` / `vegetarian` but `fish_allergy` also fired (gelatin’s `fish_source=True`), copy becomes “not suitable for **your allergens**.”

### 7.2 Required behavior

For the **primary** Avoid ingredient (first FAIL item):

1. Collect restrictions that FAILed **for that ingredient** (from fixed breakdown).  
2. Prefer diet/religious/lifestyle restriction for wording when both diet and allergy fired **and** the diet rule alone would FAIL the item (e.g. gelatin on vegetarian).  
3. Use allergen wording only when an allergy restriction is among the FAIL reasons **and** either:
   - no diet FAIL for that ingredient, **or**
   - the user-facing primary concern is allergy (e.g. only `fish_allergy` on profile).

**Attribution priority (explicit):**

1. If any FAIL restriction for primary ingredient ends with `_allergy` **and** no non-allergy FAIL for that ingredient → allergen copy.  
2. Else if any non-allergy FAIL → diet/lifestyle copy using `_diet_label(profile)`.  
3. Else fallback uncertain copy.

LLM rewrite (`llm_compose_verdict_explanation`) must receive the same attribution hint (diet vs allergen) so it cannot freely say “allergens” when the template path would say diet. If LLM omits or contradicts the attribution enum, keep template.

---

## 8. Depends / reason copy fix

### 8.1 Problem today

`_ingredient_reason` defaults to **“may conflict with your dietary requirements”** for any ingredient without an `INGREDIENT_REASONS` entry — including knowledge-gap Depends (sugar when untrusted, `2+2`, flour).

### 8.2 Copy categories (tests assert category, not only wording)

| Category ID | When | Example user-facing reason |
|-------------|------|----------------------------|
| `diet_conflict` | Avoid (FAIL) with known reason map | “derived from animal bones/skin” |
| `allergen_conflict` | Avoid attributed to allergy | “contains your allergen (fish)” |
| `source_ambiguous` | Depends: species/source unknown for diet that cares | “source not specified on the label — check packaging” |
| `compound_umbrella` | Depends: verdict_cap WARN / compound | “umbrella term — may hide restricted sources” |
| `unverified` | Depends: low knowledge / untrusted but name resolved | “could not be verified against your profile” |
| `unknown_ingredient` | Depends: unresolved after all tiers | “unknown ingredient — could not be matched” |

**Forbidden:** using `diet_conflict` language for `unverified` / `unknown_ingredient` / gate-rejected non-food.

Audit payload should carry `reason_category` (stable for tests) plus `reason` (display string). Frontend may ignore category initially; backend tests must assert it.

---

## 9. Three-tier resolution (Supabase-independent for known ingredients)

### 9.1 Strict order

```text
Tier 1  Bundled core anchor (in-process, boot-loaded)
   ↓ miss
Tier 2  Local ontology (file-backed, versioned in repo)
   ↓ miss
Tier 3  Supabase (dynamic enrichment)
   ↓ miss / error
UnknownIngredientQueue + per-ingredient UNCERTAIN/Depends
```

### 9.2 Tier 1 — Bundled core anchor

- Evolve today’s `truth_anchor.py` (and/or a sibling bundled JSON loaded at import) into the **guaranteed offline core**.
- Must include at least the break-test curated set:

  **Staples / plants:** sugar, cane sugar, beet sugar, flour (and common wheat flour aliases), water, salt, citric acid, carnauba wax  

  **Meats / animal (species explicit where needed):** chicken, beef, pork, fish (generic), egg, milk, honey, lard, gelatin, fish gelatin, collagen, rennet, carmine, shellac, isinglass  

  **Jain-critical:** onion, garlic, potato (root_vegetable), shallot, leek as already partially present  

  **Compounds:** natural flavors, spices, enzymes  

- Loaded at process boot. **Zero network.**  
- Golden matrix + “Supabase down” tests must pass using Tier 1 alone for this set.

**Sugar flags (Policy A):** `plant_origin=True`, `animal_origin=False`, LOCKED/trusted, **no** bone-char uncertainty flag by default.

**Chicken flags:** `animal_origin=True`, `animal_species=chicken` (so veg FAIL via meat_fish_derived; Hindu Non-Veg SAFE; pescatarian FAIL).

**Gelatin:** keep animal_origin + mixed species string + uncertainty; `fish_source` may remain for true fish-gelatin allergy, but explanation attribution (§7) prevents diet Avoid from being labeled “allergens” when diet also FAILs. Optional follow-up (same PR or immediate next): only set `fish_source=True` on `fish gelatin`, not generic gelatin — call out in implementation plan if tests show allergen false FAIL on Fish-only profiles for generic gelatin. **Design decision for this spec:** generic gelatin keeps current flags for safety; copy attribution is the required fix; tightening `fish_source` is allowed if tests prove false Avoid on Fish-allergen-only + gelatin without diet restriction.

### 9.3 Tier 2 — Local ontology

- Runtime read of versioned `data/ontology.json` (or a generated IKE-2 slice checked into repo).
- Deployed with the app; no live dependency.
- Trust: treat static file rows as `source=static` → `is_trusted_for_compliance(..., "static", "high")` when flags are complete enough; if a row lacks required fields, fail closed to Depends (`unverified`), never invent SAFE.

### 9.3.1 Synonymy ladder (string → identity) — locked

Coverage gaps (cuts, geo qualifiers, part morphology, orthography) are **exact-key** misses, not fail-closed bugs. Expand coverage with a deterministic ladder **in front of / inside** the tier walk. Runtime fuzzy / edit-distance / LLM resolve remain **out** (IKE-2 design §11).

```text
L0 Normalize     — NFKC, lower, punct fold (incl. apostrophe), explicit plural/variant map
L1 Exact         — Truth Anchor / ontology canonical / indexed aliases (canonical wins)
L2 Structured    — curated variant_aliases (cuts, geo fish, dairy synonyms); longest-phrase first
L3 Facet strip   — allowlisted inert facets only; accept only if residual already resolves
L4 Offline ETL   — promote / unknown-queue proposals → ontology next deploy
L5 Unknown       — UNCERTAIN / Depends; enqueue; never invent SAFE
```

**Miss-class taxonomy (owners):**

| Class | Examples | Owner |
|-------|----------|-------|
| M1 Absent identity | Barramundi, Kombu, Camembert | Seed/promote new rows + `derive_identity_flags` |
| M2 Cut/part | Beef brisket | Curated L2 alias → parent |
| M3 Species/geo | Atlantic salmon | L2 alias or L3 geo drop if residual hits |
| M4 Morphology | Basil leaves | L3 allowlisted part strip if residual hits |
| M5 Processed form | Apple puree/juice | Explicit equivalence edges only; else own row |
| M6 Dairy varieties | Camembert | Seed dairy varieties |
| M7 Compound animal | Bacon fat | Curated row/alias with animal flags |
| M8 Orthography | Baker's yeast | L0 apostrophe/punct folding |
| M9 Head asymmetry | Promote vs runtime head | Shared `commodity_head` rules |
| M10 Ambiguous | Yam-class | Stay UNCERTAIN |
| M11 Incomplete flags | Malformed DB | Stay uncertain; fix ETL |
| M12 Offline gap | Tier-3-only | Promote into `ontology.json` |

**Do:** longest-phrase match before strip (`peanut butter`, `water chestnut`); canonical/`setdefault` wins collisions; protect VERIFIED/LOCKED on promote; CI promote-drift + variant-recall gates.

**Don’t:** strip `juice`/`puree`/`butter`/`chestnut` generically; first-token parent (`cabbage bok choy`→`cabbage`); silent pick among ambiguous L2 keys (prefer refuse / disambiguation table); open stemming.

**L3 facet strip rule:** strip closed facet tokens (`raw|fresh|frozen|…`, `leaves|fillets`, geo adjectives) **only when** the residual key resolves via L1/L2/L3. Never invent a parent that is not already known.

**Observability:** L5 outcomes may carry a lightweight `miss_class` tag (M1–M12 shape heuristics) for offline promote prioritization; tags never change the verdict.

### 9.4 Tier 3 — Supabase

- Dynamic enrichment / newly discovered aliases / live updates without redeploy.
- **Only consulted on a Tier 1 + Tier 2 miss** (and never for keys already present in `ResolutionCache` from Tiers 1–2).
- On miss after a successful Tier 3 call → Unknown path (§9.6).

### 9.5 ResolutionCache — locked seeding behavior

**Decision (no “or”):** hybrid seed, Supabase-free for known ingredients.

| Phase | Behavior |
|-------|----------|
| **Boot** | Load **entire Tier 1** curated core into `ResolutionCache` (normalized alias → resolved fact). Zero network. |
| **First miss (lazy Tier 2)** | On cache miss, resolve against **local ontology (Tier 2)**; on hit, **write through** to `ResolutionCache`. Still zero network. |
| **Only after Tier 1+2 miss** | Attempt Tier 3 (Supabase). On success, optionally cache the enrichment result for the process lifetime. |
| **Repeat lookup** | Serve from `ResolutionCache` only — **never** re-enter Supabase for a key already satisfied by Tier 1 or 2. |

**Invariants:**

1. Any ingredient in the curated core (Tier 1) is answerable with Supabase down, unconfigured, or timing out.  
2. Any ingredient previously resolved from Tier 2 in this process is answerable without Supabase on subsequent requests.  
3. Cache key: `normalize_ingredient_key(alias)` (+ optional `region` suffix when region-scoped).  
4. Invalidation for this fix: process restart only (no distributed cache, no TTL requirement).

### 9.6 Supabase error / timeout handling — locked degrade path

When Tier 3 is attempted (Tier 1+2 already missed) **or** when a buggy path accidentally calls the DB:

| Event | Required behavior |
|-------|-------------------|
| Timeout, connection error, missing config, 5xx, unexpected exception | Catch inside the resolver/store boundary. **Do not raise** to chat. |
| Degrade | Return “miss” from Tier 3 and continue to Unknown path **only if** Tier 1 and Tier 2 also missed. If Tier 1 or Tier 2 already had a hit, that hit is authoritative — Supabase must not run. |
| User-facing status | Never an error toast / “service unavailable” ingredient reason. Chat still returns an audit or general reply per intent. |
| Copy when Tier 1/2 hit | Normal Safe / Avoid / Depends from rules — **unchanged by Supabase health**. |
| Copy when all tiers miss | Depends with `reason_category=unknown_ingredient` (or `unverified` if partially matched) — **never** `diet_conflict`, **never** the string “may conflict with your dietary requirements”. |
| Logging | `warning`-level log with ingredient key + exception class; no PII beyond the atom string. |

**Anti-regression (lying Depends):** A Supabase outage must not convert a Tier-1 sugar/chicken/flour resolution into Depends, and must not attach diet-conflict copy to an unresolved token. Tests in §10.3 encode both.

### 9.7 UnknownIngredientQueue

- After Tier 1–3 miss (Tier 3 miss **or** Tier 3 error treated as miss): enqueue for enrichment; return unresolved `ComplianceInput` → Depends with `reason_category=unknown_ingredient`.
- Distinct from “service briefly unreachable while Tier 1/2 had the answer” — if Tier 1/2 hit, **do not** enqueue solely because Supabase failed.

### 9.8 Explicitly out of scope

- Genuinely novel ingredients absent from all three tiers  
- Inherent source/process ambiguity (bone-char on bare sugar)  
- Errors already present in curated data  
- Manufacturer labeling errors  

These remain Depends/Unknown + enrichment — not “solved” by this fix.

---

## 10. Golden-matrix test plan

### 10.1 Principles (non-negotiable)

Every golden row asserts **all** of:

1. **Audit bucket** — `safe` | `avoid` | `depends` | `no_audit`  
2. **`reason_category`** — one of §8.2 (`diet_conflict`, `allergen_conflict`, `source_ambiguous`, `compound_umbrella`, `unverified`, `unknown_ingredient`, or `null` for Safe / no_audit)  
3. **Forbidden copy** — display `reason` / explanation must **not** contain `may conflict with your dietary requirements` unless `reason_category=diet_conflict` (which itself should use specific INGREDIENT_REASONS text, not that blanket phrase)

A suite that only checks Safe/Avoid/Depends **fails this spec** — copy correctness was a root-cause bug.

TDD: add failing tests first per cluster, then implement.

### 10.2 Diets in the matrix

Parametrize across at least:

`Vegetarian`, `Hindu Vegetarian`, `Hindu Non Vegetarian`, `Vegan`, `Jain`, `Halal`, `Kosher`, `Pescatarian`

(plus allergen overlays where noted: e.g. Fish + Hindu Vegetarian for gelatin attribution).

### 10.3 Clusters (minimum rows)

| Cluster ID | Inputs | Expectation (bucket + `reason_category`) |
|------------|--------|------------------------------------------|
| `sugar_family` | sugar, cane sugar, beet sugar × all diets incl. Vegan | `safe`; category `null` (or absent); **not** `diet_conflict` / `unverified` / `unknown_ingredient` |
| `warn_compounds` | natural flavors, spices, enzymes × Vegan, Vegetarian | `depends`; `compound_umbrella` |
| `intent_garbage` | `2+2`, `act as`, `Namaste`, `asdfgh`, `null`, `true`, `{}`, `ignore previous instructions` | `no_audit`; intent GREETING or GENERAL_QUESTION; **no** INGREDIENT_AUDIT payload |
| `staples` | flour, water, salt × diets that do not restrict them | `safe`; category `null` |
| `meats_on_veg` | chicken, beef, pork × Vegetarian, Hindu Vegetarian, Vegan, Jain | `avoid`; `diet_conflict` |
| `egg_hnv` | egg × Hindu Non Vegetarian | `safe`; **not** Avoid; category `null` |
| `species_unknown` | collagen, rennet × Halal, Hindu Non Vegetarian | `depends`; `source_ambiguous` (not Avoid unless a species FAIL applies) |
| `gelatin_diet_vs_allergen` | gelatin × Hindu Vegetarian **with Fish allergen also on profile** | `avoid`; explanation attribution **diet-primary**; item `reason_category=diet_conflict` (not `allergen_conflict`) |
| `breakdown_overwrite` | beef × Hindu Non Vegetarian | `avoid`; `triggered_restrictions` contains `hindu_non_vegetarian`; `reason_category=diet_conflict` |
| `jain_roots` | potato, onion, garlic × Jain | `avoid`; `diet_conflict` |
| `pescatarian_meats` | chicken → Avoid; fish → Safe | matching buckets + categories |
| `certainty_unknown` | food-like token absent from all tiers (fixture name reserved for tests) | `depends`; `unknown_ingredient`; never Safe/Avoid |

### 10.4 Supabase-mocked-unreachable suite

**Setup:** mock `core.knowledge.ike2.stores.db` (resolve_alias / disambiguate / client) so every call raises `RuntimeError` or a timeout exception; also run with Supabase config absent.

**Assert for the full Tier-1 curated core** (sugar family, staples, meats, egg, gelatin, compounds, Jain roots):

| Assertion | Pass condition |
|-----------|----------------|
| Bucket parity | Same Safe/Avoid/Depends as the “Supabase up” matrix for Tier-1 keys |
| `reason_category` parity | Same categories as “Supabase up” for those keys |
| No lying Depends | sugar / flour / water never flip to `depends` solely because DB is down |
| No lying copy | no `may conflict with your dietary requirements` on Safe staples; no `diet_conflict` category on unresolved-only paths |
| No exception leak | chat/compliance helpers return normally (no uncaught DB errors) |

### 10.5 File placement (plan phase)

- `backend/tests/ike2/golden/audit_matrix.jsonl` — rows: `{diet, allergens?, input, expect_bucket, expect_reason_category, expect_attribution?}`  
- `backend/tests/ike2/test_audit_mapping_contract.py`  
- `backend/tests/ike2/test_resolution_tiers.py` (includes Supabase-down)  
- `backend/tests/ike2/test_intent_plausibility.py`  
- Extend explanation tests to assert attribution + forbidden blanket phrase

---

## 11. End-to-end flow (target)

```text
User message
  → detect_intent
       → greeting / general / profile paths unchanged
       → NEW plausibility gate
       → only then ingredient extraction
  → prepare_chat_ingredients
  → profile → restriction_ids
  → resolve each atom:
       Cache → Tier1 → Tier2 → (Tier3 only on miss) → else Unknown queue
       (Tier3 errors → miss, never diet_conflict copy)
  → compliance.evaluate (breakdown keeps worst verdict)
  → map: FAIL→Avoid, WARN|UNCERTAIN→Depends, SAFE→Safe
  → explanation with diet-vs-allergen attribution
  → audit payload with reason_category
  → UI cards
```

---

## 12. Affected modules (implementation map — no code yet)

| Area | Primary files |
|------|----------------|
| Mapper contract | `backend/core/bridge.py` (`map_ike2_to_compliance_verdict`) |
| Breakdown / matched_contains | `backend/core/knowledge/ike2/compliance.py` |
| Intent gate | `backend/core/intent_detector.py` |
| Explanation + reasons | `backend/core/response_composer.py` |
| Resolution tiers + cache | `backend/core/knowledge/ike2/resolver.py`, new or extended store for ontology file, `truth_anchor.py` / bundled core data |
| Trust helper | `backend/core/evaluation/resolution_trust.py` (static Tier-2) |
| Chat emit | `backend/app.py` (only if audit schema gains `reason_category`) |
| Tests | `backend/tests/ike2/…`, intent tests |

---

## 13. Non-goals / risks

| Risk | Mitigation |
|------|------------|
| Ontology Tier 2 marks incomplete rows Safe | Incomplete → unverified Depends (`unverified`) |
| Intent gate blocks real obscure foods | Alias hit in Tier 1/2 always accepts; prefer GENERAL_QUESTION over false Depends for smash tokens |
| Gelatin + Fish-only profile still Avoid | Acceptable if `fish_source` remains; document; optional tighten flags |
| Cache serves stale Tier-2 after ops update ontology in DB only | Accept until restart; Tier 3 still used on miss; document |
| Supabase down reintroduces lying Depends | §9.6 + §10.4 explicitly forbid bucket/copy drift for Tier-1 keys |

---

## 14. Success criteria

1. Egg + Hindu Non-Vegetarian → **Safe** (no Avoid).  
2. Sugar (+ cane/beet) × all diets → **Safe**; `reason_category` not `diet_conflict`.  
3. `2+2` / `act as` → no ingredient audit.  
4. Natural flavors → **Depends** + `compound_umbrella`, never Safe.  
5. Chicken × Vegan/Vegetarian → **Avoid**, including with Supabase down.  
6. Gelatin × Hindu Vegetarian with Fish allergen → Avoid copy is **diet-primary**, not “your allergens”.  
7. Beef × Hindu Non-Veg → Avoid with `hindu_non_vegetarian` in triggered restrictions.  
8. Golden matrix + Supabase-down suite green, including **`reason_category` assertions**.  
9. No production code change ships without the failing tests from §10 existing first (TDD).

---

## 15. Deliverable summary — approved vs still open

### Locked in this spec (ready for sign-off once you approve)

| Item | Status |
|------|--------|
| Policy A Depends meaning | Locked |
| Plain Sugar → Safe on all diets incl. Vegan; no invented bone-char | Locked |
| Certainty constraint (no false Safe/Avoid) | Locked |
| Mapper: FAIL→Avoid, WARN/UNCERTAIN→Depends, SAFE→Safe | Locked |
| Breakdown keeps worst verdict | Locked |
| WARN compounds always Depends in cards | Locked |
| Intent plausibility gate before bare-ingredient fallback | Locked |
| Diet vs allergen explanation attribution priority | Locked |
| `reason_category` on audit + forbidden blanket Depends copy | Locked |
| Three-tier resolve: Tier1 → Tier2 → Tier3 → Unknown | Locked |
| **ResolutionCache:** boot-seed Tier 1; lazy Tier 2 write-through; Tier 3 only on miss | Locked (§9.5) |
| **Supabase errors:** silent degrade to miss; never diet_conflict / “may conflict…” | Locked (§9.6) |
| Golden matrix + Supabase-down tests asserting bucket **and** `reason_category` | Locked (§10) |
| No implementation until explicit approval | Locked |

### Explicitly still open / out of scope (not blocking sign-off)

| Item | Status |
|------|--------|
| Future “strict processing” / bone-char opt-in preference | Out of scope |
| Novel ingredients absent from all tiers | Remains Unknown/Depends + queue |
| Tightening generic gelatin `fish_source` (vs fish gelatin only) | Optional follow-up if Fish-only false Avoid appears |
| Frontend rendering of `reason_category` | Optional; backend emits it |
| Distributed cache / cross-process invalidation | Out of scope |

### Sign-off point

**Do not implement until this completed spec is explicitly approved.**

After approval, next step is only an implementation plan (`docs/superpowers/plans/…`) with TDD task breakdown — still no production code until you say to execute that plan.

---

## Spec self-review (completed)

- [x] Section 9 specifies cache seeding (boot Tier 1 + lazy Tier 2) without hedging  
- [x] Section 9 specifies Supabase timeout/error silent degrade and forbids lying Depends copy  
- [x] Section 10 golden matrix covers all requested break-test clusters  
- [x] Section 10 requires `reason_category` assertions (not bucket-only)  
- [x] Section 10.4 Supabase-down suite asserts Tier 1/2 correctness + copy  
- [x] Section 15 deliverable summary: locked vs open  
- [x] Policy A, sugar Safe-including-Vegan, certainty constraint consistent throughout  
- [x] No implementation authorized by this document alone  
)
