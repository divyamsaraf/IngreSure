'use client'

import React, { useState } from 'react'
import { ChevronDown } from 'lucide-react'

interface RecentChecksSectionProps {
  queries: string[]
  onSelect: (q: string) => void
}

export default function RecentChecksSection({ queries, onSelect }: RecentChecksSectionProps) {
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
              className="text-[11px] bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-full hover:border-emerald-300 hover:text-emerald-700 hover:bg-emerald-50/60 hover:shadow-card transition-all"
            >
              {q.length > 60 ? q.slice(0, 57) + '…' : q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
