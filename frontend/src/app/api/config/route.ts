import { NextResponse } from 'next/server'

/**
 * Proxy to backend GET /config (single source: profile_options + max_chat_message_length).
 */
export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
    const res = await fetch(`${backendUrl}/config`, { cache: 'no-store' })
    if (!res.ok) {
      return NextResponse.json(
        { error: 'Config unavailable' },
        { status: res.status }
      )
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('Config proxy error:', e)
    }
    return NextResponse.json(
      { error: 'Config unavailable' },
      { status: 503 }
    )
  }
}
