'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

export interface FaqItem {
  question: string
  answer: string
}

interface FaqAccordionProps {
  items: FaqItem[]
}

export default function FaqAccordion({ items }: FaqAccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <div className="divide-y divide-slate-200/90 overflow-hidden rounded-xl border border-slate-200/80 bg-surface/40">
      {items.map((item, index) => {
        const isOpen = openIndex === index
        return (
          <div key={item.question} className={isOpen ? 'bg-white' : undefined}>
            <button
              type="button"
              className="flex w-full cursor-pointer items-start justify-between gap-4 px-5 py-[1.125rem] text-left transition-colors duration-200 hover:bg-surface/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent/30 sm:px-6"
              aria-expanded={isOpen}
              onClick={() => setOpenIndex(isOpen ? null : index)}
            >
              <span className="text-[15px] font-semibold leading-snug tracking-tight text-primary md:text-base">
                {item.question}
              </span>
              <ChevronDown
                className={`mt-0.5 h-5 w-5 shrink-0 text-accent/60 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                aria-hidden
              />
            </button>
            {isOpen ? (
              <div className="px-5 pb-5 text-[15px] leading-[1.65] text-slate-600 sm:px-6 sm:pb-6 md:text-base md:leading-[1.7]">
                {item.answer}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
