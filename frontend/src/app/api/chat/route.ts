import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
    try {
        const { message, userProfile, user_id } = await req.json()
        const modeParam = req.nextUrl.searchParams.get('mode')
        const mode = (typeof modeParam === 'string' && modeParam.split('?')[0] === 'restaurant') ? 'restaurant' : 'grocery'

        const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
        const endpoint = mode === 'restaurant' ? '/chat/restaurant' : '/chat/grocery'

        let response: Response
        try {
            response = await fetch(`${backendUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: message, userProfile, user_id }),
            })
        } catch (fetchError) {
            console.error('Chat proxy: backend unreachable', fetchError)
            return NextResponse.json(
                { error: 'Backend unreachable', detail: fetchError instanceof Error ? fetchError.message : 'Unknown' },
                { status: 503 }
            )
        }

        if (!response.ok) {
            const body = await response.text()
            console.error('Backend error:', response.status, response.statusText, body)
            try {
                const json = body ? JSON.parse(body) : {}
                return NextResponse.json(
                    { error: 'Backend Error', detail: json.detail ?? body },
                    { status: response.status }
                )
            } catch {
                return NextResponse.json({ error: 'Backend Error', detail: body }, { status: response.status })
            }
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
