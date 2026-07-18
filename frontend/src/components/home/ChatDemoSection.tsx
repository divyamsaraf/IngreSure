'use client'

import { useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, ArrowRight, CheckCircle2, ChevronDown, XCircle } from 'lucide-react'

const SAFE_INGREDIENTS = ['Sugar', 'Water', 'Citric acid', 'Fruit concentrate', 'Plant fiber'] as const

export default function ChatDemoSection() {
  const [showSafeExpanded, setShowSafeExpanded] = useState(false)

  return (
    <section className="border-y border-slate-200/80 bg-white px-6 py-14 md:py-16">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 lg:flex-row lg:items-start lg:gap-14">
        <div className="flex-1 space-y-4 lg:sticky lg:top-24 lg:max-w-sm">
          <h2 className="font-display text-3xl font-bold tracking-tight text-primary md:text-[2rem]">
            A label, audited like a linter
          </h2>
          <p className="text-[15px] leading-relaxed text-slate-600">
            Avoid and Depends open first. Safe stays collapsed. Names are underlined in the verdict
            color so you scan the risk, not a wall of text.
          </p>
          {/* Soft CTA — not a second primary button */}
          <Link
            href="/chat"
            className="group inline-flex items-center gap-2 pt-1 text-sm font-semibold text-accent underline-offset-4 hover:underline"
          >
            Paste your own label
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </Link>
        </div>

        <div className="flex-1">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/90 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
            {/* One diet + allergens — matches real profile model (single dietary preference) */}
            <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-white px-4 py-3 text-xs">
              <span className="rounded-full border border-teal-200 bg-teal-50 px-3 py-1 font-medium text-teal-900">
                Diet: Vegan
              </span>
              <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 font-medium text-rose-800">
                Allergens: Peanuts
              </span>
            </div>

            <div className="space-y-3 p-4">
              <div className="rounded-xl border border-rose-200 bg-rose-50/90 p-3.5">
                <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-rose-700">
                  <XCircle className="h-3.5 w-3.5" aria-hidden />
                  Avoid · 1
                </p>
                <p className="text-[13px] leading-relaxed text-slate-800">
                  <span className="font-semibold text-rose-800 underline decoration-avoid decoration-2 underline-offset-[3px]">
                    Gelatin
                  </span>{' '}
                  isn&apos;t vegan — usually animal collagen. Prefer agar or plant gels.
                </p>
              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3.5">
                <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-amber-800">
                  <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                  Depends · 1
                </p>
                <p className="text-[13px] leading-relaxed text-slate-800">
                  <span className="font-semibold text-amber-900 underline decoration-depends decoration-2 underline-offset-[3px]">
                    Natural flavor
                  </span>{' '}
                  may include animal sources — we flag it instead of guessing.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowSafeExpanded((v) => !v)}
                className="w-full cursor-pointer rounded-xl border border-emerald-200 bg-white p-3.5 text-left transition-colors hover:bg-emerald-50/40"
                aria-expanded={showSafeExpanded}
              >
                <p className="flex items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-wide text-emerald-800">
                  <span className="inline-flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                    Safe · {SAFE_INGREDIENTS.length}
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 text-emerald-700 transition-transform ${showSafeExpanded ? 'rotate-180' : ''}`}
                    aria-hidden
                  />
                </p>
                <p className="mt-1.5 text-[13px] text-slate-700">
                  {SAFE_INGREDIENTS.slice(0, 3).map((name, i) => (
                    <span key={name}>
                      {i > 0 ? ', ' : ''}
                      <span className="font-medium text-emerald-800 underline decoration-safe decoration-2 underline-offset-[3px]">
                        {name}
                      </span>
                    </span>
                  ))}
                  , and {SAFE_INGREDIENTS.length - 3} more fit this diet.
                </p>
                {showSafeExpanded ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {SAFE_INGREDIENTS.map((item) => (
                      <span
                        key={item}
                        className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-800 underline decoration-safe decoration-2 underline-offset-[2px]"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                ) : null}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
