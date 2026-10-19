# OCI API deploy runbook (no execution — operator checklist)

**Host:** `ingresure-api.gleeze.com` (Caddy → `127.0.0.1:8000`)  
**Goal:** Put **current `main`** on the API with a matching DB, then verify via `/health` + peanut smoke.  
**Do not paste secrets.** Record project refs and env **names** only.

---

## 0. Interim lock (do this first, before deploy)

App-level `ENVIRONMENT=production` is **not** a lock on pre–Item 9 builds. Lock at Caddy.

Exact snippet for the API vhost (replace hostname; keep ACME/`default_bind` from `deploy/Caddyfile.example`):

```caddy
ingresure-api.gleeze.com {
	# Interim: require X-API-Key on /api/v1/* until app gate is confirmed live.
	# Value must match a key you will put in B2B_API_KEYS after deploy.
	@apiv1 path /api/v1/*
	handle @apiv1 {
		@nokey not header X-API-Key *
		respond @nokey "API key required" 401
		reverse_proxy 127.0.0.1:8000
	}
	handle {
		reverse_proxy 127.0.0.1:8000
	}
}
```

Stricter (fixed key at the proxy — rotate when app owns the gate):

```caddy
ingresure-api.gleeze.com {
	@apiv1 path /api/v1/*
	handle @apiv1 {
		@bad not header X-API-Key {$CADDY_API_V1_KEY}
		respond @bad "API key required" 401
		reverse_proxy 127.0.0.1:8000
	}
	handle {
		reverse_proxy 127.0.0.1:8000
	}
}
```

Set `CADDY_API_V1_KEY` in the Caddy service environment (not in git).  
`/health`, `/chat/grocery`, `/profile` stay reachable (chat still needs a separate decision if consumer traffic must stop).

Validate: `sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy`  
Probe: `curl -sS -o /dev/null -w '%{http_code}\n' -X POST https://ingresure-api.gleeze.com/api/v1/evaluate-compliance -H 'Content-Type: application/json' -d '{"ingredients":["water"],"restriction_ids":["vegan"]}'` → **401** without key.

---

## 1. Discover what is running (operator)

On the OCI host:

| Check | Command / place |
|-------|-----------------|
| Process | `systemctl status` / `docker ps` / `ps aux \| grep uvicorn` |
| Working tree | `cd` to app dir → `git rev-parse HEAD` and `git status` |
| Image tag | If Docker: `docker inspect <container> --format '{{.Image}}'` / compose image |
| Caddy | `sudo cat /etc/caddy/Caddyfile` |
| Env names | `grep -E '^(ENVIRONMENT|B2B_API_KEYS|SUPABASE_|CORS_|GIT_SHA|RATE_LIMIT)' backend/.env \| cut -d= -f1` |
| Supabase ref | Host in `SUPABASE_URL` (e.g. `gcufjqokqqmcuuayaybu`) — **not** the key |

Record: **git SHA or image digest**, **Supabase project ref**, **env names present**.

Access logs (exposure vs incident): last 7 days unique client IPs for the API vhost (Caddy/access log path on host). Note whether Vercel/`BACKEND_URL` points here — frontend BFF uses `BACKEND_URL` for `/chat/grocery`, `/profile`, `/config`, `/anon-session` (not necessarily `/api/v1`).

---

## 2. Which database

| Option | When |
|--------|------|
| **A. Linked remote** `gcufjqokqqmcuuayaybu` | Preferred if this is the intended prod project. Today: missing migrations `20260918*`–`20261014*`, empty `ike2_*` groups (see `docs/item29_remote_ike2_seed_plan.md`). |
| **B. Other Postgres on the VM / other Supabase** | If `SUPABASE_URL` is not that ref — treat as legacy; still apply the same migration set and seed. |

**Migration order:** `supabase db push --linked` (or `supabase migration up` against the URL in `SUPABASE_URL`) so **`20261014000000_ike2_alias_view_include_source`** is applied and `ike2_v_alias_resolution` exposes `source`.

**Ontology / L3 seed (Item 29):** after migrations,

1. Confirm `ike2_restriction_rules` count (expect 52 from seed migration).  
2. `python scripts/seed_ike2_ontology.py` (or current seed entrypoint) from `data/ontology.json` against that DB.  
3. Optional: `bulk_inject` for selected `data/layer1_*.json` per Item 29 plan.  
4. Do **not** copy soak `ike2_shadow_diffs`.

L1 truth_anchor and L2 `data/ontology.json` ship with the app binary/checkout; empty L3 only hurts DB-only atoms.

---

## 3. Deploy current `main` to the API

Assumes git checkout deploy (adjust if Docker image):

```bash
# on OCI, as deploy user
cd /path/to/IngreSure
git fetch origin
git checkout main
git pull --ff-only origin main
EXPECTED_SHA=$(git rev-parse HEAD)

# backend env (names — set values on host)
# ENVIRONMENT=production
# B2B_API_KEYS={"<pilot-key>":"starter"}
# SUPABASE_URL=https://<project-ref>.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=...
# CORS_ORIGINS=https://<vercel-app>.vercel.app,...
# GIT_SHA=$EXPECTED_SHA          # required so /health matches without relying on .git
# RATE_LIMIT_* as needed

cd backend
# venv + deps if not image-based
source venv/bin/activate   # or recreate
pip install -r requirements.txt

# restart API (pick what the host uses)
sudo systemctl restart ingresure-backend   # example unit name
# or: docker compose up -d --build backend
```

**Docker variant:** build/push image tagged with `$EXPECTED_SHA`, set `GIT_SHA` in compose/k8s, roll the container.

**After app restart:** remove or relax the interim Caddy key check only once `/health` shows `production: true` and unauthenticated `/api/v1` returns **401**.

---

## 4. Post-deploy verify

```bash
export PROD_API_BASE=https://ingresure-api.gleeze.com
export EXPECTED_GIT_SHA=$EXPECTED_SHA
export PROD_API_KEY=<pilot-key>   # required once gate is on

cd backend
python scripts/post_deploy_smoke.py
```

Asserts:

- `GET /health` → `git_sha` equals merge tip (or prefix match), `engine=ike2`
- `POST /api/v1/evaluate-product` with `PEANUTS (49.5%), honey, salt` + `peanut_allergy` → **`NOT_SAFE`**, no bare percent atom

Then rerun held-out parity through the **keyed** endpoint:

```bash
PROD_API_KEY=<pilot-key> python scripts/item44_prod_parity.py --sleep 1.2
```

---

## 5. Rollback

1. `git checkout <previous_sha>` (or redeploy previous image digest).  
2. Restart API; set `GIT_SHA` to that sha.  
3. DB: migrations are forward-only — do **not** auto-down. If a migration broke the view, restore from snapshot taken before `db push`.  
4. Re-enable interim Caddy `/api/v1` lock if rolling back to pre–Item 9 code.  
5. Re-run `post_deploy_smoke.py` against the rolled-back SHA (expect peanut behavior of that SHA).

---

## 6. Vercel coupling

| Surface | Env | Routes |
|---------|-----|--------|
| Frontend BFF | `BACKEND_URL` | `/chat/grocery`, `/profile`, `/config`, `/anon-session` |
| Direct B2B | clients → API host | `/api/v1/*` |

If Vercel `BACKEND_URL` is this hostname, consumer chat uses the **same** engine as the public API. Locking only `/api/v1` does not stop legacy chat until the API binary is upgraded or chat is pointed elsewhere.
