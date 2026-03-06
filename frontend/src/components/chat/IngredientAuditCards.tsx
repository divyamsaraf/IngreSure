'use client'

import React, { useState } from 'react'
import { CheckCircle2, AlertTriangle, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import FormattedMessage from './FormattedMessage'

export type IngredientStatus = 'safe' | 'avoid' | 'depends'

export interface IngredientAuditItem {
  name: string
  status: IngredientStatus
  allergens?: string[]
  alternatives?: string[]
}

export interface IngredientAuditGroup {
  status: IngredientStatus
  items: IngredientAuditItem[]
}

export interface IngredientAuditData {
  summary: string
  groups: IngredientAuditGroup[]
  explanation?: string
}

interface Props {
  data: IngredientAuditData
}

const STATUS_LABEL: Record<IngredientStatus, string> = {
  safe: 'Safe',
  avoid: 'Avoid',
  depends: 'Depends',
}

const STATUS_ICON: Record<IngredientStatus, React.ReactNode> = {
  safe: <CheckCircle2 className="h-3.5 w-3.5" />,
  avoid: <XCircle className="h-3.5 w-3.5" />,
  depends: <AlertTriangle className="h-3.5 w-3.5" />,
}

const STATUS_COLORS: Record<
  IngredientStatus,
  { pill: string; text: string; card: string }
> = {
  safe: {
    pill: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    text: 'text-emerald-700',
    card: 'from-emerald-50 to-emerald-100',
  },
  avoid: {
    pill: 'bg-rose-100 text-rose-800 border-rose-200',
    text: 'text-rose-700',
    card: 'from-rose-50 to-rose-100',
  },
  depends: {
    pill: 'bg-amber-100 text-amber-800 border-amber-200',
    text: 'text-amber-700',
    card: 'from-amber-50 to-amber-100',
  },
}

function severityRank(status: IngredientStatus): number {
  if (status === 'avoid') return 3
  if (status === 'depends') return 2
  return 1 // safe
}

export default function IngredientAuditCards({ data }: Props) {
  const [openGroups, setOpenGroups] = useState<Record<IngredientStatus, boolean>>({
    avoid: true,
    depends: true,
    safe: false,
  })
  const [showFullExplanation, setShowFullExplanation] = useState(false)

  const allStatuses = data.groups.map((g) => g.status)
  const worstStatus =
    allStatuses.length === 0
      ? 'safe'
      : allStatuses.reduce<IngredientStatus>((worst, current) =>
          severityRank(current) > severityRank(worst) ? current : worst,
        )

  const summaryColor = STATUS_COLORS[worstStatus].text

  // Ensure consistent order: Avoid → Depends → Safe
  const orderedGroups: IngredientAuditGroup[] = ['avoid', 'depends', 'safe']
    .map((status) => data.groups.find((g) => g.status === status as IngredientStatus))
    .filter(Boolean) as IngredientAuditGroup[]

  const toggleGroup = (status: IngredientStatus) => {
    setOpenGroups((prev) => ({ ...prev, [status]: !prev[status] }))
  }

  return (
    <div className="space-y-3">
      {/* Summary line */}
      {data.summary && (
        <p className={`text-sm font-semibold ${summaryColor}`}>
          {data.summary}
        </p>
      )}

      {/* Groups */}
      <div className="space-y-3">
        {orderedGroups.map((group) => {
          const status = group.status
          const colors = STATUS_COLORS[status]
          const count = group.items.length
          if (count === 0) return null

          return (
            <div
              key={status}
              className="rounded-2xl border border-slate-100 bg-[#F8FAFC] p-3 shadow-sm"
            >
              <button
                type="button"
                onClick={() => toggleGroup(status)}
                className="flex w-full items-center justify-between gap-2"
              >
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-[11px] font-medium ${colors.pill}`}
                >
                  {STATUS_ICON[status]}
                  <span>{STATUS_LABEL[status]}</span>
                  <span className="text-[10px] opacity-80">· {count}</span>
                </span>
                <span className="text-[11px] text-slate-500 flex items-center gap-1">
                  {openGroups[status] ? 'Hide' : 'Show'}
                  {openGroups[status] ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </span>
              </button>

              {openGroups[status] && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {group.items.map((item) => (
                    <div
                      key={item.name}
                      className={`inline-flex flex-col gap-1 rounded-2xl bg-gradient-to-br ${colors.card} px-3 py-2 text-[11px] text-slate-800 shadow-sm`}
                    >
                      <span className="font-semibold text-[12px]">
                        {item.name}
                      </span>
                      {item.allergens && item.allergens.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {item.allergens.map((alg) => (
                            <span
                              key={alg}
                              className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-medium text-rose-700"
                              title={`Contains allergen: ${alg}`}
                            >
                              <XCircle className="h-3 w-3" />
                              {alg}
                            </span>
                          ))}
                        </div>
                      )}
                      {item.alternatives && item.alternatives.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {item.alternatives.map((alt) => (
                            <button
                              key={alt}
                              type="button"
                              className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-800 hover:bg-emerald-200"
                              title={`Use ${alt} as a safer alternative`}
                              onClick={() => {
                                if (navigator?.clipboard?.writeText) {
                                  navigator.clipboard.writeText(alt).catch(() => {})
                                }
                              }}
                            >
                              {alt}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Residual explanation */}
      {data.explanation && (
        <div className="pt-1 text-[12px] text-slate-600">
          {data.explanation.length > 220 ? (
            <>
              <FormattedMessage
                content={
                  showFullExplanation
                    ? data.explanation
                    : data.explanation.slice(0, 220).trimEnd() + '…'
                }
              />
              <button
                type="button"
                onClick={() => setShowFullExplanation((v) => !v)}
                className="mt-1 text-[11px] font-medium text-blue-600 hover:text-blue-700"
              >
                {showFullExplanation ? 'Show less' : 'Read more'}
              </button>
            </>
          ) : (
            <FormattedMessage content={data.explanation} />
          )}
        </div>
      )}
    </div>
  )
}

