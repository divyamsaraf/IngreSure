# AI / LLM touchpoints (current)

**Authority for Item 6 work:** `docs/item6_llm_pipeline_spec.md`.  
This file replaces an obsolete “Safety Analyst / llm_normalizer” description that never matched the living codebase.

## Invariant

**IKE-2 resolve and compliance never call an LLM.** Verdicts come from ontology/DB flags × restriction rules. Ollama is UX and optional enrichment assist only.

## Where Ollama is used

| Role | Module | When |
|------|--------|------|
| Intent fallback | `core/llm_intent.py` | Chat: after rule-based intent is weak/general |
| Greeting / general / verdict prose | `core/llm_response.py` | Chat stream; templates if LLM off or down |
| Enrichment origin classify | `core/knowledge/llm_classify.py` | Worker only, after API path; adds `llm_classified` |
| Regional English-name hint | `core/external_apis/fetcher.py` | After Wikidata miss on enrich |

Config: `LLM_ENABLED` (default on; CI forces off), `OLLAMA_API_URL`, `OLLAMA_MODEL`, intent/response timeouts in `core/config.py`.

## What does not exist

- No `llm_normalizer.py`, no scan/OCR → ingredient LLM path, no `/scan` backend route.
- No embeddings / vector matching / unified “ML pipeline” package.
- Coverage OS induction (`cluster` / `propose_alias` / `propose_role`) is deterministic heuristics — not LLM.

## Fail-soft

`LLM_ENABLED=false`, timeout, or Ollama down → chat uses templates; enrichment skips classify and continues with API-only / DISCOVERED facts. Compliance behavior is unchanged.
