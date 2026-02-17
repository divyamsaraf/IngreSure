'use client'

import React, { useState, useEffect } from 'react'
import { X, Check } from 'lucide-react'
import {
  UserProfile,
  DEFAULT_PROFILE,
  DIETARY_PREFERENCE_OPTIONS,
  LIFESTYLE_OPTIONS,
  ALLERGEN_OPTIONS,
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-5 text-white shrink-0">
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
          <p className="text-blue-100 text-sm mt-1">
            Set your diet, allergens & lifestyle — we use this for personalized ingredient checks.
          </p>
        </div>

        {/* Single scrollable form */}
        <div className="p-5 overflow-y-auto space-y-6 min-h-0">
          {/* 1. Dietary preference */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Dietary preference</h3>
            <div className="grid grid-cols-2 gap-2">
              {DIETARY_PREFERENCE_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() =>
                    setProfile((p) => ({ ...p, dietary_preference: value as UserProfile['dietary_preference'], diet: value }))
                  }
                  className={`p-3 rounded-xl border-2 text-left text-sm transition-all ${
                    (profile.dietary_preference ?? profile.diet) === value
                      ? 'border-blue-600 bg-blue-50 text-blue-700 font-medium'
                      : 'border-slate-100 hover:border-blue-200 text-slate-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </section>

          {/* 2. Allergens */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Allergens</h3>
            <p className="text-xs text-slate-500 mb-2">Select any that apply.</p>
            <div className="flex flex-wrap gap-2">
              {ALLERGEN_OPTIONS.map((alg) => {
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

          {/* 3. Lifestyle */}
          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Lifestyle</h3>
            <div className="flex flex-wrap gap-2">
              {LIFESTYLE_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() =>
                    setProfile((prev) => ({
                      ...prev,
                      lifestyle: toggleList(prev.lifestyle ?? prev.lifestyle_flags ?? [], opt),
                      lifestyle_flags: toggleList(prev.lifestyle_flags ?? prev.lifestyle ?? [], opt),
                    }))
                  }
                  className={`px-3 py-2 rounded-lg border-2 text-sm ${
                    (profile.lifestyle ?? profile.lifestyle_flags ?? []).includes(opt)
                      ? 'border-blue-600 bg-blue-50 text-blue-700 font-medium'
                      : 'border-slate-100 hover:border-blue-200 text-slate-700'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-100 bg-slate-50/50 shrink-0">
          <button
            onClick={handleSave}
            className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-600/20"
          >
            {editMode ? 'Save changes' : 'Save & start chatting'}
          </button>
        </div>
      </div>
    </div>
  )
}
