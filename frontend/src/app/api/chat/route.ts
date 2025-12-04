import { NextRequest, NextResponse } from 'next/server'
import { extractIntent, generateResponseStream } from '@/lib/llm'
import { checkSafety } from '@/lib/safety_engine'

export async function POST(req: NextRequest) {
    try {
        const { message } = await req.json()

        // 1. Extract Intent (Allergens, Diets, Query)
        const intent = await extractIntent(message)
        console.log('Extracted Intent:', intent)

        // 2. Check Safety / Query DB
        const safetyResult = await checkSafety({
            allergens: intent.allergens,
            diets: intent.diets,
            query: intent.query
        })

        // 3. Generate Response (Stream)
        const stream = await generateResponseStream(message, safetyResult)

        return new NextResponse(stream, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        })
    } catch (error) {
        console.error('Chat API Error:', error)
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
    }
}
