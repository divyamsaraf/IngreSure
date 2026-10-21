'use client'

import { Phone } from 'lucide-react'
import {
  EMERGENCY_BY_REGION,
  GENERIC_EMERGENCY_NUMBERS,
  emergencyNumberForRegion,
} from '@/lib/chatContract'

interface EmergencyBlockProps {
  region: string | null
}

export default function EmergencyBlock({ region }: EmergencyBlockProps) {
  const number = emergencyNumberForRegion(region)
  const label = region ? EMERGENCY_BY_REGION[region]?.label : null

  return (
    <div
      role="alert"
      data-testid="emergency-block"
      className="rounded-2xl border-2 border-rose-600 bg-rose-50 px-4 py-4 text-rose-950 shadow-card"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-rose-600 text-white">
          <Phone className="h-5 w-5" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rose-700">
            Stop — medical emergency
          </p>
          {number ? (
            <>
              <p className="mt-1 font-display text-3xl font-semibold tabular-nums tracking-tight">
                Call {number}
              </p>
              <p className="mt-1 text-sm font-medium text-rose-800">
                {label ? `${label} emergency number` : 'Local emergency number'}
                . Or call your local emergency number.
              </p>
            </>
          ) : (
            <>
              <p className="mt-1 font-display text-xl font-semibold tracking-tight">
                Call your local emergency number now
              </p>
              <ul
                className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-sm font-semibold"
                data-testid="emergency-generic-list"
              >
                {GENERIC_EMERGENCY_NUMBERS.map((row) => (
                  <li key={`${row.number}-${row.place}`}>
                    <span className="tabular-nums">{row.number}</span>
                    <span className="ml-1 font-medium text-rose-800">({row.place})</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          <p className="mt-3 text-sm leading-snug text-rose-900">
            Stop using this app. I am not emergency services and I will not evaluate ingredients
            while you may need urgent care.
          </p>
        </div>
      </div>
    </div>
  )
}
