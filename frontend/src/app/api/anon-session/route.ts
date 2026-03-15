import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

/** Proxy to backend GET /anon-session. Returns { user_id, token } (token null when backend has no secret). */
export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/anon-session`, { cache: 'no-store' })
    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json(
        { error: 'Backend anon-session failed', detail: res.status === 503 ? 'Server-issued identity not configured' : text },
        { status: res.status }
      )
    }
    const data = (await res.json()) as { user_id: string; token: string | null }
    return NextResponse.json(data)
  } catch (e) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('Anon-session proxy error:', e)
    }
    return NextResponse.json(
      { error: 'Backend unreachable', detail: 'Could not get anonymous session' },
      { status: 503 }
    )
  }
}
