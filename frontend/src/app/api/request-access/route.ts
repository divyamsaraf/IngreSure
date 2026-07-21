import { NextRequest, NextResponse } from 'next/server'

const MAX_BODY_BYTES = 16 * 1024
const USE_CASES = new Set([
  'Grocery / retail app',
  'Food delivery / marketplace',
  'Restaurant / meal kit',
  'Recipe or meal-planning app',
  'Corporate dining / catering',
  'CPG / private label',
  'Other',
])

export interface RequestAccessBody {
  company_name?: string
  use_case?: string
  monthly_volume?: string
  email?: string
  problem_focus?: string
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export async function POST(req: NextRequest) {
  try {
    const raw = await req.text()
    if (raw.length > MAX_BODY_BYTES) {
      return NextResponse.json({ error: 'Payload too large' }, { status: 413 })
    }

    let body: RequestAccessBody
    try {
      body = JSON.parse(raw) as RequestAccessBody
    } catch {
      return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
    }

    const company_name = typeof body.company_name === 'string' ? body.company_name.trim() : ''
    const use_case = typeof body.use_case === 'string' ? body.use_case.trim() : ''
    const monthly_volume = typeof body.monthly_volume === 'string' ? body.monthly_volume.trim() : ''
    const email = typeof body.email === 'string' ? body.email.trim() : ''
    const problem_focus =
      typeof body.problem_focus === 'string' ? body.problem_focus.trim().slice(0, 2000) : ''

    if (!company_name || !use_case || !monthly_volume || !email) {
      return NextResponse.json({ error: 'All fields are required' }, { status: 400 })
    }
    if (!USE_CASES.has(use_case)) {
      return NextResponse.json({ error: 'Invalid use case' }, { status: 400 })
    }
    if (!isValidEmail(email)) {
      return NextResponse.json({ error: 'Invalid email' }, { status: 400 })
    }

    // Early-access intake: log for now; wire to CRM/email when ready.
    console.info('[request-access]', {
      company_name,
      use_case,
      monthly_volume,
      email,
      problem_focus: problem_focus || undefined,
      at: new Date().toISOString(),
    })

    return NextResponse.json({ ok: true })
  } catch (e) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('request-access error:', e)
    }
    return NextResponse.json({ error: 'Server error' }, { status: 500 })
  }
}
