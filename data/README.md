# Data files

**Canonical IKE-2 bulk path:** `python -m core.knowledge.ike2.etl.bulk_inject`
(from `backend/`) against `data/layer1_*.json` with `--source <label>` and
`--dry-run` first. Do **not** use `backend/scripts/ingest_layer1_json.py` for
IKE-2 — that script is deprecated and writes legacy `ingredient_*` tables only
(Item 1 Prompt 7). Optional aggregator: `scripts/bulk_inject_all.sh --dry-run`.

- **profile_options.json** — Single source of truth for diet, allergen, and lifestyle options. Backend reads this file and serves it via **GET /config** (with `max_chat_message_length`). Frontend fetches from `/api/config` and uses that; `frontend/src/constants/profile_options.json` is used only as fallback when the backend is unreachable.
- **ontology.json**, **dynamic_ontology.json** — Ingredient knowledge.
- **restrictions.json** — Dietary/restriction rules for the compliance engine.
- **layer1_*.json** — Per-source Layer-1 dumps for IKE-2 `bulk_inject` (including `layer1_produce_catalog.json`, `layer1_animal_catalog.json`).
