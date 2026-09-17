# IKE-2 regional source promote (US / India / EU) — design

**Status:** Approved 2026-07-20  
**Aligns with:** IKE-2 design (fail-closed), §9.3–9.3.1 synonymy + L4 offline promote, M12 offline gap, `ensure_commodity_coverage` gates.

## Problem

Layer1 dumps (NIN, IFCT, FSSAI, FoodEx2, USDA, …) exist on disk but chat Tier-2 only reads `data/ontology.json`. Promote historically ingested USDA commodity heads + grocery seeds only. India NIN (82) and regional remaps were stranded. Regional normalize often remapped into English keys absent from L2 (e.g. `bajra` → `pearl millet` → Depends).

## Non-goals

- Blind merge of all layer1 (~34k) into chat (false Safe / noise).
- Runtime fuzzy / LLM resolve.
- Changing the L1→L2→L3→L5 ladder or fail-closed semantics.
- Wiring `learned_regional_mappings.json` into chat normalize.

## Principles (quality over raw coverage)

1. Firm Safe/Avoid only for trusted Tier-1/2 rows with usable identity flags.
2. Unknown / under-flagged → Depends (never invent Safe).
3. Coverage grows via **L4 offline promote**, same architecture as §9.3.1.
4. Different sources have different **right places** (foods → ontology; E-numbers → truth anchor; chemistry → not grocery KB).

## Data completeness reality

| Source | Identity/diet flags | Chat policy |
|--------|---------------------|-------------|
| NIN (82) | Strong origin/dairy/soy; some allergen gaps (e.g. gluten on atta) | Promote all; run `derive_identity_flags`; strip provenance `uncertainty_flags` |
| IFCT / FoodEx2 foods | Partial / inferred | Later PR: strict commodity-head filter only |
| FSSAI | Mostly additives, empty diet flags | Not grocery Safe; additive/WARN path later |
| USDA | Via existing commodity-head promote | Keep |
| E-numbers | Tier-1 | Keep |
| ChEBI / most GRAS / PubChem | Chemistry | Not grocery Tier-2 |

Missing flags after derive → Prefer Depends over false Safe.

### Compound / prepared dishes (quality rule)

Do **not** invent firm `dairy_source` / `animal_origin` for multi-ingredient dishes (e.g. affogato = espresso + gelato; vegan versions exist). Put them on Tier-1 as `verdict_cap=WARN` compounds (never firm Safe; never invented Avoid). Grocery seed lists must skip `_COMPOUND_NEVER_FIRM_SEED`.

## Design

### PR1+PR2 (delivered)

1. NIN + regional remap invariant + CI  
2. Compound dishes (`affogato`, souffle, ice cream sandwich, …) → Tier-1 `verdict_cap=WARN` — **never invent dairy/egg**  
3. Strict IFCT + FoodEx2 short-food promote (origin required; additives/dishes excluded) + CI recall 100% on promotable set  
4. USDA commodity-head promote retained  

### Still not “every dump row”

FSSAI additives, ChEBI/chemistry, FoodEx2 rows without origin flags, long multi-ingredient IFCT names — stay offline or Depends. That preserves quality.

## Success criteria

- NIN 82/82 trusted resolve; bajra/poha/hing/makhana/jaggery class works  
- No regional remap to a missing L2 key for static mappings  
- Untrusted never firm Safe (existing invariant tests still pass)  
- No hand-adding forever — new India foods enter via NIN/transform → promote → CI

## Out of scope for PR1

IFCT/FoodEx2/FSSAI bulk promote; Supabase bulk_inject as primary KB; learned regional in chat.
