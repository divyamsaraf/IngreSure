# Diet and restriction IDs: where to add or change

To keep dietary preferences, allergens, and lifestyle options consistent across the app, update **all** of the following when you add or change a diet or restriction. The backend uses these for intent detection, profile→restriction mapping, and compliance.

## 1. Profile options (UI and API)

**File:** `data/profile_options.json`

- **`dietary_preference_options`** — Array of `{ "value": "<Canonical Name>", "label": "<Display>" }`. These are the values users can select. Use the same `value` strings in the backend maps below (normalized to lowercase with spaces/underscores for lookup).
- **`allergen_options`** — Array of display strings (e.g. `"Milk"`, `"Peanuts"`). Backend maps these (normalized) to restriction IDs.
- **`lifestyle_options`** — Array of `{ "value": "<internal>", "label": "<Display>" }` (e.g. `"no onion"`, `"Gluten-Free"`).
- **`diet_icon`** — Optional map of diet value → emoji for UI.

**Sync:** The frontend keeps a fallback copy at `frontend/src/constants/profile_options.json`. Keep it in sync (run `python3 backend/scripts/check_profile_options_sync.py`). The backend serves profile options via **GET /config**.

## 2. Bridge (profile → restriction_id)

**File:** `backend/core/bridge.py`

- **`DIETARY_PREFERENCE_TO_RESTRICTION_ID`** — Map from normalized diet name (lowercase, spaces or underscores) to `restriction_id` (e.g. `"vegan"` → `"vegan"`, `"hindu vegetarian"` → `"hindu_vegetarian"`). Add entries for any new dietary preference so the compliance engine gets the right restrictions.
- **`ALLERGEN_TO_RESTRICTION_ID`** — Normalized allergen key → restriction_id (e.g. `"peanuts"` → `"peanut_allergy"`).
- **`LIFESTYLE_TO_RESTRICTION_ID`** — Lifestyle value → restriction_id (e.g. `"no_onion"` → `"no_onion"`).

Normalization: lowercase, strip, and for display names with spaces you can use both `"hindu vegetarian"` and `"hindu_vegetarian"` as keys pointing to the same restriction_id if needed.

## 3. Intent detector (natural language)

**File:** `backend/core/intent_detector.py`

- **`DIET_KEYWORDS`** — Map from **lowercase phrase** (as users might type or say) to **canonical display name** (e.g. `"hindu veg"` → `"Hindu Vegetarian"`, `"vegan"` → `"Vegan"`). Add variants here so phrases like "I am Jain", "set diet to Halal" are recognized. The canonical name must match a `value` in `profile_options.json` and a key (normalized) in `DIETARY_PREFERENCE_TO_RESTRICTION_ID`.
- **`DIET_SYNONYMS`** — Canonical diet → list of input variants (for docs and consistency).

When adding a new diet: add at least one entry in `DIET_KEYWORDS` (e.g. the canonical name lowercased) so intent detection can set `profile_updates["dietary_preference"]` to the canonical value.

## 4. Restriction definitions (compliance rules)

**File:** `data/restrictions.json`

Each restriction_id used in the bridge (e.g. `vegan`, `jain`, `peanut_allergy`) should have a corresponding definition here (name, description, rules, triggered ingredients, etc.). The compliance engine loads this file; if a restriction_id is missing, that restriction will not be evaluated.

## Checklist: adding a new diet

1. Add the diet to **`data/profile_options.json`** under `dietary_preference_options` (value + label) and optionally `diet_icon`.
2. Add the normalized key(s) to **`backend/core/bridge.py`** → `DIETARY_PREFERENCE_TO_RESTRICTION_ID` (and to a new or existing restriction_id).
3. Add phrase(s) to **`backend/core/intent_detector.py`** → `DIET_KEYWORDS` so natural language maps to the same canonical name as in step 1.
4. If the restriction is new, add its definition to **`data/restrictions.json`**.
5. Run **`backend/scripts/check_profile_options_sync.py`** so the frontend fallback stays in sync with `data/profile_options.json`.

## Summary table

| What you change        | Where |
|------------------------|--------|
| Options shown in UI    | `data/profile_options.json` (+ frontend fallback) |
| Profile → restriction  | `backend/core/bridge.py` (DIETARY_*, ALLERGEN_*, LIFESTYLE_*) |
| “I am X” / diet phrases| `backend/core/intent_detector.py` (DIET_KEYWORDS) |
| Compliance rules       | `data/restrictions.json` |
