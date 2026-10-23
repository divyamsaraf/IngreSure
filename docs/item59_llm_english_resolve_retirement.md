# Item 59 — retire `_resolve_to_english_llm`

The enrichment fetcher no longer asks Ollama for an English name when
Wikidata misses. Regional resolve is Wikidata `resolve_to_english_label`
only. Prompt-shaped ingredient strings must not reach an LLM.

## What was removed

- `core.external_apis.fetcher._resolve_to_english_llm`
- The call site that ran after `resolve_to_english_label` returned None

## CI

`tests/ike2/test_item59_llm_english_retired.py` asserts the symbol is gone
and that injection-style queries never call `requests.post` (Ollama).
