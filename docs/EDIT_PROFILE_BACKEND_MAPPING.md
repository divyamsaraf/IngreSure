# Edit Profile → Backend / DB / Logic Mapping

Every option in the updated Edit Profile modal is correctly handled by the backend, bridge, compliance engine, and storage.

---

## 1. Dietary Preference (choose one)

| UI option           | Sent value           | Bridge key (normalized)   | Restriction ID         | data/restrictions.json |
|---------------------|----------------------|---------------------------|------------------------|------------------------|
| No preference       | `No rules`           | — (skipped)               | —                      | —                      |
| Vegan               | `Vegan`              | `vegan`                   | `vegan`                | ✅                     |
| Vegetarian          | `Vegetarian`         | `vegetarian`              | `vegetarian`           | ✅                     |
| Pescatarian         | `Pescatarian`        | `pescatarian`             | `pescatarian`          | ✅                     |
| Jain                | `Jain`               | `jain`                    | `jain`                 | ✅                     |
| Halal               | `Halal`              | `halal`                   | `halal`                | ✅                     |
| Kosher              | `Kosher`             | `kosher`                  | `kosher`               | ✅                     |
| Hindu Vegetarian    | `Hindu Vegetarian`   | `hindu vegetarian`        | `hindu_vegetarian`     | ✅                     |
| Hindu Non Vegetarian| `Hindu Non Vegetarian`| `hindu non vegetarian`   | `hindu_non_vegetarian` | ✅                     |

- **Storage:** `dietary_preference` stored as-is in profile (e.g. `data/profiles.json` or Supabase).
- **Logic:** `user_profile_model_to_restriction_ids()` and `profile_to_restriction_ids()` use `DIETARY_PREFERENCE_TO_RESTRICTION_ID` (bridge). All keys above exist and map to restriction IDs that exist in `data/restrictions.json`.

---

## 2. Additional Restrictions (optional, multi-select)

| UI option                    | Sent value              | Bridge key (normalized) | Restriction ID      | data/restrictions.json |
|-----------------------------|-------------------------|--------------------------|---------------------|------------------------|
| Gluten-Free                 | `Gluten-Free`           | `gluten_free`           | `gluten_free`       | ✅                     |
| Dairy-Free                  | `Dairy-Free`            | `dairy_free`            | `dairy_free`        | ✅                     |
| Egg-Free                    | `Egg-Free`              | `egg_free`              | `egg_free`          | ✅                     |
| No Onion                    | `no onion`              | `no_onion`              | `no_onion`          | ✅                     |
| No Garlic                   | `no garlic`             | `no_garlic`             | `no_garlic`         | ✅                     |
| No Alcohol                  | `no alcohol`            | `no_alcohol`            | `no_alcohol`        | ✅                     |
| No Palm Oil                 | `no palm oil`           | `no_palm_oil`           | `no_palm_oil`       | ✅                     |
| No Insect-Derived Ingredients | `no insect derived`  | `no_insect_derived`     | `no_insect_derived` | ✅                     |

- **Storage:** All stored in `lifestyle` array in the profile.
- **Logic:** For each lifestyle value, bridge uses `_normalize_key()` (lowercase, spaces → underscores). Then `rid = LIFESTYLE_TO_RESTRICTION_ID.get(key) or DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(key)`. Gluten-Free / Dairy-Free / Egg-Free resolve via `DIETARY_PREFERENCE_TO_RESTRICTION_ID`; the rest via `LIFESTYLE_TO_RESTRICTION_ID`. All resulting restriction IDs exist in `data/restrictions.json`.

---

## 3. Allergens (multi-select)

| UI option     | Sent value (after normalizeAllergen) | Bridge key | Restriction ID     | data/restrictions.json |
|---------------|--------------------------------------|------------|--------------------|------------------------|
| Milk          | `milk`                                | `milk`     | `dairy_free`       | ✅                     |
| Eggs          | `eggs`                                | `eggs`     | `egg_free`         | ✅                     |
| Peanuts       | `peanuts`                             | `peanuts`  | `peanut_allergy`   | ✅                     |
| Tree Nuts     | `tree nuts` → `tree_nuts` (bridge)    | `tree_nuts`| `tree_nut_allergy` | ✅ (tree_nut_allergy)  |
| Soy           | `soy`                                 | `soy`      | `soy_allergy`      | ✅                     |
| Wheat/Gluten  | `wheat` (frontend strips after `/`)   | `wheat`    | `gluten_free`      | ✅                     |
| Fish          | `fish`                                | `fish`     | `fish_allergy`     | ✅                     |
| Shellfish     | `shellfish`                           | `shellfish`| `shellfish_allergy`| ✅                     |
| Sesame        | `sesame`                              | `sesame`   | `sesame_allergy`   | ✅                     |
| Mustard       | `mustard`                             | `mustard`  | `mustard_allergy`  | ✅                     |
| Celery        | `celery`                              | `celery`   | `celery_allergy`   | ✅                     |
| Other         | (user input, stored as-is)            | —          | —                  | (no rule; custom)      |

- **Storage:** `allergens` array; frontend sends lowercase (and for "Wheat/Gluten" sends `wheat`). Backend stores as received.
- **Logic:** Bridge `ALLERGEN_TO_RESTRICTION_ID` has entries for milk, eggs, peanuts, tree_nut, soy, wheat, fish, shellfish, sesame, mustard, celery. “Other” and custom entries are stored but may not map to a restriction (no rule in engine).
- **Display:** When loading profile, frontend `allergenToDisplay()` maps backend values back to display labels (e.g. `egg`/`eggs` → “Eggs”, `wheat` → “Wheat/Gluten”).

---

## 4. Database and services

| Layer            | Role |
|------------------|------|
| **Profile storage** | `core/profile_storage.py`: reads/writes `dietary_preference`, `allergens`, `lifestyle` to `data/profiles.json` (or Supabase if configured). No schema change; same three fields. |
| **Profile API**     | `POST /profile` and `GET /profile/{user_id}` use the same fields. Request/response shape unchanged. |
| **Chat**           | `POST /chat/grocery` merges `request.userProfile` (dietary_preference, allergens, lifestyle) into the in-memory profile, then runs intent → compliance with `user_profile_model_to_restriction_ids(profile)`. |
| **Compliance**      | IKE-2 (`core/knowledge/ike2/` + `bridge` / `v1_evaluate`) evaluates `restriction_ids` from the bridge. Rule seed + DB `ike2_restriction_rules` cover the profile options above; legacy `data/restrictions.json` is no longer the serve path (Item 16). |

---

## 5. Summary

- **Dietary Preference:** All 9 options (including No preference) are stored and mapped to the correct restriction IDs; all IDs exist in `data/restrictions.json`.
- **Additional Restrictions:** All 8 options are stored in `lifestyle` and mapped to restriction IDs via bridge; all IDs exist in `data/restrictions.json`.
- **Allergens:** All 12 options (including Other) are stored; the 11 non-Other options are normalized and mapped to restriction IDs; those IDs exist in `data/restrictions.json`. Other/custom are stored and displayed without requiring a restriction rule.

**Note:** The bridge was updated to include `"tree_nuts": "tree_nut_allergy"` so that the frontend value "tree nuts" (normalized to `tree_nuts`) maps correctly. All other options were already covered.

No other backend, database, or restriction data changes are required for the updated Edit Profile UI.
