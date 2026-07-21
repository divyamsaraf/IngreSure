/**
 * Site-wide product copy, contact, and SEO constants.
 * Import from here so landing, About, For Business, FAQ, and metadata stay aligned.
 */

export const CONTACT_EMAIL = 'divyam.saraf@gmail.com'

/** Canonical production origin — override with NEXT_PUBLIC_SITE_URL in deploy. */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ||
  process.env.NEXT_PUBLIC_APP_URL ||
  'https://ingresure.com'
).replace(/\/$/, '')

export const BRAND = {
  name: 'IngreSure',
  tagline: 'Eat with confidence. Know what’s inside.',
  oneLiner:
    'Personalized ingredient audits for your diet and allergens — rules decide safety, language explains it.',
  seoTitleDefault: 'IngreSure — Ingredient & allergen safety checks',
  seoDescriptionDefault:
    'Check grocery lists, menus, and labels against your diet and allergens. Clear Safe / Avoid / Depends answers from rules — not AI guesswork. No signup required.',
} as const

export const SEO_KEYWORDS = [
  // Brand
  'IngreSure',
  'ingresure',
  'IngreSure app',
  'IngreSure ingredient checker',

  // Core product
  'ingredient checker',
  'ingredient scanner',
  'ingredient analyzer',
  'ingredient list checker',
  'food ingredient checker',
  'check food ingredients',
  'paste ingredients check diet',
  'label ingredient checker',
  'product label checker',
  'food label scanner diet',
  'grocery list ingredient check',
  'grocery assistant diet',
  'menu ingredient checker',
  'recipe ingredient checker',
  'food safety checker',
  'dietary restriction checker',
  'diet food checker',
  'personalized food safety',
  'Safe Avoid Depends food',
  'food verdict Safe Avoid Depends',

  // Allergens
  'allergen checker',
  'allergen scanner',
  'food allergy checker',
  'food allergy label checker',
  'allergen label checker',
  'check food for allergens',
  'peanut allergy ingredient checker',
  'tree nut allergy food check',
  'milk allergy ingredient check',
  'egg allergy food checker',
  'soy allergy ingredient checker',
  'wheat allergy food check',
  'gluten allergy ingredient checker',
  'sesame allergy food checker',
  'fish allergy ingredient check',
  'shellfish allergy food checker',
  'undeclared allergen check',
  'cross contamination allergen info',

  // Vegan / vegetarian
  'vegan ingredient checker',
  'vegan food checker',
  'is it vegan checker',
  'vegan label scanner',
  'vegan grocery list check',
  'vegetarian ingredient checker',
  'vegetarian food checker',
  'is gelatin vegan',
  'is E471 vegan',
  'animal derived additives checker',
  'pescatarian food checker',
  'plant based ingredient check',

  // Religious / cultural diets
  'halal ingredient checker',
  'halal food checker',
  'is it halal ingredients',
  'halal additives list check',
  'kosher ingredient checker',
  'kosher food checker',
  'is it kosher ingredients',
  'jain food ingredients',
  'jain diet ingredient checker',
  'jain grocery list checker',
  'hindu vegetarian ingredient checker',
  'hindu non vegetarian food check',
  'religious diet food checker',

  // Use cases
  'grocery list allergen scan',
  'check grocery list for diet',
  'menu allergen checker',
  'restaurant menu diet check',
  'delivery order allergen check',
  'meal kit ingredient checker',
  'recipe diet compatibility check',
  'OCR food label diet check',
  'E-number diet checker',
  'food additive diet check',

  // B2B / business
  'allergen compliance software',
  'dietary restriction API',
  'food allergy compliance tool',
  'restaurant allergen management',
  'menu allergen compliance',
  'grocery app diet filter',
  'food delivery allergen check API',
  'CPG allergen labeling check',
  'food platform diet safety',
  'allergen risk reduction software',

  // Intent / problem
  'avoid food allergy mistake',
  'diet mistake grocery shopping',
  'wrong ingredient allergy risk',
  'food mislabeling risk',
  'know what is in your food',
  'eat with confidence app',
] as const

/** Extra keywords for the chat / grocery assistant surface. */
export const SEO_KEYWORDS_CHAT = [
  ...SEO_KEYWORDS,
  'free ingredient checker no signup',
  'check ingredients online free',
  'paste label check vegan',
  'paste menu check allergens',
  'online grocery diet assistant',
] as const

/** Extra keywords for the partner / business surface. */
export const SEO_KEYWORDS_BUSINESS = [
  ...SEO_KEYWORDS,
  'B2B food allergen software',
  'partner API food safety',
  'checkout allergen warning',
  'reduce allergen lawsuit risk restaurants',
  'food recall allergen labeling',
  'dietary compliance for platforms',
] as const

/**
 * Public coverage claims — update once; surfaces pull from here.
 * Counts must match profile_options.json (UI) and restrictions.json / bridge mappings (engine).
 */
export const COVERAGE = {
  allergenProfileNamedCount: 11,
  allergenEngineRuleCount: 15,
  allergenCountLabel: '15 allergen rules',
  allergenDetail: 'Tracked in the resolution engine',
  dietFrameworks: [
    'Vegan',
    'Vegetarian',
    'Pescatarian',
    'Jain',
    'Halal',
    'Kosher',
    'Hindu Vegetarian',
    'Hindu Non Vegetarian',
  ] as const,
  dietCountLabel: '8 diet frameworks',
  rulesPromise: 'Rules, not LLM',
  rulesDetail: 'Safety call comes from explicit logic',
  privacyPromise: 'No signup',
  privacyDetail: 'Profile stays on your device',
} as const

/** FAQ / long-form copy derived from COVERAGE so pages stay aligned. */
export const COVERAGE_DIETS_AND_ALLERGENS_SUMMARY = [
  `Currently eight diet profiles: ${COVERAGE.dietFrameworks.join(', ')}.`,
  `Your safety profile includes ${COVERAGE.allergenProfileNamedCount} named allergens (plus custom Other);`,
  `the resolution engine tracks ${COVERAGE.allergenEngineRuleCount} allergen-related rules.`,
  'We are actively expanding this list.',
].join(' ')

export const TRUST_SIGNALS = [
  { label: COVERAGE.allergenCountLabel, detail: COVERAGE.allergenDetail },
  {
    label: COVERAGE.dietCountLabel,
    detail: 'Religious & lifestyle diets supported',
  },
  { label: COVERAGE.rulesPromise, detail: COVERAGE.rulesDetail },
  { label: COVERAGE.privacyPromise, detail: COVERAGE.privacyDetail },
] as const

/** Absolute URL helper for sitemap / canonical / OG. */
export function absoluteUrl(path = '/'): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${SITE_URL}${p === '/' ? '' : p}`
}
