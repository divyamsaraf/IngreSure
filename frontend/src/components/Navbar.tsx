'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ShieldCheck, CircleUser } from 'lucide-react'
import { useProfileContext } from '@/context/ProfileContext'

export default function Navbar() {
    const pathname = usePathname()
    const isChat = pathname === '/chat' || pathname?.startsWith('/chat')
    const isHome = pathname === '/'
    const { profile, profileLoaded } = useProfileContext()

    const diet =
      profile.dietary_preference && profile.dietary_preference !== 'No rules'
        ? profile.dietary_preference
        : profile.diet && profile.diet !== 'No rules'
          ? profile.diet
          : ''

    const activeClass = 'text-secondary border-b-2 border-secondary'
    const linkClass = 'py-2 px-1 rounded-md transition-colors hover:text-secondary border-b-2 border-transparent'

    return (
        <nav className="bg-white/90 backdrop-blur-sm border-b border-slate-100 py-3 px-4 md:px-6 sticky top-0 z-50 shadow-card">
            <div className="container mx-auto flex items-center justify-between gap-4 max-w-6xl">
                <Link href="/" className="flex items-center gap-2 shrink-0">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-primary to-secondary text-white shadow-card">
                        <ShieldCheck className="w-4 h-4" />
                    </div>
                    <span className="font-serif text-lg font-semibold text-slate-900 tracking-tight">IngreSure</span>
                </Link>

                <div className="flex items-center gap-3 md:gap-6 font-medium text-slate-600">
                    <Link
                        href="/chat"
                        className={`md:hidden py-2 px-2 rounded-md border-b-2 border-transparent transition-colors hover:text-secondary ${isChat ? activeClass : ''}`}
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
                        className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-2 py-1.5 text-slate-600 shadow-card transition-all hover:bg-slate-50 hover:border-slate-300 hover:shadow-md"
                        aria-label="Open profile"
                    >
                        <CircleUser className="w-5 h-5 shrink-0" />
                        {profileLoaded && diet ? (
                            <span className="hidden sm:inline text-sm font-medium text-slate-700 max-w-[80px] truncate">
                                {diet}
                            </span>
                        ) : null}
                    </Link>
                    <Link
                        href="/chat?openProfile=1"
                        className="hidden sm:inline-flex items-center justify-center px-3 py-1.5 rounded-full text-xs font-medium text-white bg-gradient-to-r from-primary to-secondary shadow-card transition-all hover:opacity-95 hover:shadow-md"
                    >
                        Edit Profile
                    </Link>
                </div>
            </div>
        </nav>
    )
}
