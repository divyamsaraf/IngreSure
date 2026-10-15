# Item 9 — B2B API and productization

**Status:** Prompts **1–4** done (2026-09-30). Sibling key is `ike2`. `verdict` stays `ComplianceVerdict.to_dict()`. 401 only when `ENVIRONMENT=production`. `rpm` overrides the tier limit. Locked decisions in §3 are not reopened.

**Tracker:** Item **9**. Companion: Item **10.1** (per-restriction breakdown rides this schema). Gap: `docs/phase2_gap_analysis.md` §9.

---

## 1. What this item is

`/api/v1` already evaluates on IKE-2. A pilot still cannot be given a key that is required, a payload with `schema_version`, or a per-key `rpm` cap. Chat and profile stay the consumer app. This item does not build a second product surface.

## 2. What exists today

| Surface | Today |
|---------|--------|
| `POST /api/v1/evaluate-compliance`, `evaluate-product` | IKE-2. Body is `ComplianceVerdict.to_dict()` inside `{verdict: ...}`. No `schema_version`. |
| `POST /api/v1/resolve-ingredient`, `GET /ingredient/{name}` | IKE-2 facts via `map_ike2_to_resolved_response`. |
| `ike2/response.py` `assemble(..., mode="b2b")` | Library only. `SCHEMA_VERSION = "ike2.v1"`. **No HTTP caller.** The b2b dict is headline, audit, caution, matched contains/may-contain, and a severity map. It is not a per-restriction matrix (that is Item 10.1). |
| `B2B_API_KEYS` | Parsed. `X-API-Key` or `Authorization: Bearer` selects a tier limit (`starter` / `growth` / `enterprise`). A missing or unknown key is limited, not rejected. |
| `rpm` on the key object | Parsed in `rate_limit._normalize_b2b_entry` and then ignored. The tier name picks `B2B_TIER_LIMITS`. |
| Frontend | Does not call `/api/v1`. |

## 3. Locked (do not reopen)

From `docs/phase2_gap_analysis.md` §1 and §9:

- A valid key is required on `/api/v1` in production. Missing or unknown key → **401**.
- A key's `rpm` overrides that key's tier limit.
- The B2B body carries `schema_version` from `assemble`.
- Chat, profile, and `/health` are not this item. No SSE/streaming product.

## 4. Check-in (2026-09-30)

1. **Contract.** Keep both for one release. Add the b2b object beside the existing `verdict` body. Deprecate `verdict` in a later prompt. Do not break existing tests in the prompt that adds the new object.
2. **Production gate.** `ENVIRONMENT=production`, the same flag as `config.PRODUCTION` and the CORS guard (`validate_cors_origins(..., PRODUCTION)` in `app.py`). 401 only when that flag is true. Pytest leaves `ENVIRONMENT` unset, so the gate stays open.
3. **Key issuance.** A static `B2B_API_KEYS` entry. Rotation, sandbox, and a dashboard stay a customer-conversation item.
4. **Severity.** See Item 10.1 §4. Item 9 does not add a caller-supplied severity field.

### Prompt 1 findings (2026-09-30)

`assemble(mode="b2b")` returns `schema_version` (`ike2.v1`), `external_verdict`, `audit` (`canonical_name`, `triggered`), `caution_reasons`, `matched_contains`, `matched_may_contain`, `severity` (the profile's restriction map), and `verdict` (an **int**).

`ComplianceVerdict.to_dict()` returns `status`, `triggered_restrictions`, `triggered_ingredients`, `triggered_ingredient_to_input`, `triggered_restrictions_by_ingredient`, `uncertain_ingredients`, `informational_ingredients`, `confidence_score`, `ontology_version`, `evidence_tier`. HTTP wraps that dict as `{"verdict": ...}` (`routes.py`). The HTTP tests that would break if `verdict` stopped being that dict are `tests/test_api_v1_evaluate_ike2.py` (`verdict.status` on compliance; product also asserts `triggered_restrictions`, `triggered_ingredients`, `uncertain_ingredients`, `confidence_score`, `evidence_tier`, and `parsed_ingredients`). `test_confidence_tier.py` calls `to_dict()` on the dataclass, not the HTTP envelope. Chat tests do not read this body.

**Collision:** the existing envelope key `verdict` is the to_dict object. `assemble` also uses the name `verdict` for an int. Putting the b2b dict at the top level under that name would replace the object those tests read. The additive block needs its own key. `verdict` stays `to_dict()`.

## 5. Out of scope

- Rewriting `evaluate()` (Item 10.1).
- Request-history / Sentry (Item 12).
- Keying the Next.js chat routes.
- Editing `assemble`'s existing b2b headline rule (contains/may-contain → FAIL) unless a prompt's test shows the HTTP body needs a different headline. Do not change it while drafting.

## 6. Prompts (blocked on §4)

**Prompt 1** — **Done (2026-09-30).** Findings are in §4. No route change.

**Prompt 2** — **Done.** Known `B2B_API_KEYS` entry required on `/api/v1` when `config.PRODUCTION` is true. Missing or unknown key is 401. Chat and profile are not gated.

**Prompt 3** — **Done.** Both evaluate routes return `verdict` plus `ike2` (`schema_version` `ike2.v1`, including `assemble`'s integer `verdict`). Resolve routes stay fact-only.

**Prompt 4** — **Done.** A key `rpm` replaces the tier string. Absent `rpm` keeps the tier default.

## 7. Success

- Production `/api/v1` without a known key is 401. Chat still works without one.
- Evaluate responses include `schema_version` in the shape Q1 locked.
- `rpm` changes the limit for that key.
- Item 10.1's breakdown has a place in that same body, not a second schema.
