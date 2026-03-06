'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, CheckCircle } from 'lucide-react'

export default function ChatDemoSection() {
  const [showSafeExpanded, setShowSafeExpanded] = useState(false)

  return (
    <section className="border-y border-slate-100 bg-white/80 px-6 py-16 md:py-20">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 md:flex-row md:items-center">
        <div className="flex-1 space-y-4">
          <h3 className="font-serif text-2xl font-bold text-slate-900 md:text-3xl">
            See how IngreSure reads your label
          </h3>
          <p className="text-sm text-slate-600 md:text-base">
            We break your ingredient list into human language verdicts. Unsafe ingredients are
            expanded first, while safe ones stay neatly grouped so you&apos;re never overwhelmed.
          </p>
          <ul className="space-y-2 text-sm text-slate-600">
            <li>• Collapsible ingredient verdicts with clear red / amber / green states.</li>
            <li>• Profile pills show exactly which diet and allergies we considered.</li>
            <li>• One tap to move from this preview into the full chat experience.</li>
          </ul>

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 rounded-[16px] bg-gradient-to-r from-emerald-500 to-lime-400 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-500/30 transition-transform transition-shadow hover:-translate-y-0.5 hover:shadow-emerald-500/50 active:translate-y-0"
            >
              Start Your Audit – Chat Now
              <ArrowRight className="h-4 w-4" />
            </Link>
            <p className="text-xs text-slate-500">
              Mobile-friendly • No login • Personalized in under 30 seconds
            </p>
          </div>
        </div>

        {/* Scrollable demo column */}
        <div className="flex-1">
          <div className="overflow-hidden rounded-3xl border border-slate-100 bg-slate-50/80 shadow-[0_18px_60px_rgba(15,23,42,0.09)]">
            <div className="flex gap-2 border-b border-slate-100 bg-white/70 px-4 py-3 text-xs text-slate-500">
              <span className="rounded-full bg-emerald-50 px-3 py-1 font-medium text-emerald-700">
                Example profile: Vegan · Halal
              </span>
              <span className="rounded-full bg-rose-50 px-3 py-1 font-medium text-rose-700">
                Allergens: Peanuts
              </span>
            </div>

            <div className="flex snap-x gap-4 overflow-x-auto px-4 py-4 md:flex-col md:overflow-visible">
              {/* Unsafe card */}
              <div className="min-w-[260px] snap-start rounded-2xl border border-rose-100 bg-rose-50/80 p-3 text-[12px] shadow-sm md:min-w-0">
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-rose-600">
                  ❌ Unsafe for your profile
                </p>
                <p className="text-[11px] text-slate-800">
                  This ingredient list contains <span className="font-semibold">Gelatin</span>,
                  which is not allowed for vegan or Jain diets and may be derived from pork or beef.
                </p>
                <p className="mt-2 text-[11px] text-slate-800">
                  We recommend products that use <span className="font-semibold">agar</span> or{' '}
                  <span className="font-semibold">plant-based gelling agents</span> instead.
                </p>
              </div>

              {/* Depends card */}
              <div className="min-w-[260px] snap-start rounded-2xl border border-amber-100 bg-amber-50/70 p-3 text-[12px] shadow-sm md:min-w-0">
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                  ⚠ Depends on your rules
                </p>
                <p className="text-[11px] text-slate-800">
                  <span className="font-semibold">Natural flavor</span> can sometimes include
                  animal-derived ingredients. We flag this for extra review, but don&apos;t mark it
                  unsafe by default.
                </p>
              </div>

              {/* Safe ingredients card (collapsible) */}
              <button
                type="button"
                onClick={() => setShowSafeExpanded((v) => !v)}
                className="min-w-[260px] snap-start rounded-2xl border border-emerald-100 bg-white p-3 text-left text-[12px] shadow-sm md:min-w-0"
              >
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
                  ✅ 5 ingredients fully safe
                </p>
                <p className="text-[11px] text-slate-800">
                  Sugar, Water, Citric acid, Fruit concentrate, and Plant fiber all comply with your
                  profile.
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    {showSafeExpanded ? 'Hide ingredient list' : 'Show ingredient list'}
                  </span>
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
                </div>
                {showSafeExpanded && (
                  <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-slate-700">
                    {['Sugar', 'Water', 'Citric acid', 'Natural flavor', 'Fruit concentrate'].map(
                      (item) => (
                        <span
                          key={item}
                          className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700"
                        >
                          {item}
                        </span>
                      ),
                    )}
                  </div>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

