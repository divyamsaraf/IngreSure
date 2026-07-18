/**
 * Site-wide product copy & coverage facts.
 * Import from here so landing, About, For Business, and FAQ stay aligned.
 */
export const CONTACT_EMAIL = 'hello@ingresure.com'

export const BRAND = {
  name: 'IngreSure',
  tagline: 'Eat with confidence. Know what’s inside.',
  oneLiner:
    'Personalized ingredient audits for your diet and allergens — rules decide safety, language explains it.',
} as const

/**
 * Public coverage claims — update once; surfaces pull from here.
 * Counts must match profile_options.json (UI) and restrictions.json / bridge mappings (engine).
 * - Diets: selectable dietary preferences excluding "No rules".
 * - Allergens: named profile chips excluding "Other"; engine rules = allergy category +
 *   dairy_free / egg_free / gluten_free (mapped from Milk, Eggs, Wheat/Gluten).
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
