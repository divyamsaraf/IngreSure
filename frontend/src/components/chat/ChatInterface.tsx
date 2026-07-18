'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2, X, Info } from 'lucide-react'
import OnboardingModal from './OnboardingModal'
import FormattedMessage from './FormattedMessage'
import IngredientAuditCards from './IngredientAuditCards'
import ChatEmptyPreview from './ChatEmptyPreview'
import { type Message, streamChatResponse, stripStatusPlaceholders } from './streamChatResponse'
import { UserProfile, profileToBackend, hasProfileRules } from '@/types/userProfile'
import { useProfileContext } from '@/context/ProfileContext'
import { useConfig } from '@/context/ConfigContext'
import { PROFILE_BANNER_DISMISSED_KEY } from '@/constants/profileStorage'
import {
  getOrCreateUserId,
  getAnonSessionToken,
  persistProfileToStorage,
} from '@/lib/profileStorage'
import { getDietIcon } from '@/lib/dietIcon'
import { colors, spacing } from '@/theme/tokens'
import { CHAT_PANEL_DISCLAIMER } from '@/constants/disclaimers'

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
    const [analysisStatus, setAnalysisStatus] = useState<'idle' | 'checking' | 'complete' | 'fading' | 'hidden' | 'error'>('idle')
    const [showOnboarding, setShowOnboarding] = useState(false)
    const [profileSaveStatus, setProfileSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')
    const [profileSaveError, setProfileSaveError] = useState<string>('')
    const [reanalyseStatus, setReanalyseStatus] = useState('')
    const [lastQuery, setLastQuery] = useState<string | null>(null)
    const [bannerVisible, setBannerVisible] = useState(false)
    const [bannerExiting, setBannerExiting] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLTextAreaElement>(null)

    // Profile API base: /api (no double /api). apiEndpoint is e.g. /api/chat so base = /api, then /api/profile
    const profileApiBase = apiEndpoint.replace(/\/chat.*$/, '') || '/api'

    const { profile, setProfile, userId, profileLoaded, isProfileComplete } = useProfileContext()
    const config = useConfig()
    const maxChatLength = config.max_chat_message_length
    const dietIcon = config.profile_options.diet_icon ?? {}
    const showPersonaliseNudge = profileLoaded && !hasProfileRules(profile)

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

    useEffect(() => {
        if (!profileLoaded || typeof window === 'undefined') return
        if (hasProfileRules(profile)) {
            setBannerVisible(false)
            return
        }
        if (localStorage.getItem(PROFILE_BANNER_DISMISSED_KEY) === '1') {
            setBannerVisible(false)
            return
        }
        setBannerVisible(true)
    }, [profileLoaded, profile])

    const dismissProfileBanner = () => {
        setBannerExiting(true)
        window.setTimeout(() => {
            localStorage.setItem(PROFILE_BANNER_DISMISSED_KEY, '1')
            setBannerVisible(false)
            setBannerExiting(false)
        }, 200)
    }

    const saveProfile = (newProfile: UserProfile) => {
        const uid = userId || getOrCreateUserId()
        const toSave = { ...newProfile, user_id: uid, is_onboarding_completed: true }
        const queryToRerun = lastQuery
        const shouldRerun = !!queryToRerun && messages.some((m) => m.role === 'assistant' && m.audit)
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
              if (shouldRerun && queryToRerun) {
                setReanalyseStatus('Re-analysing with your profile…')
                void submitMessage(queryToRerun, { profileOverride: toSave, replaceLast: true }).finally(() => {
                  setReanalyseStatus('')
                })
              } else {
                const parts: string[] = []
                if (toSave.dietary_preference && toSave.dietary_preference !== 'No rules') parts.push(`Diet: ${toSave.dietary_preference}`)
                if (toSave.allergens?.length) parts.push(`Allergens: ${toSave.allergens.join(', ')}`)
                if (toSave.lifestyle?.length) parts.push(`Lifestyle: ${toSave.lifestyle.join(', ')}`)
                setMessages(prev => [...prev, {
                  role: 'assistant',
                  content: `✅ Profile saved. ${parts.length ? parts.join(' · ') : 'No restrictions set.'} I'll use this for personalized advice.`
                }])
              }
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
    }, [messages, loading])

    useEffect(() => {
        const el = inputRef.current
        if (!el) return
        el.style.height = 'auto'
        el.style.height = `${Math.min(el.scrollHeight, 160)}px`
    }, [input])

    useEffect(() => {
        if (analysisStatus !== 'complete') return
        // Brief success flash then hide — avoid lingering "Analysis complete" chrome
        const timer = window.setTimeout(() => setAnalysisStatus('hidden'), 900)
        return () => window.clearTimeout(timer)
    }, [analysisStatus])

    const submitMessage = async (
        rawMessage: string,
        options?: { profileOverride?: UserProfile; replaceLast?: boolean },
    ) => {
        const userMsg = rawMessage.trim()
        if (!userMsg || loading) return

        if (userMsg.length > maxChatLength) {
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: `Message is too long. Please keep it under ${(maxChatLength / 1000).toFixed(0)},000 characters.` }
            ])
            return
        }

        setLastQuery(userMsg)

        if (options?.replaceLast) {
            setMessages((prev) => {
                if (prev.length >= 2 && prev[prev.length - 1].role === 'assistant' && prev[prev.length - 2].role === 'user') {
                    return prev.slice(0, -2)
                }
                return prev
            })
        }

        setInput('')
        setLoading(true)
        setAnalysisStatus('checking')
        setMessages(prev => [
            ...prev,
            { role: 'user', content: userMsg },
            { role: 'assistant', content: '' },
        ])

        try {
            const uid = userId || getOrCreateUserId()
            const activeProfile = options?.profileOverride ?? profile
            const payload = {
                message: userMsg,
                user_id: uid,
                userProfile: activeProfile
            }
            const token = getAnonSessionToken()
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (token) headers['Authorization'] = `Bearer ${token}`

            const response = await fetch(normalizeChatUrl(apiEndpoint), {
                method: 'POST',
                headers,
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
            setAnalysisStatus('complete')

        } catch (error) {
            console.error('Chat error:', error)
            setAnalysisStatus('error')
            const message = error instanceof Error ? error.message : 'Sorry, I encountered an error. Please try again.'
            setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: `Sorry, something went wrong. ${message}` }
            ])
        } finally {
            setLoading(false)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        await submitMessage(input)
    }

    const chipsDisabled = loading || !profileLoaded

    const hasAssistantResult = messages.some(
        (m) =>
            m.role === 'assistant' &&
            (!!m.audit || !!stripStatusPlaceholders(m.content)),
    )

    return (
        <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 shadow-[0_8px_40px_rgba(15,23,42,0.06)] backdrop-blur-sm">

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
                        <h1 className="font-display text-lg font-semibold text-slate-900 truncate">{title}</h1>
                        <p className="text-sm text-slate-500 truncate">{subtitle}</p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                        {profileLoaded && profile.dietary_preference && profile.dietary_preference !== 'No rules' ? (
                            <button
                                type="button"
                                onClick={() => setShowOnboarding(true)}
                                className="inline-flex items-center gap-1.5 rounded-full border font-semibold text-[13px] px-2.5 py-1 bg-teal-50 border-teal-200 text-teal-900 cursor-pointer transition-colors hover:bg-teal-100"
                                title="Edit profile"
                                aria-label="Edit profile"
                            >
                                {getDietIcon(dietIcon, profile.dietary_preference)} {profile.dietary_preference}
                            </button>
                        ) : (
                            <span className="text-[13px] text-slate-500">No diet set</span>
                        )}
                        <button
                            type="button"
                            onClick={() => setShowOnboarding(true)}
                            className="ml-1.5 text-[13px] font-medium cursor-pointer transition-colors hover:underline text-accent"
                            aria-label="Edit profile"
                        >
                            Edit
                        </button>
                    </div>
                </div>

                {bannerVisible && (
                    <div
                        className={`mt-3 flex items-center gap-2 rounded-2xl border border-teal-200 bg-teal-50 px-4 py-2.5 shadow-card transition-all duration-200 ${
                            bannerExiting
                                ? 'opacity-0 -translate-y-1 max-h-0 py-0 mt-0 overflow-hidden'
                                : 'opacity-100 translate-y-0 animate-in slide-in-from-top-2 duration-200'
                        }`}
                        role="region"
                        aria-label="Profile setup prompt"
                    >
                        <p className="flex-1 min-w-0 text-sm text-teal-900">
                            Set your diet for personalised results — takes about 10 seconds.
                        </p>
                        <button
                            type="button"
                            onClick={() => setShowOnboarding(true)}
                            className="shrink-0 text-sm font-semibold text-teal-900 hover:text-teal-950 transition-colors"
                        >
                            Set up →
                        </button>
                        <button
                            type="button"
                            onClick={dismissProfileBanner}
                            className="shrink-0 p-0.5 rounded text-accent hover:text-teal-900 hover:bg-teal-100 transition-colors"
                            aria-label="Dismiss profile setup banner"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                )}
            </div>

            {/* Profile save feedback */}
            {profileSaveStatus === 'success' && (
                <div className="shrink-0 px-4 py-2 bg-teal-50 border-b border-teal-100 text-teal-900 text-sm font-medium flex items-center justify-center gap-2" role="status" aria-live="polite">
                    Profile saved.
                </div>
            )}
            {profileSaveStatus === 'error' && (
                <div className="shrink-0 px-4 py-2 bg-red-50 border-b border-red-100 text-red-800 text-sm font-medium flex items-center justify-between gap-2" role="alert" aria-live="polite">
                    <span>{profileSaveError}</span>
                    <button type="button" onClick={() => { setProfileSaveStatus('idle'); setProfileSaveError(''); }} className="px-2 py-0.5 rounded hover:bg-red-100 transition-colors" aria-label="Dismiss">Dismiss</button>
                </div>
            )}
            {reanalyseStatus && (
                <div className="shrink-0 px-4 py-2 bg-teal-50 border-b border-teal-100 text-teal-900 text-sm font-medium flex items-center justify-center gap-2" role="status" aria-live="polite">
                    {reanalyseStatus}
                </div>
            )}

            {/* Messages (scrolls with follow-up prompt and recent checks below results) */}
            <div
                className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 px-6 pt-6 pb-3 scroll-smooth"
            >
                {messages.length === 0 && (
                    <div className="flex flex-col items-center px-2 py-6 text-center sm:py-10">
                        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-100 bg-teal-50 text-accent shadow-card">
                            <Bot className="h-6 w-6" aria-hidden />
                        </div>
                        <h3 className="font-display text-2xl font-semibold tracking-tight text-primary">
                            Check what&apos;s in the label
                        </h3>
                        <p className="mt-2 max-w-md text-[15px] leading-relaxed text-slate-500">
                            Paste ingredients below — or tap an example. You&apos;ll see Safe, Avoid,
                            and Depends against your diet and allergens.
                        </p>
                        {!isProfileComplete && !bannerVisible && (
                            <button
                                type="button"
                                onClick={() => setShowOnboarding(true)}
                                className="mt-3 cursor-pointer text-sm font-semibold text-accent underline-offset-2 hover:underline"
                            >
                                Set diet &amp; allergens for a personal check
                            </button>
                        )}

                        <ChatEmptyPreview
                            onTryExample={() => {
                                const example =
                                    suggestions[0] ||
                                    'Ingredients: Sugar, Gelatin, Citric Acid, Natural Flavors, Carnauba Wax'
                                setInput(example)
                                void submitMessage(example)
                            }}
                        />

                        <div className="mt-6 flex w-full max-w-lg flex-col gap-2">
                            <p className="text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                                More examples
                            </p>
                            {suggestions.map((s, i) => (
                                <button
                                    key={i}
                                    type="button"
                                    disabled={chipsDisabled}
                                    onClick={() => {
                                        setInput(s)
                                        void submitMessage(s)
                                    }}
                                    className="inline-flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-chat-chip font-medium text-slate-700 shadow-card transition-all hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    <span className="line-clamp-2">{s}</span>
                                    <span className="shrink-0 text-accent" aria-hidden>
                                        →
                                    </span>
                                </button>
                            ))}
                        </div>
                        <p className="mt-5 text-xs text-slate-400">
                            Or paste your own list in the box below — Enter to send
                        </p>
                    </div>
                )}

                {messages.length > 0 && (
                    <div className="space-y-6">
                        {messages.map((msg, idx) => {
                    const isLastAssistant =
                        msg.role === 'assistant' &&
                        idx === messages.length - 1 &&
                        analysisStatus !== 'idle' &&
                        analysisStatus !== 'hidden'
                    const showAnalysisStatus = isLastAssistant
                    const analysisStatusText =
                        analysisStatus === 'error' ? 'Something went wrong' : null
                    const displayContent =
                        msg.role === 'assistant' ? stripStatusPlaceholders(msg.content) : msg.content
                    const hasResultContent = !!(msg.audit || displayContent)
                    const isPendingAssistant =
                        msg.role === 'assistant' &&
                        loading &&
                        idx === messages.length - 1 &&
                        !hasResultContent
                    const showStatusLabel =
                        showAnalysisStatus &&
                        !!analysisStatusText &&
                        !isPendingAssistant &&
                        analysisStatus === 'error'

                    return (
                    <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-2 duration-300`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full bg-white border border-slate-100 flex items-center justify-center flex-shrink-0 mt-1 shadow-card">
                                <Bot className="w-4 h-4 text-slate-600" />
                            </div>
                        )}
                        <div
                            className={`rounded-2xl shadow-card font-sans ${
                                msg.role === 'user'
                                    ? 'max-w-[85%] sm:max-w-[75%] bg-primary text-white rounded-br-none px-4 py-3.5'
                                    : msg.audit
                                      ? 'max-w-full flex-1 bg-white border border-slate-100 text-primary rounded-bl-none px-4 py-4 sm:max-w-[min(100%,42rem)]'
                                      : 'max-w-[85%] sm:max-w-[80%] bg-white border border-slate-100 text-primary rounded-bl-none px-4 py-3.5'
                            }`}
                        >
                            <div className="text-chat-body">
                                {showStatusLabel && analysisStatusText ? (
                                    <p
                                        role="status"
                                        aria-live="polite"
                                        className="mb-2 text-chat-meta font-medium text-avoid"
                                    >
                                        {analysisStatusText}
                                    </p>
                                ) : null}
                                {isPendingAssistant ? (
                                    <div className="flex items-center gap-2 text-slate-500 animate-in fade-in duration-200" role="status" aria-live="polite" aria-label="Analyzing ingredients">
                                        <span>Analyzing ingredients</span>
                                        <span className="loading-dots" aria-hidden="true">
                                            <span className="loading-dot" />
                                            <span className="loading-dot" />
                                            <span className="loading-dot" />
                                        </span>
                                    </div>
                                ) : msg.role === 'assistant' && msg.audit ? (
                                    <div className="space-y-3">
                                        {displayContent ? (
                                            <FormattedMessage content={displayContent} isUser={false} />
                                        ) : null}
                                        <IngredientAuditCards
                                            data={msg.audit}
                                            showPersonaliseNudge={showPersonaliseNudge && !bannerVisible}
                                            onPersonalise={() => setShowOnboarding(true)}
                                        />
                                    </div>
                                ) : (
                                    <FormattedMessage content={displayContent} isUser={msg.role === 'user'} />
                                )}
                            </div>
                        </div>
                        {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1 shadow-card">
                                <User className="w-4 h-4 text-white" />
                            </div>
                        )}
                    </div>
                    )
                })}
                    </div>
                )}

                {hasAssistantResult && (
                    <p
                        className="text-chat-meta font-medium text-center"
                        style={{ color: colors.muted, marginTop: spacing.inner }}
                    >
                        Paste another label or ask a follow-up below
                    </p>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input area (sticky bottom) */}
            <form onSubmit={handleSubmit} className="shrink-0 border-t border-slate-100 bg-white px-4 pb-3 pt-2">
                <p
                    role="note"
                    className="mb-2 text-[11px] leading-snug text-slate-500"
                >
                    <Info className="mr-1 inline h-3 w-3 align-text-bottom text-slate-400" aria-hidden />
                    {CHAT_PANEL_DISCLAIMER}
                </p>
                <div className="flex items-end gap-3">
                    <div className="relative w-full">
                        <textarea
                            ref={inputRef}
                            rows={1}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault()
                                    if (!loading && input.trim() && profileLoaded) {
                                        void submitMessage(input)
                                    }
                                }
                            }}
                            placeholder="Paste an ingredient list or ask a question…"
                            className={`max-h-40 min-h-[52px] w-full resize-none overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3.5 font-sans text-chat-input font-medium text-slate-700 shadow-card transition-all placeholder:text-slate-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 ${input ? 'pr-10' : 'pr-4'}`}
                            disabled={loading || !profileLoaded}
                            aria-label="Ingredient list or question"
                        />
                        {input ? (
                            <button
                                type="button"
                                onClick={() => setInput('')}
                                className="absolute right-3 top-3 rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600"
                                aria-label="Clear input"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        ) : null}
                    </div>
                    <button
                        type="submit"
                        disabled={loading || !input.trim() || !profileLoaded}
                        className="inline-flex h-[52px] w-[52px] shrink-0 cursor-pointer items-center justify-center rounded-2xl bg-gradient-to-r from-primary to-accent text-white shadow-card transition-all hover:opacity-95 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60"
                        aria-label="Send"
                    >
                        {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                    </button>
                </div>
                {!profileLoaded ? (
                    <p className="mt-1.5 text-[11px] text-slate-400">Loading your profile…</p>
                ) : null}
            </form>
        </div>
    )

}
