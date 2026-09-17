# USE_PROFILE_DB — What, How, Why

**Status:** Not implemented. The backend currently stores user profiles only in a JSON file (`data/profiles.json`). The docstring in `core/profile_storage.py` mentions an optional `USE_PROFILE_DB=supabase`; this document explains what that would do and why you might add it.

---

## What it would do

**USE_PROFILE_DB** would switch profile persistence from the file-based store to a database (e.g. Supabase). When enabled (e.g. `USE_PROFILE_DB=supabase`):

- **Read path:** `get_profile(user_id)`, `get_or_create_profile(user_id)` would load the profile from a DB table (e.g. `user_profiles`) instead of reading `data/profiles.json`.
- **Write path:** `save_profile(profile)` and `update_profile_partial(...)` would write to the same table instead of (or in addition to) updating the JSON file.
- **Behaviour:** The rest of the app (chat, profile merge, restriction IDs, etc.) would stay the same; only the storage layer would change. The profile shape (user_id, dietary_preference, allergens, lifestyle) would remain the same.

So: same API and same behaviour, different backing store.

---

## How it would work (conceptually)

1. **Config:** Read `USE_PROFILE_DB` from env (e.g. `supabase` or empty). If unset or empty, keep current file-based logic.
2. **Supabase:** Reuse the same Supabase URL and service role key already used for the ingredient knowledge DB. Add a table, e.g. `user_profiles`, with columns: `user_id` (PK), `dietary_preference`, `allergens` (array or JSON), `lifestyle` (array or JSON), and optionally `updated_at`.
3. **Storage layer:** In `profile_storage.py`, branch on `USE_PROFILE_DB`:  
   - If file mode: current `_load_all()` / `_save_all()` and key by `user_id` in the in-memory dict.  
   - If DB mode: implement `get_profile` / `save_profile` / `update_profile_partial` with Supabase client (select by user_id, upsert row, merge semantics for partial updates).
4. **No change to callers:** `app.py` and any other code that call `get_or_create_profile`, `save_profile`, `update_profile_partial` would not change; they would still receive and pass the same `UserProfile` model.

So: one storage implementation per backend (file vs Supabase), chosen by env, with the same interface.

---

## Why you might want it

| Reason | Explanation |
|--------|-------------|
| **Scale / multi-instance** | With file storage, all instances must share the same `profiles.json` (e.g. NFS) or you get split state. A DB gives a single source of truth and works with multiple app instances. |
| **Durability and backups** | Supabase (or any DB) gives transactions, backups, and point-in-time recovery. A single JSON file is easier to corrupt or lose. |
| **Audit and analytics** | You can query and log profile changes in the DB, add `updated_at`, and (if needed) enforce retention or anonymization. |
| **Future auth** | If you later tie `user_id` to Supabase Auth (or another provider), having profiles in the same DB simplifies joins and consistency. |

You might **not** need it if you run a single instance, are fine with file backups, and do not plan to scale horizontally or integrate with auth/DB soon.

---

## Summary

- **What:** Switch profile storage from JSON file to DB (e.g. Supabase table) when `USE_PROFILE_DB` is set.
- **How:** Env flag; in `profile_storage.py` branch to DB client for get/save/update; same `UserProfile` interface.
- **Why:** Multi-instance, durability, backups, audit, and future auth integration.

No code is implemented today; this doc is for planning and product/security decisions.
