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
        <div className="flex flex-col h-[600px] border border-slate-200 rounded-3xl bg-white shadow-xl overflow-hidden">
            <div className="bg-slate-900 text-white p-6 flex items-center gap-3">
                <div className="p-2 bg-white/10 rounded-full">
                    <Bot className="w-6 h-6" />
                </div>
                <div>
                    <h2 className="font-bold text-lg">IngreSure Assistant</h2>
                    <p className="text-xs text-slate-400">Powered by Mistral AI</p>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50">
                {messages.length === 0 && (
                    <div className="text-center text-slate-400 mt-20 space-y-4">
                        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Bot className="w-8 h-8 text-slate-400" />
                        </div>
                        <p className="font-medium text-lg text-slate-600">How can I help you today?</p>
                        <div className="flex flex-wrap justify-center gap-2 max-w-xs mx-auto">
                            <button onClick={() => setInput("Is the burger vegan?")} className="text-xs bg-white border px-3 py-1.5 rounded-full hover:bg-slate-50 transition">&quot;Is the burger vegan?&quot;</button>
                            <button onClick={() => setInput("I have a peanut allergy.")} className="text-xs bg-white border px-3 py-1.5 rounded-full hover:bg-slate-50 transition">&quot;I have a peanut allergy.&quot;</button>
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role === 'assistant' && (
                            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 shadow-sm">
                                <Bot className="w-6 h-6 text-blue-600" />
                            </div>
                        )}
                        <div className={`max-w-[80%] p-4 rounded-2xl shadow-sm ${msg.role === 'user'
                            ? 'bg-blue-600 text-white rounded-br-none'
                            : 'bg-white border border-slate-100 text-slate-800 rounded-bl-none'
                            }`}>
                            <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                        </div>
                        {msg.role === 'user' && (
                            <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 shadow-sm">
                                <User className="w-6 h-6 text-slate-600" />
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-slate-100 flex gap-3 items-center">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about ingredients, allergens..."
                    className="flex-1 px-6 py-3 bg-slate-50 border-none rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:bg-white transition-all placeholder:text-slate-400"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-600/20"
                >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                </button>
            </form>
        </div>
    )
}
