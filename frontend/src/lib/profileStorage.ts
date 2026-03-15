import type { UserProfile } from '@/types/userProfile'
import { USER_ID_STORAGE_KEY, ANON_SESSION_TOKEN_KEY, PROFILE_STORAGE_KEY, PROFILE_UPDATED_EVENT_NAME } from '@/constants/profileStorage'

/**
 * Ensure we have a session: if no user_id in storage, fetch GET /api/anon-session and store user_id + token.
 * Call once before using getOrCreateUserId() so new users get server-issued identity when available.
 */
export async function ensureAnonSession(): Promise<void> {
  if (typeof window === 'undefined') return
  if (localStorage.getItem(USER_ID_STORAGE_KEY)) return
  try {
    const res = await fetch('/api/anon-session', { cache: 'no-store' })
    if (!res.ok) return
    const data = (await res.json()) as { user_id?: string; token?: string | null }
    if (data.user_id) {
      localStorage.setItem(USER_ID_STORAGE_KEY, data.user_id)
      if (data.token) {
        localStorage.setItem(ANON_SESSION_TOKEN_KEY, data.token)
      }
    }
  } catch {
    // fall back to getOrCreateUserId() creating a client UUID
  }
}

/** Return the stored anon-session token, if any (for Authorization: Bearer). */
export function getAnonSessionToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(ANON_SESSION_TOKEN_KEY)
}

/**
 * Get or create a stable user id (stored in localStorage). Safe to call from client only.
 * Call ensureAnonSession() first so new users get server-issued identity when available.
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
