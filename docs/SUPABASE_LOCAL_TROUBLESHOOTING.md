# Supabase Local Troubleshooting

## port is already allocated (e.g. 54322) / Bind for 0.0.0.0:54322 failed

**Cause:** The previous Supabase project (e.g. `IngreSure`) is still running and holding the DB port. This can happen after changing `project_id` in config: `supabase stop` stops the *current* project (`ingresure`), but the *old* project’s containers may still be running.

**Fix:**

```bash
# Stop the old project by its previous project_id (exact name from the error message)
supabase stop --no-backup --project-id IngreSure

# Then start again
supabase start
```

---

## getaddrinfo ENOTFOUND supabase_db_IngreSure

**Cause:** A Supabase service (e.g. Studio, Auth, Storage) cannot resolve the database hostname. Docker creates the DB container with a name derived from `project_id` in `supabase/config.toml` (e.g. `supabase_db_IngreSure`). On some systems, mixed-case or long hostnames can fail to resolve on the Docker network.

**Fix:**

1. **Use a lowercase project_id** (already set in `config.toml`):
   - `project_id = "ingresure"` so the container name is `supabase_db_ingresure`.

2. **Full restart:**
   ```bash
   cd /path/to/IngreSure
   supabase stop --no-backup
   supabase start
   ```

3. If it still fails: ensure Docker Desktop is running and no other Supabase project is using the same ports. Try `docker network prune` then `supabase start` again.

---

## duplicate key value violates unique constraint "migrations_name_key"

**Cause:** An internal Supabase service (e.g. Storage) is running migrations and trying to insert a migration row that already exists. This can happen after an incomplete start or when the migration history is out of sync.

**Fix:**

1. **Clean restart** (wipes local DB and re-runs all migrations):
   ```bash
   supabase stop --no-backup
   supabase start
   ```

2. If the error persists, it may be a bug in the Supabase CLI version. Try updating:
   ```bash
   brew upgrade supabase/tap/supabase
   ```
   Then `supabase stop --no-backup` and `supabase start` again.

---

## supabase_storage_IngreSure in Docker — required?

- **`supabase_storage_IngreSure`** (capital I): **Old leftover.** Not required. Remove with `supabase stop --no-backup --project-id IngreSure` then `docker container prune -f`.
- **`supabase_storage_ingresure`** (lowercase): Part of current stack. App does not use Storage; disabled in `config.toml` so it will not start on next `supabase start`.

## supabase_storage_IngreSure container is not ready: unhealthy

Usually a **consequence** of the above (Storage can’t reach the DB or its migrations fail). Fix the ENOTFOUND or migration error first, then run `supabase stop --no-backup` and `supabase start`.

---

## After changing project_id

If you changed `project_id` from `IngreSure` to `ingresure`, run:

```bash
supabase stop --no-backup
supabase start
```

Local URLs (Studio, API, etc.) are unchanged; only the internal container names and hostnames use the new id.
