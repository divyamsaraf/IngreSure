import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'

export async function GET(req: NextRequest) {
  const user_id = req.nextUrl.searchParams.get('user_id')
  if (!user_id) {
    return NextResponse.json({ error: 'user_id required' }, { status: 400 })
  }
  try {
    const res = await fetch(`${BACKEND_URL}/profile/${encodeURIComponent(user_id)}`)
    if (!res.ok) {
      if (res.status === 404) {
        return NextResponse.json({
          user_id,
          dietary_preference: 'No rules',
          allergens: [],
          lifestyle: [],
          religious_preferences: [], // backward compat
        })
      }
      return NextResponse.json({ error: 'Backend error' }, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    console.error('Profile GET error:', e)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { user_id, dietary_preference, allergens, lifestyle } = body
    if (!user_id) {
      return NextResponse.json({ error: 'user_id required' }, { status: 400 })
    }
    const payload: Record<string, unknown> = {
      user_id,
      allergens: allergens ?? [],
      lifestyle: lifestyle ?? [],
    }
    if (dietary_preference != null) payload.dietary_preference = dietary_preference

    const res = await fetch(`${BACKEND_URL}/profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      return NextResponse.json({ error: 'Backend error' }, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    console.error('Profile POST error:', e)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
