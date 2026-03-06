'use client'

import React, { useRef, useState } from 'react'
import { CheckCircle2, AlertTriangle, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import FormattedMessage from './FormattedMessage'
import { statusColors } from '@/theme/tokens'
import { StatusPill } from '@/components/ui/Pill'

export type IngredientStatus = 'safe' | 'avoid' | 'depends'

export interface IngredientAuditItem {
  name: string
  status: IngredientStatus
  diets?: string[]
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
  const [expandedItems, setExpandedItems] = useState<Record<IngredientStatus, boolean>>({
    avoid: false,
    depends: false,
    safe: false,
  })
  const [showFullExplanation, setShowFullExplanation] = useState(false)

  const groupRefs: Record<IngredientStatus, React.RefObject<HTMLDivElement>> = {
    safe: useRef<HTMLDivElement>(null),
    avoid: useRef<HTMLDivElement>(null),
    depends: useRef<HTMLDivElement>(null),
  }

  const allStatuses = data.groups.map((g) => g.status)
  const worstStatus =
    allStatuses.length === 0
      ? 'safe'
      : allStatuses.reduce<IngredientStatus>((worst, current) =>
          severityRank(current) > severityRank(worst) ? current : worst,
        )

  const summaryColor = statusColors[worstStatus].text

  // Ensure consistent order: Avoid → Depends → Safe
  const orderedGroups: IngredientAuditGroup[] = ['avoid', 'depends', 'safe']
    .map((status) => data.groups.find((g) => g.status === status as IngredientStatus))
    .filter(Boolean) as IngredientAuditGroup[]

  const counts = orderedGroups.reduce(
    (acc, g) => {
      acc[g.status] += g.items.length
      return acc
    },
    { safe: 0, avoid: 0, depends: 0 } as Record<IngredientStatus, number>,
  )

  const toggleGroup = (status: IngredientStatus) => {
    setOpenGroups((prev) => ({ ...prev, [status]: !prev[status] }))
  }

  return (
    <div className="space-y-3">
      {/* Summary line: pills per status */}
      <div className="flex flex-wrap items-center gap-2">
        {(['safe', 'avoid', 'depends'] as IngredientStatus[]).map((status) => {
          const count = counts[status]
          if (!count) return null
          return (
            <button
              key={status}
              type="button"
              onClick={() => {
                groupRefs[status].current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  groupRefs[status].current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }
              }}
              aria-label={
                status === 'safe'
                  ? 'Jump to safe ingredients'
                  : status === 'avoid'
                  ? 'Jump to ingredients to avoid'
                  : 'Jump to ingredients that depend on source'
              }
              className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50 rounded-full"
            >
              <StatusPill
                status={status}
                className="hover:scale-105 active:scale-95 transition-transform"
              >
                {STATUS_ICON[status]}
                <span className="font-semibold">
                  {count} {STATUS_LABEL[status]}
                </span>
              </StatusPill>
            </button>
          )
        })}
      </div>
      {data.summary && (
        <p className={`text-xs font-medium ${summaryColor}`}>
          {data.summary}
        </p>
      )}

      {/* Groups */}
      <div className="space-y-3">
        {orderedGroups.map((group) => {
          const status = group.status
          const colors = statusColors[status]
          const count = group.items.length
          if (count === 0) return null

          const limit = 6
          const showAll = expandedItems[status] || count <= limit
          const visibleItems = showAll ? group.items : group.items.slice(0, limit)

          return (
            <div
              key={status}
              ref={groupRefs[status]}
              className="rounded-2xl border border-slate-100 bg-[#F8FAFC] p-3 shadow-sm transition-all duration-200"
            >
              <button
                type="button"
                onClick={() => toggleGroup(status)}
                className="flex w-full items-center justify-between gap-2"
                aria-expanded={openGroups[status]}
              >
                <StatusPill status={status}>
                  {STATUS_ICON[status]}
                  <span>{STATUS_LABEL[status]}</span>
                  <span className="text-[10px] opacity-80">· {count}</span>
                </StatusPill>
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
                <div className="mt-3 flex flex-wrap gap-2 transition-all duration-200">
                  {visibleItems.map((item) => (
                    <div
                      key={item.name}
                      className={`inline-flex flex-col gap-1 rounded-2xl bg-gradient-to-br ${colors.card} px-3 py-2 text-[11px] text-slate-800 shadow-sm transition-transform duration-150 hover:-translate-y-0.5`}
                    >
                      <span className="font-semibold text-[12px]">
                        {item.name}
                      </span>
                      {item.diets && item.diets.length > 0 && (
                        <div className="flex flex-wrap gap-1 max-w-full overflow-x-auto">
                          {item.diets.map((diet) => (
                            <span
                              key={diet}
                              className="rounded-full bg-slate-900/5 px-2 py-0.5 text-[10px] font-medium text-slate-700"
                              title={`Relevant for ${diet} diet`}
                            >
                              {diet}
                            </span>
                          ))}
                        </div>
                      )}
                      {item.allergens && item.allergens.length > 0 && (
                        <div className="flex flex-wrap gap-1 max-w-full overflow-x-auto">
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
                        <div className="mt-1 flex flex-wrap gap-1 max-w-full overflow-x-auto">
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
                  {count > limit && (
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedItems((prev) => ({
                          ...prev,
                          [status]: !prev[status],
                        }))
                      }
                      className="mt-1 text-[11px] font-medium text-blue-600 hover:text-blue-700"
                    >
                      {showAll
                        ? 'Show less'
                        : `Show ${count - limit} more`}
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Residual explanation */}
      {data.explanation && (
        <div className="mt-2 rounded-2xl bg-[#F8FAFC] p-3 shadow-sm">
          <div className="text-sm text-slate-700 leading-relaxed">
            {data.explanation.length > 260 ? (
              <>
                <FormattedMessage
                  content={
                    showFullExplanation
                      ? data.explanation
                      : data.explanation.slice(0, 260).trimEnd() + '…'
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
        </div>
      )}
    </div>
  )
}

