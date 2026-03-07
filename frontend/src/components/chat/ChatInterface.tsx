'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2, ChevronDown } from 'lucide-react'
import OnboardingModal from './OnboardingModal'
import FormattedMessage from './FormattedMessage'
import IngredientAuditCards, {
  IngredientAuditData,
  IngredientAuditGroup,
  IngredientStatus,
} from './IngredientAuditCards'
import { UserProfile, DEFAULT_PROFILE, backendToProfile, profileToBackend, DIET_ICON } from '@/types/userProfile'

const USER_ID_KEY = 'ingresure_user_id'

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

function getOrCreateUserId(): string {
  if (typeof window === 'undefined') return ''
  let id = localStorage.getItem(USER_ID_KEY)
  if (!id) {
    id = crypto.randomUUID?.() ?? `anon-${Date.now()}`
    localStorage.setItem(USER_ID_KEY, id)
  }
  return id
}

function normalizeAuditData(raw: any): IngredientAuditData {
  // Normalize groups: accept either array or { safe: [], avoid: [], depends: [] }
  const groupsArray: IngredientAuditGroup[] = []
  const keys: IngredientStatus[] = ['safe', 'avoid', 'depends']

  if (Array.isArray(raw.groups)) {
    for (const g of raw.groups as any[]) {
      if (!g || !keys.includes(g.status)) continue
      groupsArray.push({
        status: g.status,
        items: (g.items || []).map((item: any) => ({
          name: String(item.name ?? ''),
          status: g.status,
          diets: item.diets ?? item.diet ?? [],
          allergens: item.allergens ?? [],
          alternatives: item.alternatives ?? [],
        })),
      })
    }
  } else if (raw.groups && typeof raw.groups === 'object') {
    for (const status of keys) {
      const arr = raw.groups[status]
      if (!Array.isArray(arr) || arr.length === 0) continue
      groupsArray.push({
        status,
        items: arr.map((item: any) => ({
          name: String(item.name ?? ''),
          status,
          diets: item.diets ?? item.diet ?? [],
          allergens: item.allergens ?? [],
          alternatives: item.alternatives ?? [],
        })),
      })
    }
  }

  // Compute counts for summary string
  const counts = groupsArray.reduce(
    (acc, g) => {
      acc[g.status] += g.items.length
      return acc
    },
    { safe: 0, avoid: 0, depends: 0 } as Record<IngredientStatus, number>,
  )

  const summary =
    raw.summary && typeof raw.summary === 'string'
      ? raw.summary
      : `${counts.safe} Safe, ${counts.avoid} Avoid, ${counts.depends} Depends`

  return {
    summary,
    groups: groupsArray,
    explanation: raw.explanation,
  }
}

interface Message {
    role: 'user' | 'assistant'
    content: string
    audit?: IngredientAuditData
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

function RecentChecksSection({ queries, onSelect }: { queries: string[]; onSelect: (q: string) => void }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="px-4 pb-1 pt-2 bg-white border-t border-slate-100">
            <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className="flex items-center gap-2 w-full text-left py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50 rounded"
                aria-expanded={open}
            >
                <span className="text-[11px] font-medium text-slate-500">
                    Recent checks:
                </span>
                <span className="text-slate-400 text-[10px]">
                    {queries.length} {queries.length === 1 ? 'query' : 'queries'}
                </span>
                <span className={`ml-auto inline-block transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                </span>
            </button>
            {open && (
                <div className="flex flex-wrap gap-2 pt-1 pb-2 animate-in fade-in slide-in-from-top-1 duration-200">
                    {queries.map((q) => (
                        <button
                            key={q}
                            type="button"
                            onClick={() => onSelect(q)}
                            className="text-[11px] bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-full hover:border-emerald-300 hover:text-emerald-700 hover:bg-emerald-50/60 hover:shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all"
                        >
                            {q.length > 60 ? q.slice(0, 57) + '…' : q}
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
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
    const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE)
    const [showOnboarding, setShowOnboarding] = useState(false)
    const [userId, setUserId] = useState<string>('')
    const [profileLoaded, setProfileLoaded] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const messagesRef = useRef<HTMLDivElement>(null)

    // Profile API base: /api (no double /api). apiEndpoint is e.g. /api/chat so base = /api, then /api/profile
    const profileApiBase = apiEndpoint.replace(/\/chat.*$/, '') || '/api'

    // Get or create user_id and load profile from backend (or show onboarding)
    useEffect(() => {
        const uid = getOrCreateUserId()
        setUserId(uid)
        fetch(`${profileApiBase}/profile?user_id=${encodeURIComponent(uid)}`)
          .then(res => res.ok ? res.json() : null)
          .then(data => {
            if (data && (data.dietary_preference && data.dietary_preference !== 'No rules' || (data.allergens?.length > 0) || (data.lifestyle?.length > 0) || (data.lifestyle_flags?.length > 0))) {
              setProfile(backendToProfile(data))
              setShowOnboarding(false)
            } else {
              const saved = localStorage.getItem('ingresure_profile')
              if (saved) {
                try {
                  const p = JSON.parse(saved)
                  if (p.is_onboarding_completed) setShowOnboarding(false)
                  setProfile({ ...DEFAULT_PROFILE, ...p, user_id: uid })
                } catch (_) {
                  setShowOnboarding(true)
                }
              } else {
                setShowOnboarding(true)
              }
            }
            setProfileLoaded(true)
          })
          .catch((err) => {
            console.error('Profile fetch failed:', err)
            setProfileLoaded(true)
            const saved = localStorage.getItem('ingresure_profile')
            if (saved) {
              try {
                const p = JSON.parse(saved)
                setProfile({ ...DEFAULT_PROFILE, ...p, user_id: getOrCreateUserId() })
                if (p.is_onboarding_completed) setShowOnboarding(false)
              } catch (_) {
                setShowOnboarding(true)
              }
            } else {
              setShowOnboarding(true)
            }
          })
    }, [apiEndpoint])

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
        localStorage.setItem('ingresure_profile', JSON.stringify(toSave))
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('ingresure-profile-updated'))
        }

        const payload = profileToBackend(toSave, uid)
        fetch(`${profileApiBase}/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
          .then(res => res.ok && res.json())
          .then(() => {})
          .catch(err => console.error('Profile save failed:', err))

        const parts: string[] = []
        if (toSave.dietary_preference && toSave.dietary_preference !== 'No rules') parts.push(`Diet: ${toSave.dietary_preference}`)
        if (toSave.allergens?.length || toSave.allergies?.length) parts.push(`Allergens: ${(toSave.allergens ?? toSave.allergies ?? []).join(', ')}`)
        if (toSave.lifestyle?.length || toSave.lifestyle_flags?.length) parts.push(`Lifestyle: ${(toSave.lifestyle ?? toSave.lifestyle_flags ?? []).join(', ')}`)
        setMessages(prev => [...prev, {
            role: 'assistant',
            content: `✅ Profile saved. ${parts.length ? parts.join(' · ') : 'No restrictions set.'} I'll use this for personalized advice.`
        }])
    }

    useEffect(() => {
        const el = messagesRef.current
        if (el) {
            el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
        }
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

            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const chunk = decoder.decode(value, { stream: true })
                buffer += chunk

                // Check for <<<PROFILE_REQUIRED>>> → open single profile dialog
                if (buffer.includes('<<<PROFILE_REQUIRED>>>')) {
                    setShowOnboarding(true)
                    buffer = buffer.replace(/<<<PROFILE_REQUIRED>>>[^]*?(?=<<<PROFILE_UPDATE>>>|$)/g, '').trim()
                    if (!buffer.trim()) buffer = 'Please set your dietary preference, allergens, and lifestyle in the form above so we can give you personalized advice.'
                }

                // Check for profile update protocol: <<<PROFILE_UPDATE>>>{...json...}<<<PROFILE_UPDATE>>>
                const tag = "<<<PROFILE_UPDATE>>>"
                if (buffer.includes(tag)) {
                    const parts: string[] = buffer.split(tag)
                    if (parts.length >= 3) {
                        const jsonStr = parts[1]
                        try {
                            const raw = JSON.parse(jsonStr)
                            const updatedProfile = raw.user_id != null
                              ? backendToProfile(raw)
                              : { ...DEFAULT_PROFILE, ...raw, allergies: raw.allergies ?? raw.allergens ?? [], allergens: raw.allergens ?? raw.allergies ?? [] }
                            updatedProfile.is_onboarding_completed = true
                            // Don't overwrite a filled profile with an empty one (prevents reset to "No rules")
                            const isEmpty = !updatedProfile.dietary_preference || updatedProfile.dietary_preference === 'No rules'
                              && (updatedProfile.allergens?.length ?? 0) === 0
                              && (updatedProfile.lifestyle?.length ?? 0) === 0
                            setProfile(prev => {
                              if (isEmpty && prev.dietary_preference && prev.dietary_preference !== 'No rules') return prev
                              if (isEmpty && ((prev.allergens?.length ?? 0) > 0 || (prev.lifestyle?.length ?? 0) > 0)) return prev
                              return updatedProfile
                            })
                            if (!isEmpty) localStorage.setItem('ingresure_profile', JSON.stringify(updatedProfile))
                            buffer = parts[0] + (parts[2] || '')
                        } catch (e) {
                            console.error('Failed to parse backend profile update', e)
                        }
                    }
                }

                // Check for ingredient audit block: <<<INGREDIENT_AUDIT>>>{...json...}<<<INGREDIENT_AUDIT>>>
                const AUDIT_TAG = '<<<INGREDIENT_AUDIT>>>'
                if (buffer.includes(AUDIT_TAG)) {
                    const parts = buffer.split(AUDIT_TAG)
                    if (parts.length >= 3) {
                        const jsonStr = parts[1]
                        try {
                            const raw = JSON.parse(jsonStr) as any
                            const normalized = normalizeAuditData(raw)
                            setMessages(prev => {
                                const next = [...prev]
                                const last = next[next.length - 1]
                                if (last && last.role === 'assistant') {
                                    last.audit = normalized
                                }
                                return next
                            })
                            buffer = (parts[0] + (parts[2] || '')).trim()
                        } catch (e) {
                            console.error('Failed to parse ingredient audit payload', e)
                        }
                    }
                }

                // Update UI with the CLEAN buffer (strip protocol tags)
                setMessages(prev => {
                    const newMsgs = [...prev]
                    let content = buffer
                        .replace(/<<<PROFILE_UPDATE>>>[\s\S]*?<<<PROFILE_UPDATE>>>/g, '')
                        .replace(/<<<PROFILE_REQUIRED>>>[\s\S]*?(?=<<<PROFILE_UPDATE>>>|$)/g, '')
                        .replace(/<<<INGREDIENT_AUDIT>>>[\s\S]*?<<<INGREDIENT_AUDIT>>>/g, '')
                        .trim()
                    newMsgs[newMsgs.length - 1].content = content || newMsgs[newMsgs.length - 1].content
                    return newMsgs
                })
            }

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

    const hasProfileRules =
        profile.is_onboarding_completed &&
        (profile.dietary_preference && profile.dietary_preference !== 'No rules'
            || (profile.allergies?.length ?? profile.allergens?.length ?? 0) > 0)

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
                editMode={profile.is_onboarding_completed}
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
                                className="inline-flex items-center gap-1.5 rounded-full border font-semibold text-[13px] px-2.5 py-1"
                                style={{ background: '#ecfdf5', borderColor: '#bbf7d0', color: '#065f46' }}
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
                            className="ml-1.5 text-[13px] font-medium cursor-pointer transition-colors hover:underline"
                            style={{ color: '#2563eb' }}
                            aria-label="Edit profile"
                        >
                            Edit
                        </button>
                    </div>
                </div>
            </div>

            {/* Messages (only this section scrolls) */}
            <div
                ref={messagesRef}
                className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 px-6 py-6 space-y-6 scroll-smooth"
            >
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
                    <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-2 duration-300`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full bg-white border border-slate-100 flex items-center justify-center flex-shrink-0 mt-1 shadow-[0_2px_8px_rgba(0,0,0,0.08)]">
                                <Bot className="w-4 h-4 text-slate-600" />
                            </div>
                        )}
                        <div
                            className={`max-w-[80%] sm:max-w-[75%] rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.08)] font-sans ${msg.role === 'user'
                                ? 'bg-[#0F172A] text-white rounded-br-none px-4 py-4'
                                : 'bg-white border border-slate-100 text-[#0F172A] rounded-bl-none px-4 py-4'
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
                            <div className="w-8 h-8 rounded-full bg-[#0F172A] flex items-center justify-center flex-shrink-0 mt-1 shadow-[0_2px_8px_rgba(0,0,0,0.08)]">
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
                        className="w-full px-4 py-3.5 pr-4 bg-slate-50 border border-slate-200 rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.08)] focus:outline-none focus:ring-2 focus:ring-[#10B981]/30 focus:border-[#10B981] transition-all placeholder:text-slate-400 font-sans font-medium text-slate-700"
                        disabled={loading || !profileLoaded}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim() || (!profile.is_onboarding_completed && !profileLoaded)}
                        className="shrink-0 inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-[#0F172A] to-[#10B981] p-3.5 text-white shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all hover:opacity-95 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    </button>
                </div>
            </form>
            <div className="px-4 pb-3 pt-2 bg-white flex justify-center gap-2 flex-wrap shrink-0">
                <button
                    type="button"
                    onClick={() => setInput('')}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-[12px] hover:bg-slate-50 hover:shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all"
                >
                    Clear Input
                </button>
                <button
                    type="button"
                    onClick={() => {
                        const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
                        if (lastUserMsg) setInput(lastUserMsg.content)
                    }}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-[12px] hover:bg-slate-50 hover:shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all"
                >
                    Check Again
                </button>
                <button
                    type="button"
                    onClick={() => setShowOnboarding(true)}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-[12px] hover:bg-slate-50 hover:shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all inline-flex items-center gap-1"
                >
                    Edit Profile
                </button>
            </div>
        </div>
    )

}
