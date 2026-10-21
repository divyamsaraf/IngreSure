# Item 39 leftovers (additive guards)

No blind rewrite of `ontology.json`. These leftovers are locked with tests
and an operator script.

## sesame_source null on catalog rows

Produce and animal catalog seeds omit `sesame_source` rather than storing
JSON null. After `map_record`, the flag is always a bool (default false).
`tests/ike2/test_item39_leftovers.py` fails if any catalog row stores
`sesame_source: null` or if adapt emits `None`.

## Dietary fibre / fiber identity

`dietary fibre` is an ontology row; `dietary fiber` is the US spelling.
They are an orthographic pair and must share hazard derive flags. Aliasing
`dietary fiber` onto `dietary fibre` in ontology.json is an owner patch
(not applied here).

## Orthographic baseline shrink (allergy first)

`orthographic_safe_uncertain_baseline.json` grandfathers 528 SAFE↔UNCERTAIN
triples. `scripts/shrink_orthographic_baseline.py` re-evaluates allergy
restrictions first and drops triples that no longer reproduce the
asymmetry.

```
python scripts/shrink_orthographic_baseline.py --dry-run
python scripts/shrink_orthographic_baseline.py --apply
```
