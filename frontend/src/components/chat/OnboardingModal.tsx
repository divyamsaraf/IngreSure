'use client'

import React, { useState } from 'react'
import { X, Check, RotateCcw } from 'lucide-react'
import { UserProfile, DEFAULT_PROFILE } from '@/types/userProfile'
import { useConfig } from '@/context/ConfigContext'

interface OnboardingModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (profile: UserProfile) => void
  initialProfile?: UserProfile
  /** When true, show as "Edit profile" (no skip). */
  editMode?: boolean
}

/** Case-insensitive toggle: removes any casing variant before adding/removing the canonical key. */
function toggleListCI(prev: string[], key: string): string[] {
  const keyLower = key.toLowerCase()
  const filtered = prev.filter((x) => x.toLowerCase() !== keyLower)
  // If length changed, the key was present → remove it
  if (filtered.length < prev.length) return filtered
  // Otherwise add it
  return [...prev, key]
}

/** Case-insensitive includes check. */
function includesCI(arr: string[], key: string): boolean {
  const keyLower = key.toLowerCase()
  return arr.some((x) => x.toLowerCase() === keyLower)
}

function mergeInitialProfile(base: UserProfile | undefined): UserProfile {
  const p = base ?? DEFAULT_PROFILE
  return {
    ...DEFAULT_PROFILE,
    ...p,
    user_id: p.user_id,
    dietary_preference: p.dietary_preference ?? 'No rules',
    allergens: p.allergens ?? [],
    lifestyle: p.lifestyle ?? [],
    is_onboarding_completed: p.is_onboarding_completed ?? false,
  }
}

interface OnboardingModalInnerProps {
  initialProfile?: UserProfile
  onClose: () => void
  onSave: (profile: UserProfile) => void
  editMode: boolean
}

function OnboardingModalInner({
  initialProfile,
  onClose,
  onSave,
  editMode,
}: OnboardingModalInnerProps) {
  const config = useConfig()
  const dietaryOptions = config.profile_options.dietary_preference_options ?? []
  const lifestyleOptions = config.profile_options.lifestyle_options ?? []
  const allergenOptions = config.profile_options.allergen_options ?? []
  const dietIcon: Record<string, string> = config.profile_options.diet_icon ?? {}

  const [profile, setProfile] = useState<UserProfile>(() => mergeInitialProfile(initialProfile))
  const [customAllergy, setCustomAllergy] = useState('')

  const toggleAllergy = (label: string) => {
    setProfile((prev) => ({
      ...prev,
      allergens: toggleListCI(prev.allergens ?? [], label),
    }))
  }

  const handleSave = () => {
    const rawAllergens = profile.allergens ?? []
    const seen = new Set<string>()
    const deduped: string[] = []
    for (const a of rawAllergens) {
      const key = a.toLowerCase()
      if (!seen.has(key)) {
        seen.add(key)
        deduped.push(a)
      }
    }
    const final: UserProfile = {
      ...profile,
      is_onboarding_completed: true,
      dietary_preference: profile.dietary_preference || 'No rules',
      allergens: deduped,
      lifestyle: profile.lifestyle ?? [],
    }
    onSave(final)
    onClose()
  }

  const handleSkip = () => {
    const empty: UserProfile = {
      ...DEFAULT_PROFILE,
      is_onboarding_completed: true,
      dietary_preference: 'No rules',
      allergens: [],
      lifestyle: [],
    }
    onSave(empty)
    onClose()
  }

  const handleReset = () => {
    setProfile({
      ...DEFAULT_PROFILE,
      user_id: profile.user_id,
      is_onboarding_completed: profile.is_onboarding_completed,
      dietary_preference: 'No rules',
      allergens: [],
      lifestyle: [],
    })
    setCustomAllergy('')
  }

  const removeAllergen = (toRemove: string) => {
    setProfile((prev) => ({
      ...prev,
      allergens: (prev.allergens ?? []).filter(
        (a) => a.toLowerCase() !== toRemove.toLowerCase()
      ),
    }))
  }

  return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-card w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header - sticky */}
        <div className="bg-gradient-to-r from-primary to-secondary p-5 text-white shrink-0 sticky top-0">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">
              {editMode ? 'Edit profile' : 'Set your safety profile'}
            </h2>
            <div className="flex items-center gap-2">
              {!editMode && (
                <button
                  onClick={handleSkip}
                  className="text-sm text-white/90 hover:text-white px-2 py-1 rounded"
                >
                  Skip
                </button>
              )}
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/10 rounded-full transition-colors"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          <p className="text-white/90 text-sm mt-1">
            Set your diet and restrictions so we can check ingredients accurately.
          </p>
        </div>

        {/* Single scrollable form */}
        <div className="p-5 overflow-y-auto space-y-6 min-h-0">
          {/* 1. Dietary Preference (primary — choose ONE) */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Dietary Preference</h3>
            <p className="text-xs text-slate-500 mb-2">Choose your main diet.</p>
            <div className="flex flex-wrap gap-2">
              {dietaryOptions.map(({ value, label }) => {
                const selected = (profile.dietary_preference ?? 'No rules') === value
                const icon = dietIcon[value] ?? '🍽️'
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() =>
                      setProfile((p) => ({ ...p, dietary_preference: value as UserProfile['dietary_preference'] }))
                    }
                    className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-full border-2 text-sm transition-all ${
                      selected
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-800 font-medium'
                        : 'border-slate-200 hover:border-emerald-200 text-slate-700'
                    }`}
                  >
                    <span aria-hidden>{icon}</span>
                    {label}
                  </button>
                )
              })}
            </div>
          </section>

          {/* 2. Additional Restrictions (optional) */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Additional Restrictions</h3>
            <p className="text-xs text-slate-500 mb-2">Optional filters on top of your diet.</p>
            <div className="flex flex-wrap gap-2">
              {lifestyleOptions.map(({ value, label }) => {
                const selected = includesCI(profile.lifestyle ?? [], value)
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() =>
                      setProfile((prev) => ({
                        ...prev,
                        lifestyle: toggleListCI(prev.lifestyle ?? [], value),
                      }))
                    }
                    className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-full border-2 text-sm transition-all ${
                      selected
                        ? 'border-blue-600 bg-blue-50 text-blue-700 font-medium'
                        : 'border-slate-200 hover:border-blue-100 text-slate-700'
                    }`}
                  >
                    {selected && <Check className="w-3.5 h-3.5" />}
                    {label}
                  </button>
                )
              })}
            </div>
          </section>

          {/* 3. Allergens */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Allergens</h3>
            <p className="text-xs text-slate-500 mb-2">Select any that apply.</p>
            <div className="flex flex-wrap gap-2">
              {[...allergenOptions].map((alg) => {
                const selected = includesCI(profile.allergens ?? [], alg)
                return (
                  <button
                    key={alg}
                    type="button"
                    onClick={() => toggleAllergy(alg)}
                    className={`px-3 py-2 rounded-lg border-2 text-sm transition-all ${
                      selected
                        ? 'border-red-500 bg-red-50 text-red-700 font-medium'
                        : 'border-slate-100 hover:border-red-100 text-slate-700'
                    }`}
                  >
                    {alg}
                    {selected && (
                      <Check className="w-3.5 h-3.5 inline-block ml-1 -mt-0.5" />
                    )}
                  </button>
                )
              })}
            </div>
            {/* Custom/Other allergens: show as removable chips */}
            {(profile.allergens ?? []).filter(
              (a) => !allergenOptions.some((opt) => opt.toLowerCase() === a.toLowerCase())
            ).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {(profile.allergens ?? []).filter(
                  (a) => !allergenOptions.some((opt) => opt.toLowerCase() === a.toLowerCase())
                ).map((alg) => (
                  <span
                    key={alg}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border-2 border-red-200 bg-red-50 text-red-700 text-sm"
                  >
                    {alg}
                    <button
                      type="button"
                      onClick={() => removeAllergen(alg)}
                      className="p-0.5 rounded hover:bg-red-200 transition-colors"
                      aria-label={`Remove ${alg}`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="mt-2">
              <input
                type="text"
                value={customAllergy}
                onChange={(e) => setCustomAllergy(e.target.value)}
                onBlur={() => {
                  if (customAllergy.trim()) {
                    const newAlgs = customAllergy
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean)
                    setProfile((prev) => {
                      const existing = prev.allergens ?? []
                      const toAdd = newAlgs.filter((a) => !includesCI(existing, a))
                      return { ...prev, allergens: [...existing, ...toAdd] }
                    })
                    setCustomAllergy('')
                  }
                }}
                placeholder="Other (comma-separated)"
                className="w-full p-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
              />
            </div>
          </section>

        </div>

        {/* Footer - sticky */}
        <div className="p-5 border-t border-slate-100 bg-slate-50/50 shrink-0 sticky bottom-0 space-y-2">
          {editMode && (
            <button
              type="button"
              onClick={handleReset}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-[12px] border-2 border-slate-200 text-slate-600 hover:bg-slate-100 hover:border-slate-300 transition-colors text-sm font-medium"
            >
              <RotateCcw className="w-4 h-4" />
              Reset Profile
            </button>
          )}
          <button
            onClick={handleSave}
            className="w-full bg-gradient-to-r from-primary to-secondary text-white py-3 rounded-[12px] font-bold hover:opacity-95 transition-opacity shadow-card"
          >
            {editMode ? 'Save Changes' : 'Save & start chatting'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function OnboardingModal({
  isOpen,
  onClose,
  onSave,
  initialProfile,
  editMode = false,
}: OnboardingModalProps) {
  if (!isOpen) return null
  return (
    <OnboardingModalInner
      key={`onboarding-${initialProfile?.user_id ?? 'new'}`}
      initialProfile={initialProfile}
      onClose={onClose}
      onSave={onSave}
      editMode={editMode}
    />
  )
}
