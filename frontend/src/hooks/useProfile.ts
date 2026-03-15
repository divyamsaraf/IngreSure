'use client'

import { useEffect, useState } from 'react'
import { UserProfile, DEFAULT_PROFILE, backendToProfile } from '@/types/userProfile'
import { PROFILE_STORAGE_KEY } from '@/constants/profileStorage'
import { getOrCreateUserId } from '@/lib/profileStorage'

export function useProfile(profileApiBase: string) {
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE)
  const [userId, setUserId] = useState<string>('')
  const [profileLoaded, setProfileLoaded] = useState(false)

  useEffect(() => {
    const uid = getOrCreateUserId()
    fetch(`${profileApiBase}/profile?user_id=${encodeURIComponent(uid)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setUserId(uid)
        if (
          data &&
          ((data.dietary_preference && data.dietary_preference !== 'No rules') ||
            (data.allergens?.length > 0) ||
            (data.lifestyle?.length > 0))
        ) {
          setProfile(backendToProfile(data))
        } else {
          const saved = typeof window !== 'undefined' ? localStorage.getItem(PROFILE_STORAGE_KEY) : null
          if (saved) {
            try {
              const p = JSON.parse(saved) as Record<string, unknown>
              setProfile({
                ...DEFAULT_PROFILE,
                user_id: uid,
                dietary_preference: (p.dietary_preference ?? p.diet ?? 'No rules') as string,
                allergens: Array.isArray(p.allergens) ? p.allergens : Array.isArray(p.allergies) ? p.allergies : [],
                lifestyle: Array.isArray(p.lifestyle) ? p.lifestyle : Array.isArray(p.lifestyle_flags) ? p.lifestyle_flags : [],
                is_onboarding_completed: Boolean(p.is_onboarding_completed),
              })
            } catch {
              // ignore parse error and fall through to default onboarding behavior
            }
          }
        }
        setProfileLoaded(true)
      })
      .catch((err) => {
        console.error('Profile fetch failed:', err)
        setUserId(getOrCreateUserId())
        setProfileLoaded(true)
        const saved = typeof window !== 'undefined' ? localStorage.getItem(PROFILE_STORAGE_KEY) : null
        if (saved) {
          try {
            const p = JSON.parse(saved) as Record<string, unknown>
            const uid = getOrCreateUserId()
            setProfile({
              ...DEFAULT_PROFILE,
              user_id: uid,
              dietary_preference: (p.dietary_preference ?? p.diet ?? 'No rules') as string,
              allergens: Array.isArray(p.allergens) ? p.allergens : Array.isArray(p.allergies) ? p.allergies : [],
              lifestyle: Array.isArray(p.lifestyle) ? p.lifestyle : Array.isArray(p.lifestyle_flags) ? p.lifestyle_flags : [],
              is_onboarding_completed: Boolean(p.is_onboarding_completed),
            })
          } catch {
            // ignore parse error and leave default profile
          }
        }
      })
  }, [profileApiBase])

  return { profile, setProfile, userId, profileLoaded }
}

