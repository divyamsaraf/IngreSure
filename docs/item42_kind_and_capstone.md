# Item 42 — Kind sample + capstone (report)

Same-day from this pass: `crayfish` (OFF → shellfish, was SAFE under shellfish_allergy) and `american sea scallop` (fish_only wrong-kind) patched in `ontology.json` (+ live sync).

## Kind assignment (fish / shellfish / both)

- **ifct** n=23: {'shellfish_only': 13, 'fish_only': 10}; wrong-kind risk (shellfish-named + fish_only): **0**
- **infoods** n=389: {'shellfish_only': 78, 'fish_only': 311}; wrong-kind risk (shellfish-named + fish_only): **1**
  - names: `american sea scallop`
  - probe `american sea scallop` shellfish_allergy=UNCERTAIN via L3_db_alias (shellfish_on_ci=False, fish_on_ci=True)
- **ontology** n=156: {'fish_only': 136, 'shellfish_only': 14, 'both': 6}; wrong-kind risk (shellfish-named + fish_only): **0**
- **usda** n=242: {'fish_only': 182, 'shellfish_only': 59, 'both': 1}; wrong-kind risk (shellfish-named + fish_only): **0**

## Capstone a — seeded-DB invariant (design + dry-run)

CI test against seeded DB: for every ike2_ingredient_groups row, for every allergy/medical restriction whose trigger flag is true on the compliance input after production resolve, verdict must not be SAFE (expect NOT_SAFE). This catches Item 34 (KS demotion), Item 42 (inferred untrusted), and the 26-style table rows when the flag actually reaches CI.

- Unique names with a live allergen true: **1800**
- Flag probes (flag reached CI): counted among probes where CI kept the flag
- Violations (CI flag true → SAFE): **0** {}
- Dry-run after Item 42 compliance fix. A true CI test should load a seeded fixture DB, not depend on a developer's local Supabase.

## Capstone b — OFF taxonomy ancestry

Expected hazards from OFF parent chains (halloumi→cheese→dairy). Finding = taxonomy says hazard, flag absent on CI, production SAFE. This catches oat-shape rows invisible to animal_origin/no-kind buckets.

- Names matched to OFF: **612**
- Findings (taxonomy hazard, flag false, SAFE): **1** {'shellfish_source': 1}
- Dairy oat-shape subset: **0**


Artifact: `docs/item42_kind_and_capstone.json`.
