# Item 10.1 — Multi-restriction combination

**Status:** Prompts **1–4** done (2026-09-30). Vegan + pescatarian is rejected on `POST /profile` and both evaluate routes. The breakdown label is the four-way catalog category. `rule.min_knowledge_state` was not changed. Locked decisions in §3 are not reopened.

**Tracker:** Item **10.1**. The HTTP breakdown ships in the Item **9** body. Gap: `docs/phase2_gap_analysis.md` §10.1. Investigation: `docs/item5_6_10_1_12_investigation.md` §3.

---

## 1. What this item is

The engine already applies every active restriction and takes the most severe verdict. This item adds the policy and the API view around that. It does not replace `evaluate()`.

## 2. What exists today

`compliance.evaluate()` loops ingredients × rules and aggregates with `max` (`SAFE < UNCERTAIN < WARN < FAIL`). An active restriction with no rule contributes UNCERTAIN, so a gap cannot look SAFE.

`POST /api/v1/evaluate-compliance` takes `restriction_ids: List[str]` only. The bridge stores each id as `medical`. There is no per-restriction block in the HTTP body. `assemble()` audits whether an ingredient was triggered, not a restriction-by-restriction status.

The named golden `test_multi_restriction_aggregates_most_severe` was listed in the design and never added. Aggregate behavior is covered indirectly. The acceptance golden named in the gap is vegan + peanut + gluten.

Contradictory diets (vegan + pescatarian) are not rejected. They would AND.

## 3. Locked (do not reopen)

From `docs/phase2_gap_analysis.md` §1:

- Do not rewrite `evaluate()`'s AND + most-severe aggregation.
- Contradictory diets are rejected at profile-set time (warn / pick one). Not a silent AND.
- Medical vs preference is preserved through to the API. Do not flatten every id to `medical`.
- Evaluate HTTP gets a per-restriction breakdown in the Item 9 schema.
- Acceptance golden: vegan + peanut + gluten.

## 4. Check-in (2026-09-30)

1. **Where the reject lives.** Both. `POST /profile` is the primary catch. `evaluate-compliance` and `evaluate-product` also reject a contradictory pair, because they accept `restriction_ids` directly. The pair on record is vegan + pescatarian. Do not expand that list in the first build.
2. **Breakdown label.** Do not ask the caller. Each restriction on the breakdown carries `data/restrictions.json` `category`: `allergy`, `medical`, `lifestyle`, or `religious`. All four stay distinct. Do not collapse religious into lifestyle. `ike2_restriction_rules.category` is the restriction id, not this label. Do not write that catalog category into the string `evaluate()` reads as severity in the same change: `_verdict_for` treats `severity == "medical"` as firm FAIL on a trace or may-contain, so swapping the stored string would change verdicts. The label is response data.
3. **Breakdown.** Default response is one verdict per restriction. The ingredient × restriction matrix is opt-in. `evaluate()` already stores that matrix on `ComplianceResult.breakdown` (key is canonical name × restriction). `assemble()` does not emit it. `is_triggered` only knows a short flag map (`vegan` / `vegetarian` / `jain` / `peanut` / `dairy` / `alcohol`) and is not the breakdown.

**Prompt 1** — **Done (2026-09-30).** No behavior change.

## 5. Out of scope

- Changing aggregate order or the uncovered-restriction UNCERTAIN guard.
- Item 12 telemetry.
- New restriction catalogs.

## 6. Prompts (blocked on §4)

**Prompt 1** — **Done (2026-09-30).** See §4. No behavior change.

**Prompt 2** — **Done.** `vegan` + `pescatarian` returns 400 on `POST /profile`, `evaluate-compliance`, and `evaluate-product`. `vegan` + `peanut_allergy` still evaluates.

**Prompt 3** — **Done.** `by_restriction` carries `data/restrictions.json` category (`allergy`, `medical`, `lifestyle`, `religious`). The severity string `evaluate()` reads is still `medical` for every id on the API path.

**Prompt 4** — **Done.** Default body has one verdict per restriction. `include_restriction_matrix` adds the ingredient × restriction cells. Golden: beef (vegan only), peanut (peanut only), wheat (gluten only), water (none). Headline `NOT_SAFE`.

## 7. Success

- `evaluate()` aggregation is unchanged.
- A checked-in contradictory pair is rejected where §4 says, and vegan + peanut is not.
- Each restriction on the breakdown shows its catalog category (`allergy`, `medical`, `lifestyle`, or `religious`).
- The vegan + peanut + gluten golden shows a per-restriction verdict, and the headline is still the most severe of those.
