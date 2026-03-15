# Data files

- **profile_options.json** — Single source of truth for diet, allergen, and lifestyle options. Backend reads this file and serves it via **GET /config** (with `max_chat_message_length`). Frontend fetches from `/api/config` and uses that; `frontend/src/constants/profile_options.json` is used only as fallback when the backend is unreachable.
- **ontology.json**, **dynamic_ontology.json** — Ingredient knowledge.
- **restrictions.json** — Dietary/restriction rules for the compliance engine.
