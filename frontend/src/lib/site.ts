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
  'ingredient checker',
  'allergen checker',
  'vegan ingredient checker',
  'vegetarian food checker',
  'halal ingredient checker',
  'kosher ingredient check',
  'jain food ingredients',
  'food allergy label checker',
  'diet restriction app',
  'grocery list allergen scan',
  'menu allergen checker',
  'food safety for diets',
  'IngreSure',
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
