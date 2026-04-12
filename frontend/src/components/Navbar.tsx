'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ShieldCheck } from 'lucide-react'
import { useProfileContext } from '@/context/ProfileContext'
import { useConfig } from '@/context/ConfigContext'
import { getDietIcon } from '@/lib/dietIcon'

export default function Navbar() {
    const pathname = usePathname()
    const isChat = pathname === '/chat' || pathname?.startsWith('/chat')
    const isHome = pathname === '/'
    const { profile, profileLoaded } = useProfileContext()
    const config = useConfig()
    const dietIconMap = config.profile_options.diet_icon ?? {}

    const hasDiet =
        Boolean(profile.dietary_preference && profile.dietary_preference !== 'No rules')

    const activeClass = 'text-secondary border-b-2 border-secondary'
    const linkClass = 'py-2 px-1 rounded-md transition-colors hover:text-secondary border-b-2 border-transparent'

    const profileAria = hasDiet
        ? `Profile: ${profile.dietary_preference}. Open to edit`
        : 'Set up your safety profile'

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

                <div className="flex items-center shrink-0">
                    <Link
                        href="/chat?openProfile=1"
                        className="group flex max-w-[min(100vw-8rem,20rem)] items-center gap-1.5 rounded-xl border border-transparent px-1 py-1 transition-colors hover:border-slate-200 hover:bg-slate-50/80 sm:max-w-none"
                        aria-label={profileAria}
                    >
                        {!profileLoaded ? (
                            <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[13px] text-slate-500">
                                <span className="h-2 w-2 animate-pulse rounded-full bg-slate-300" aria-hidden />
                                Profile…
                            </span>
                        ) : hasDiet ? (
                            <>
                                <span
                                    className="inline-flex min-w-0 max-w-[11rem] items-center gap-1.5 truncate rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[13px] font-semibold text-emerald-800 sm:max-w-[14rem]"
                                    title="Active diet profile"
                                >
                                    <span className="shrink-0" aria-hidden>
                                        {getDietIcon(dietIconMap, profile.dietary_preference)}
                                    </span>
                                    <span className="truncate">{profile.dietary_preference}</span>
                                </span>
                                <span className="shrink-0 text-[13px] font-medium text-blue-600 group-hover:underline">
                                    Edit
                                </span>
                            </>
                        ) : (
                            <>
                                <span className="whitespace-nowrap text-[13px] text-slate-500">No diet set</span>
                                <span className="text-[13px] font-medium text-blue-600 group-hover:underline">
                                    Set up
                                </span>
                            </>
                        )}
                    </Link>
                </div>
            </div>
        </nav>
    )
}
