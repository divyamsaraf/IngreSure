# Phase 1 inject — flag changes on existing ontology groups

**2026-10-01. Report only.** Replayed `ontology.json` against the IFCT, FSSAI, and USDA dumps in inject order. A row is listed only when a stored false became true. That is the only change that set `needs_review` and demoted `knowledge_state` to `DISCOVERED`. Ontology-true versus dump-false is listed as an ignored disagreement: the true was kept and did not demote the row.

Added only: **10**. Added plus an ignored disagreement: **72**. The replay also sees a USDA `fungal` addition on `yeast extract spread`, but that live ontology row was already `fungal=true` and stayed `AUTO_CLASSIFIED`, so it is not in this list.

## Added only

- `canthaxanthin` — added: fssai:synthetic false→true uncertainty=['may_be_synthetic_or_animal_derived']
- `disodium 5 ribonucleotides` — added: fssai:synthetic false→true uncertainty=['animal_or_yeast_source']
- `dulce de leche` — added: usda:egg_source false→true
- `polyglycerol esters of fatty acids` — added: fssai:synthetic false→true uncertainty=['animal_or_plant_fatty_acid_source']
- `potato pancakes` — added: usda:root_vegetable false→true
- `sorbitan monooleate` — added: fssai:synthetic false→true uncertainty=['animal_or_plant_fatty_acid_source']
- `sorbitan monopalmitate` — added: fssai:synthetic false→true uncertainty=['animal_or_plant_fatty_acid_source']
- `sorbitan monostearate` — added: fssai:synthetic false→true uncertainty=['stearate_may_be_animal_derived']
- `sucroglycerides` — added: fssai:synthetic false→true uncertainty=['animal_or_plant_fatty_acid_source']
- `sucrose esters of fatty acids` — added: fssai:synthetic false→true uncertainty=['animal_or_plant_fatty_acid_source']
## Added, plus a disagreement the merge ignored

- `acetic acid` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept), fssai:fermented ontology=true dump=false (kept)
- `acetylated distarch adipate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `acetylated distarch phosphate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `acetylated oxidized starch` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `agar` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `alginic acid` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `alpha tocopherol` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept), fssai:soy_source ontology=true dump=false (kept)
- `ammonium alginate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `annatto` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `beeswax` — added: fssai:synthetic false→true. Ignored disagreement: fssai:animal_origin ontology=true dump=false (kept), fssai:insect_derived ontology=true dump=false (kept)
- `calcium alginate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `calcium lactate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept)
- `calcium tartrate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `candelilla wax` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `carnauba wax` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `carotenes` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `carotenoids` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `carrageenan` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `cassia gum` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `chlorophylls` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `curcumin` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `dextrins` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `erythritol` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept), fssai:fermented ontology=true dump=false (kept)
- `ethyl cellulose` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `gellan gum` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept)
- `ghee` — added: ifct:plant_origin false→true. Ignored disagreement: ifct:animal_origin ontology=true dump=false (kept), ifct:dairy_source ontology=true dump=false (kept)
- `glucono delta lactone` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `glycerol` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept) uncertainty=['mono_diglycerides']
- `guar gum` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `gum arabic` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `honey` — added: usda:plant_origin false→true. Ignored disagreement: usda:animal_origin ontology=true dump=false (kept), usda:bee_product ontology=true dump=false (kept)
- `hydroxypropyl cellulose` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `hydroxypropyl distarch phosphate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `hydroxypropyl methyl cellulose` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `hydroxypropyl starch` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `isomalt` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `karaya gum` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `l-cysteine` — added: fssai:synthetic false→true. Ignored disagreement: fssai:animal_origin ontology=true dump=false (kept) uncertainty=['may_be_synthetic_or_from_plant_fermentation', 'traditionally_from_poultry_feathers_or_hog_hair']
- `lactic acid` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept), fssai:fermented ontology=true dump=false (kept) uncertainty=['may_be_animal_derived_in_some_processes']
- `lactitol` — added: fssai:synthetic false→true. Ignored disagreement: fssai:animal_origin ontology=true dump=false (kept), fssai:dairy_source ontology=true dump=false (kept)
- `lysozyme` — added: fssai:synthetic false→true. Ignored disagreement: fssai:animal_origin ontology=true dump=false (kept), fssai:egg_source ontology=true dump=false (kept)
- `malic acid` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `maltitol` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `metatartaric acid` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `methyl cellulose` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `methyl ethyl cellulose` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `monostarch phosphate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `natamycin` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept)
- `nisin` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept)
- `oxidized starch` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `paprika` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `paprika extract` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `phosphated distarch phosphate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `polyglycerol polyricinoleate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `potassium alginate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `potassium lactate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept)
- `potato flour` — added: usda:root_vegetable false→true. Ignored disagreement: usda:gluten_source ontology=true dump=false (kept)
- `propylene glycol alginate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `pullulan` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept)
- `shellac` — added: fssai:synthetic false→true. Ignored disagreement: fssai:animal_origin ontology=true dump=false (kept), fssai:insect_derived ontology=true dump=false (kept)
- `sodium alginate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `sodium lactate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:fungal ontology=true dump=false (kept)
- `sorbitan monolaurate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `sorbitol` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `starch sodium octenyl succinate` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `tara gum` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `tartaric acid` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `thaumatin` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `tragacanth` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `turmeric` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)
- `xanthan gum` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept), fssai:fungal ontology=true dump=false (kept)
- `xylitol` — added: fssai:synthetic false→true. Ignored disagreement: fssai:plant_origin ontology=true dump=false (kept)

