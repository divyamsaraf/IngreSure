# Chat contract (frontend inventory)

Read-only source: PR #17 backend (`/chat/grocery` stream). Frontend tag literals live in `src/constants/chatProtocol.ts` and must match `backend/core/stream_tags.py`.

This file is what Next.js chat consumes. It does not change the backend.

## Stream tags

| Tag | Backend emit | Frontend consume |
| --- | --- | --- |
| `<<<PROFILE_REQUIRED>>>` | Bare marker, then prose. No JSON body. No `<<<INGREDIENT_AUDIT>>>`. | Set `profileRequired`. Keep the prose. Open the profile modal. **No verdict chips.** |
| `<<<PROFILE_UPDATE>>>` | `<<<PROFILE_UPDATE>>>{user_id, dietary_preference, allergens, lifestyle}<<<PROFILE_UPDATE>>>` | Merge into profile + localStorage. Strip the block from visible text. |
| `<<<INGREDIENT_AUDIT>>>` | `<<<INGREDIENT_AUDIT>>>{summary, groups, explanation, explanation_source, confidence_tier}<<<INGREDIENT_AUDIT>>>` | Render audit cards. Strip the block from visible text. |

There is **no** `<<<EMERGENCY>>>`, `<<<CONFIRM>>>`, `<<<ECHO>>>`, or `<<<DEGRADED>>>` tag.

## Message shapes (plain text)

### Profile required

Emitted when the profile has no restriction ids, including:

- general question, empty profile
- ingredients present, empty profile
- ingredients present, still no restriction ids after merge

Typical body (after the tag):

```
I need to know which restrictions apply before I can say SAFE or NOT SAFE. Tell me your diet or allergies.
I read: water, salt.
```

or a general-question fallback. Frontend must not show Safe / Avoid / Depends.

### Confirm line + yes / no / only-today

Unconfirmed restrictions **tighten** the session immediately. Persist / relax wait for a follow-up.

Lactose example (action `tighten`, `needs_confirm`):

```
I'll treat this as a dairy restriction for this check. Is lactose-free dairy acceptable, and should I save this on your profile?
```

Other confirm lines the parser emits:

- gluten-sensitive: *I'll treat this as gluten-free… I will not save it until you confirm.*
- temporary: *This sounds temporary. Confirm if I should change your saved profile.*
- someone else's restriction: *This looks like someone else's restriction. Confirm whose profile to use.*
- remove medical / saved rule: *I will not remove a … restriction without an explicit confirm.*

Follow-up **must** be a standalone line (backend `classify_confirm`):

| Reply | Accepted forms | Backend yield |
| --- | --- | --- |
| yes | `yes`, `y`, `yeah`, `yep`, `confirm`, `that's right`, `ok`, `okay` | `Saved on your profile.` + `PROFILE_UPDATE` |
| no | `no`, `n`, `nope`, `nah`, `cancel`, `never mind` | `Okay, I won't save that restriction.` |
| only-today | `only today`, `just today`, `this once`, `just for today`, `today only` | `I'll keep this restriction for this session only; it is not saved.` |

Any other follow-up leaves session tightening in place and does not persist. Frontend shows Yes / No / Only today actions when the last assistant turn is a confirm prompt.

### Understanding echo

Plain sentences, usually before `Checking ingredients…` (that progress line is stripped from the UI):

```
I understood: milk, sugar.
I could not use: leftover phrase.
Checking against: dairy-free.
```

Optional preface by `block_kind`:

- recipe: `Treating this as a recipe, not a packaged label.`
- multi_product: `That looks like more than one product.`
- product_name: `That looks like a product name, not an ingredient list.`

Restriction labels: `gluten-free`, `dairy-free`, `vegan`, `peanut allergy`, `Jain`, `Halal`, `vegetarian`, `egg-free`, else `id` with `_` → space.

Frontend renders the echo as its own block (not a verdict).

### Degraded

Two different backend shapes — **neither is a stream tag**:

1. Engine fail-closed **text** (chat stream stays HTTP 200):

   ```
   I could not finish that check. Treat this as UNCERTAIN, not safe.
   ```

2. `ComplianceVerdict.degraded: true` on evaluate APIs. `build_ingredient_audit_payload` **does not copy `degraded` into `<<<INGREDIENT_AUDIT>>>`**.

Frontend treats (1) as degraded, and also honors `degraded: true` on the audit JSON if a future backend adds it. **No verdict chips** in degraded mode.

### Emergency block

Emergency preempts the verdict flow. No audit tag. Then a `PROFILE_UPDATE`.

`/chat/grocery` currently calls `detect_emergency(query)` **without a region**, so the stream is almost always the generic list:

```
If this is a medical emergency, stop using this app and call your local emergency number now: 911 (US/Canada), 999 (UK), 112 (EU/India), 000 (Australia), 111 (New Zealand), 998 (UAE). I am not emergency services and I will not evaluate ingredients while you may need urgent care.
```

If a region were supplied, the region-specific line is:

```
If this is a medical emergency, stop using this app and call {number} now (or your local emergency number). I am not emergency services and I will not evaluate ingredients while you may need urgent care.
```

Verified numbers (backend `core.emergency.NUMBERS`):

| Region | Number |
| --- | --- |
| US, CA | 911 |
| GB, UK | 999 |
| EU (+ FR DE IT ES NL IE PT SE PL BE) | 112 |
| AU | 000 |
| NZ | 111 |
| AE (UAE) | 998 |
| IN | 112 |
| unknown / missing | generic list above |

Frontend **does not wait for a region from the stream**. It styles the emergency block first, and picks the number from `userProfile.region` or the browser locale. Unknown locale → generic list.

Triggers (backend patterns the UI also recognizes on the user turn): `call/dial 911|999|112|000|111|998`, bare `911`, can't/cannot breathe, anaphylax, allergic reaction, throat closing/swelling, epipen, `call emergency`.

### Product-name question

```
I need the ingredient list from the pack, not just the product name. I will not mark this SAFE from the name alone.
```

No audit. No SAFE chip.

### Multi-product

```
That looks like more than one product. Paste one ingredient list at a time so I don't combine them into one verdict.
```

No combined verdict.

### Unsupported restriction

```
I don't evaluate keto, diabetic. I can still check ingredients you paste against a diet or allergy profile.
```

(`keto`, `diabetic`, `low_sodium`, `low_fodmap`; `organic` may also appear.)

### Bilingual label

Not a separate stream shape. One `label` block, one echo, one audit. Language headers (`Ingredients (FR):`, `Zutaten:`) are not `multi_product`.

## HTTP statuses the chat BFF can surface

| Status | Who emits | Chat UI |
| --- | --- | --- |
| **413** | Next.js `/api/chat` when body > 512KB. Backend `/api/v1/evaluate-*` oversized body / too many atoms. **Not** grocery chat query-too-long. | “This request is too large…” |
| **422** | Backend `/api/v1/evaluate-*` empty `restriction_ids` or empty ingredients. Grocery chat uses `PROFILE_REQUIRED` instead of 422. | “That request could not be processed…” |
| **429** | SlowAPI on `/chat/grocery` (anon 20/min, auth 30/min). BFF forwards the status. | “Too many requests…” |
| **400** | Grocery chat query longer than `MAX_CHAT_QUERY_LENGTH`. BFF also 400 when the message exceeds config max. | Keep under N characters. |
| **503** | BFF when the backend is unreachable. | Backend unreachable. |

Chat stream failures are **HTTP 200** plus the degraded fail-closed sentence, not 5xx.

## Frontend state matrix

| State | Verdict chips | Audit cards | Extra UI |
| --- | --- | --- | --- |
| `PROFILE_REQUIRED` | no | no | profile modal + notice |
| emergency | no | no | styled emergency block first |
| confirm pending | only if an audit also arrived | allowed (session tighten) | Yes / No / Only today |
| understanding echo | — | — | echo block |
| degraded | no | optional, no chips | UNCERTAIN banner |
| product-name / multi-product / unsupported | no | no | prose |
| normal verdict | yes | yes | echo + cards |

## Contract gaps (backend emits X, frontend cannot consume Y)

Recorded for Track B; backend is not changed here.

1. **No emergency tag / no region on the wire.** Stream is generic-list text. Frontend infers emergency from wording and applies region locally. `detect_emergency(query)` is called without `region`.
2. **`userProfile` has no `region` field** on `ChatRequest` / `ProfileBody`. A frontend `region` hint is local-only and is not sent to the engine.
3. **`degraded` is not in `<<<INGREDIENT_AUDIT>>>`.** Chat fail-closed is unmarked 200 text. Frontend regexes that sentence and will honor `degraded` on the JSON if it appears later.
4. **Confirm is unmarked prose.** No structured `{action, restriction_ids}` block. Yes/No/Only-today matching is frontend-side against known sentences + the backend reply whitelist.
5. **Echo is unmarked prose.** No `<<<ECHO>>>`. Frontend parses `I understood` / `I could not use` / `Checking against`.
6. **Grocery chat does not use 413/422 for the cases the evaluate API does.** Query-too-long is 400. Empty restrictions are `PROFILE_REQUIRED` at 200. 413/422 in the chat UI are BFF/proxy or evaluate-shaped errors only.
7. **`PROFILE_REQUIRED` has no JSON payload** (no suggested fields). Frontend can only open the existing profile form.
