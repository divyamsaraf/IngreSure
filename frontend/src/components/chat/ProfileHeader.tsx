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
  const allergensList = (profile.allergens ?? profile.allergies ?? []) as string[]
  const allergensLabel =
    allergensList.length === 0
      ? 'No allergens set'
      : allergensList.length <= 2
      ? allergensList.join(', ')
      : `${allergensList.slice(0, 2).join(', ')} +${allergensList.length - 2} more`

  // Always show the header so "Edit profile" is always visible
  return (
    <div className="flex items-center justify-between gap-3 border-t border-slate-100 bg-slate-100/80 px-4 py-2.5 text-xs text-slate-700">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 shrink-0">
          <ShieldCheck className="w-3.5 h-3.5" />
        </div>
        {!minimal && (profile.is_onboarding_completed || diet !== 'No rules' || hasAllergens || hasLifestyle) ? (
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <span
              className="inline-flex max-w-[140px] items-center gap-1 rounded-full bg-slate-900/5 px-3 py-1 text-[11px] font-medium text-slate-800"
              title={`Diet: ${diet}`}
            >
              <span className="truncate">{diet}</span>
            </span>
            {hasAllergens && (
              <span
                className="inline-flex max-w-[160px] items-center gap-1 rounded-full bg-rose-50 px-3 py-1 text-[11px] font-medium text-rose-700"
                title={`Allergens: ${allergensList.join(', ')}`}
              >
                Allergens:
                <span className="truncate">{allergensLabel}</span>
              </span>
            )}
            {hasLifestyle && (
              <span
                className="inline-flex max-w-[160px] items-center gap-1 rounded-full bg-slate-200 px-3 py-1 text-[11px] font-medium text-slate-700"
                title={`Lifestyle: ${(profile.lifestyle ?? profile.lifestyle_flags ?? []).join(', ')}`}
              >
                Lifestyle:
                <span className="truncate">
                  {(profile.lifestyle ?? profile.lifestyle_flags ?? []).join(', ')}
                </span>
              </span>
            )}
          </div>
        ) : (
          <span className="text-slate-500 text-xs">No profile set. Set it for personalized checks.</span>
        )}
      </div>

      <button
        type="button"
        onClick={onEdit}
        className="shrink-0 rounded-full border border-blue-100 bg-white px-3 py-1.5 text-[11px] font-medium text-blue-600 transition-colors hover:bg-blue-50"
        aria-label="Edit profile"
      >
        <Edit2 className="w-3 h-3" />
        Edit profile
      </button>
    </div>
  )
}
