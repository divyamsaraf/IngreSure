'use client'

import React, { createContext, useContext } from 'react'
import type { UserProfile } from '@/types/userProfile'
import { useProfile } from '@/hooks/useProfile'

interface ProfileContextValue {
  profile: UserProfile
  setProfile: React.Dispatch<React.SetStateAction<UserProfile>>
  userId: string
  profileLoaded: boolean
  /** True when user has completed onboarding (saved at least once). */
  isProfileComplete: boolean
}

const ProfileContext = createContext<ProfileContextValue | undefined>(undefined)

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  // Use the same /api base that ChatInterface derives for profile calls
  const { profile, setProfile, userId, profileLoaded } = useProfile('/api')
  const isProfileComplete = profile.is_onboarding_completed === true

  return (
    <ProfileContext.Provider value={{ profile, setProfile, userId, profileLoaded, isProfileComplete }}>
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfileContext(): ProfileContextValue {
  const ctx = useContext(ProfileContext)
  if (!ctx) {
    throw new Error('useProfileContext must be used within a ProfileProvider')
  }
  return ctx
}

