# Data inventory — what IngreSure stores about users

**Status:** engineering inventory for a privacy / legal baseline.  
**Not legal advice.** Counsel should review classification (including
health-related data), retention, cross-border processing, and the public
privacy policy before relying on this document.

Allergy selections and diet / religious-diet preferences are **health-related
data** (they can reveal medical conditions or religious practice). Treat them
as sensitive until counsel says otherwise.

Last inventoried: 2026-10-21 (Track C / Item 12). Code can drift; re-check
before a production privacy review.

---

## 1. Identity

| Field | Location | Who sets it | Retention |
| --- | --- | --- | --- |
| `user_id` (opaque string or UUID) | Browser `localStorage` key `ingresure_user_id`; backend profile key; `request_history.user_id` | Server `GET /anon-session` when `ANON_SESSION_SECRET` is set; else client UUID | Until the user clears site data. Server rows: **no TTL** |
| Anon session token (HMAC `user_id\|expiry`) | Browser `localStorage` key `ingresure_anon_token` | Backend; verified on `Authorization: Bearer` | Token default expiry 365 days (`core/anon_session.py`). Secret is env-only |
| `org_id` + partner `user_id` | Profile storage key `org:{org_id}:user:{user_id}` | B2B `X-API-Key` / `X-User-Id` | Same as profiles |
| `public.users.id`, `name`, `email` | Supabase `public.users` (schema from init migration) | Only when `USE_PROFILE_DB` and `user_id` is a UUID. Consumer chat does **not** collect name/email today | **No TTL**. RLS: own-row select/update for `auth.uid()`; service role bypasses |
| B2B API keys | Process env `B2B_API_KEYS` | Operators | Until rotated |

The product does not require an account for grocery chat. `public.users.name` /
`email` exist on the table and must not be assumed unused in every deploy.

---

## 2. Profiles (health-related)

| Field | Location | Notes | Retention |
| --- | --- | --- | --- |
| `dietary_preference` / `diet_type` | `data/profiles.json`; `public.users.diet_type`; browser `ingresure_profile`; `request_history.profile_update` | Jain, Halal, Kosher, Vegan, medical-style diets, “No rules” | **No TTL** |
| `allergens` / `allergies` | Same | Health-related. JSON lists of allergen labels | **No TTL** |
| `lifestyle` / `preferences.lifestyle` | Same; DB stores extra JSON in `preferences` | Lifestyle constraints | **No TTL** |
| In-process profile cache | `core.profile_storage` (max 500) | Process memory | Until evict / restart |

Default file path: repo `data/profiles.json` (org-namespaced keys). UUID
profiles can be copied to `public.users` via `USE_PROFILE_DB=1`.

Frontend also stores `ingresure_profile_banner_dismissed` (UI flag only).

---

## 3. Chats and evaluations

| Field | Location | Notes | Retention |
| --- | --- | --- | --- |
| `user_input` (raw query / label text) | Supabase `public.request_history.user_input` | Written by `core.request_history.record_request_history` from `/chat/grocery` | **No TTL**. Toggle `REQUEST_HISTORY_ENABLED` |
| `output_text` (assistant text + audit names) | `request_history.output_text` | Capped by `REQUEST_HISTORY_OUTPUT_MAX_CHARS` (default 8000) | **No TTL** |
| Route, status, duration, error_code, metadata | `request_history` | Includes timestamps | **No TTL** |
| `profile_update` JSON | `request_history.profile_update` | May repeat diet/allergen fields | **No TTL** |
| Recent checks | Browser `ingresure_recent_checks` | Last 5 `{query, verdict}` | Until cleared |
| Chat proxy | `frontend/src/app/api/chat/route.ts` | Forwards to backend; **does not persist** | None on the BFF |

`request_history` is append-only, RLS enabled, **no client policies** (service
role only). This is the primary server-side chat store.

Structured request logs (`ingresure.request` / Item 12 middleware) are
**not** supposed to contain raw user text. Confirm after `app.py` is wired.

---

## 4. Unknown queue and discovery

| Field | Location | Notes | Retention |
| --- | --- | --- | --- |
| `normalized_key`, `frequency`, `status` | `public.ike2_unknown_queue` | L5 misses; not a user id | Until resolved / ops delete |
| `enrichment.raw_inputs` | Same jsonb | Up to 20 raw atom strings (user-typed ingredients) | Same |
| `enrichment.restriction_ids_sample`, `profile_context_sample` | Same | Can echo diet/allergen context from legacy migration | Same |
| Legacy `public.unknown_ingredients` | Same fields historically (`raw_inputs`, restriction samples, profile context) | Still in schema; IKE-2 writes go to `ike2_unknown_queue` | **No TTL** |
| `data/unknown_ingredients_log.json` | File log via `core.enrichment.unknown_log` | `normalized_key`, `raw_inputs`, frequency, restriction sample, **profile_context_sample** | **No TTL** |
| miss_class counts | `data/observability/miss_class.json` (Item 12) | Tag + sha256(key) only; **no raw atom** | Until file deleted |

---

## 5. Logs and analytics

| Store | Fields | Retention |
| --- | --- | --- |
| Application logs | May include query / user_id unless `LOG_REDACT_PII` is set. Some enrichment paths log a 50-char raw prefix | Host/container default (unset in code) |
| Structured HTTP logs (Item 12) | `request_id`, route, method, status, `latency_ms`, engine, degraded, verdict **counts** | Host default once wired |
| Sentry (optional, Item 12) | Exceptions; `send_default_pii=false`; bodies and profile/ingredient keys scrubbed; `release` = git SHA | Sentry org retention (operator-set). **Do not enable until hooks + SDK are reviewed** |
| Vercel Analytics | Page views, device/browser (not query text) per privacy page | Vercel plan default |
| `ike2_shadow_diffs.raw_input` | Label text vs verdicts (cutover / soak infra) | **No TTL** |
| Coverage / induction CSVs | Ingredient + profile + miss_class (offline jobs) | Job artifact lifetime |
| B2B request-access | `company_name`, `use_case`, `monthly_volume`, **email**, `problem_focus` logged to `console.info` in `frontend/src/app/api/request-access/route.ts` | Host log retention. Not written to a table today |

`/metrics` (Item 12) is auth-protected (`METRICS_TOKEN`). It exposes counters
and hashed miss_class keys, not queries.

---

## 6. What is not stored (current product)

- Password / login for consumer chat
- Payment data
- Precise geolocation
- Device contacts
- A server-side multi-turn chat transcript table (only per-request history)

Restaurant/menu tables from the init schema were dropped
(`20260306100000_drop_restaurant_submissions.sql`). Do not assume they still
hold user data.

---

## 7. Health-related data (flag for counsel)

The following can be **health-related or otherwise sensitive**:

- Allergen lists (`allergens` / `allergies`)
- Diet type (`dietary_preference` / `diet_type`), including medical and
  religious diets
- Lifestyle flags when they imply health practice
- Ingredient queries that mention conditions (“I’m allergic to…”) stored in
  `request_history.user_input` and recent-checks
- Profile context copied onto unknown-queue / unknown-log samples

Counsel should classify under applicable regimes (e.g. health data, special
category data) and decide lawful basis, minimization, and whether
`request_history` should store raw queries at all.

---

## 8. Retention gap (policy vs code)

The public privacy policy (`frontend/src/app/privacy-policy/page.tsx`) states
there is **no automatic deletion schedule** and that queries/verdicts are kept
to improve the product. That matches the code: no TTL on
`request_history`, profiles, or unknown queues.

**Counsel review needed** before promising deletion SLAs, DSR workflows, or
health-data handling. Engineering can add TTLs only after that review.

Suggested questions for counsel (not recommendations):

1. May we store raw ingredient queries and allergen profiles without a TTL?
2. Are hashed miss_class keys and anonymous `user_id`s personal data here?
3. Is Vercel Analytics + optional Sentry compatible with the public policy?
4. What is the process when a user asks to delete “their” anon history?

---

## 9. Related code

- Profiles: `backend/core/profile_storage.py`, `frontend/src/lib/profileStorage.ts`
- Chats: `backend/core/request_history.py`, `supabase/migrations/20260409120000_request_history.sql`
- Unknown queue: `backend/core/knowledge/ike2/unknown_queue.py`
- Item 12 logs/metrics: `backend/core/observability/`
- Public policy: `frontend/src/app/privacy-policy/page.tsx`
