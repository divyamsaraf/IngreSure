# Item 7 — Testing & QA

**Status:** Prompts **1–4** done (2026-10-07). Never-SAFE **140** rows; DB-rule-parity CI gate on. Full suite **1892 passed, 4 skipped, 0 failed**.  
**Tracker:** Item **7**. Gap: `docs/phase2_gap_analysis.md` §7.

---

## 1. What this item is

IKE-2 already has a strong CI safety spine (never-SAFE gate, safety budget, label-corpus shadow). Production evaluate uses **`load_rules()`** (DB with seed fallback); golden runners use **`seeded_rules()`** only. Item 7 closes that parity gap and expands the never-SAFE corpus where coverage is thin. It does **not** build fuzz/property testing or continuous soak-in-CI (P2).

## 2. What exists today

| Asset | Path | Role |
|-------|------|------|
| Exact-verdict corpus | `tests/ike2/golden/corpus.jsonl` (**62**) | Pipeline e2e / expected verdict |
| Never-SAFE corpus | `must_never_be_safe.jsonl` (**120**) | CI hard gate — SAFE = merge blocker |
| Audit matrix | `audit_matrix.jsonl` (**18**) | |
| Runner | `golden_runner.py` | Always `seeded_rules()` |
| Seed ↔ SQL column parity | `test_rules.py` `test_seed_sql_covers_rule_seed` | Migration replay == `RULE_SEED` columns |
| Production rules | `bridge.py` → `load_rules()` | Live DB or seed fallback |
| CI | `ci.yml` | never-SAFE + safety budget + shadow + full pytest |

## 3. Locked (do not reopen)

From `docs/phase2_gap_analysis.md` §1:

- Expand never-SAFE corpus **now**.
- Add **DB-rule-parity goldens now**.
- Defer fuzz/property + continuous soak-in-CI to **P2**.

## 4. Prompt 1 findings (2026-10-07)

### 4.1 Production vs golden rule path

| Path | Rules source |
|------|----------------|
| Chat / evaluate (`bridge.py`) | `load_rules()` |
| Shadow runner | `load_rules()` (optional override) |
| `golden_runner.run_case` / never-SAFE tests | **`seeded_rules()` only** |

Column-level seed↔SQL parity already exists (`test_seed_sql_covers_rule_seed`). What does **not** exist: evaluating the never-SAFE (or exact-verdict) corpus under rules reconstructed from migration-replayed DB rows and asserting **identical external verdicts** to the seed path. A future SQL-only drift that `_to_rule` interprets differently would not trip CI today if goldens stay seed-only.

### 4.2 Never-SAFE coverage (120 rows)

| severity_tier | Count |
|---------------|------:|
| R (religious) | 54 |
| M (medical) | 45 |
| P (preference) | 21 |

Restriction keys present (top): jain 22, vegan 19, hindu_vegetarian 12, halal 11, fish_allergy 9, peanut_allergy 7, kosher 6, …  
**Thin or absent** vs `SUPPORTED_RESTRICTIONS`: `onion_allergy`, `garlic_allergy`, `sulfite_sensitive`, `lactose_free`, `celiac_strict`, `dairy_free` (only 4), `no_alcohol`, `no_insect_derived`, `no_onion`/`no_garlic` lifestyle — several have 0–1 cases. Corpus floor test only requires `>= 80` and tiers `{M,R,P}`.

### 4.3 Check-in (decided here)

1. **DB-rule-parity** = evaluate the never-SAFE corpus twice — `seeded_rules()` vs rules built from `_migration_rule_rows()` via `_to_rule` — and require identical `to_external` verdicts. No live Supabase required in CI (same migration-replay approach as `test_seed_sql_covers_rule_seed`).
2. **Expand never-SAFE** by adding cases for the thin restrictions above (and any Item 3.1 / 34 canons still missing), not by bulk-duplicating existing jain/vegan rows. Target: raise floor assertion after expansion (e.g. `>= 140` once additions land — exact number set in Prompt 3).
3. Exact-verdict `corpus.jsonl` stays seed-driven for expected verdicts; parity gate is on never-SAFE (fail-closed class). Optional: one exact-verdict parity sample in the same test file if cheap.
4. Fuzz / soak / property testing stay **out**.

## 5. Out of scope

- Hypothesis/fuzz property suites.
- Continuous soak jobs in CI.
- Rewriting `evaluate()` or multi-restriction policy (Item 10.1 done).
- Item 12 observability.
- Replacing seed fallback in `load_rules()`.

## 6. Prompts

**Prompt 1** — **Done (2026-10-07).** Findings in §4. No behavior change.

**Prompt 2** — **Done.** `tests/ike2/test_db_rule_parity.py`; `run_case(..., rules=)`; CI Must-never-Safe step includes the parity file.

**Prompt 3** — **Done.** +20 never-SAFE rows (onion/garlic allergy + lifestyle, no_alcohol, sulfite, lactose_free, celiac_strict, no_insect_derived, enzyme/diet gaps). Floor `>= 140`. Skipped `sodium sulfite` (currently resolves SAFE — under-flagged; do not mint a lying golden).

**Prompt 4** — **Done.** `phase_plan.md` Batch 3 Item 7 marked done.

## 7. Success

- Never-SAFE under migration-replayed rules ≡ seed rules (CI).
- Never-SAFE corpus covers previously thin restrictions with real FAIL/UNCERTAIN (never SAFE) cases.
- No fuzz/soak scope creep.
- Full suite green.
