export type DietType =
  | "No rules"
  | "Jain"
  | "Vegan"
  | "Vegetarian"
  | "Hindu Veg"
  | "Hindu Non Vegetarian"
  | "Halal"
  | "Kosher"
  | "Lacto Vegetarian"
  | "Ovo Vegetarian"
  | "Pescatarian"
  | "Gluten-Free"
  | "Dairy-Free"
  | "Egg-Free"
  | string;

/** Backend profile shape (user_id + dietary_preference + lists). */
export interface BackendProfile {
  user_id: string;
  dietary_preference?: string;
  allergens: string[];
  religious_preferences: string[];
  lifestyle: string[];
  /** Legacy keys (backend may still return these) */
  dietary_restrictions?: string[];
  lifestyle_flags?: string[];
}

export interface UserProfile {
  user_id?: string;
  /** Primary diet for display and backend (new shape). */
  dietary_preference: DietType;
  /** Legacy; maps from dietary_preference for compatibility. */
  diet?: DietType;
  allergies: string[];
  allergens?: string[];
  religious_preferences: string[];
  lifestyle: string[];
  /** Legacy */
  lifestyle_flags?: string[];
  dietary_restrictions?: string[];
  dairy_allowed?: boolean;
  meat_allowed?: boolean;
  is_onboarding_completed: boolean;
}

export const DEFAULT_PROFILE: UserProfile = {
  dietary_preference: "No rules",
  diet: "No rules",
  allergies: [],
  allergens: [],
  religious_preferences: [],
  lifestyle: [],
  lifestyle_flags: [],
  dietary_restrictions: [],
  dairy_allowed: true,
  meat_allowed: true,
  is_onboarding_completed: false,
};

export const DIETARY_PREFERENCE_OPTIONS: { value: string; label: string }[] = [
  { value: "No rules", label: "No rules" },
  { value: "Jain", label: "Jain" },
  { value: "Vegan", label: "Vegan" },
  { value: "Vegetarian", label: "Vegetarian" },
  { value: "Hindu Veg", label: "Hindu Veg" },
  { value: "Hindu Non Vegetarian", label: "Hindu Non Vegetarian" },
  { value: "Halal", label: "Halal" },
  { value: "Kosher", label: "Kosher" },
  { value: "Lacto Vegetarian", label: "Lacto Vegetarian" },
  { value: "Ovo Vegetarian", label: "Ovo Vegetarian" },
  { value: "Pescatarian", label: "Pescatarian" },
  { value: "Gluten-Free", label: "Gluten-Free" },
  { value: "Dairy-Free", label: "Dairy-Free" },
  { value: "Egg-Free", label: "Egg-Free" },
];

export const RELIGIOUS_OPTIONS = ["halal", "kosher", "jain", "hindu vegetarian", "hindu non vegetarian"] as const;

export const LIFESTYLE_OPTIONS = ["no alcohol", "no insect derived", "no palm oil", "no onion", "no garlic"] as const;

export const ALLERGEN_OPTIONS = [
  "Milk",
  "Egg",
  "Nuts",
  "Peanuts",
  "Tree Nuts",
  "Soy",
  "Wheat/Gluten",
  "Fish",
  "Shellfish",
  "Sesame",
  "Mustard",
  "Celery",
  "Other",
] as const;

/** Convert backend profile to UserProfile for UI. */
export function backendToProfile(backend: BackendProfile): UserProfile {
  const dietary =
    backend.dietary_preference ??
    (backend.dietary_restrictions && backend.dietary_restrictions[0]) ??
    "No rules";
  const lifestyle = backend.lifestyle ?? backend.lifestyle_flags ?? [];
  // Map backend lowercase allergens back to display names and deduplicate
  const rawAllergens = backend.allergens ?? [];
  const displayAllergens = [...new Set(rawAllergens.map(allergenToDisplay))];
  return {
    user_id: backend.user_id,
    dietary_preference: dietary,
    diet: dietary,
    allergies: displayAllergens,
    allergens: displayAllergens,
    religious_preferences: backend.religious_preferences ?? [],
    lifestyle,
    lifestyle_flags: lifestyle,
    dietary_restrictions: backend.dietary_restrictions ?? (dietary !== "No rules" ? [dietary] : []),
    is_onboarding_completed: true,
  };
}

function normalizeAllergen(s: string): string {
  return String(s).toLowerCase().replace(/\s*\/.*$/, "").trim();
}

/**
 * Map a backend (lowercase) allergen name back to the canonical display name
 * from ALLERGEN_OPTIONS (e.g. "milk" → "Milk", "wheat" → "Wheat/Gluten").
 * If no match found, return the original string (for custom allergens).
 */
const _BACKEND_TO_DISPLAY: Record<string, string> = {};
// Build reverse map: lowercase/normalized → display name
for (const opt of ALLERGEN_OPTIONS) {
  _BACKEND_TO_DISPLAY[normalizeAllergen(opt)] = opt;
}

function allergenToDisplay(backendName: string): string {
  const key = normalizeAllergen(backendName);
  return _BACKEND_TO_DISPLAY[key] ?? backendName;
}

/** Convert UserProfile to backend payload. Send full profile on save so backend can persist correctly (no accidental reset). */
export function profileToBackend(
  p: UserProfile,
  user_id: string
): Partial<BackendProfile> & { user_id: string } {
  return {
    user_id,
    dietary_preference: p.dietary_preference ?? "No rules",
    allergens: (p.allergens ?? p.allergies ?? []).map(normalizeAllergen),
    religious_preferences: p.religious_preferences ?? [],
    lifestyle: p.lifestyle ?? p.lifestyle_flags ?? [],
  };
}
