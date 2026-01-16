'use client'

import React from 'react'
import { Edit2, ShieldCheck } from 'lucide-react'
import { UserProfile } from '@/types/userProfile'

interface ProfileHeaderProps {
    profile: UserProfile
    onEdit: () => void
}

export default function ProfileHeader({ profile, onEdit }: ProfileHeaderProps) {
    if (!profile || !profile.is_onboarding_completed) return null;

    return (
        <div className="bg-white border-b border-slate-100 px-4 py-3 flex items-center justify-between shadow-sm sticky top-0 z-10">
            <div className="flex items-center gap-3">
                <div className="bg-green-100 p-1.5 rounded-lg">
                    <ShieldCheck className="w-4 h-4 text-green-700" />
                </div>
                <div className="text-sm">
                    <span className="font-bold text-slate-800">{profile.diet}</span>
                    <span className="mx-2 text-slate-300">|</span>
                    <span className={profile.dairy_allowed ? "text-green-600" : "text-amber-600"}>
                        {profile.dairy_allowed ? "Dairy OK" : "No Dairy"}
                    </span>
                    {profile.allergies && profile.allergies.length > 0 && (
                        <>
                            <span className="mx-2 text-slate-300">|</span>
                            <span className="text-red-600 font-medium">Allergies: {profile.allergies.length}</span>
                        </>
                    )}
                </div>
            </div>

            <button
                onClick={onEdit}
                className="text-xs text-blue-600 font-medium hover:bg-blue-50 px-3 py-1.5 rounded-full flex items-center gap-1 transition-colors"
            >
                Edit <Edit2 className="w-3 h-3" />
            </button>
        </div>
    )
}
