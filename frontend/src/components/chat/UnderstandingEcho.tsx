'use client'

import type { UnderstandingEcho as UnderstandingEchoData } from '@/lib/chatContract'

interface UnderstandingEchoProps {
  echo: UnderstandingEchoData
}

export default function UnderstandingEcho({ echo }: UnderstandingEchoProps) {
  const rows: { label: string; value: string }[] = []
  if (echo.understood) rows.push({ label: 'I understood', value: echo.understood })
  if (echo.unused) rows.push({ label: 'I could not use', value: echo.unused })
  if (echo.checkingAgainst) rows.push({ label: 'Checking against', value: echo.checkingAgainst })

  if (!echo.preface && rows.length === 0) return null

  return (
    <div
      data-testid="understanding-echo"
      className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-[13px] leading-snug text-slate-700"
    >
      {echo.preface ? <p className="mb-1.5 font-medium text-slate-800">{echo.preface}</p> : null}
      {rows.map((row) => (
        <p key={row.label}>
          <span className="font-semibold text-slate-800">{row.label}:</span> {row.value}
        </p>
      ))}
    </div>
  )
}
