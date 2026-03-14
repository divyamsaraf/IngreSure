import type { UserProfile } from '@/types/userProfile'
import { USER_ID_STORAGE_KEY, PROFILE_STORAGE_KEY, PROFILE_UPDATED_EVENT_NAME } from '@/constants/profileStorage'

/**
 * Get or create a stable user id (stored in localStorage). Safe to call from client only.
 */
export function getOrCreateUserId(): string {
  if (typeof window === 'undefined') return ''
  let id = localStorage.getItem(USER_ID_STORAGE_KEY)
  if (!id) {
    id = crypto.randomUUID?.() ?? `anon-${Date.now()}`
    localStorage.setItem(USER_ID_STORAGE_KEY, id)
  }
  return id
}

/**
 * Persist profile to localStorage and dispatch profile-updated event.
 * The event is for cross-tab profile sync; no in-app listener uses it (Navbar uses ProfileContext).
 */
export function persistProfileToStorage(profile: UserProfile): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile))
  window.dispatchEvent(new CustomEvent(PROFILE_UPDATED_EVENT_NAME))
}
