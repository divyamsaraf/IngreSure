# Using Redis to Make the System Faster and More User-Friendly (Simple Deployment)

**Goal:** Use Redis where it clearly improves speed and UX, without adding new services or complex deployment. Reuse the **existing** Redis instance (already in Docker Compose for Celery).

---

## Full flow today (rule-based + where LLM is used)

End-to-end for a chat request (e.g. “Is milk vegan?”):

1. **Request** — User sends `query` (+ optional `user_id`, `userProfile`). Backend validates length and identity.

2. **Profile** — Load or create profile (file-based + in-memory cache). Merge any `userProfile` from the request.

3. **Slash command** — If query is `/update dietary_preference|allergens|lifestyle ...`, apply and return; no intent/ingredient path.

4. **Intent (rule-based first)** — `detect_intent(query)` runs **rules only**: regexes and keyword maps (e.g. `DIET_KEYWORDS`, “can X eat Y”, “Ingredients: …”). Output: `ParsedIntent` with `intent` (GREETING | PROFILE_UPDATE | INGREDIENT_QUERY | MIXED | GENERAL_QUESTION), `profile_updates`, `ingredients`.

5. **LLM fallback (only when needed)** — If rule-based result is `GENERAL_QUESTION` with **no** ingredients and **no** profile update, we call **LLM** to re-parse and get intent/ingredients. Otherwise we never call LLM for intent.

6. **Short-circuit paths (no ingredients)**  
   - **GREETING** → LLM or template greeting + profile blob, return.  
   - **PROFILE_UPDATE only** → Apply profile updates, template acknowledgment + profile blob, return.  
   - **GENERAL_QUESTION (no ingredients)** → LLM or template answer + profile blob, return.

7. **Ingredient path** — We have `ingredients` (e.g. `["milk"]`). Expand compounds → `eval_ingredients`, `compound_map`. Yield “Checking ingredients…”.

8. **Compliance (rule-based, deterministic)**  
   - **Profile → restriction_ids** — Map diet/allergens/lifestyle to restriction IDs (e.g. Jain → `jain`). Rule-based only.  
   - **Resolve each ingredient** — For each string in `eval_ingredients`, **CanonicalResolver** runs (this is **not** rule-based; it’s lookup/enrichment only):
     - **In-memory cache** (key = normalized ingredient + try_api) → if hit, return cached resolution.
     - **Miss** → **DB (Supabase)** when `USE_KNOWLEDGE_DB` is true — alias → group lookup; if found, return.
     - **Still miss** → **static** ontology (`data/ontology.json`) → **dynamic** ontology (`data/dynamic_ontology.json`) → if not found and `try_api`, **external APIs** (USDA → Open Food Facts → PubChem → ChEBI → Wikidata). Result is one **Ingredient** (canonical name + flags like `root_vegetable`, `animal_origin`).
   - **Evaluate restrictions (rules only)** — For each restriction_id (e.g. `jain`), **RestrictionRegistry** evaluates each resolved ingredient against **rules** (e.g. `root_vegetable == true` → FAIL). No LLM.  
   - **Aggregate** → ComplianceVerdict (status SAFE | NOT_SAFE | UNCERTAIN, triggered_restrictions, triggered_ingredients, confidence).

9. **Response (template only)** — `template_verdict(verdict, profile, …)` builds the text (e.g. “Based on your Jain diet, …”). No LLM. Then we emit INGREDIENT_AUDIT JSON and PROFILE_UPDATE blob.

So: **rules** handle intent, profile→restriction mapping, and compliance (ingredient vs restriction). **LLM** is only for greeting text, general Q&A text, and optional intent re-parse when rules say GENERAL_QUESTION with no ingredients. **Resolution** (ingredient → canonical + flags) is **not** rule-based; order is: **in-memory cache → DB (Supabase when `USE_KNOWLEDGE_DB`) → static ontology → dynamic ontology → external APIs**.

---

## Flow with Redis (resolution cache)

If we add an **optional** Redis resolution cache (when `REDIS_URL` is set), only **step 8 (resolve each ingredient)** changes. The rest (rules, profile, compliance evaluation, template response) is unchanged.

**Today (no Redis):**  
For each ingredient: **in-memory cache** → if miss → **DB (Supabase when enabled)** → static → dynamic → APIs → store in in-memory cache.

**With Redis:**  
For each ingredient: **in-memory cache** → if miss, **Redis** (key e.g. `ingresure:resolve:{normalized_key}:{try_api}`) → if miss → **DB (Supabase when enabled)** → static → dynamic → APIs → store in **in-memory cache** and in **Redis** (with TTL).  

So:

- **Rule-based flow is unchanged:** Intent, profile→restriction_ids, and restriction evaluation stay exactly as they are.
- **Resolution becomes:** check in-memory → (if Redis configured) check Redis → on miss run static/dynamic/APIs, then fill both in-memory and Redis.
- **Faster when:** The same ingredient was resolved before (same or different user). Cache hit in Redis avoids static/dynamic/API work, so “Checking ingredients…” and the rest of the response come back sooner.
- **Deployment:** Same as today. If `REDIS_URL` is unset, we never touch Redis and behavior is identical to current.

---

## Current state

- **Redis today:** Used only as Celery broker (and optional result backend). Same Redis is already in `docker-compose.yml` and healthy when you run the full stack.
- **Caches today:** All in-process (in-memory): profile read cache, resolution cache (CanonicalResolver), fetcher (external API) cache. They are lost on restart and not shared across multiple backend instances.

---

## Where Redis helps (speed + UX, low complexity)

### 1. Resolution cache (best UX win) — **recommended** *(implemented)*

**What:** Cache the result of “resolve this ingredient” (static → dynamic → API) in Redis so the next request (same or different user) can skip resolution work. Implemented in `backend/core/cache/redis_resolution.py` and wired in `CanonicalResolver.resolve_with_fallback`; active when `REDIS_URL` is set.

**Why it’s user-friendly:**
- “Is milk vegan?” / “Is yam okay for Jain?” etc. get **faster answers** on repeat (same ingredient).
- First byte (“Checking ingredients…”) and full result appear sooner when the resolution is a cache hit.
- No change to UI or flow—just faster backend.

**Why it’s simple:**
- **Reuse existing Redis** (same `REDIS_URL` as Celery; use a key prefix like `ingresure:resolve:`).
- **Optional:** If `REDIS_URL` is not set, keep current in-memory-only behavior. No new container; dev without Docker is unchanged.
- **One layer:** On resolution request, try Redis get; on miss, run current logic, then set Redis with a TTL (e.g. 24 hours). No invalidation logic needed.
- Serialize the resolution result (e.g. canonical name + flags as JSON); keep value small.

**Deployment:** Unchanged. When Redis is already there (e.g. Docker), set `REDIS_URL` for the backend; resolution cache starts using it. When Redis is not there, leave `REDIS_URL` unset.

---

### 2. Profile read cache — **optional, good for multi-instance**

**What:** Cache “get profile by user_id” in Redis so repeated profile reads (e.g. every chat request) avoid file I/O and are shared across backend instances.

**Why it’s user-friendly:**
- Slightly faster personalization and less latency when loading profile at the start of a chat.
- Helps most when you run **multiple backend replicas** or restart often.

**Why it’s simple:**
- Same Redis, key prefix e.g. `ingresure:profile:{user_id}`.
- Optional: use Redis only when `REDIS_URL` is set; otherwise keep current in-memory profile cache.
- On `save_profile`, write-through to Redis (set key); on `get_profile`, try Redis first, then file, then set Redis. TTL optional (e.g. 1 hour) or no TTL if you always invalidate on save.

**Deployment:** Same as today. Backend already has profile cache; adding Redis as L2 is a backend-only, opt-in change.

---

### 3. What *not* to do (to keep it simple)

- **Fetcher (external API) cache in Redis:** Would require serializing `EnrichmentResult` and more error handling. The resolution cache already covers “we resolved this ingredient once”; fetcher cache is a smaller win. Skip for now.
- **GET /config in Redis:** Frontend calls it once per load; benefit is small. Skip.
- **New Redis instance or separate “cache” Redis:** Use the **existing** Redis; separate key prefixes (e.g. `ingresure:resolve:`, `ingresure:profile:`) avoid clashes with Celery. No new service.

---

## Summary

| Use                | Benefit for speed/UX                    | Complexity | Deployment        |
|--------------------|-----------------------------------------|------------|-------------------|
| **Resolution cache** | Faster “Checking ingredients…” and result on repeat queries | Low        | Reuse Redis; optional |
| **Profile read cache** | Faster profile load; helps multi-instance/restarts   | Low        | Reuse Redis; optional |
| Fetcher in Redis   | Smaller gain                            | Medium     | Skip for now      |
| GET /config in Redis | Minor                                   | Low        | Skip for now      |

**Recommendation:** Add **optional** Redis-backed **resolution cache** first (when `REDIS_URL` is set). Add **optional** Redis-backed **profile read cache** if you run multiple backends or want faster profile load. Use the same Redis already in Docker Compose; no new containers or config. Keep behavior unchanged when `REDIS_URL` is unset so the system stays easy to deploy and run without Redis.

---

## Cache by ingredient only (not by question or user)

To keep responses fast and logic simple, **cache only ingredient resolution**, not the full question or the per-user verdict.

| What we cache | What we don’t cache |
|---------------|---------------------|
| **Ingredient → resolved data** (canonical name, flags like `root_vegetable`, `animal_origin`) | The user’s question (“Is milk vegan?”) |
| Key = normalized **ingredient** (e.g. `milk`, `yam`) | Key ≠ (ingredient + diet) or (ingredient + user_id) |
| One cache entry per ingredient; shared by all users and all diets | Per-user or per-diet verdict (computed each time from cached resolution + profile) |

So:
- “Is milk vegan?” and “Can I have milk?” both use the same cache key for **milk** → one resolution, reused.
- Verdict (“milk is not safe for vegan”) is computed on each request from the cached resolution + the user’s profile. No cache invalidation when the user changes diet; no storing per-user answers.

Result: **fewer trips** (same ingredient = one resolution, then cache), **faster response** (cache hit = no DB/APIs), **simple** (no per-user or per-question keys).

---

## Better UX without complexity

1. **Resolution cache in Redis (by ingredient)**  
   First check Redis for the normalized ingredient; on miss, resolve (static → dynamic → APIs), then store. Next user or same user later = cache hit = faster. No extra services; optional when `REDIS_URL` is set.

2. **Keep one clear “working” message**  
   Already have “Checking ingredients…” before the compliance run. Keeps UX consistent: user sees progress, then the result. No need for per-ingredient progress in the UI (that would add complexity).

3. **Keep verdict computation per request**  
   Don’t cache “milk + vegan = avoid.” Compute it each time from cached resolution + profile. That way diet changes and different users are always correct without cache invalidation.

4. **Optional later: prewarm top ingredients**  
   A small script or startup step could resolve and cache e.g. 50–100 common ingredients (milk, egg, onion, etc.) so the first user also gets fast responses. Only add if you want that; not required for a good experience.

5. **No new UI or flow**  
   Everything stays “user asks → we respond.” Faster backend is enough; no need for extra steps, progress bars, or toggles.

---

## How to improve response time (without affecting quality)

These changes reduce latency while keeping answers the same.

| Priority | What | Why it helps | Quality impact |
|----------|------|----------------|----------------|
| **1** | **Redis resolution cache** (see above) | Repeat ingredients (same or different user) skip DB/static/dynamic/APIs. Biggest win when the same ingredients are asked often. | None — we cache resolution only; verdict is still computed per request from profile. |
| **2** | **Eager first byte** | Already done: yield "Checking ingredients…" before running compliance so the user sees progress immediately. | None. |
| **3** | **Parallel resolution** | Already done: multiple ingredients are resolved in parallel (ThreadPoolExecutor) in the compliance engine. | None. |
| **4** | **In-memory caches** | Resolution cache (CanonicalResolver, 1000 entries) and fetcher API cache already avoid repeat work within a process. | None. |
| **5** | **Optional: Redis profile cache** | When running multiple backends or after restarts, profile reads can hit Redis instead of disk. | None — same profile data. |
| **6** | **Optional: Prewarm resolution cache** | On startup or via a script, resolve 50–100 common ingredients (milk, egg, onion, garlic, etc.) so the first request gets more cache hits. | None — same resolution logic. |
| **7** | **Ollama warmup** | Already done on backend startup so the first LLM call (greeting/intent/general) is faster. | None. |

**What not to do (would hurt quality or add risk):**

- **Don't cache verdicts per user/diet** — Verdict must be recomputed from resolution + current profile so diet changes and correctness are preserved.
- **Don't skip API fallback for unknowns** — Turning off external APIs would make many ingredients stay "unknown"; quality would drop.
- **Don't shorten LLM timeouts too much** — Greeting/general replies could be cut off or fail; keep timeouts as-is unless you tune with tests.

**Main takeaway:** The largest gain is **Redis-backed resolution cache** (by ingredient). Everything else is either already in place (first byte, parallel resolution, in-memory caches, warmup) or a smaller optional improvement (profile cache, prewarm).
