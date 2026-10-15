# Item 44 follow-up — multilingual aliases (OFF taxonomy)

## Check: were OFF taxonomy synonyms (fr/de/es/it/nl) ingested?

**No — not as language-keyed aliases on trusted heads.**

What exists today:

| Path | What it stores | Languages |
|------|----------------|-----------|
| OFF enrichment (`open_food_facts` fetcher) | DISCOVERED candidate rows for unknown atoms | whatever OFF returns for that query |
| `sources.py` / adapt | `openfoodfacts` → DISCOVERED tier | not synonym expansion |
| Item 42 capstone b | OFF taxonomy **ancestry** for kind/hazard checks | taxonomy tags, not label synonyms |
| Ontology / truth_anchor | mostly English (+ some vernacular in `flag_derive`) | no systematic fr/de/es/it/nl |

Item 44 UNCERTAIN tops (`sel`, `eau`, `sucre`, `huile de colza`, `arôme naturel`)
are therefore L5 even when the English head (`salt`, `water`, `sugar`,
`rapeseed oil`) is a trusted ontology row.

**Upstream source available (not yet wired):** ODbL JSON export
`https://static.openfoodfacts.org/data/taxonomies/ingredients.json`
(and the text taxonomy under `openfoodfacts-server/taxonomies/`). Names include
`fr`/`de`/`es`/`it`/`nl` synonyms for canonical `en:*` tags (e.g. `en:sugar` →
`sucre`).

## Plan: language-keyed aliases → trusted heads

1. **Source:** OFF ingredients taxonomy JSON above (ODbL). Prefer that export
   over scraping product `ingredients_text`.
2. **Shape:** alias rows `{alias, lang, group_id}` pointing at existing
   **trusted** heads only (ontology / human / e-number). Never invent groups
   from OFF-only synonyms.
3. **Trust inheritance:** alias → head keeps the head’s `source` and
   `trusted` bit (same as English orthographic variants). No per-row review
   when the head is already firm-SAFE eligible.
4. **Scope (wave 1):** fr/de high-frequency pantry terms from Item 44
   UNCERTAIN tops + UK/EU L5 mass. Wave 2: es/it/nl.
5. **English gaps in parallel:** `iodised salt` / `edible common salt` →
   `salt`; `vitamin b12` → existing vitamin head — orthographic / synonym
   table, not OFF taxonomy.
6. **Non-goal:** marketing free-from claims stay non-evidence. Mandatory
   allergen declarations (EU FIC / US FALCPA) are a separate policy decision
   after the coverage curve exists.

## Acceptance

- `sel`, `eau`, `sucre`, `huile de colza` resolve L2/L1 trusted (or L1 e-number
  path) under FR labels in the Item 44 sample.
- UK/EU L5 instance rate drops materially without raising derive-only false
  Avoids on pantry staples.
- License note: ODbL attribution on any committed synonym dump (IDs/aliases
  only; no full OFF product redistributions).
