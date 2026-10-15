# Item 6 — LLM/ML pipeline (harden, do not abstract)

**Status:** Prompts **1–4** done (2026-10-07). Full suite **1891 passed, 4 skipped, 0 failed**.  
**Tracker:** Item **6**. Gap: `docs/phase2_gap_analysis.md` §6. Investigation: `docs/item5_6_10_1_12_investigation.md` §2.

---

## 1. What this item is

Production already wires **Ollama** for chat UX and optional enrichment assist. There is no unified ML pipeline, no embeddings package, and **compliance never calls an LLM**. Item 6 hardens those existing touchpoints and retires stale docs that invent a scan/OCR LLM path. It does **not** build a pipeline abstraction.

## 2. What exists today

| Capability | Path | Role |
|------------|------|------|
| Config gates | `config.py` — `llm_enabled()` (default **on**), Ollama URL/model, intent/response timeouts | CI sets `LLM_ENABLED=false` |
| Rule intent (primary) | `intent_detector.py` | Deterministic |
| LLM intent fallback | `llm_intent.py` → `_call_ollama` | Chat only, after weak rule intent |
| Chat compose / verdict prose | `llm_response.py`, `response_composer.py` | Templates if LLM off/down |
| Enrichment classify | `llm_classify.py` → worker `tasks.py` | Optional after API medium confidence; adds `llm_classified` uncertainty |
| Regional English hint | `fetcher.py` `_resolve_to_english_llm` | After Wikidata miss; hardcoded 5s timeout |
| Profile-update LLM | `llm_compose_profile_update` | **Dead** — never called; templates used |
| Scan/OCR LLM / `llm_normalizer.py` | — | **Does not exist** (stale docs only) |
| Induction / Coverage OS | `coverage_os/induction/*` | Heuristic only — **out of Item 6 scope** |
| IKE-2 resolve + compliance | `ike2/resolver.py`, `ike2/compliance.py` | **Zero** LLM imports |

**Fail behavior:** LLM down or `LLM_ENABLED=false` → templates / skip enrichment assist; verdicts unchanged.

## 3. Locked (do not reopen)

From `docs/phase2_gap_analysis.md` §1:

- Harden existing Ollama touchpoints; **no** pipeline abstraction.
- Compliance **never** calls LLM (preserve).
- Enrichment LLM **in scope**; induction heuristics **out**.
- Retire scan-LLM claims in `AI_ENGINE.md` / `SERVICES_OVERVIEW.md`.
- `LLM_ENABLED` default **on** in production (fallback already safe). CI stays off.

## 4. Check-in + Prompt 1 findings (2026-10-07)

### Check-in (decided in this spec — not reopening §3)

1. **No shared Ollama client module in v1.** Four near-duplicate `requests.post` call sites stay local. A thin shared helper would be the thin end of “pipeline abstraction” and is not required for the locked bar. Harden **in place**: timeouts, dead code, docs, fail-soft tests, enrichment trust boundary.
2. **Dead `llm_compose_profile_update`:** delete in Prompt 3 (not “keep for later”). Templates already own profile acks.
3. **Enrichment trust:** `enrichment_api` stays DISCOVERED / tier 1. `apply_classification_to_ingredient` already appends `llm_classified`. Prompt 3 adds a regression test that this path cannot mint `LOCKED`/`VERIFIED`. No change to reconcile tiers.

### Prompt 1 inventory (findings only)

| Call site | Module | Timeout today | Fail → |
|-----------|--------|---------------|--------|
| Intent fallback | `llm_intent.py` | `LLM_INTENT_TIMEOUT` (30) | `None` → keep rule intent |
| Greeting / general / verdict prose | `llm_response.py` | `LLM_RESPONSE_TIMEOUT` (30) | `None` → templates |
| Profile-update prose | `llm_response.py` `llm_compose_profile_update` | same | **Unreachable** |
| Enrichment classify | `llm_classify.py` | module `_CLASSIFY_TIMEOUT=15` (not in `config.py`) | `None` → API-only flags |
| English-name hint | `fetcher.py` | hardcoded `5` | `None` → continue fetch chain |
| Warmup | `app.py` lifespan | short ping | log + continue |

**Compliance / resolve:** `rg` over `backend/core/knowledge/ike2/` — no `llm_*` imports. Worker is the only production caller of `classify_ingredient_origin`.

**Stale docs:** `AI_ENGINE.md` describes nonexistent `safety_analyst.py` / `llm_normalizer.py` / LLM-on-unclear-ingredient safety path. `SERVICES_OVERVIEW.md` claims scan uses LLM normalizer and that Ollama is required for scan; backend has **no** `/scan` route.

## 5. Out of scope

- MLPipeline / provider abstraction / multi-model router.
- OpenAI/Anthropic or cloud LLM providers.
- Embeddings / vector search / `ml/` package.
- Induction / Coverage OS (not ML).
- Scan/OCR product rebuild (docs only — no code path to fix).
- Item 12 Sentry / request_history (Batch 4).
- Changing `LLM_ENABLED` default off.

## 6. Prompts

**Prompt 1** — **Done (2026-10-07).** Inventory + check-in recorded in §4. No behavior change.

**Prompt 2** — **Done (2026-10-07).** `AI_ENGINE.md` rewritten to current touchpoints; `SERVICES_OVERVIEW.md` scan/LLM-normalizer claims removed.

**Prompt 3** — **Done (2026-10-07).** Deleted `llm_compose_profile_update`; `LLM_CLASSIFY_TIMEOUT` / `LLM_ENGLISH_HINT_TIMEOUT` in `config.py`; `tests/ike2/test_item6_llm_boundaries.py` guards IKE-2↔LLM import boundary, enrichment DISCOVERED default, `llm_classified` uncertainty, and dead-helper removal.

**Prompt 4** — **Done (2026-10-07).** Full suite **1891 passed, 4 skipped, 0 failed**. `phase_plan.md` Batch 3 Item 6 marked done.

## 7. Success

- Docs no longer claim scan/OCR LLM normalization or LLM-driven safety evaluation.
- Dead profile-update LLM helper gone.
- Enrichment + chat LLM timeouts are config-named; CI still forces `LLM_ENABLED=false`.
- Automated guard: IKE-2 compliance path has no LLM imports; LLM classify cannot mint LOCKED/VERIFIED.
- No new pipeline module, no new LLM provider, no induction changes.
