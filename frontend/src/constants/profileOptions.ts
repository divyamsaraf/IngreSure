/**
 * Profile options: diet, allergens, lifestyle.
 * Single source of truth — keep in sync with data/profile_options.json (backend reads that file).
 */

import data from './profile_options.json'

export interface DietOption {
  value: string
  label: string
}

export interface LifestyleOption {
  value: string
  label: string
}

export const DIETARY_PREFERENCE_OPTIONS: DietOption[] =
  data.dietary_preference_options as DietOption[]

export const ALLERGEN_OPTIONS: readonly string[] =
  data.allergen_options as readonly string[]

export const ADDITIONAL_RESTRICTIONS: LifestyleOption[] =
  data.lifestyle_options as LifestyleOption[]

export const DIET_ICON: Record<string, string> =
  (data.diet_icon as Record<string, string>) ?? {}
