const OLLAMA_URL = 'http://localhost:11434/api/generate'
const MODEL = 'mistral'

export interface ChatIntent {
    allergens: string[]
    diets: string[]
    query: string
}

export async function extractIntent(userMessage: string): Promise<ChatIntent> {
    const prompt = `
    Extract the following from the user's message:
    1. Allergens (e.g. peanuts, gluten, dairy)
    2. Diet constraints (e.g. vegan, halal, vegetarian)
    3. Search query (the main item they are looking for, or empty if general)

    User Message: "${userMessage}"

    Respond ONLY with a valid JSON object in this format:
    {
        "allergens": ["list", "of", "allergens"],
        "diets": ["list", "of", "diets"],
        "query": "search term"
    }
    `

    try {
        const response = await fetch(OLLAMA_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: MODEL,
                prompt: prompt,
                stream: false,
                format: "json"
            })
        })

        if (!response.ok) throw new Error('Ollama extraction failed')

        const data = await response.json()
        return JSON.parse(data.response)
    } catch (e) {
        console.error('Intent extraction failed:', e)
        // Fallback: return empty intent
        return { allergens: [], diets: [], query: userMessage }
    }
}

export async function generateResponseStream(userMessage: string, context: unknown) {
    const prompt = `
    You are a helpful restaurant assistant. 
    User Query: "${userMessage}"
    
    Context (Database Facts):
    ${JSON.stringify(context, null, 2)}

    Instructions:
    - Answer the user's question based ONLY on the provided Context.
    - If safe items are found, list them with their prices.
    - If no items match, explain why (e.g. "I couldn't find any vegan burgers").
    - Do NOT hallucinate items not in the context.
    - Be concise and friendly.
    `

    const response = await fetch(OLLAMA_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: MODEL,
            prompt: prompt,
            stream: true
        })
    })

    return response.body
}
