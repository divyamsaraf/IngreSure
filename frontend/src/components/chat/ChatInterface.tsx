'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2, X } from 'lucide-react'
import OnboardingModal from './OnboardingModal'
import FormattedMessage from './FormattedMessage'
import IngredientAuditCards, { type IngredientAuditData } from './IngredientAuditCards'
import { type Message, streamChatResponse, stripStatusPlaceholders } from './streamChatResponse'
import { UserProfile, profileToBackend, hasProfileRules } from '@/types/userProfile'
import { useProfileContext } from '@/context/ProfileContext'
import { useConfig } from '@/context/ConfigContext'
import { PROFILE_BANNER_DISMISSED_KEY } from '@/constants/profileStorage'
import { getOrCreateUserId, getAnonSessionToken, persistProfileToStorage } from '@/lib/profileStorage'
import { getDietIcon } from '@/lib/dietIcon'
import { colors, spacing } from '@/theme/tokens'

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

const EMPTY_STATE_EXAMPLE_QUERY =
  'Ingredients: Sugar, Gelatin, Citric Acid, Natural Flavors, Red 40, Carnauba Wax'

const EMPTY_STATE_EXAMPLE_AUDIT: IngredientAuditData = {
  summary: '3 Safe, 1 Avoid, 2 Depends',
  groups: [
    {
      status: 'avoid',
      items: [
        {
          name: 'Gelatin',
          status: 'avoid',
          reason: 'animal-derived (bovine/porcine)',
        },
      ],
    },
    {
      status: 'depends',
      items: [
        {
          name: 'Natural Flavors',
          status: 'depends',
          reason: 'may contain animal derivatives — check with manufacturer',
        },
        {
          name: 'Red 40',
          status: 'depends',
          reason: 'some Jain/vegan diets avoid synthetic dyes',
        },
      ],
    },
    {
      status: 'safe',
      items: [
        { name: 'Sugar', status: 'safe' },
        { name: 'Citric Acid', status: 'safe' },
        { name: 'Carnauba Wax', status: 'safe' },
      ],
    },
  ],
  explanation:
    'Based on a Vegan profile, Gelatin is not suitable — it is derived from animal collagen. Natural Flavors also carries a warning as the source is unspecified.',
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

    /* Recent checks hidden — re-enable with RecentChecksSection when needed
    useEffect(() => {
        setRecentChecks(loadRecentChecks())
    }, [])

    useEffect(() => {
        const fromMessages = buildRecentChecksFromMessages(messages)
        if (fromMessages.length === 0) return
        setRecentChecks(fromMessages)
        persistRecentChecks(fromMessages)
    }, [messages])
    */

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }, [messages, loading])

    useEffect(() => {
        if (analysisStatus !== 'complete') return
        const timer = window.setTimeout(() => setAnalysisStatus('fading'), 2000)
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
                            <button
                                type="button"
                                onClick={() => setShowOnboarding(true)}
                                className="inline-flex items-center gap-1.5 rounded-full border font-semibold text-[13px] px-2.5 py-1 bg-emerald-50 border-emerald-200 text-emerald-800 cursor-pointer transition-colors hover:bg-emerald-100"
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
                            className="ml-1.5 text-[13px] font-medium cursor-pointer transition-colors hover:underline text-blue-600"
                            aria-label="Edit profile"
                        >
                            Edit
                        </button>
                    </div>
                </div>

                {bannerVisible && (
                    <div
                        className={`mt-3 flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 shadow-card transition-all duration-200 ${
                            bannerExiting
                                ? 'opacity-0 -translate-y-1 max-h-0 py-0 mt-0 overflow-hidden'
                                : 'opacity-100 translate-y-0 animate-in slide-in-from-top-2 duration-200'
                        }`}
                        role="region"
                        aria-label="Profile setup prompt"
                    >
                        <p className="flex-1 min-w-0 text-sm text-emerald-800">
                            👋 Set your diet for personalised results — takes 10 seconds.
                        </p>
                        <button
                            type="button"
                            onClick={() => setShowOnboarding(true)}
                            className="shrink-0 text-sm font-semibold text-emerald-800 hover:text-emerald-950 transition-colors"
                        >
                            Set up →
                        </button>
                        <button
                            type="button"
                            onClick={dismissProfileBanner}
                            className="shrink-0 p-0.5 rounded text-emerald-600 hover:text-emerald-900 hover:bg-emerald-100 transition-colors"
                            aria-label="Dismiss profile setup banner"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                )}
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
            {reanalyseStatus && (
                <div className="shrink-0 px-4 py-2 bg-emerald-50 border-b border-emerald-100 text-emerald-800 text-sm font-medium flex items-center justify-center gap-2" role="status" aria-live="polite">
                    {reanalyseStatus}
                </div>
            )}

            {/* Messages (scrolls with follow-up prompt and recent checks below results) */}
            <div
                className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 px-6 pt-6 pb-3 scroll-smooth"
            >
                {messages.length === 0 && (
                    <>
                        <div className="flex flex-col items-center text-center space-y-4 pb-2">
                            <div className="w-16 h-16 rounded-2xl bg-white border border-slate-100 flex items-center justify-center shadow-card">
                                <Bot className="w-8 h-8 text-slate-600" />
                            </div>
                            <div className="max-w-md space-y-2">
                                <h3 className="font-bold text-2xl text-slate-800">What&apos;s on your mind?</h3>
                                <p className="text-slate-500">Check ingredients for allergies, religious diets (Halal, Jain, Hindu), or hidden additives.</p>
                                {!isProfileComplete && (
                                    <p className="text-xs text-slate-400">Set your diet &amp; allergens above for personalized results.</p>
                                )}
                            </div>

                            {!isProfileComplete && (
                                <button
                                    type="button"
                                    onClick={() => setShowOnboarding(true)}
                                    className="text-secondary font-bold bg-emerald-50 border border-emerald-200 px-6 py-3 rounded-full hover:bg-emerald-100 transition-colors"
                                >
                                    Setup my Safety Profile
                                </button>
                            )}

                            <div className="flex flex-col items-stretch gap-2 w-full max-w-lg pt-1">
                                {suggestions.map((s, i) => (
                                    <button
                                        key={i}
                                        type="button"
                                        disabled={chipsDisabled}
                                        onClick={() => {
                                            setInput(s)
                                            void submitMessage(s)
                                        }}
                                        className="inline-flex items-center justify-between gap-3 w-full text-left text-chat-chip font-medium bg-white border border-slate-200 px-4 py-2.5 rounded-xl shadow-card transition-all duration-200 hover:border-secondary hover:text-secondary disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:border-slate-200 disabled:hover:text-inherit"
                                    >
                                        <span>{s}</span>
                                        <span className="shrink-0 text-secondary" aria-hidden="true">→</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-6 w-full border-t border-slate-100 pt-6">
                            <p
                                className="text-chat-meta font-medium text-center"
                                style={{ color: colors.muted }}
                            >
                                Example result — try your own ingredients below ↓
                            </p>
                            <div className="flex gap-3 justify-end animate-in slide-in-from-bottom-2 duration-300">
                                <div className="max-w-[80%] sm:max-w-[75%] rounded-2xl shadow-card font-sans bg-primary text-white rounded-br-none px-4 py-4">
                                    <div className="text-chat-body">
                                        <FormattedMessage content={EMPTY_STATE_EXAMPLE_QUERY} isUser />
                                    </div>
                                </div>
                                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1 shadow-card">
                                    <User className="w-4 h-4 text-white" />
                                </div>
                            </div>
                            <div className="flex gap-3 justify-start animate-in slide-in-from-bottom-2 duration-300">
                                <div className="w-8 h-8 rounded-full bg-white border border-slate-100 flex items-center justify-center flex-shrink-0 mt-1 shadow-card">
                                    <Bot className="w-4 h-4 text-slate-600" />
                                </div>
                                <div className="max-w-[80%] sm:max-w-[75%] rounded-2xl shadow-card font-sans bg-white border border-slate-100 text-primary rounded-bl-none px-4 py-4">
                                    <div className="text-chat-body">
                                        <IngredientAuditCards data={EMPTY_STATE_EXAMPLE_AUDIT} />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </>
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
                        analysisStatus === 'checking'
                            ? 'Checking ingredients...'
                            : analysisStatus === 'error'
                              ? 'Something went wrong'
                              : analysisStatus === 'complete' || analysisStatus === 'fading'
                                ? '✓ Analysis complete'
                                : null
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
                        analysisStatusText &&
                        !isPendingAssistant &&
                        (analysisStatus === 'error' ||
                            analysisStatus === 'complete' ||
                            analysisStatus === 'fading')

                    return (
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
                            <div className="text-chat-body">
                                {showStatusLabel && analysisStatusText ? (
                                    <p
                                        role="status"
                                        aria-live="polite"
                                        className={`analysis-status-label text-chat-meta text-slate-500 mb-2 ${analysisStatus === 'fading' ? 'opacity-0' : 'opacity-100'} ${analysisStatus === 'complete' || analysisStatus === 'fading' ? 'text-emerald-600' : ''}`}
                                        onTransitionEnd={(e) => {
                                            if (e.propertyName === 'opacity' && analysisStatus === 'fading') {
                                                setAnalysisStatus('hidden')
                                            }
                                        }}
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
                                            showPersonaliseNudge={showPersonaliseNudge}
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
                        Ask a follow-up or paste a new ingredient list ↓
                    </p>
                )}

                {/* Recent checks hidden for now
                {recentChecks.length > 0 && (
                    <div style={{ marginTop: spacing.inner }}>
                        <RecentChecksSection
                            entries={recentChecks}
                            onSelect={(q) => setInput(q)}
                        />
                    </div>
                )}
                */}

                <div ref={messagesEndRef} />
            </div>

            {/* Input area (sticky bottom) */}
            <form onSubmit={handleSubmit} className="border-t border-slate-100 bg-white px-4 py-3 shrink-0">
                <div className="flex gap-3 items-center">
                    <div className="relative w-full">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Type ingredient or question…"
                            className={`w-full px-4 py-3.5 bg-slate-50 border border-slate-200 rounded-2xl shadow-card focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all placeholder:text-slate-400 font-sans font-medium text-chat-input text-slate-700 ${input ? 'pr-10' : 'pr-4'}`}
                            disabled={loading || !profileLoaded}
                        />
                        {input ? (
                            <button
                                type="button"
                                onClick={() => setInput('')}
                                className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
                                aria-label="Clear input"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        ) : null}
                    </div>
                    <button
                        type="submit"
                        disabled={loading || !input.trim() || !profileLoaded}
                        className="shrink-0 inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-primary to-secondary p-3.5 text-white shadow-card transition-all hover:opacity-95 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </div>
            </form>
        </div>
    )

}
