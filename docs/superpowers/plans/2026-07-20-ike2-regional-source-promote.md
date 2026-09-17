# Regional source promote PR1 — Implementation Plan

> **For agentic workers:** Implement task-by-task. Spec: `docs/superpowers/specs/2026-07-20-ike2-regional-source-promote-design.md`

**Goal:** Promote NIN into live ontology, fix regional remap-into-void, gate with CI — without loosening fail-closed.

**Architecture:** Existing L4 promote → `ontology.json`; extend sources + derive flags + resolver bare-key fallback.

## Tasks

- [ ] Extend `flag_derive` for gluten (wheat/atta/maida/suji/semolina) and groundnut→peanut
- [ ] `normalize_ingredient_key(..., apply_regional=)` + resolver bare-key fallback
- [ ] `load_nin_commodities` + regional alias attach in promote; wire into `promote()`
- [ ] variant alias `asafoetida` → `asafetida`
- [ ] CI: NIN 100% + regional key recall in ensure + pytest
- [ ] Run promote, pytest, ensure check
