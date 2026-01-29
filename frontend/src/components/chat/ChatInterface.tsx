'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2 } from 'lucide-react'
import OnboardingModal from './OnboardingModal'
import ProfileHeader from './ProfileHeader'
import { UserProfile, DEFAULT_PROFILE } from '@/types/userProfile'

interface Message {
    role: 'user' | 'assistant'
    content: string
}

interface ChatInterfaceProps {
    apiEndpoint?: string
    title?: string
    subtitle?: string
    suggestions?: string[]
}

export default function ChatInterface({
    apiEndpoint = '/api/chat',
    title = 'IngreSure Assistant',
    subtitle = 'Powered by SafetyAnalyst',
    suggestions = [
        "Is the burger vegan?",
        "I have a peanut allergy."
    ]
}: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE)
    const [showOnboarding, setShowOnboarding] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Load profile from local storage on mount
    useEffect(() => {
        const saved = localStorage.getItem('ingresure_profile')
        if (saved) {
            setProfile(JSON.parse(saved))
        } else {
            // First time user -> Show modal
            setShowOnboarding(true)
        }
    }, [])

    const saveProfile = (newProfile: UserProfile) => {
        setProfile(newProfile)
        localStorage.setItem('ingresure_profile', JSON.stringify(newProfile))

        // Unified Sync: Notify Backend immediately
        fetch(apiEndpoint.replace('/chat', '') + '/update-profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile: newProfile })
        }).catch(err => console.error("Background Sync Failed:", err))

        // Add a system update message
        setMessages(prev => [...prev, {
            role: 'assistant',
            content: `✅ Profile Updated: **${newProfile.diet}** (${newProfile.dairy_allowed ? 'Dairy Allowed' : 'No Dairy'}). I'll keep this in mind!`
        }])
    }

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

        setMessages(prev => [...prev, { role: 'assistant', content: '' }])

        try {
            // Include profile in context if available
            // Note: We need to append it to the message or send as separate context field
            // Here we basically append it as a system instruction prefix if API accepts raw string
            // Or ideally, the backend parses this.
            // For now, let's append it to the body as 'context'

            const payload = {
                message: userMsg,
                // Pass profile context to backend so it knows current state without NLP parsing every time
                userProfile: profile
            }

            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })

            if (!response.ok) throw new Error('Chat failed')

            const reader = response.body?.getReader()
            if (!reader) return

            const decoder = new TextDecoder()
            let assistantMessage = ''
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const chunk = decoder.decode(value, { stream: true })
                buffer += chunk

                // Check for profile update protocol
                // Format: <<<PROFILE_UPDATE>>>{...json...}<<<PROFILE_UPDATE>>>
                const tag = "<<<PROFILE_UPDATE>>>"
                if (buffer.includes(tag)) {
                    const parts = buffer.split(tag)
                    // Pattern: [Text, JSON, RemainingText] assuming clean wrap
                    // It can be: "Text... <<<PROFILE_UPDATE>>> JSON <<<PROFILE_UPDATE>>>"

                    if (parts.length >= 3) {
                        const jsonStr = parts[1]
                        try {
                            const updatedProfile = JSON.parse(jsonStr)
                            if (!updatedProfile.allergies) updatedProfile.allergies = []
                            console.log("Syncing Profile from Backend:", updatedProfile)

                            // Update Local State & Storage
                            setProfile(updatedProfile)
                            localStorage.setItem('ingresure_profile', JSON.stringify(updatedProfile))

                            // Remove the protocol from valid text
                            // Reconstruct text without the JSON block
                            // Ideally, the JSON block is at the end, so we take parts[0]
                            // But if there is text after (unlikely based on backend), we append it?
                            // Backend sends it at the very end.

                            buffer = parts[0] + (parts[2] || "") // Remove parts[1] (json) and delimiters
                        } catch (e) {
                            console.error("Failed to parse backend profile update", e)
                        }
                    }
                }

                // Update UI with the CLEAN buffer (text only)
                setMessages(prev => {
                    const newMsgs = [...prev]
                    newMsgs[newMsgs.length - 1].content = buffer.replace(/<<<PROFILE_UPDATE>>>.*?<<<PROFILE_UPDATE>>>/g, '')
                    return newMsgs
                })
            }

        } catch (error) {
            console.error('Chat error:', error)
            setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }
            ])
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex flex-col h-[85vh] max-h-[900px] border border-slate-100 rounded-2xl bg-white shadow-xl overflow-hidden backdrop-blur-sm relative">

            {/* Onboarding Modal */}
            <OnboardingModal
                isOpen={showOnboarding}
                onClose={() => setShowOnboarding(false)}
                onSave={saveProfile}
                initialProfile={profile}
            />

            {/* Header Area */}
            <div className="bg-slate-50/50 backdrop-blur border-b border-slate-100">
                {/* Main Title Bar */}
                <div className="p-4 flex items-center gap-3">
                    <div className="p-2 bg-blue-100/50 rounded-xl">
                        <Bot className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                        <h2 className="font-bold text-gray-800 text-lg">{title}</h2>
                        <p className="text-xs text-slate-500 font-medium">{subtitle}</p>
                    </div>
                </div>

                {/* Persistent Profile Header */}
                <ProfileHeader profile={profile} onEdit={() => setShowOnboarding(true)} />
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-6">
                        <div className="w-20 h-20 bg-blue-50 rounded-2xl flex items-center justify-center mb-2 shadow-sm animate-in fade-in zoom-in duration-500">
                            <Bot className="w-10 h-10 text-blue-600" />
                        </div>
                        <div className="max-w-md space-y-2">
                            <h3 className="font-bold text-2xl text-slate-800">What's on your mind?</h3>
                            <p className="text-slate-500">Check ingredients for allergies, religious diets (Halal, Jain, Hindu), or hidden additives.</p>
                        </div>

                        {/* Profile CTA if not set */}
                        {!profile.is_onboarding_completed && (
                            <button
                                onClick={() => setShowOnboarding(true)}
                                className="text-blue-600 font-bold bg-blue-50 px-6 py-3 rounded-full hover:bg-blue-100 transition-colors"
                            >
                                Setup my Safety Profile
                            </button>
                        )}

                        <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                            {suggestions.map((s, i) => (
                                <button
                                    key={i}
                                    onClick={() => setInput(s)}
                                    className="text-sm bg-white border border-slate-200 px-4 py-2 rounded-xl hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50/50 transition-all duration-200 shadow-sm"
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-2 duration-300`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0 mt-1">
                                <Bot className="w-5 h-5 text-blue-600" />
                            </div>
                        )}
                        <div className={`max-w-[85%] p-4 rounded-2xl shadow-sm ${msg.role === 'user'
                            ? 'bg-blue-600 text-white rounded-br-none'
                            : 'bg-white border border-slate-100 text-slate-800 rounded-bl-none shadow-md'
                            }`}>
                            <div className="prose prose-sm max-w-none">
                                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                            </div>
                        </div>
                        {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center flex-shrink-0 mt-1">
                                <User className="w-5 h-5 text-slate-600" />
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-slate-100">
                <div className="relative flex items-center">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={profile.is_onboarding_completed ? "Paste ingredients here..." : "Setup profile first or type ingredients..."}
                        className="w-full px-6 py-4 pr-14 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder:text-slate-400 font-medium text-slate-700"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="absolute right-2 p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:bg-slate-300 transition-all shadow-md shadow-blue-600/20"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </div>
            </form>
            <div className="bg-slate-50 p-2 border-t border-slate-100 flex justify-center gap-2">
                <button
                    onClick={() => setInput('')}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                >
                    Clear Input
                </button>
                <button
                    onClick={() => {
                        const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
                        if (lastUserMsg) setInput(lastUserMsg.content)
                    }}
                    className="px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-100 rounded-lg hover:bg-blue-100 transition-colors"
                >
                    Check Again
                </button>
                <button
                    onClick={() => setShowOnboarding(true)}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                >
                    Edit Profile
                </button>
            </div>
        </div>
    )

}
