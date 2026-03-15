import { NextRequest, NextResponse } from 'next/server'
import type { BackendProfile } from '@/types/userProfile'

/** Profile and user_id are client-held identifiers; auth/authorization must be enforced by the backend. */
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
const MAX_PROFILE_BODY_BYTES = 64 * 1024 // 64KB

/** Default profile shape returned when backend is unreachable or 404/5xx. */
const defaultProfilePayload = (
  user_id: string
): BackendProfile => ({
  user_id,
  dietary_preference: 'No rules',
  allergens: [],
  lifestyle: [],
})

export async function GET(req: NextRequest) {
  const user_id = req.nextUrl.searchParams.get('user_id')
  if (!user_id) {
    return NextResponse.json({ error: 'user_id required' }, { status: 400 })
  }
  const auth = req.headers.get('authorization')
  const headers: Record<string, string> = {}
  if (auth) headers['Authorization'] = auth
  try {
    const res = await fetch(`${BACKEND_URL}/profile/${encodeURIComponent(user_id)}`, { headers })
    if (!res.ok) {
      if (res.status === 404 || res.status >= 500) {
        return NextResponse.json<BackendProfile>(defaultProfilePayload(user_id))
      }
      return NextResponse.json({ error: 'Backend error' }, { status: res.status })
    }
    const data = (await res.json()) as BackendProfile
    return NextResponse.json<BackendProfile>(data)
  } catch (e) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('Profile GET error (backend unreachable?):', e)
    }
    return NextResponse.json<BackendProfile>(defaultProfilePayload(user_id))
  }
}

/** Request body for profile POST (subset of BackendProfile). */
export interface ProfilePostBody {
  user_id: string
  dietary_preference?: string
  allergens?: string[]
  lifestyle?: string[]
}

export async function POST(req: NextRequest) {
  try {
    const raw = await req.text()
    if (raw.length > MAX_PROFILE_BODY_BYTES) {
      return NextResponse.json({ error: 'Payload too large' }, { status: 413 })
    }
    let body: ProfilePostBody
    try {
      body = JSON.parse(raw) as ProfilePostBody
    } catch {
      return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
    }
    const { user_id, dietary_preference, allergens, lifestyle } = body
    if (!user_id) {
      return NextResponse.json({ error: 'user_id required' }, { status: 400 })
    }
    const payload: BackendProfile = {
      user_id,
      allergens: allergens ?? [],
      lifestyle: lifestyle ?? [],
    }
    if (dietary_preference != null) payload.dietary_preference = dietary_preference

    const auth = req.headers.get('authorization')
    const backendHeaders: Record<string, string> = { 'Content-Type': 'application/json' }
    if (auth) backendHeaders['Authorization'] = auth
    const res = await fetch(`${BACKEND_URL}/profile`, {
      method: 'POST',
      headers: backendHeaders,
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const resText = await res.text()
      if (process.env.NODE_ENV !== 'production') {
        console.error('Profile POST backend error:', res.status, resText)
      } else {
        console.error('Profile POST backend error:', res.status)
      }
      const safeDetail = process.env.NODE_ENV === 'production' ? 'Request failed' : (resText || res.statusText)
      return NextResponse.json({ error: 'Backend error', detail: safeDetail }, { status: res.status })
    }
    const data = (await res.json()) as BackendProfile
    return NextResponse.json<BackendProfile>(data)
  } catch (e) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('Profile POST error:', e)
    }
    const safeDetail =
      process.env.NODE_ENV === 'production' ? 'Request failed' : (e instanceof Error ? e.message : 'Unknown error')
    return NextResponse.json({ error: 'Profile save failed', detail: safeDetail }, { status: 500 })
  }
}
