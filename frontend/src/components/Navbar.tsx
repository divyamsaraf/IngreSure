'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, ShieldCheck, X } from 'lucide-react'
import { useProfileContext } from '@/context/ProfileContext'
import { useConfig } from '@/context/ConfigContext'
import { getDietIcon } from '@/lib/dietIcon'

const navItems = [
  { href: '/', label: 'Home', match: (p: string) => p === '/' },
  { href: '/chat', label: 'Grocery Assistant', match: (p: string) => p === '/chat' || p.startsWith('/chat') },
  { href: '/about', label: 'About', match: (p: string) => p === '/about' || p.startsWith('/about') },
  { href: '/faq', label: 'FAQ', match: (p: string) => p === '/faq' || p.startsWith('/faq') },
  { href: '/for-business', label: 'For Business', match: (p: string) => p === '/for-business' || p.startsWith('/for-business') },
] as const

export default function Navbar() {
  const pathname = usePathname() ?? '/'
  const { profile, profileLoaded } = useProfileContext()
  const config = useConfig()
  const dietIconMap = config.profile_options.diet_icon ?? {}
  const [menuOpen, setMenuOpen] = useState(false)

  const hasDiet = Boolean(profile.dietary_preference && profile.dietary_preference !== 'No rules')

  const activeClass = 'text-accent border-b-2 border-accent'
  const linkClass =
    'cursor-pointer py-2 px-1 rounded-md transition-colors duration-200 hover:text-accent border-b-2 border-transparent'

  const profileAria = hasDiet
    ? `Profile: ${profile.dietary_preference}. Open to edit`
    : 'Set up your safety profile'

  useEffect(() => {
    setMenuOpen(false)
  }, [pathname])

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200/80 bg-surface/90 py-3 px-4 shadow-card backdrop-blur-md md:px-6">
      <div className="container mx-auto flex max-w-6xl items-center justify-between gap-4">
        <div className="flex min-w-0 shrink-0 items-center gap-3">
          <Link href="/" className="flex shrink-0 cursor-pointer items-center gap-2">
            <div className="rounded-lg bg-gradient-to-br from-primary to-accent p-1.5 text-white shadow-card">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <span className="font-display text-lg font-semibold tracking-tight text-slate-900">
              IngreSure
            </span>
          </Link>
          <Link
            href="/for-business"
            className="hidden cursor-pointer items-center rounded-full border border-accent/25 bg-teal-50 px-2.5 py-0.5 text-[11px] font-semibold text-accent transition-colors duration-200 hover:bg-teal-100/80 sm:inline-flex"
          >
            Onboarding early B2B partners
          </Link>
        </div>

        <div className="hidden items-center gap-5 font-medium text-slate-600 md:flex">
          {navItems.map((item, i) => (
            <React.Fragment key={item.href}>
              {i > 0 ? <span className="text-slate-300" aria-hidden>|</span> : null}
              <Link
                href={item.href}
                className={`${linkClass} ${item.match(pathname) ? activeClass : ''}`}
              >
                {item.label}
              </Link>
            </React.Fragment>
          ))}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <Link
            href="/chat?openProfile=1"
            className="group flex max-w-[min(100vw-8rem,20rem)] cursor-pointer items-center gap-1.5 rounded-xl border border-transparent px-1 py-1 transition-colors duration-200 hover:border-slate-200 hover:bg-white/70 sm:max-w-none"
            aria-label={profileAria}
          >
            {!profileLoaded ? (
              <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[13px] text-slate-500">
                <span className="h-2 w-2 animate-pulse rounded-full bg-slate-300" aria-hidden />
                Profile…
              </span>
            ) : hasDiet ? (
              <>
                <span
                  className="inline-flex min-w-0 max-w-[9rem] items-center gap-1.5 truncate rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 text-[13px] font-semibold text-teal-900 sm:max-w-[14rem]"
                  title="Active diet profile"
                >
                  <span className="shrink-0" aria-hidden>
                    {getDietIcon(dietIconMap, profile.dietary_preference)}
                  </span>
                  <span className="truncate">{profile.dietary_preference}</span>
                </span>
                <span className="shrink-0 text-[13px] font-medium text-accent group-hover:underline">
                  Edit
                </span>
              </>
            ) : (
              <>
                <span className="whitespace-nowrap text-[13px] text-slate-500">No diet set</span>
                <span className="text-[13px] font-medium text-accent group-hover:underline">Set up</span>
              </>
            )}
          </Link>

          <button
            type="button"
            className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition-colors duration-200 hover:border-accent/30 hover:text-accent md:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen((v) => !v)}
          >
            {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {menuOpen ? (
        <div
          id="mobile-nav"
          className="mt-3 border-t border-slate-200/80 pt-3 md:hidden"
          role="navigation"
          aria-label="Mobile"
        >
          <ul className="flex flex-col gap-1">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`block cursor-pointer rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-200 ${
                    item.match(pathname)
                      ? 'bg-teal-50 text-accent'
                      : 'text-slate-700 hover:bg-white hover:text-accent'
                  }`}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </nav>
  )
}
