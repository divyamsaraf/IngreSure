# Japan parser plan (UNVERIFIED — no ingest)

**Status:** plan only. Japan remains **UNVERIFIED**. Do not enable `JP` in onboarding or `emergency.py`. Do not ingest MEXT tables or Open Food Facts Japan. UAE (`AE`) stays in scope.

Source: `docs/g4_japan_readiness.md` (retrieval date 2026-10-22). Confirmed facts below are from CAA PDFs / e-Gov fetched on that date. Everything else stays **UNVERIFIED**.

## Why parser work is required

Current `ingredient_parser.py` is Latin-script. Japanese packs will not atomize:

- List separator is ideographic comma `、` (NFKC does not fold it to `,`). `split_top_level` only splits on `,;`.
- Allergen collective `（一部に○○・○○を含む）` and per-token `（○○を含む）` / `（○○由来）` are unparsed. English/French/German `contains` / `contient` / `enthält` only.
- Full-width `／` in `原材料名` is **ingredients | additives** (CAA examples), not the EU translation-pair slash that `expand_slash_atom` handles. Treating it as a pair would glue the additive block onto the last ingredient.

No Japanese pack corpus exists. Do not add OFF Japan texts.

## Parser changes (later ticket — not this branch)

1. **CJK atoms.** Split on `、` and `，` after NFKC. Keep `（…）` nesting. Do not lowercase-away kanji/kana meaning.
2. **Full-width.** NFKC first (`／` `（）` full-width alphanumerics). After NFKC, treat `、` as a list comma. Do not strip `・` inside a collective allergen line before that parser runs.
3. **Slash.** A single top-level `/` in a Japanese `原材料名` field is ingredients | additives. Do **not** run translation-pair logic on that slash. Nested slashes inside parentheses stay nested.
4. **Allergen line.**
   - Field-end `（一部に(?P<names>.+)を含む）` → specified-item names split on `・`; declared-contains, **not** new recipe atoms.
   - Token-final `（(?P<name>.+)を含む）` and `（(?P<name>.+)由来）` annotate the preceding atom.
   - Do not parse `入っているかもしれない` (CAA forbids possibility wording). Keep existing English `may contain`.
5. **Fail closed.** Unknown CJK atom → UNCERTAIN, never SAFE. Absence of a recommended-20 item is not “free from.” Cashew missing during the 2028-03-31 transition → UNCERTAIN for cashew, not SAFE.
6. **Goldens (later).** Synthetic labels modeled on CAA handbook examples only (濃縮つゆ, 醤油, みりん, ゼラチン, 一括表示). No OFF Japan in git.

## Do not encode from G4 as verdict rules

Dashi/bonito composition, mirin vs 酒類 vs alcohol-lifestyle, shojin, and unnamed `だし` stay **UNVERIFIED**. Soy sauce typically includes wheat (CAA typical case) — missing wheat is a data issue, not a legal exemption.

## Licenses — still no ingest

- **MEXT** Standard Tables: Japanese page vs English royalty note **conflict**. Not in `license_allowlist.json`. Legal review required first.
- **OFF Japan:** ODbL share-alike. Report-only, no alias promotion, no `ike2_*` ingest.

## Later gate still must confirm

CAA hub figure transcription; full e-Gov Annex 14 (卵 / 乳 scrape caveat); shelf cashew transition; live `／` vs `/` vs newline mix; owner decision to add `JP`.
