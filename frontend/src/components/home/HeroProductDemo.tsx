'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, CheckCircle2, Loader2, XCircle } from 'lucide-react'

type Phase = 'paste' | 'scanning' | 'avoid' | 'depends' | 'safe' | 'hold'

const PHASE_MS: Record<Phase, number> = {
  paste: 900,
  scanning: 850,
  avoid: 1100,
  depends: 1100,
  safe: 1200,
  hold: 3600,
}

const ORDER: Phase[] = ['paste', 'scanning', 'avoid', 'depends', 'safe', 'hold']

/**
 * Autoplaying product demo for the hero — timed flow beats a static screenshot.
 * Respects prefers-reduced-motion (jumps to final state).
 */
export default function HeroProductDemo() {
  const [phase, setPhase] = useState<Phase>('paste')
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const apply = () => {
      setReduced(mq.matches)
      if (mq.matches) setPhase('hold')
    }
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  useEffect(() => {
    if (reduced) return
    const t = window.setTimeout(() => {
      const i = ORDER.indexOf(phase)
      setPhase(ORDER[(i + 1) % ORDER.length])
    }, PHASE_MS[phase])
    return () => window.clearTimeout(t)
  }, [phase, reduced])

  const showAvoid = phase === 'avoid' || phase === 'depends' || phase === 'safe' || phase === 'hold'
  const showDepends = phase === 'depends' || phase === 'safe' || phase === 'hold'
  const showSafe = phase === 'safe' || phase === 'hold'

  return (
    <Link
      href="/chat"
      className="group block cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
      aria-label="Open IngreSure chat — watch the demo, then try it yourself"
    >
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)] transition-shadow duration-300 group-hover:shadow-[0_28px_90px_rgba(15,118,110,0.14)] md:rounded-tl-[1.75rem]">
        {/* Chrome */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/90 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-slate-300" aria-hidden />
            <span className="h-2 w-2 rounded-full bg-slate-300" aria-hidden />
            <span className="h-2 w-2 rounded-full bg-slate-300" aria-hidden />
            <span className="ml-2 text-[11px] font-medium text-slate-500">Grocery Assistant</span>
          </div>
          <span className="rounded-full border border-teal-200 bg-teal-50 px-2.5 py-0.5 text-[11px] font-semibold text-teal-900">
            Diet: Vegan
          </span>
        </div>

        <div className="space-y-3 p-4 md:p-5" aria-live="polite">
          {/* User paste bubble */}
          <div
            className={`ml-auto max-w-[92%] rounded-2xl rounded-br-md bg-primary px-3.5 py-2.5 text-[13px] leading-snug text-white transition-all duration-500 ${
              phase === 'paste' ? 'opacity-100 translate-y-0' : 'opacity-90'
            }`}
          >
            Ingredients: Sugar, Gelatin, Citric Acid, Natural Flavors, Carnauba Wax
          </div>

          {/* Scanning */}
          {(phase === 'scanning' || (phase !== 'paste' && !showAvoid)) && (
            <div className="flex items-center gap-2 text-[12px] font-medium text-slate-500">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" aria-hidden />
              Checking against your vegan rules…
            </div>
          )}

          {phase === 'scanning' && !showAvoid ? (
            <div className="h-24 rounded-xl border border-dashed border-slate-200 bg-slate-50/80" />
          ) : null}

          {/* Avoid */}
          <div
            className={`overflow-hidden transition-all duration-500 ease-out ${
              showAvoid ? 'max-h-40 opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="rounded-xl border border-rose-200 bg-rose-50/90 p-3">
              <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-rose-700">
                <XCircle className="h-3.5 w-3.5" aria-hidden />
                Avoid · 1
              </p>
              <p className="text-[13px] leading-relaxed text-slate-800">
                <span className="font-semibold text-rose-800 underline decoration-avoid decoration-2 underline-offset-[3px]">
                  Gelatin
                </span>{' '}
                — animal collagen. Not vegan.
              </p>
            </div>
          </div>

          {/* Depends */}
          <div
            className={`overflow-hidden transition-all duration-500 ease-out ${
              showDepends ? 'max-h-40 opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3">
              <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-amber-800">
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                Depends · 1
              </p>
              <p className="text-[13px] leading-relaxed text-slate-800">
                <span className="font-semibold text-amber-900 underline decoration-depends decoration-2 underline-offset-[3px]">
                  Natural Flavors
                </span>{' '}
                — source unclear; we flag, not guess.
              </p>
            </div>
          </div>

          {/* Safe */}
          <div
            className={`overflow-hidden transition-all duration-500 ease-out ${
              showSafe ? 'max-h-24 opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="rounded-xl border border-emerald-200 bg-white p-3">
              <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-800">
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                Safe · 3 ingredients
              </p>
              <p className="mt-1 text-[12px] text-slate-600">
                <span className="font-medium text-emerald-800 underline decoration-safe decoration-2 underline-offset-[2px]">
                  Sugar
                </span>
                ,{' '}
                <span className="font-medium text-emerald-800 underline decoration-safe decoration-2 underline-offset-[2px]">
                  Citric Acid
                </span>
                ,{' '}
                <span className="font-medium text-emerald-800 underline decoration-safe decoration-2 underline-offset-[2px]">
                  Carnauba Wax
                </span>
              </p>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 bg-slate-50/80 px-4 py-2.5 text-center text-[11px] font-medium text-slate-500 transition-colors group-hover:text-accent">
          Click to try with your own label →
        </div>
      </div>
    </Link>
  )
}
