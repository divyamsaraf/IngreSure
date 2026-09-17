# Why "bajra" still shows "Couldn't find reliable information" and how to fix it

The backend code was updated so that:

1. **Built-in regional map** is applied (e.g. `bajra` → `pearl millet`) even when `data/regional_ingredient_names.json` is missing.
2. **Open Food Facts** is tried with "pearl millet" first (OFF returns a result for that).
3. **Wikidata** is tried with both "pearl millet" and "bajra".
4. **Medium-confidence** API results are stored so the knowledge base expands automatically.

If you still see the message in the frontend, the backend process is almost certainly **still running the old code**.

## Fix: Restart the backend

Your backend runs in Docker **without** `--reload`, so it only loads code when the process starts. You must **restart** the backend container so it loads the new code.

### If you use Docker Compose

**Option A – Restart the backend only (code is mounted as volume):**
```bash
docker compose restart backend
```

**Option B – Rebuild and restart (if you don’t use a code volume or want a clean build):**
```bash
docker compose build backend --no-cache
docker compose up -d backend
```

Then try "bajra" again in the Grocery Safety Assistant.

### How to confirm the new code is running

After restarting, when you send "bajra" in chat, check the backend logs. You should see something like:

- `REGIONAL_QUERY using built-in mapping: bajra -> pearl millet`
- `ENRICHMENT open_food_facts query=pearl millet success=True confidence=medium`
- `ONTOLOGY_ENRICHMENT added (medium) raw=bajra ... canonical_name=pearl millet`

If you see those lines, the new path is active and "bajra" should resolve. If you still see only "EXTERNAL_LOOKUP failed" or no "REGIONAL_QUERY" / "pearl millet" lines, the process is still running old code or there is a network issue from the container to Open Food Facts.

### If you run the backend locally (no Docker)

Stop the running server (Ctrl+C) and start it again:

```bash
cd backend && uvicorn app:app --host 0.0.0.0 --port 8000
```

Then try "bajra" again.
