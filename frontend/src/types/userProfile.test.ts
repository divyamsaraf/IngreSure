import { describe, it, expect } from 'vitest'
import { backendToProfile, profileToBackend, DEFAULT_PROFILE, hasProfileRules, type UserProfile } from './userProfile'

describe('backendToProfile and profileToBackend', () => {
  it('converts a backend profile to frontend profile', () => {
    const backend = {
      user_id: 'user-123',
      dietary_preference: 'Vegan',
      allergens: ['Peanuts', 'Milk'],
      lifestyle: ['no alcohol'],
    }

    const profile = backendToProfile(backend)

    expect(profile.user_id).toBe('user-123')
    expect(profile.dietary_preference).toBe('Vegan')
    expect(profile.allergens).toEqual(['Peanuts', 'Milk'])
    expect(profile.lifestyle).toEqual(['no alcohol'])
    expect(profile.is_onboarding_completed).toBe(true)
  })

  it('handles minimal backend profile', () => {
    const backend = {
      user_id: 'legacy-1',
      dietary_preference: 'Vegetarian',
      allergens: ['egg'],
      lifestyle: [],
    }

    const profile = backendToProfile(backend)

    expect(profile.user_id).toBe('legacy-1')
    expect(profile.dietary_preference).toBe('Vegetarian')
    expect(profile.allergens).toEqual(['Eggs'])
    expect(profile.lifestyle).toEqual([])
  })

  it('round-trips profile through backendToProfile and profileToBackend', () => {
    const profile: UserProfile = {
      ...DEFAULT_PROFILE,
      user_id: 'roundtrip-1',
      dietary_preference: 'Vegan',
      allergens: ['Wheat/Gluten'],
      lifestyle: ['no alcohol'],
      is_onboarding_completed: true,
    }

    const backend = profileToBackend(profile, profile.user_id!)
    const roundTripped = backendToProfile(backend)

    expect(roundTripped.user_id).toBe(profile.user_id)
    expect(roundTripped.dietary_preference).toBe(profile.dietary_preference)
    expect(roundTripped.allergens).toEqual(profile.allergens)
    expect(roundTripped.lifestyle).toEqual(profile.lifestyle)
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
