'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2 } from 'lucide-react'

interface Message {
    role: 'user' | 'assistant'
    content: string
}

export default function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || loading) return

        const userMsg = input.trim()
        setInput('')
        setMessages(prev => [...prev, { role: 'user', content: userMsg }])
        setLoading(true)

        // Add placeholder for assistant message
        setMessages(prev => [...prev, { role: 'assistant', content: '' }])

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMsg })
            })

            if (!response.ok) throw new Error('Chat failed')

            const reader = response.body?.getReader()
            if (!reader) return

            const decoder = new TextDecoder()
            let assistantMessage = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const chunk = decoder.decode(value, { stream: true })
                // Ollama returns multiple JSON objects like { "response": "word" }
                // We need to parse them. They might be concatenated.
                // e.g. {"response":"H"}{"response":"i"}

                // Simple regex to find "response":"..." patterns might be safer than splitting by }
                // Or split by newline if Ollama sends newlines (it usually does)
                const lines = chunk.split('\n').filter(line => line.trim() !== '')

                for (const line of lines) {
                    try {
                        const json = JSON.parse(line)
                        if (json.response) {
                            assistantMessage += json.response
                            setMessages(prev => {
                                const newMsgs = [...prev]
                                newMsgs[newMsgs.length - 1].content = assistantMessage
                                return newMsgs
                            })
                        }
                    } catch (e) {
                        console.error('Error parsing chunk:', e)
                    }
                }
            }

        } catch (error) {
            console.error('Chat error:', error)
            setMessages(prev => [
                ...prev.slice(0, -1), // Remove empty assistant message
                { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }
            ])
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex flex-col h-[600px] border rounded-xl bg-white shadow-lg overflow-hidden">
            <div className="bg-slate-900 text-white p-4 flex items-center gap-2">
                <Bot className="w-6 h-6" />
                <h2 className="font-semibold">IngreSure Assistant</h2>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                {messages.length === 0 && (
                    <div className="text-center text-gray-400 mt-20">
                        <p>Ask me anything about the menu!</p>
                        <p className="text-sm mt-2">"Is the burger vegan?"</p>
                        <p className="text-sm">"I have a peanut allergy."</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                                <Bot className="w-5 h-5 text-blue-600" />
                            </div>
                        )}
                        <div className={`max-w-[80%] p-3 rounded-lg ${msg.role === 'user'
                                ? 'bg-blue-600 text-white rounded-br-none'
                                : 'bg-white border shadow-sm rounded-bl-none'
                            }`}>
                            <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                        </div>
                        {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                                <User className="w-5 h-5 text-slate-600" />
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="p-4 bg-white border-t flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your question..."
                    className="flex-1 px-4 py-2 border rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="p-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                </button>
            </form>
        </div>
    )
}
