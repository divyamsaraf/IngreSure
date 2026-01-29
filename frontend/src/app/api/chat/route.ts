import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
    try {
        const { message, userProfile } = await req.json()
        const mode = req.nextUrl.searchParams.get('mode') // 'grocery' or 'restaurant'

        // Forward to Python Backend
        // Note: Python backend expects {"query": "message"}
        const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
        
        // Determine endpoint
        const endpoint = mode === 'restaurant' ? '/chat/restaurant' : '/chat/grocery';

        const response = await fetch(`${backendUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: message, userProfile }),
        })

        if (!response.ok) {
            console.error('Backend error:', response.status, response.statusText)
            return NextResponse.json({ error: 'Backend Error' }, { status: response.status })
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
