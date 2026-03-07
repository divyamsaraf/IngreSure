'use client'

import React, { useState, useEffect } from 'react'
import { X, Check, RotateCcw } from 'lucide-react'
import {
  UserProfile,
  DEFAULT_PROFILE,
  DIETARY_PREFERENCE_OPTIONS,
  ADDITIONAL_RESTRICTIONS,
  ALLERGEN_OPTIONS,
  DIET_ICON,
} from '@/types/userProfile'

interface OnboardingModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (profile: UserProfile) => void
  initialProfile?: UserProfile
  /** When true, show as "Edit profile" (no skip). */
  editMode?: boolean
}

function toggleList(prev: string[], key: string): string[] {
  if (prev.includes(key)) return prev.filter((x) => x !== key)
  return [...prev, key]
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

export default function OnboardingModal({
  isOpen,
  onClose,
  onSave,
  initialProfile,
  editMode = false,
}: OnboardingModalProps) {
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE)
  const [customAllergy, setCustomAllergy] = useState('')

  useEffect(() => {
    if (isOpen) {
      const base = initialProfile ?? DEFAULT_PROFILE
      setProfile({
        ...DEFAULT_PROFILE,
        ...base,
        user_id: base.user_id,
        dietary_preference: base.dietary_preference ?? base.diet ?? 'No rules',
        diet: base.diet ?? base.dietary_preference ?? 'No rules',
        allergies: base.allergies ?? base.allergens ?? [],
        allergens: base.allergens ?? base.allergies ?? [],
        lifestyle: base.lifestyle ?? base.lifestyle_flags ?? [],
        lifestyle_flags: base.lifestyle_flags ?? base.lifestyle ?? [],
        is_onboarding_completed: base.is_onboarding_completed ?? false,
      })
      setCustomAllergy('')
    }
  }, [isOpen, initialProfile])

  if (!isOpen) return null

  const toggleAllergy = (label: string) => {
    setProfile((prev) => ({
      ...prev,
      allergies: toggleListCI(prev.allergies ?? [], label),
      allergens: toggleListCI(prev.allergens ?? prev.allergies ?? [], label),
    }))
  }

  const handleSave = () => {
    // Deduplicate allergens (case-insensitive): keep the first occurrence of each
    const rawAllergens = profile.allergens ?? profile.allergies ?? []
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
      diet: profile.dietary_preference || profile.diet || 'No rules',
      allergens: deduped,
      allergies: deduped,
      lifestyle: profile.lifestyle ?? profile.lifestyle_flags ?? [],
      lifestyle_flags: profile.lifestyle ?? profile.lifestyle_flags ?? [],
    }
    onSave(final)
    onClose()
  }

  const handleSkip = () => {
    const empty: UserProfile = {
      ...DEFAULT_PROFILE,
      is_onboarding_completed: true,
      dietary_preference: 'No rules',
      allergies: [],
      allergens: [],
      lifestyle: [],
      lifestyle_flags: [],
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
      diet: 'No rules',
      allergies: [],
      allergens: [],
      lifestyle: [],
      lifestyle_flags: [],
    })
    setCustomAllergy('')
  }

  const removeAllergen = (toRemove: string) => {
    setProfile((prev) => {
      const next = (prev.allergens ?? prev.allergies ?? []).filter(
        (a) => a.toLowerCase() !== toRemove.toLowerCase()
      )
      return { ...prev, allergies: next, allergens: next }
    })
  }

  return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.08)] w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header - sticky */}
        <div className="bg-gradient-to-r from-[#0F172A] to-[#10B981] p-5 text-white shrink-0 sticky top-0">
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
              {DIETARY_PREFERENCE_OPTIONS.map(({ value, label }) => {
                const selected = (profile.dietary_preference ?? profile.diet ?? 'No rules') === value
                const icon = DIET_ICON[value] ?? '🍽️'
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() =>
                      setProfile((p) => ({ ...p, dietary_preference: value as UserProfile['dietary_preference'], diet: value }))
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
              {ADDITIONAL_RESTRICTIONS.map(({ value, label }) => {
                const selected = includesCI(profile.lifestyle ?? profile.lifestyle_flags ?? [], value)
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() =>
                      setProfile((prev) => ({
                        ...prev,
                        lifestyle: toggleListCI(prev.lifestyle ?? prev.lifestyle_flags ?? [], value),
                        lifestyle_flags: toggleListCI(prev.lifestyle_flags ?? prev.lifestyle ?? [], value),
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
              {[...ALLERGEN_OPTIONS].map((alg) => {
                const selected = includesCI(profile.allergies ?? profile.allergens ?? [], alg)
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
            {(profile.allergens ?? profile.allergies ?? []).filter(
              (a) => !ALLERGEN_OPTIONS.some((opt) => opt.toLowerCase() === a.toLowerCase())
            ).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {(profile.allergens ?? profile.allergies ?? []).filter(
                  (a) => !ALLERGEN_OPTIONS.some((opt) => opt.toLowerCase() === a.toLowerCase())
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
                      const existing = prev.allergies ?? []
                      // Only add items not already present (case-insensitive)
                      const toAdd = newAlgs.filter((a) => !includesCI(existing, a))
                      const merged = [...existing, ...toAdd]
                      return { ...prev, allergies: merged, allergens: merged }
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
            className="w-full bg-gradient-to-r from-[#0F172A] to-[#10B981] text-white py-3 rounded-[12px] font-bold hover:opacity-95 transition-opacity shadow-[0_2px_8px_rgba(0,0,0,0.08)]"
          >
            {editMode ? 'Save Changes' : 'Save & start chatting'}
          </button>
        </div>
      </div>
    </div>
  )
}
