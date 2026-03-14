'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2 } from 'lucide-react'
import OnboardingModal from './OnboardingModal'
import FormattedMessage from './FormattedMessage'
import IngredientAuditCards from './IngredientAuditCards'
import RecentChecksSection from './RecentChecksSection'
import { type Message, streamChatResponse } from './streamChatResponse'
import { UserProfile, profileToBackend, DIET_ICON, hasProfileRules } from '@/types/userProfile'
import { useProfileContext } from '@/context/ProfileContext'
import { PROFILE_STORAGE_KEY } from '@/constants/profileStorage'
import { getOrCreateUserId, persistProfileToStorage } from '@/lib/profileStorage'

/** Ensure chat URL has exactly one mode param (avoids ?mode=grocery?mode=grocery from duplicate appends). */
function normalizeChatUrl(url: string): string {
  try {
    const pathOnly = url.split('?')[0].replace(/\/+$/, '') || '/api/chat'
    const params = new URLSearchParams(url.includes('?') ? url.split('?').slice(1).join('?') : '')
    const mode = params.get('mode') || 'grocery'
    return `${pathOnly}?mode=${mode}`
  } catch {
    return url.startsWith('/') ? url : '/api/chat?mode=grocery'
  }
}

interface ChatInterfaceProps {
    apiEndpoint?: string
    title?: string
    subtitle?: string
    suggestions?: string[]
}

function getDietIcon(diet: string | undefined): string {
    if (!diet || diet === 'No rules') return DIET_ICON['No rules'] ?? '🍽️'
    const key = diet.trim()
    const found = DIET_ICON[key] ?? Object.entries(DIET_ICON).find(([k]) => k.toLowerCase() === key.toLowerCase())?.[1]
    return found ?? '🥗'
}

export default function ChatInterface({
    apiEndpoint = '/api/chat',
    title = 'IngreSure Assistant',
    subtitle = 'Deterministic Compliance Engine',
    suggestions = [
        "Is the burger vegan?",
        "I have a peanut allergy."
    ]
}: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [showOnboarding, setShowOnboarding] = useState(false)
    const [profileSaveStatus, setProfileSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')
    const [profileSaveError, setProfileSaveError] = useState<string>('')
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Profile API base: /api (no double /api). apiEndpoint is e.g. /api/chat so base = /api, then /api/profile
    const profileApiBase = apiEndpoint.replace(/\/chat.*$/, '') || '/api'

    const { profile, setProfile, userId, profileLoaded, isProfileComplete } = useProfileContext()

    // Decide initial onboarding visibility once profile has been loaded
    useEffect(() => {
        if (!profileLoaded || typeof window === 'undefined') return

        // Prefer explicit onboarding completion flag from saved profile
        const saved = localStorage.getItem(PROFILE_STORAGE_KEY)
        if (saved) {
            try {
                const p = JSON.parse(saved)
                if (p.is_onboarding_completed) {
                    setShowOnboarding(false)
                    return
                }
            } catch {
                // ignore parse error and fall through to rules-based check
            }
        }

        setShowOnboarding(!hasProfileRules(profile))
    }, [profileLoaded, profile])

    // Open profile modal when navigating with ?openProfile=1 (e.g. from navbar avatar)
    useEffect(() => {
        if (typeof window === 'undefined') return
        const params = new URLSearchParams(window.location.search)
        if (params.get('openProfile') === '1') {
            setShowOnboarding(true)
            const url = new URL(window.location.href)
            url.searchParams.delete('openProfile')
            window.history.replaceState({}, '', url.pathname + (url.search || ''))
        }
    }, [])

    const saveProfile = (newProfile: UserProfile) => {
        const uid = userId || getOrCreateUserId()
        const toSave = { ...newProfile, user_id: uid, is_onboarding_completed: true }
        setProfile(toSave)
        persistProfileToStorage(toSave)
        setProfileSaveStatus('idle')
        setProfileSaveError('')

        const payload = profileToBackend(toSave, uid)
        fetch(`${profileApiBase}/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
          .then(async (res) => {
            if (res.ok) {
              setProfileSaveStatus('success')
              setTimeout(() => setProfileSaveStatus('idle'), 3000)
              const parts: string[] = []
              if (toSave.dietary_preference && toSave.dietary_preference !== 'No rules') parts.push(`Diet: ${toSave.dietary_preference}`)
              if (toSave.allergens?.length || toSave.allergies?.length) parts.push(`Allergens: ${(toSave.allergens ?? toSave.allergies ?? []).join(', ')}`)
              if (toSave.lifestyle?.length || toSave.lifestyle_flags?.length) parts.push(`Lifestyle: ${(toSave.lifestyle ?? toSave.lifestyle_flags ?? []).join(', ')}`)
              setMessages(prev => [...prev, {
                role: 'assistant',
                content: `✅ Profile saved. ${parts.length ? parts.join(' · ') : 'No restrictions set.'} I'll use this for personalized advice.`
              }])
            } else {
              const body = await res.json().catch(() => ({}))
              setProfileSaveStatus('error')
              setProfileSaveError(typeof body?.detail === 'string' ? body.detail : body?.error || 'Could not save profile.')
            }
          })
          .catch((err) => {
            console.error('Profile save failed:', err)
            setProfileSaveStatus('error')
            setProfileSaveError('Network error. Please try again.')
          })
    }

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
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
            const payload = {
                message: userMsg,
                user_id: userId || getOrCreateUserId(),
                userProfile: profile
            }

            const response = await fetch(normalizeChatUrl(apiEndpoint), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })

            if (!response.ok) {
                let errMsg = 'Chat failed'
                try {
                    const errBody = await response.json()
                    if (errBody?.detail) errMsg = typeof errBody.detail === 'string' ? errBody.detail : errMsg
                    else if (errBody?.error) errMsg = errBody.error + (errBody.detail ? `: ${errBody.detail}` : '')
                } catch {
                    // ignore
                }
                throw new Error(errMsg)
            }

            const reader = response.body?.getReader()
            if (!reader) return

            await streamChatResponse(reader, setMessages, setProfile, setShowOnboarding, persistProfileToStorage)

        } catch (error) {
            console.error('Chat error:', error)
            const message = error instanceof Error ? error.message : 'Sorry, I encountered an error. Please try again.'
            setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: `Sorry, something went wrong. ${message}` }
            ])
        } finally {
            setLoading(false)
        }
    }

    // Recent user queries for suggestion chips
    const recentQueries: string[] = Array.from(
        new Set(
            [...messages]
                .filter((m) => m.role === 'user')
                .map((m) => m.content)
                .reverse(),
        ),
    ).slice(0, 5)

    return (
        <div className="flex flex-col h-full rounded-2xl bg-white shadow-sm border border-slate-100 overflow-hidden">

            {/* Onboarding Modal */}
            <OnboardingModal
                isOpen={showOnboarding}
                onClose={() => setShowOnboarding(false)}
                onSave={saveProfile}
                initialProfile={profile}
                editMode={isProfileComplete}
            />

            {/* Header: left = product identity, right = profile context (sticky when chat scrolls) */}
            <div className="sticky top-0 z-10 bg-white border-b border-slate-100 shrink-0 px-6 py-4">
                <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0">
                        <h1 className="font-serif text-lg font-semibold text-slate-900 truncate">{title}</h1>
                        <p className="text-sm text-slate-500 truncate">{subtitle}</p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                        {profileLoaded && profile.dietary_preference && profile.dietary_preference !== 'No rules' ? (
                            <span
                                className="inline-flex items-center gap-1.5 rounded-full border font-semibold text-[13px] px-2.5 py-1 bg-emerald-50 border-emerald-200 text-emerald-800"
                                title="Active diet profile"
                            >
                                {getDietIcon(profile.dietary_preference)} {profile.dietary_preference}
                            </span>
                        ) : (
                            <span className="text-[13px] text-slate-500">No diet set</span>
                        )}
                        <button
                            type="button"
                            onClick={() => setShowOnboarding(true)}
                            className="ml-1.5 text-[13px] font-medium cursor-pointer transition-colors hover:underline text-blue-600"
                            aria-label="Edit profile"
                        >
                            Edit
                        </button>
                    </div>
                </div>
            </div>

            {/* Profile save feedback */}
            {profileSaveStatus === 'success' && (
                <div className="shrink-0 px-4 py-2 bg-emerald-50 border-b border-emerald-100 text-emerald-800 text-sm font-medium flex items-center justify-center gap-2" role="status" aria-live="polite">
                    Profile saved.
                </div>
            )}
            {profileSaveStatus === 'error' && (
                <div className="shrink-0 px-4 py-2 bg-red-50 border-b border-red-100 text-red-800 text-sm font-medium flex items-center justify-between gap-2" role="alert" aria-live="polite">
                    <span>{profileSaveError}</span>
                    <button type="button" onClick={() => { setProfileSaveStatus('idle'); setProfileSaveError(''); }} className="px-2 py-0.5 rounded hover:bg-red-100 transition-colors" aria-label="Dismiss">Dismiss</button>
                </div>
            )}

            {/* Messages (only this section scrolls) */}
            <div
                className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 px-6 py-6 space-y-6 scroll-smooth"
            >
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-6">
                        <div className="w-20 h-20 bg-blue-50 rounded-2xl flex items-center justify-center mb-2 shadow-sm animate-in fade-in zoom-in duration-500">
                            <Bot className="w-10 h-10 text-blue-600" />
                        </div>
                        <div className="max-w-md space-y-2">
                            <h3 className="font-bold text-2xl text-slate-800">What&apos;s on your mind?</h3>
                            <p className="text-slate-500">Check ingredients for allergies, religious diets (Halal, Jain, Hindu), or hidden additives.</p>
                            {!isProfileComplete && (
                                <p className="text-xs text-slate-400">Set your diet &amp; allergens above for personalized results.</p>
                            )}
                        </div>

                        {/* Profile CTA if not set */}
                        {!isProfileComplete && (
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
                    <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-2 duration-300`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full bg-white border border-slate-100 flex items-center justify-center flex-shrink-0 mt-1 shadow-card">
                                <Bot className="w-4 h-4 text-slate-600" />
                            </div>
                        )}
                        <div
                            className={`max-w-[80%] sm:max-w-[75%] rounded-2xl shadow-card font-sans ${msg.role === 'user'
                                ? 'bg-primary text-white rounded-br-none px-4 py-4'
                                : 'bg-white border border-slate-100 text-primary rounded-bl-none px-4 py-4'
                                }`}
                        >
                            <div className="text-[15px] leading-[1.5]">
                                {msg.role === 'assistant' && !msg.content.trim() && !msg.audit ? (
                                    <div className="flex items-center gap-1 text-slate-400 animate-in fade-in duration-200" role="status" aria-label="Loading">
                                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:-0.2s]" />
                                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-bounce [animation-delay:-0.1s]" />
                                        <span className="h-1.5 w-1.5 rounded-full bg-slate-300 animate-bounce" />
                                    </div>
                                ) : msg.role === 'assistant' && msg.audit ? (
                                    <div className="space-y-3">
                                        {msg.content.trim() ? (
                                            <FormattedMessage content={msg.content.trim()} isUser={false} />
                                        ) : null}
                                        <IngredientAuditCards data={msg.audit} />
                                    </div>
                                ) : (
                                    <FormattedMessage content={msg.content} isUser={msg.role === 'user'} />
                                )}
                            </div>
                        </div>
                        {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1 shadow-card">
                                <User className="w-4 h-4 text-white" />
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Recent checks (above input, does not scroll) */}
            {recentQueries.length > 0 && (
                <RecentChecksSection
                    queries={recentQueries}
                    onSelect={(q) => setInput(q)}
                />
            )}

            {/* Input area (sticky bottom) */}
            <form onSubmit={handleSubmit} className="border-t border-slate-100 bg-white px-4 py-3 shrink-0">
                <div className="flex gap-3 items-center">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type ingredient or question…"
                        className="w-full px-4 py-3.5 pr-4 bg-slate-50 border border-slate-200 rounded-2xl shadow-card focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all placeholder:text-slate-400 font-sans font-medium text-slate-700"
                        disabled={loading || !profileLoaded}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim() || (!isProfileComplete && !profileLoaded)}
                        className="shrink-0 inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-primary to-secondary p-3.5 text-white shadow-card transition-all hover:opacity-95 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </div>
            </form>
            <div className="px-4 pb-3 pt-2 bg-white flex justify-center gap-2 flex-wrap shrink-0">
                <button
                    type="button"
                    onClick={() => setInput('')}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-[12px] hover:bg-slate-50 hover:shadow-card transition-all"
                >
                    Clear Input
                </button>
                <button
                    type="button"
                    onClick={() => {
                        const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
                        if (lastUserMsg) setInput(lastUserMsg.content)
                    }}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-[12px] hover:bg-slate-50 hover:shadow-card transition-all"
                >
                    Check Again
                </button>
                <button
                    type="button"
                    onClick={() => setShowOnboarding(true)}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-[12px] hover:bg-slate-50 hover:shadow-card transition-all inline-flex items-center gap-1"
                >
                    Edit Profile
                </button>
            </div>
        </div>
    )

}
