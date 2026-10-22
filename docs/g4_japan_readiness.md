# G4 — Japan readiness (report only)

**Gate:** G4 report only. No ingest. No verdict-code changes. Do not merge this branch as a product launch.

**Retrieval date for all fetches in this report:** 2026-10-22.

**Product status:** Japan is **UNVERIFIED** as an IngreSure region. UAE (`AE`) stays in scope unless a later gate drops it.

How to read this file:

- **Confirmed** means the fact was taken from a regulator or national-government page/PDF fetched on 2026-10-22, with the URL below.
- **UNVERIFIED** means IngreSure must not treat the claim as a live labeling or verdict rule until a regulator source with a retrieval date confirms it.
- Tokyo metropolitan pages, municipal summaries, Open Food Facts, MEXT tables, and product-culture traps are supporting context only. They do not make Japan verified.

---

## 1. Scope and current product posture

| Region | Product status | Notes |
|--------|----------------|-------|
| UAE (`AE`) | In scope | Present in `ONBOARDING_ORDER` and `emergency.py` (`998`). This report does not drop UAE. |
| Japan (`JP`) | **UNVERIFIED** | Not in `ONBOARDING_ORDER`. No `JP` entry in `emergency.py`. No Japanese label parser. Do not enable Japan as a region from this report. |

Owner onboarding order in `backend/core/region_profile.py` is India, USA, Canada, UK, AU/NZ, EU-by-language, UAE. Japan is not on that list.

---

## 2. Mandatory and recommended allergen lists

**Regulator:** Consumer Affairs Agency (消費者庁, CAA), plus Food Labeling Standards (食品表示基準) on e-Gov.

### 2.1 What the CAA HTML hub does and does not say

Fetched: [食物アレルギー表示に関する情報](https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/allergy/) (2026-10-22).

The HTML hub states that specified ingredients (特定原材料) are set from periodic national surveys, and that packaged processed foods containing those ingredients must declare them. It shows a figure titled **「特定原材料等の図(令和8年4月時点)」** (figure as of April 2026). The HTML text **does not enumerate** the 9 mandatory or 20 recommended items.

**Confirm before treating the HTML hub as the item list:** open the figure on that page and record the 9 + 20 names from the image itself. Until that image text is transcribed from the live page, the enumerated lists below come from CAA PDFs, not from the hub HTML.

### 2.2 Mandatory — 特定原材料 (9 items) — confirmed from CAA PDFs

Fetched CAA documents (2026-10-22):

- [加工食品の食物アレルギー表示ハンドブック](https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/allergy/assets/food_labeling_cms204_260401_02.pdf) (`food_labeling_cms204_260401_02.pdf`)
- [別添 アレルゲンを含む食品に関する表示](https://www.caa.go.jp/policies/policy/food_labeling/food_labeling_act/assets/food_labeling_cms201_260401_10.pdf) (`food_labeling_cms201_260401_10.pdf`, notice annex)
- [アレルゲンを含む食品に関する表示について](https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/allergy/assets/food_labeling_cms204_260401_03.pdf) (CAA Food Labeling Division, 令和8年4月1日)

CAA handbook and the notice annex list **display-obligated** 特定原材料 as **9 items**:

| JP name | English (descriptive, not an official CAA English list) |
|---------|----------------------------------------------------------|
| えび | shrimp / prawn |
| カシューナッツ | cashew |
| かに | crab |
| くるみ | walnut |
| 小麦 | wheat |
| そば | buckwheat |
| 卵 | egg |
| 乳 | milk |
| 落花生（ピーナッツ） | peanut |

Legal hook: Food Labeling Standards Art. 3 table points at **Annex 14 (別表第十四)** for 特定原材料. Fetched [食品表示基準 on e-Gov](https://laws.e-gov.go.jp/law/427M60000002010/) (2026-10-22). Allergen method in that table: declare that specified ingredients are included, in principle immediately after the ingredient name in parentheses.

**e-Gov Annex 14 caveat (UNVERIFIED as a complete scrape):** the e-Gov HTML annex is collapsed. The retrieved fragment showed えび, カシューナッツ, かに, くるみ, 小麦, そば, 落花生. **卵 and 乳 were not present in that collapsed fragment.** Confirm the live Annex 14 table on e-Gov before citing the Cabinet Order text as independently complete. Until then, the 9-item enumeration is **confirmed from CAA PDFs**, not from a full Annex 14 HTML dump.

Cashew move (confirmed from CAA 令和8年4月1日 notice + e-Gov 附則):

- Cashew was added to 特定原材料 (mandatory) by amendment of the Food Labeling Standards.
- Pistachio was added to 特定原材料に準ずるもの (recommended) by amendment of the CAA notice.
- Transitional measure, e-Gov 附則（令和八年四月一日内閣府令第三四号）第二条: labels of processed foods manufactured, processed, or imported **by 令和10年3月31日 (2028-03-31)** (and business-use processed foods sold by that date) **may follow the previous Annex 14**. So cashew may be absent from some labels until that date.

**UNVERIFIED:** whether any given shelf product has completed the cashew switch. Absence of 「カシューナッツ」 on a 2026–2028 label is not proof of absence.

### 2.3 Recommended — 特定原材料に準ずるもの (20 items) — confirmed from CAA PDFs

These 20 are **not** in the Cabinet Order as obligated items. CAA notice annex (fetched 2026-10-22) says operators should **endeavour** to declare them (可能な限り表示するよう努める).

| JP name | English (descriptive) |
|---------|------------------------|
| アーモンド | almond |
| あわび | abalone |
| いか | squid / cuttlefish |
| いくら | salmon roe |
| オレンジ | orange |
| キウイフルーツ | kiwifruit |
| 牛肉 | beef |
| ごま | sesame |
| さけ | salmon |
| さば | mackerel |
| 大豆 | soybean |
| 鶏肉 | chicken |
| バナナ | banana |
| ピスタチオ | pistachio |
| 豚肉 | pork |
| マカダミアナッツ | macadamia |
| もも | peach |
| やまいも | yam |
| りんご | apple |
| ゼラチン | gelatin |

CAA handbook: if a pack only covers the obligated 9, consumers cannot tell whether a recommended item is unused or used-but-undeclared. Near-label wording such as 「アレルゲン（特定原材料のみ）」 vs 「29品目対象」 is encouraged. **UNVERIFIED for IngreSure:** we have no Japanese pack corpus, so we cannot measure how often the 20 are actually printed.

Possibility wording such as 「入っているかもしれない」 is **not allowed**, including outside the collective box (CAA notice annex, 2026-10-22).

Out of scope of packaged-food allergen rules (CAA handbook): unpackaged retail, restaurant/served food, and **alcoholic beverages (酒類), including alcohol used in food manufacturing**, are not currently subject to the specified-ingredient allergen mandate. That is a labeling-law fact, not a safety fact.

---

## 3. Allergen statement format 「（一部に…を含む）」

Confirmed from CAA handbook and CAA notice annex (both fetched 2026-10-22).

Two allowed methods; **they must not be mixed**.

1. **Individual (原則).** Immediately after each ingredient or additive:
   - ingredients: `（○○を含む）`
   - additives: `（○○由来）` (milk additive exception in the handbook: `乳由来`, not `乳成分由来`)
2. **Collective (例外, 一括表示).** When individual display is impractical, put **all** specified ingredients present (including those already named or covered by allowed alternate wording) at the **end of the ingredients field** as:

   `（一部に○○・○○・…を含む）`

   If ingredients and additives are separate fields, the collective line goes at the **end of each field**.

CAA handbook example (not a live product):

`（一部に大豆・乳成分・小麦・牛肉・卵を含む）`

Joiners: when two or more specified names are listed together, CAA says use **「・」** (`〇〇・〇〇`).

Parser implication (plan only, §9): `（一部に…を含む）` is an **allergen summary**, not a new recipe item. Individual `（○○を含む）` / `（○○由来）` are allergen annotations on the preceding token. Current `ingredient_parser.py` only matches English/French/German `contains` / `contient` / `enthält`. Japanese collective lines are **unparsed today**.

---

## 4. Slash structure of Japanese lists (ingredients vs additives)

Confirmed from CAA consumer pamphlet and CAA additive leaflet (fetched 2026-10-22):

- [知っておきたい食品の表示（令和7年4月版）](https://www.caa.go.jp/policies/policy/food_labeling/information/pamphlets/assets/food_labeling_cms201_250512_01.pdf)
- [食品添加物表示に関するマメ知識](https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/food_additive/assets/food_labeling_cms204_260401_04.pdf)

Food Labeling Standards require ingredients and additives to be **clearly distinguished**, either as two labeled fields (`原材料名` / `添加物`) or inside the ingredients field.

When they share one field, CAA’s worked example uses a **full-width slash `／`**:

```
原材料名 いちご、砂糖／ゲル化剤（ペクチン）、酸化防止剤（ビタミンＣ）
```

Left of `／`: main ingredients, descending weight. Right of `／`: additives, descending weight. A line break is an allowed alternative to the slash.

CAA handbook croquette / noodle / dashi examples use the same `／` split (for example しょうゆ … みりん … ／調味料（アミノ酸等）).

This Japanese `／` is **not** the EU bilingual translation-pair slash (`sugar/sucre`) that `expand_slash_atom` currently handles. Treating `／` as “two names for one ingredient” would merge the entire additive block into the last ingredient. **UNVERIFIED:** how often packs use ASCII `/` vs full-width `／` vs a newline; CAA examples use `／`.

---

## 5. Scripts and full-width normalisation needs

**UNVERIFIED as a measured corpus** (no Japanese OFF ingest; none will be done in G4). Needs below are from CAA examples plus Unicode behaviour of the current normalizer.

Japanese packaged labels mix:

| Script / form | Typical use | Current IngreSure behaviour |
|---------------|-------------|-----------------------------|
| Kanji | 小麦, 醤油, 乳 | NFKC does not split words. Lookup is English-key oriented. **No JP aliases.** |
| Hiragana | えび, そば, りんご | Same. |
| Katakana | カシューナッツ, ゼラチン | Same. |
| Full-width punctuation | `、` `／` `（）` `・` | `normalize_ingredient_key` runs **NFKC then `.lower()`**. NFKC maps `／` → `/`, `（）` → `()`, and full-width digits/letters to ASCII. **It does not map `、` (U+3001) to comma.** |
| Full-width ASCII | `１`, `Ａ` | NFKC folds these. |
| Middle dot `・` | allergen joiner in `（一部に大豆・小麦を含む）` | Would be treated as part of the token or stripped as punctuation (`[,;:\-…]`), not as an allergen-list joiner. |
| Ideographic comma `、` | ingredient separator in CAA examples | `tokenize_ingredients` / clause split uses `,` `;` newline, **not** `、`. Japanese lists will not atomize. |

Current pipeline (`normalizer.py`, `label_normalize.py`, `ingredient_parser.py`) is Latin-script: `Ingredients:`, `may contain`, `and` as a separator, `/` as translation-pair or English section slash. CJK is not a first-class label language.

**UNVERIFIED:** OCR error modes for Japanese (similar-kanji, kana/kanji mix, half-width katakana). Do not invent an OCR table without a labeled corpus.

---

## 6. Product traps (do not encode as verdict rules from this report)

These are readiness traps for a future Japan parser/ontology. Only rows with a CAA citation are labeling facts. The rest stay **UNVERIFIED**.

### 6.1 Dashi / bonito — **UNVERIFIED** as a specified allergen; confirmed as an opaque compound in CAA examples

CAA handbook example **濃縮つゆ**:

`しょうゆ、風味原料（かつおぶし、かつおエキス、さばぶし、にぼし、こんぶ）、…、みりん、…／調味料（アミノ酸等）`

- さば is on the **recommended** 20.
- かつお (bonito / skipjack), にぼし (dried sardine-type fish), and こんぶ (kelp) are **not** on the 9 or 20.
- Token `だし` / `風味原料` does not name the fish. A Safe vegetarian/pescatarian/fish-allergy path from the word “dashi” alone would be a false-SAFE risk.

**UNVERIFIED:** composition of unnamed restaurant dashi; whether kombu-only dashi is distinguishable on pack without inner parentheses. Confirm with CAA range tables (日本標準商品分類 mapping in the handbook) before mapping かつお to `fish` as a specified-item equivalent. It is fish for identity flags; it is **not** a 特定原材料 name.

### 6.2 Soy sauce with wheat — confirmed as CAA’s typical case

CAA handbook, instant-noodle worked example: **「醤油…一般的に大豆、小麦を原料として製造します。」** Individual display example: `醤油（大豆・小麦を含む）`. Soy is recommended; wheat is mandatory.

Trap: English “soy sauce” in IngreSure may already imply soy. For Japan, **wheat is the usual second specified ingredient**. Tamari / wheat-free soy sauce is **UNVERIFIED** as a labeled class here; do not assume 醤油 without `（小麦を含む）` is wheat-free (cashew-style transition logic does not apply; wheat has long been mandatory). Missing wheat on soy sauce is a data/quality issue, not a legal exemption found in this fetch.

### 6.3 Mirin / alcohol — mixed: labeling exemption confirmed; mirin class **UNVERIFIED**

CAA handbook: **酒類 (including alcohol used in food manufacturing)** are **not** under the specified-ingredient allergen mandate, because flushing/palpitations cannot be reliably separated from alcohol effects vs antigen.

CAA examples still print `みりん` as a **normal ingredient** (not behind the additive slash). Handbook additive examples also show `酒精`.

**UNVERIFIED (must confirm before any alcohol-lifestyle rule):**

- Whether hon-mirin is 酒類 vs a processed food for Food Labeling Standards purposes.
- Whether みりん風調味料 (mirin-style seasoning, often lower alcohol) is labeled differently.
- Whether IngreSure’s alcohol restriction should treat みりん like wine, like vinegar, or as UNCERTAIN.

Do not infer “alcohol-free” from the allergen exemption.

### 6.4 Gelatin — confirmed as recommended item; origin split confirmed in CAA range notes

ゼラチン is on the recommended 20. CAA handbook range note: no clear Japan Standard Commodity Classification item; products sold as gelatin are in scope; usually cattle or pig, **sometimes fish**. If gelatin is extracted from pork or beef in process, display `（豚肉を含む）` / `（牛肉を含む）`.

Trap: vegetarian/jellied sweets, gummy, dessert cups, and some たんぱく加水分解物. CAA croquette/kamaboko examples include `たんぱく加水分解物（豚肉・ゼラチンを含む）`. Fish gelatin is not a specified name of its own; fish-allergy overlap is **UNVERIFIED** beyond the handbook’s “sometimes fish” sentence.

### 6.5 Shojin (精進) — **UNVERIFIED**

精進料理 is not a CAA labeling category. It is a Buddhist vegetarian practice. Common false-SAFE: dishes described as shojin still using katsuobushi dashi, hon-mirin, or gelatin-adjacent gelling agents.

**Confirm:** nothing. Do not add a `shojin` diet id from this report. If a user states shojin, treat like a vegetarian profile plus **UNVERIFIED** dashi/fish/gelatin traps until a human-curated synonym list exists.

---

## 7. Emergency numbers

Japan is **not** wired in `backend/core/emergency.py`. This section is citation-only. Do not add `JP` in G4.

| Number | Use | Source fetched 2026-10-22 | Status |
|--------|-----|---------------------------|--------|
| **119** | Fire and ambulance | [消防庁 119番緊急通報](https://www.fdma.go.jp/mission/enrichment/kyukyumusen_kinkyutuhou/119.html) — 119 is the emergency number for fire engines and ambulances. Also [法務省 出入国在留管理庁 “Emergency call” PDF](https://www.moj.go.jp/isa/content/001451207.pdf): dial 119 for medical emergency, injury, or fire. | Confirmed as the medical/fire emergency number. **UNVERIFIED:** a distinct anaphylaxis protocol or English-operator guarantee nationwide (Tokyo-only pages are not national CAA/FDMA rules). |
| **110** | Police (crime, traffic accident) | Same MOJ PDF; [警視庁 multilingual living guide](https://www.keishicho.metro.tokyo.lg.jp/multilingual/english/finding_services/living_guide/living_guide_e_7.html) (Tokyo Metropolitan Police, page dated 2021-04-08). | 110 as police is confirmed on MOJ + Tokyo MP. Tokyo MP is prefectural, not a national police HQ page. **UNVERIFIED** if a later gate wants a National Police Agency citation instead of MOJ + Tokyo MP. |
| **118** | Japan Coast Guard, maritime incidents | [海上保安庁 118](https://www.kaiho.mlit.go.jp/doc/tel118.html) | Confirmed. Not the default medical number for a food-allergy emergency on land. |

UAE remains in the live emergency table: `998`, citation `https://u.ae/en/information-and-services/justice-safety-and-the-law/handling-emergencies/medical-emergencies`, code retrieval date in `emergency.py` is 2026-10-21. This G4 fetch did not re-verify UAE; it also does not drop UAE.

**UNVERIFIED:** `#7119` / other non-emergency medical consult lines. Do not add them without a national-government page.

---

## 8. Source licenses — do not ingest

G4 does **not** ingest MEXT tables or Open Food Facts Japan. License notes are so a later ingest gate cannot skip the check.

### 8.1 MEXT Standard Tables of Food Composition in Japan (日本食品標準成分表)

Fetched 2026-10-22:

- [文部科学省 日本食品標準成分表](https://www.mext.go.jp/a_menu/syokuhinseibun/) — current published set named **日本食品標準成分表（八訂）増補2023年**. Japanese page: component data may be used freely; secondary use in papers, books, and applications should cite 「日本食品標準成分表（八訂）増補2023年から引用（又は出典）」.
- [MEXT Website Usage Policy (Attachment)](https://www.mext.go.jp/en/other/title01/detail01/sdetail01/1375300.htm) — English attachment lists **Standard Tables of Food Composition in Japan** under content that may need **notification and royalty** for commercial print/e-book distribution, and says to confirm with the department in charge.

Those two MEXT pages **conflict** on commercial reuse. **UNVERIFIED:** whether IngreSure (app, not a printed food-composition book) needs notification. **Do not ingest** until legal review records a single license decision with a retrieval date. Also **UNVERIFIED:** SPDX mapping; MEXT is **not** in `license_allowlist.json` `source_licenses`.

### 8.2 Open Food Facts Japan — ODbL

Fetched 2026-10-22: [Open Food Facts Japan 利用規約](https://jp.openfoodfacts.org/terms-of-use).

- Database: **Open Database License (ODbL)**.
- Individual contents: Database Contents License (DbCL).
- Product images: CC-BY-SA, plus third-party packaging rights.

ODbL obligations that block naive ingest into a closed knowledge graph: **attribution**, **share-alike** on adapted databases, keep-open. OFF itself says data is crowd-sourced, **not guaranteed accurate, not for medical use**.

Existing IngreSure practice already treats OFF dumps as **ODbL-tagged, report-only, do not promote aliases** (`region_off_dump_sample.py`, Item 44 product-code files). `license_allowlist.json` lists `ODbL-1.0` as an allowed license class, which is **not** permission to ingest Japan OFF into `ike2_*` from G4.

**Do not ingest OFF Japan in G4.** A later gate must decide share-alike compatibility with IKE-2 before any alias promotion.

---

## 9. Parser plan (plan only — do not implement in G4)

Success criterion for a later parser ticket, not this branch:

1. **CJK atoms.** Split Japanese lists on `、` and `，` (after NFKC), not on kanji/kana character boundaries. Keep `（…）` nesting like the current parenthetical classifier. Do not lowercase-away meaning; NFKC + casefold is fine for Latin islands only.
2. **Full-width normalisation.** NFKC first so `／` `（）` and full-width alphanumerics match ASCII rules. After NFKC, treat `、` as a list comma (NFKC does not fold it). Do not strip `・` inside `（一部に…を含む）` before the allergen-line parser runs.
3. **Slash split.** After NFKC, a **single top-level** `/` in a Japanese `原材料名` field is **ingredients | additives**, matching CAA examples. Do **not** run `expand_slash_atom` translation-pair logic on that slash. Nested slashes inside parentheses stay nested.
4. **Allergen line.**
   - Match `（一部に(?P<names>.+)を含む）` at field end → specified-item names split on `・`, mark as declared-contains (not new recipe atoms).
   - Match token-final `（(?P<name>.+)を含む）` and `（(?P<name>.+)由来）` as annotations on the preceding atom.
   - Do not parse `入っているかもしれない` as a legal may-contain (CAA forbids it). English `may contain` remains the contamination pattern we already have.
5. **Fail closed.** Unknown CJK atom → UNCERTAIN, never SAFE. Recommended-20 absence → do not treat as “free from.” Cashew absence during the 2028-03-31 transition → UNCERTAIN for cashew, not SAFE.
6. **Goldens (later).** Synthetic labels only, modeled on CAA handbook examples (濃縮つゆ, 醤油, みりん, ゼラチン, 一括表示). No OFF Japan texts in git.

This plan is not an implementation ticket and does not change verdict code.

---

## 10. UAE stays in scope

Nothing in this report authorizes dropping UAE. Live facts as of the current `main` this branch was cut from:

- Region code `AE` in `ONBOARDING_ORDER` and `DEFAULTS` (`998`, label languages `ar`/`en`).
- Emergency number `998` with u.ae citation in `emergency.py` (code comment retrieval 2026-10-21).
- Existing OFF regional sampling comments: OFF-UAE is OFF coverage, not UAE shelves.

Japan work, if scheduled after a later gate, is **additive**. It does not replace UAE.

---

## 11. What a later Japan gate must still confirm

| Item | Why it is still open |
|------|----------------------|
| Transcribe CAA hub figure 「特定原材料等の図(令和8年4月時点)」 | Hub HTML did not list items in text. |
| Full e-Gov Annex 14 table including 卵 and 乳 | Collapsed HTML scrape was incomplete. |
| Cashew / pistachio on-pack prevalence during 2028-03-31 transition | Legal transition exists; shelf state is unknown. |
| Japanese `／` vs ASCII `/` vs newline frequency | CAA examples use `／`; live mix is unmeasured. |
| Mirin vs 酒類 vs alcohol-lifestyle mapping | Allergen exemption is confirmed; lifestyle mapping is not. |
| Unnamed だし composition | CAA example expands 風味原料; packs may not. |
| Shojin | Not a regulator category. |
| MEXT commercial-use conflict (Japanese “free with attribution” vs English royalty note) | Blocks ingest. |
| ODbL share-alike vs IKE-2 | Blocks OFF Japan ingest. |
| National Police Agency page for 110, if required beyond MOJ | Tokyo MP is prefectural. |
| Owner decision to add `JP` to onboarding / emergency | Explicitly out of G4. |

---

## 12. Retrieval log (2026-10-22)

| URL | Role |
|-----|------|
| https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/allergy/ | CAA allergen hub |
| https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/allergy/assets/food_labeling_cms204_260401_02.pdf | CAA allergen handbook (9 + 20, 一括表示, traps) |
| https://www.caa.go.jp/policies/policy/food_labeling/food_labeling_act/assets/food_labeling_cms201_260401_10.pdf | CAA notice annex (lists + `（一部に…を含む）`) |
| https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/allergy/assets/food_labeling_cms204_260401_03.pdf | CAA 令和8年4月1日 cashew/pistachio notice |
| https://www.caa.go.jp/policies/policy/food_labeling/information/pamphlets/assets/food_labeling_cms201_250512_01.pdf | CAA consumer pamphlet (`／` split) |
| https://www.caa.go.jp/policies/policy/food_labeling/food_sanitation/food_additive/assets/food_labeling_cms204_260401_04.pdf | CAA additive leaflet (`／` and newline) |
| https://laws.e-gov.go.jp/law/427M60000002010/ | Food Labeling Standards + Annex 14 pointer + cashew 附則 |
| https://www.fdma.go.jp/mission/enrichment/kyukyumusen_kinkyutuhou/119.html | 119 |
| https://www.moj.go.jp/isa/content/001451207.pdf | 119 / 110 |
| https://www.keishicho.metro.tokyo.lg.jp/multilingual/english/finding_services/living_guide/living_guide_e_7.html | 110 / 119 (Tokyo MP) |
| https://www.kaiho.mlit.go.jp/doc/tel118.html | 118 |
| https://www.mext.go.jp/a_menu/syokuhinseibun/ | MEXT tables + Japanese reuse note |
| https://www.mext.go.jp/en/other/title01/detail01/sdetail01/1375300.htm | MEXT English usage attachment (royalty note) |
| https://jp.openfoodfacts.org/terms-of-use | OFF Japan ODbL |

Municipal pages (Kagoshima, Saitama, Iwaki) were seen in search snippets for the cashew transition. They are **not** cited as regulator confirmation; the 2028-03-31 date used above is from **e-Gov 附則**, not from those cities.

---

## 13. G4 outcome

Japan remains **UNVERIFIED**. CAA PDFs confirm the 9/20 lists (with the Annex 14 scrape caveat), the `（一部に…を含む）` collective form, and the `／` ingredient/additive split. Emergency 119/110/118 are cited from national or prefectural government pages and are **not** implemented. MEXT tables and OFF Japan are **not ingested**; OFF is ODbL. Parser work stays a plan. UAE stays in scope.
