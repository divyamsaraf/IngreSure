import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

import { getMaxChatMessageLength } from '@/lib/backendConfig'

const MAX_CHAT_BODY_BYTES = 512 * 1024 // 512KB

export async function POST(req: NextRequest) {
    try {
        const raw = await req.text()
        if (raw.length > MAX_CHAT_BODY_BYTES) {
            return NextResponse.json({ error: 'Payload too large' }, { status: 413 })
        }
        let body: { message?: string; userProfile?: unknown; user_id?: string }
        try {
            body = JSON.parse(raw)
        } catch {
            return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
        }
        const { message, userProfile, user_id } = body
        const messageStr = typeof message === 'string' ? message : ''
        const maxLength = await getMaxChatMessageLength()
        if (messageStr.length > maxLength) {
            return NextResponse.json(
                { error: 'Message too long', detail: `Maximum ${maxLength} characters allowed.` },
                { status: 400 }
            )
        }
        const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
        const endpoint = '/chat/grocery'
        const auth = req.headers.get('authorization')
        const backendHeaders: Record<string, string> = { 'Content-Type': 'application/json' }
        if (auth) backendHeaders['Authorization'] = auth

        let response: Response
        try {
            response = await fetch(`${backendUrl}${endpoint}`, {
                method: 'POST',
                headers: backendHeaders,
                body: JSON.stringify({ query: messageStr, userProfile, user_id }),
            })
        } catch (fetchError) {
            if (process.env.NODE_ENV === 'production') {
                console.error('Chat proxy: backend unreachable')
            } else {
                console.error('Chat proxy: backend unreachable', fetchError)
            }
            const safeDetail =
                process.env.NODE_ENV === 'production' ? 'Service unavailable' : (fetchError instanceof Error ? fetchError.message : 'Unknown')
            return NextResponse.json({ error: 'Backend unreachable', detail: safeDetail }, { status: 503 })
        }

        if (!response.ok) {
            const resText = await response.text()
            if (process.env.NODE_ENV !== 'production') {
                console.error('Backend error:', response.status, response.statusText, resText)
            } else {
                console.error('Backend error:', response.status, response.statusText)
            }
            const safeDetail =
                process.env.NODE_ENV === 'production'
                    ? 'Request failed'
                    : (() => {
                          try {
                              const json = resText ? JSON.parse(resText) : {}
                              return json.detail ?? resText
                          } catch {
                              return resText
                          }
                      })()
            return NextResponse.json(
                { error: 'Backend Error', detail: safeDetail },
                { status: response.status }
            )
        }

        // Stream the response back to the client
        return new NextResponse(response.body, {
            headers: {
                'Content-Type': 'text/plain', // Python backend returns text/plain stream currently
                'Transfer-Encoding': 'chunked'
            }
        })

    } catch (error) {
        console.error('Chat Proxy Error:', error)
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
    }
}
