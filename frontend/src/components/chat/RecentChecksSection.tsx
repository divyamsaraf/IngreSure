'use client'

import React, { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { RecentCheckEntry, RecentCheckVerdict } from '@/lib/profileStorage'
import { statusColors } from '@/theme/tokens'

interface RecentChecksSectionProps {
  entries: RecentCheckEntry[]
  onSelect: (q: string) => void
}

const VERDICT_BADGE: Record<RecentCheckVerdict, string> = {
  safe: '✓ Safe',
  avoid: '✗ Avoid',
  depends: '⚠ Warning',
}

export default function RecentChecksSection({ entries, onSelect }: RecentChecksSectionProps) {
  const [open, setOpen] = useState(true)
  return (
    <div className="px-4 pb-1 pt-2 bg-white border-t border-slate-100">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 w-full text-left py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50 rounded"
        aria-expanded={open}
      >
        <span className="text-chat-meta font-medium text-slate-500">
          Recent checks:
        </span>
        <span className="text-chat-meta text-slate-400">
          {entries.length} {entries.length === 1 ? 'query' : 'queries'}
        </span>
        <span className={`ml-auto inline-block transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </span>
      </button>
      {open && (
        <div className="flex flex-wrap gap-2 pt-1 pb-2 animate-in fade-in slide-in-from-top-1 duration-200">
          {entries.map((entry) => (
            <button
              key={entry.query}
              type="button"
              onClick={() => onSelect(entry.query)}
              className="inline-flex items-center gap-1.5 text-chat-recent font-normal bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-full hover:border-emerald-300 hover:text-emerald-700 hover:bg-emerald-50/60 hover:shadow-card transition-all"
            >
              {entry.verdict ? (
                <span
                  className={`shrink-0 inline-flex items-center rounded-full px-1.5 py-0.5 text-chat-meta leading-none font-semibold ${statusColors[entry.verdict].pill}`}
                >
                  {VERDICT_BADGE[entry.verdict]}
                </span>
              ) : null}
              <span>{entry.query.length > 60 ? entry.query.slice(0, 57) + '…' : entry.query}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
