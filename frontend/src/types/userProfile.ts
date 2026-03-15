/** Canonical diet values; use "Hindu Vegetarian" (single source in profile_options). */
export type DietType =
  | "No rules"
  | "Jain"
  | "Vegan"
  | "Vegetarian"
  | "Hindu Vegetarian"
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

/** JSON payload inside <<<PROFILE_UPDATE>>>…<<<PROFILE_UPDATE>>> in chat stream. */
export interface ProfileUpdateStreamPayload {
  user_id?: string
  dietary_preference?: string
  allergens?: string[]
  lifestyle?: string[]
  lifestyle_flags?: string[]
  allergies?: string[]
  [key: string]: unknown
}

/** Backend profile shape (user_id + dietary_preference + allergens + lifestyle). */
export interface BackendProfile {
  user_id: string;
  dietary_preference?: string;
  allergens: string[];
  lifestyle: string[];
}

export interface UserProfile {
  user_id?: string;
  dietary_preference: DietType;
  allergens: string[];
  lifestyle: string[];
  is_onboarding_completed: boolean;
}

export const DEFAULT_PROFILE: UserProfile = {
  dietary_preference: "No rules",
  allergens: [],
  lifestyle: [],
  is_onboarding_completed: false,
};

/** Single source: data/profile_options.json (backend) / frontend src/constants/profile_options.json */
import {
  DIET_ICON,
  DIETARY_PREFERENCE_OPTIONS,
  ADDITIONAL_RESTRICTIONS,
  ALLERGEN_OPTIONS,
} from '@/constants/profileOptions'
export { DIET_ICON, DIETARY_PREFERENCE_OPTIONS, ADDITIONAL_RESTRICTIONS, ALLERGEN_OPTIONS }

/** True when profile has at least one rule (diet other than "No rules", or allergens, or lifestyle). */
export function hasProfileRules(profile: UserProfile): boolean {
  return (
    (profile.dietary_preference != null && profile.dietary_preference !== "No rules") ||
    (profile.allergens?.length ?? 0) > 0 ||
    (profile.lifestyle?.length ?? 0) > 0
  )
}

/** Convert backend profile to UserProfile for UI. */
export function backendToProfile(backend: BackendProfile): UserProfile {
  const dietary = backend.dietary_preference ?? "No rules";
  const lifestyle = backend.lifestyle ?? [];
  const rawAllergens = backend.allergens ?? [];
  const displayAllergens = [...new Set(rawAllergens.map(allergenToDisplay))];
  return {
    user_id: backend.user_id,
    dietary_preference: dietary,
    allergens: displayAllergens,
    lifestyle,
    is_onboarding_completed: true,
  };
}

function normalizeAllergen(s: string): string {
  return String(s).toLowerCase().replace(/\s*\/.*$/, "").trim();
}

/**
 * Map a backend (lowercase) allergen name back to the canonical display name
 * from ALLERGEN_OPTIONS (e.g. "milk" -> "Milk", "wheat" -> "Wheat/Gluten").
 * If no match found, return the original string (for custom allergens).
 */
const _BACKEND_TO_DISPLAY: Record<string, string> = {};
for (const opt of ALLERGEN_OPTIONS) {
  _BACKEND_TO_DISPLAY[normalizeAllergen(opt)] = opt;
}
_BACKEND_TO_DISPLAY["egg"] = "Eggs"; // backend may return "egg"

function allergenToDisplay(backendName: string): string {
  const key = normalizeAllergen(backendName);
  return _BACKEND_TO_DISPLAY[key] ?? backendName;
}

/** Convert UserProfile to backend payload. */
export function profileToBackend(
  p: UserProfile,
  user_id: string
): Partial<BackendProfile> & { user_id: string } {
  return {
    user_id,
    dietary_preference: p.dietary_preference ?? "No rules",
    allergens: (p.allergens ?? []).map(normalizeAllergen),
    lifestyle: p.lifestyle ?? [],
  };
}
