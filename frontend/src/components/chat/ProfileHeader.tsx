'use client'

import React from 'react'
import { Edit2, ShieldCheck } from 'lucide-react'
import { UserProfile } from '@/types/userProfile'

interface ProfileHeaderProps {
  profile: UserProfile
  onEdit: () => void
  /** When true, show a minimal bar with only "Edit profile" (e.g. before onboarding). */
  minimal?: boolean
}

export default function ProfileHeader({ profile, onEdit, minimal = false }: ProfileHeaderProps) {
  const diet = profile.dietary_preference ?? profile.diet ?? 'No rules'
  const hasAllergens = (profile.allergies?.length ?? profile.allergens?.length ?? 0) > 0
  const hasLifestyle = (profile.lifestyle?.length ?? profile.lifestyle_flags?.length ?? 0) > 0

  // Always show the header so "Edit profile" is always visible
  return (
    <div className="bg-white/80 border-b border-slate-100 px-4 py-2.5 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <div className="bg-green-100 p-1.5 rounded-lg shrink-0">
          <ShieldCheck className="w-4 h-4 text-green-700" />
        </div>
        {!minimal && (profile.is_onboarding_completed || diet !== 'No rules' || hasAllergens || hasLifestyle) ? (
          <div className="text-sm flex flex-wrap items-center gap-x-2 gap-y-1 min-w-0">
            <span className="font-bold text-slate-800 truncate">{diet}</span>
            {hasAllergens && (
              <>
                <span className="text-slate-300">|</span>
                <span className="text-red-600 font-medium">
                  Allergies: {(profile.allergens ?? profile.allergies ?? []).length}
                </span>
              </>
            )}
            {hasLifestyle && (
              <>
                <span className="text-slate-300">|</span>
                <span className="text-slate-600 text-xs">
                  Lifestyle: {(profile.lifestyle ?? profile.lifestyle_flags ?? []).join(', ')}
                </span>
              </>
            )}
          </div>
        ) : (
          <span className="text-slate-500 text-sm">No profile set</span>
        )}
      </div>

      <button
        type="button"
        onClick={onEdit}
        className="shrink-0 text-xs text-blue-600 font-medium hover:bg-blue-50 px-3 py-1.5 rounded-full flex items-center gap-1 transition-colors border border-blue-100"
        aria-label="Edit profile"
      >
        <Edit2 className="w-3 h-3" />
        Edit profile
      </button>
    </div>
  )
}
