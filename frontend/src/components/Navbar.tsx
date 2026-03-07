'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ShieldCheck, CircleUser } from 'lucide-react'

const PROFILE_STORAGE_KEY = 'ingresure_profile'
const PROFILE_UPDATED_EVENT = 'ingresure-profile-updated'

function getProfileLabel(): string {
    if (typeof window === 'undefined') return ''
    try {
        const raw = localStorage.getItem(PROFILE_STORAGE_KEY)
        if (!raw) return ''
        const p = JSON.parse(raw)
        const diet = p?.dietary_preference ?? p?.diet
        if (diet && diet !== 'No rules') return diet
        return ''
    } catch {
        return ''
    }
}

export default function Navbar() {
    const pathname = usePathname()
    const isChat = pathname === '/chat' || pathname?.startsWith('/chat')
    const isHome = pathname === '/'
    const [profileLabel, setProfileLabel] = useState('')

    useEffect(() => {
        setProfileLabel(getProfileLabel())
        const onUpdate = () => setProfileLabel(getProfileLabel())
        window.addEventListener(PROFILE_UPDATED_EVENT, onUpdate)
        return () => window.removeEventListener(PROFILE_UPDATED_EVENT, onUpdate)
    }, [])

    const activeClass = 'text-[#10B981] border-b-2 border-[#10B981]'
    const linkClass = 'py-2 px-1 rounded-md transition-colors hover:text-[#10B981] border-b-2 border-transparent'

    return (
        <nav className="bg-white/90 backdrop-blur-sm border-b border-slate-100 py-3 px-4 md:px-6 sticky top-0 z-50 shadow-[0_2px_8px_rgba(0,0,0,0.08)]">
            <div className="container mx-auto flex items-center justify-between gap-4 max-w-6xl">
                <Link href="/" className="flex items-center gap-2 shrink-0">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-[#0F172A] to-[#10B981] text-white shadow-[0_2px_8px_rgba(0,0,0,0.08)]">
                        <ShieldCheck className="w-4 h-4" />
                    </div>
                    <span className="font-serif text-lg font-semibold text-slate-900 tracking-tight">IngreSure</span>
                </Link>

                <div className="flex items-center gap-3 md:gap-6 font-medium text-slate-600">
                    <Link
                        href="/chat"
                        className={`md:hidden py-2 px-2 rounded-md border-b-2 border-transparent transition-colors hover:text-[#10B981] ${isChat ? activeClass : ''}`}
                    >
                        Grocery Assistant
                    </Link>
                    <div className="hidden md:flex items-center gap-6 font-medium text-slate-600">
                        <Link
                            href="/"
                            className={`${linkClass} ${isHome ? activeClass : ''}`}
                        >
                            Home
                        </Link>
                        <span className="text-slate-300" aria-hidden>|</span>
                        <Link
                            href="/chat"
                            className={`${linkClass} ${isChat ? activeClass : ''}`}
                        >
                            Grocery Assistant
                        </Link>
                    </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                    <Link
                        href="/chat?openProfile=1"
                        className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-2 py-1.5 text-slate-600 shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all hover:bg-slate-50 hover:border-slate-300 hover:shadow-md"
                        aria-label="Open profile"
                    >
                        <CircleUser className="w-5 h-5 shrink-0" />
                        {profileLabel ? (
                            <span className="hidden sm:inline text-sm font-medium text-slate-700 max-w-[80px] truncate">
                                {profileLabel}
                            </span>
                        ) : null}
                    </Link>
                    <Link
                        href="/chat?openProfile=1"
                        className="hidden sm:inline-flex items-center justify-center px-3 py-1.5 rounded-full text-xs font-medium text-white bg-gradient-to-r from-[#0F172A] to-[#10B981] shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-all hover:opacity-95 hover:shadow-md"
                    >
                        Edit Profile
                    </Link>
                </div>
            </div>
        </nav>
    )
}
