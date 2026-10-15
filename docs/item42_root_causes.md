# Item 42 — Root causes (INFOODS, lexicon, OFF)

Companion numbers: [`item42_infoods_kind_classes.json`](item42_infoods_kind_classes.json), [`item42_off_ancestry_coverage.json`](item42_off_ancestry_coverage.json). Full verification: [`item42_verification.md`](item42_verification.md).

## INFOODS kind mapping

Sheet-09 fish rows set `shellfish_source` from **subgroup** tokens (`mollusc`, `bivalve`, `cephalopod`, `gastropod`, …). Empty/wrong subgroup → fish-only.

Among the 389 fish/shellfish INFOODS groups (name-class inventory):

| Class | Count | Remaining fish-only |
|-------|------:|--------------------:|
| Bivalve | 32 | 0 |
| Cephalopod | 4 | 0 |
| Gastropod | 1 | 0 |

`american sea scallop` was the canary: fish_source true, shellfish false. Fix: name lexicon in `infoods_anfood.flags_for_sheet` when subgroup misses (same crustacean/mollusc tokens as USDA, including scallop).

## Shellfish lexicon (crayfish miss)

OFF ancestry found `crayfish` SAFE under shellfish_allergy; stem/flag scans missed it. Lexicon gaps closed in USDA `_SHELLFISH_NAME` and INFOODS name lex: **crayfish, crawfish, langoustine, krill, yabby** (+ prior prawn/shrimp/crab/lobster/mollusc set).

## OFF ancestry denominator

Earlier report said “612 names matched” without a base. Denominator = unique normalized names in `ontology.json` ∪ live `ike2_ingredient_groups`:

- **612 / 6913 = 8.85%** matched to an OFF `en:` node  
- **966** unmatched names hit a hazard lexicon (milk/egg/fish/shellfish/…) — sample in the JSON artifact  

Thin OFF coverage is why crayfish needed an explicit ontology/L2 patch rather than taxonomy ancestry alone.
