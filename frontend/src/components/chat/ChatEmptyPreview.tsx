'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle2, ChevronDown, XCircle } from 'lucide-react'

/**
 * Compact, expandable example for the chat empty state.
 * Teaches the product in one glance without a fake full conversation.
 */
export default function ChatEmptyPreview({ onTryExample }: { onTryExample: () => void }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="mt-8 w-full max-w-lg text-left">
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full cursor-pointer items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/80 px-4 py-3 text-left transition-colors hover:bg-slate-50"
          aria-expanded={open}
        >
          <div>
            <p className="text-sm font-semibold text-primary">See what a check looks like</p>
            <p className="mt-0.5 text-xs text-slate-500">
              Example · vegan profile · gelatin flagged
            </p>
          </div>
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
            aria-hidden
          />
        </button>

        {open ? (
          <div className="space-y-2.5 p-4">
            <p className="rounded-xl bg-primary/95 px-3 py-2 text-[12px] leading-snug text-white">
              Ingredients: Sugar, Gelatin, Citric Acid, Natural Flavors
            </p>

            <div className="flex flex-wrap gap-1.5">
              <span className="inline-flex items-center gap-1 rounded-full bg-avoid px-2.5 py-1 text-[11px] font-semibold text-white">
                <XCircle className="h-3 w-3" aria-hidden />
                Avoid 1
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-depends px-2.5 py-1 text-[11px] font-semibold text-white">
                <AlertTriangle className="h-3 w-3" aria-hidden />
                Depends 1
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-safe px-2.5 py-1 text-[11px] font-semibold text-white">
                <CheckCircle2 className="h-3 w-3" aria-hidden />
                Safe 2
              </span>
            </div>

            <div className="rounded-xl border border-rose-200 bg-rose-50/90 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-700">
                Avoid
              </p>
              <p className="mt-1 text-[13px] leading-relaxed text-slate-800">
                <span className="font-semibold text-rose-800 underline decoration-avoid decoration-2 underline-offset-[3px]">
                  Gelatin
                </span>{' '}
                is animal-derived — not vegan. Prefer agar or plant gels.
              </p>
            </div>

            <p className="text-[12px] leading-relaxed text-slate-600">
              Safe names stay quiet until you open them. Depends means we refuse to guess.
            </p>

            <button
              type="button"
              onClick={onTryExample}
              className="w-full cursor-pointer rounded-xl bg-gradient-to-r from-primary to-accent px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-95"
            >
              Try this example yourself
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
