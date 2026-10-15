# Unknown ingredients, external APIs, and the Yam bug

**No code in this doc** — explanation, API overview, how to test, and solution direction.

---

## 1. Why you saw “Yam” in both Safe and Avoid

### What’s going wrong

- **Avoid:** Built from the verdict’s **triggered_ingredients**, which are **canonical names** (e.g. `"sweet potato"`). The UI shows the **raw** user input via `triggered_to_input` (canonical → raw), so you see “Yam” under Avoid.
- **Safe:** Built from the **raw ingredients** list (e.g. `["yam"]`) by excluding anything whose **normalized raw name** is in `triggered_norm`. But `triggered_norm` is built from **canonical** names (`"sweet potato"`), not from the raw names that led to them. So normalized `"yam"` is not in `triggered_norm` → “yam” is wrongly added to the safe list.

So the same user input “Yam” appears in both Avoid and Safe because:

1. The engine correctly resolves “yam” → **sweet potato** (static ontology: yam is an alias of sweet potato).
2. Jain rule correctly fails on that ingredient (sweet potato has `root_vegetable: true`).
3. The **audit payload** uses canonical names for “triggered” but raw names for “safe”, and never treats “raw input that mapped to a triggered canonical” as triggered. So the raw “yam” is not excluded from safe.

**Root cause:** In `build_ingredient_audit_payload`, the “safe” list must exclude any raw ingredient that **corresponds to** a triggered ingredient (e.g. via `triggered_to_input`: if a raw value maps to a triggered canonical, that raw must not appear in safe). Today we only exclude by matching **canonical** names to the raw list, so alias/raw vs canonical mismatch causes duplicate placement.

---

## 2. How unknown ingredients are handled (no DB adds)

### Resolution order (single pipeline)

1. **Static ontology** (`data/ontology.json`) — lookup by normalized key and aliases. “yam” → sweet potato (alias there).
2. **Dynamic ontology** (`data/dynamic_ontology.json`) — same shape; learned from past API enrichments.
3. **External APIs** (only if not found in 1 or 2) — fetcher runs: USDA FDC → Open Food Facts → PubChem → ChEBI → Wikidata. First good result wins; result can be written to dynamic ontology and in-memory registry for next time.

So “yam” is **not** unknown: it’s in static ontology as an alias of sweet potato. The wrong output is from the **audit payload** (safe vs avoid split), not from resolution. For ingredients that are **truly** not in DB/ontology, they go to external APIs; if all APIs return no result, the ingredient is treated as **uncertain** (Depends), not given a firm Safe/Avoid.

### Compliance verdict

- **Resolved** ingredients are evaluated against each active restriction (e.g. Jain → `root_vegetable == true` → FAIL). Triggered ingredients are stored by **canonical name** and `triggered_to_input` stores canonical → raw for display.
- **Unresolved** (unknown) ingredients end up in `uncertain_ingredients` and drive “Depends” / lower confidence; they are not marked Safe.

So for unknowns we do use all configured external APIs; the Yam bug is not “wrong API” but “wrong use of canonical vs raw in the audit groups”.

---

## 3. External APIs: what’s used and how to test

All are used only when the ingredient is **not** in static or dynamic ontology. Order and purpose:

| API | Purpose | Key / auth | How to test (conceptually) |
|-----|--------|------------|----------------------------|
| **USDA FDC** | FoodData Central: food names, categories, flags (e.g. root_vegetable, dairy). | `USDA_FDC_API_KEY` (env). Free key at fdc.nal.usda.gov. | `GET https://api.nal.usda.gov/fdc/v1/foods/search?api_key=KEY&query=yam&pageSize=1` — check JSON for `foods[].foodCategory`, `foodNutrients`, and any flags your code maps to `Ingredient`. |
| **Open Food Facts** | Product/ingredient names, categories; no key. | None (can disable with `OPEN_FOOD_FACTS_ENABLED=false`). | `GET https://world.openfoodfacts.org/cgi/search.pl?search_terms=yam&json=1&page_size=1` — check response shape and that your code maps it to `Ingredient` (e.g. root_vegetable). |
| **PubChem** | Chemical/supplement names; used when food APIs miss. | None. | Search by name; check that your code handles “no result” and doesn’t misclassify food as chemical. |
| **ChEBI** | Chemical entities; same role as PubChem. | None. | Same idea: verify “no result” and no wrong food→chemical mapping. |
| **Wikidata** | English labels and entity types; used for regional names and fallback. | None. | Query by ingredient name; check `resolve_to_english_label` and that you don’t get wrong translations. |
| **Ollama (LLM)** | Optional: “regional name → English” when Wikidata doesn’t help. | Local Ollama; no key. | Only if `_resolve_to_english_llm` is called; confirm it doesn’t invent a wrong English name that then gets cached. |

**Are they “legit and working”?**

- **USDA FDC and OFF** are the main sources for **food** flags (e.g. root_vegetable). They are legitimate and widely used. Correctness depends on your mapping from their JSON to `Ingredient` (e.g. `root_vegetable`, `animal_origin`).
- **PubChem/ChEBI** are authoritative for chemicals; for pure foods they often return “no result”, which is correct.
- **Wikidata** is best-effort; always treat as one signal, not single source of truth.
- **Ollama** is local and unverified; use only as a hint and never cache aggressive guesses.

So: yes, we check/use all these external APIs for unknowns; the main way to make things more accurate is (1) fix the audit payload so the same ingredient can’t be Safe and Avoid, and (2) tighten mapping and fallback order so API results are interpreted consistently and unknowns stay in “Depends” when uncertain.

---

## 4. How to test the external APIs (no code)

- **USDA:** With a valid key, run a search for “yam”, “sweet potato”, “elephant foot yam”, “suran”. Confirm you get sensible foods and that your code sets `root_vegetable` (or equivalent) from the right field. Check one animal product (e.g. “gelatin”) to ensure it doesn’t get marked plant.
- **OFF:** Same queries; confirm category/labels and that your mapping to `Ingredient` matches (e.g. root vs not). Check that “no result” is handled (no fake ingredient).
- **PubChem/ChEBI:** Query a chemical (e.g. “ascorbic acid”) and a food (“yam”). Expect chemical to resolve and food possibly to return nothing; ensure “no result” doesn’t create a wrong ingredient.
- **Wikidata:** Test `resolve_to_english_label` with a regional name (e.g. from `regional_ingredient_names.json`) and confirm the English label is correct and that wrong or empty results don’t break the pipeline.
- **End-to-end:** Run the compliance flow for “Yam” with Jain diet and confirm: (1) resolution is sweet potato (or another single canonical), (2) verdict is NOT_SAFE and that ingredient is in triggered_ingredients, and (3) **after** the payload fix, “Yam” appears only under Avoid, not under Safe.

---

## 5. Making it more accurate and avoiding similar issues

### Fix the duplicate Safe/Avoid (Yam) bug

- When building the **safe** list for the audit payload, treat as “triggered” not only ingredients whose **canonical** name is in `triggered_ingredients`, but also any **raw** ingredient that is the **value** in `triggered_to_input` (i.e. the user input that was resolved to a triggered canonical). So: add to the “exclude from safe” set the normalized form of every `raw` in `triggered_to_input.values()`. Then “yam” will be excluded from safe because it is the raw input for the triggered “sweet potato”. No need to add yam to the database; the data is already there (alias in ontology).

### Unknown ingredients (not in DB)

- **Do not** manually add every unknown to the DB. Keep using static → dynamic → external APIs.
- **Single identity per input:** The engine should assign one resolved ingredient (or “unknown”) per raw input. The audit payload and any UI must use that same identity for both “triggered” and “safe” so the same raw never appears in both.
- **Uncertain = Depends:** If all APIs return no result, keep treating as uncertain (Depends) and don’t show as Safe. Optionally add a short UI line like “We couldn’t verify X; check with your dietitian.”
- **API order and mapping:** Keep USDA and OFF as primary for food; use PubChem/ChEBI for chemical/supplement. Document the exact fields you map to `Ingredient` (e.g. root_vegetable, animal_origin) and add a small test suite that runs known ingredients (e.g. yam, gelatin) and checks the resolved flags.
- **Caching:** Continue not caching “no result” so a retry or updated API can later resolve. Cache only successful resolutions; consider TTL or invalidation for dynamic ontology so bad learns can age out.
- **Regional names:** Keep using `regional_ingredient_names.json` and Wikidata/LLM for “regional → English” so “suran” resolves to “elephant foot yam” (or similar) and then compliance uses one canonical; again, audit payload must use the same identity for safe/avoid.

### Future-proofing

- **One place for “is this raw ingredient triggered?”:** Define a single function or rule: “raw is triggered if (a) its resolved canonical is in triggered_ingredients, or (b) it appears as a raw in triggered_to_input.” Use that for both the conversational reply and the audit payload (safe list and any badges).
- **Logging:** Log resolution result (canonical or “unknown”) and which restriction fired (e.g. jain / root_vegetable) so you can debug mismatches without adding manual DB rows.
- **Tests:** Add a test that submits “yam” with Jain and asserts: exactly one resolution (sweet potato), verdict NOT_SAFE, and in the audit payload “Yam” appears only in avoid, not in safe.

---

## 6. Summary

| Issue | Cause | Direction (no code) |
|-------|--------|---------------------|
| Yam in both Safe and Avoid | Safe list excludes by canonical name only; raw “yam” doesn’t match canonical “sweet potato”. | Exclude from safe any raw that appears in `triggered_to_input.values()` (same identity as avoid). |
| “Wrong output” for yam | Same as above; compliance and resolution are correct. | Fix audit payload logic; no new data needed. |
| Unknown ingredients | Handled by static → dynamic → USDA → OFF → PubChem → ChEBI → Wikidata (and optional LLM). | Don’t add unknowns manually; fix payload; keep uncertain → Depends; verify API mapping and tests. |
| External APIs “legit?” | USDA and OFF are standard for food; PubChem/ChEBI for chemical; Wikidata best-effort. | Test with real queries; document field mapping; add regression tests for key ingredients. |

Implementing the safe-list fix (using `triggered_to_input` to exclude raw inputs from safe) will remove the Yam duplicate and prevent similar cases for any ingredient that resolves to a different canonical name.

---

## 7. Recent fixes (June 2026)

| Issue | Fix |
|-------|-----|
| Gelatin marked SAFE for halal/kosher | Legacy: `contains porcine` in `data/restrictions.json`. IKE-2: `_species_is_porcine()` matches species strings containing `porcine` (gelatin species is `bovine/porcine/fish depending on source`). |
| `soy` not resolving to soybean | Added `soy` alias on soybean in `data/ontology.json` — fixes legacy/IKE-2 divergence on `May contain: soy` labels. |
| External API unit tests flaky | Mock `core.external_apis.http_retry.get_with_retries` instead of `requests.get` (production uses retry wrapper). |

**IKE-2 shadow:** With `IKE2_MODE=shadow`, resolution and compliance run in parallel; user verdict remains legacy until cutover. Monitor with `python scripts/ike2_shadow_soak_report.py --days 7`.

---

## 8. Coverage miss classes → offline promote loop (July 2026)

IKE-2 never invents Safe for unknowns (fail-closed → Depends). Grocery variant misses (cuts, geo fish, leaves, dairy varieties) are **exact-key gaps**, not resolver bugs.

**Runtime synonymy ladder** (design §9.3.1): normalize → exact L1/L2/L3 → curated `variant_aliases.json` → allowlisted facet strip (residual must already resolve) → L5 unknown with `miss_class` tag.

**Offline loop (do not hot-path):**

1. Chat/L5 logs carry `ResolvedIngredient.miss_class` (M1–M8 shape heuristics).
2. Prioritize unknown-queue / promote seeds by miss class (`identity_expand.txt`, `variant_aliases.json`).
3. Run `python backend/scripts/promote_commodity_coverage.py` (or CI `ensure_commodity_coverage.py`).
4. Commit updated `data/ontology.json`; process restart reloads Tier-2.

**Never:** runtime fuzzy/LLM resolve; blind strip of juice/puree/butter/chestnut; silent pick of ambiguous aliases.
