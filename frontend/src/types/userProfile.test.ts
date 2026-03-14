import { describe, it, expect } from 'vitest'
import { backendToProfile, profileToBackend, DEFAULT_PROFILE, hasProfileRules, type UserProfile } from './userProfile'

describe('backendToProfile and profileToBackend', () => {
  it('converts a modern backend profile to frontend profile', () => {
    const backend = {
      user_id: 'user-123',
      dietary_preference: 'Vegan',
      allergens: ['Peanuts', 'Milk'],
      lifestyle: ['Halal'],
      lifestyle_flags: ['Halal'],
      is_onboarding_completed: true,
    }

    const profile = backendToProfile(backend)

    expect(profile.user_id).toBe('user-123')
    expect(profile.dietary_preference).toBe('Vegan')
    expect(profile.allergens).toEqual(['Peanuts', 'Milk'])
    expect(profile.allergies).toEqual(['Peanuts', 'Milk'])
    expect(profile.lifestyle).toEqual(['Halal'])
    expect(profile.lifestyle_flags).toEqual(['Halal'])
    expect(profile.is_onboarding_completed).toBe(true)
  })

  it('handles legacy backend profile fields (diet, allergies, lifestyle_flags)', () => {
    const backendLegacy = {
      user_id: 'legacy-1',
      dietary_preference: 'Vegetarian',
      allergens: ['egg'],
      lifestyle: ['Jain'],
    }

    const profile = backendToProfile(backendLegacy)

    expect(profile.user_id).toBe('legacy-1')
    expect(profile.dietary_preference).toBe('Vegetarian')
    expect(profile.diet).toBe('Vegetarian')
    expect(profile.allergens).toEqual(['Eggs'])
    expect(profile.allergies).toEqual(['Eggs'])
    expect(profile.lifestyle_flags).toEqual(['Jain'])
  })

  it('round-trips profile through backendToProfile and profileToBackend', () => {
    const profile: UserProfile = {
      ...DEFAULT_PROFILE,
      user_id: 'roundtrip-1',
      dietary_preference: 'Vegan',
      diet: 'Vegan',
      allergens: ['Gluten'],
      allergies: ['Gluten'],
      lifestyle: ['Halal'],
      lifestyle_flags: ['Halal'],
      is_onboarding_completed: true,
    }

    const backend = profileToBackend(profile, profile.user_id)
    const roundTripped = backendToProfile(backend)

    expect(roundTripped.user_id).toBe(profile.user_id)
    expect(roundTripped.dietary_preference).toBe(profile.dietary_preference)
    expect(roundTripped.allergens).toEqual(['gluten'])
    expect(roundTripped.lifestyle_flags).toEqual(profile.lifestyle_flags)
    expect(roundTripped.is_onboarding_completed).toBe(true)
  })
})

describe('hasProfileRules', () => {
  it('returns false for default / empty profile', () => {
    expect(hasProfileRules(DEFAULT_PROFILE)).toBe(false)
  })
  it('returns true when dietary_preference is set', () => {
    expect(hasProfileRules({ ...DEFAULT_PROFILE, dietary_preference: 'Vegan' })).toBe(true)
  })
  it('returns true when allergens are set', () => {
    expect(hasProfileRules({ ...DEFAULT_PROFILE, allergens: ['Peanuts'] })).toBe(true)
  })
  it('returns false when only "No rules" diet', () => {
    expect(hasProfileRules({ ...DEFAULT_PROFILE, dietary_preference: 'No rules', is_onboarding_completed: true })).toBe(false)
  })
})

