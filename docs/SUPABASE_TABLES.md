# Supabase Tables

> **Current state:** Menu/restaurant tables (`menu_items`, `verified_items`, `verification_logs`, `item_ingredients`, `tag_history`, `embeddings`, `restaurant_submissions`) have been **dropped** (migration `20260306100000`). Living schema = legacy knowledge tables + `users` + `request_history` + full `ike2_*` / `ike2_staging` set (migrations `20260409120000`, `20260616000000`+). See `docs/SUPABASE_AFTER_RESTAURANT_REMOVAL.md` and `docs/system_state_audit.md`.

## Verification

From repo root:

```bash
python backend/scripts/verify_supabase.py
```

This checks connectivity, lists public tables and their RLS status, and summarizes which tables are required vs optional.

## Tables Overview

| Table | Purpose | Required? | RLS |
|-------|---------|-----------|-----|
| **Knowledge base (legacy)** | | | |
| `ingredient_groups` | Canonical ingredient identity (origin, flags) | Yes (legacy path / enrichment) | ON, backend-only |
| `ingredients` | Names/strings that map to a group | Yes | ON, backend-only |
| `ingredient_aliases` | Normalized alias → ingredient → group | Yes | ON, backend-only |
| `unknown_ingredients` | Legacy discovery queue (no longer drained after Items 18+23) | No (safe to truncate; see note below) | ON, backend-only |
| `enrichment_metrics` | Coverage/resolution metrics per day | No (analytics only) | ON, backend-only |
| **App** | | | |
| `users` | Auth-linked profiles (`diet_type`, `allergies`, `preferences`) | Optional (auth / `USE_PROFILE_DB`) | ON, own row |
| `request_history` | Write-only HTTP/chat analytics from FastAPI | No (ops) | ON, no client policies |
| **IKE-2 (public)** | | | |
| `ike2_ingredient_groups` | IKE-2 canonical groups + flags + knowledge_state | Yes (IKE-2 primary) | ON, backend-only |
| `ike2_ingredients` | Normalized ingredient rows under a group | Yes | ON, backend-only |
| `ike2_aliases` | Alias → ingredient (region/type/confidence) | Yes | ON, backend-only |
| `ike2_alias_disambiguation` | Ambiguous alias context → ingredient | Yes | ON, backend-only |
| `ike2_restriction_rules` | Restriction rules (category/field/action) | Yes | ON, backend-only |
| `ike2_resolution_cache` | Optional SQL resolution audit cache | No (hot path is in-process) | ON, backend-only |
| `ike2_unknown_queue` | IKE-2 discovery + enrichment queue (Items 18+23) | Yes | ON, backend-only |
| `ike2_shadow_diffs` | Legacy vs IKE-2 observational diffs | Yes (cutover / Item 16) | ON, backend-only |
| `ike2_group_merges` | Group merge / rollback snapshots | No (ops) | ON, backend-only |
| **IKE-2 staging schema** | | | |
| `ike2_staging.ingredient_groups` | Raw bulk-inject staging (no UNIQUE/CHECK) | No (ETL) | n/a (non-public) |
| `ike2_staging.stg_rejects` | Reject quarantine for failed staging rows | No (ETL) | n/a (non-public) |

**View:** `public.ike2_v_alias_resolution` — alias → active ingredient → non-DEPRECATED group.

**Enum:** `ike2_knowledge_state` = `UNCLASSIFIED | DISCOVERED | AUTO_CLASSIFIED | VERIFIED | LOCKED | DEPRECATED`.

**Dropped (migration 20260306100000):** `menu_items`, `item_ingredients`, `tag_history`, `verification_logs`, `restaurant_submissions`, `verified_items`, `embeddings`, and `search_menu_items()`.

## Tables That Can Be Removed or Disabled

- **`unknown_ingredients`** – Legacy queue. The worker does not drain it (Items 18+23), and resolve / `log_unknown` no longer write it (Item 33 Prompt 4). Remaining rows are historical. **Safe to truncate.**
- **`enrichment_metrics`** – No writer after Item 33 Prompt 5 (`canonicalizer._emit_resolution_metric` was the only one). Nothing reads it. Item 12 owns any future resolution telemetry, which starts from zero. Safe to drop.
- **`ike2_resolution_cache`** – Optional; runtime resolution cache is in-process.
- **`ike2_group_merges`** – Optional ops table until merge tooling is active.

## Unknown Ingredients → Knowledge Base Flow

**Current (Items 18+23):** IKE-2 L5 miss → `ike2_unknown_queue` → Celery `enrich_unknown_batch` / `run_enrich_unknown_once.py` → external APIs → `ike2_*` via adapt→validate→reconcile as source `enrichment_api` (DISCOVERED).

**Legacy table:** nothing on the product path writes `unknown_ingredients` anymore. Do not expect the worker to clear leftover rows.
