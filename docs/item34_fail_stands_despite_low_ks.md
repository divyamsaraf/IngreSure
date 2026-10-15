# Item 34 — Triggered FAIL must stand despite low knowledge_state

**Status:** Done (fix-today — evaluate root + goldens + §4.4).  
**Created:** 2026-09-18 — surfaced by Item 4.1 decay golden; **not** caused by decay.  
**Companion:** `compliance.py` `_verdict_for` · Item **4.1** §4.4 (corrected) · tracker row **34**

---

## Problem

`_verdict_for` applied `min_knowledge_state` / `_ks_gate_ok` to **FAIL** outcomes: a row with a true hazard flag (e.g. `peanut_source=True`) but `knowledge_state` below the rule minimum was demoted to UNCERTAIN (`unverified_knowledge`).

That inverted the established asymmetry:

| Low trust (DISCOVERED / UNCLASSIFIED) | Intended | Pre-fix bug |
|---------------------------------------|----------|--------------|
| Clean pass → firm **SAFE** | Barred | Barred (correct) |
| Triggered **FAIL** (positive flag) | Must stand | Silenced → UNCERTAIN |

Wrongly silencing Avoid costs more than a false caution: the user loses a still-true hazard warning.

Decay (Item 4.1) only made the bug easier to hit over time (AUTO→DISCOVERED). The same path already affected DISCOVERED rows with zero decay involved.

---

## Exposure (local IKE-2 DB, 2026-09-18)

Scanned `ike2_ingredient_groups` (1738 rows) for boolean RULE_SEED FAIL flags where row KS &lt; strictest seeded min:

| Scope | Distinct groups |
|-------|-----------------|
| All FAIL flag rules | **1** |
| Allergen/medical (`min=AUTO_CLASSIFIED`) | **1** |
| After Tier-1 KS elevation | **1** (unchanged) |

**Example:** `oat` — `gluten_source=True`, `knowledge_state=DISCOVERED` (min for gluten_free/celiac = AUTO_CLASSIFIED). Pre-fix: gluten FAIL → UNCERTAIN.

---

## Fix

In `_verdict_for`: do **not** demote triggered FAIL via `_ks_gate_ok`. Leave the SAFE floor (UNCLASSIFIED→UNCERTAIN, DISCOVERED→WARN) untouched.

---

## Explicit non-goals

- Changing decay TTLs or CLI behavior (Item 4.1).
- Rewriting multi-restriction aggregation (Item 10.1).
- Backfilling `oat` to AUTO_CLASSIFIED (optional hygiene; not required once FAIL stands).
