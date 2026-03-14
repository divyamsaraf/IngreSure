'use client'

import React, { useRef } from 'react'
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import FormattedMessage from './FormattedMessage'
import { statusColors, colors, cardBg } from '@/theme/tokens'

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

/** Backend audit payload: groups may be array or keyed object; item shape is permissive. */
export interface BackendAuditPayload {
  summary?: string
  explanation?: string
  groups?:
    | Array<{ status?: IngredientStatus; items?: Array<Record<string, unknown>> }>
    | Record<IngredientStatus, Array<Record<string, unknown>>>
}

interface Props {
  data: IngredientAuditData
}

const STATUS_LABEL: Record<IngredientStatus, string> = {
  safe: 'Safe',
  avoid: 'Avoid',
  depends: 'Depends',
}

const STATUS_TOOLTIP: Record<IngredientStatus, string> = {
  safe: 'These ingredients are safe for your dietary profile.',
  avoid: 'Ingredients to avoid based on your diet and allergens.',
  depends: 'Depends on source or preparation; check details below.',
}

const STATUS_ICON: Record<IngredientStatus, React.ReactNode> = {
  safe: <CheckCircle2 className="h-3.5 w-3.5" />,
  avoid: <XCircle className="h-3.5 w-3.5" />,
  depends: <AlertTriangle className="h-3.5 w-3.5" />,
}

function buildItemTooltip(item: IngredientAuditItem, status: IngredientStatus): string {
  const parts: string[] = []
  if (item.diets?.length) {
    parts.push(
      status === 'avoid'
        ? `Not suitable for ${item.diets.join(', ')} diet`
        : status === 'depends'
        ? `Depends on source for ${item.diets.join(', ')}`
        : `OK for ${item.diets.join(', ')} diet`,
    )
  }
  if (item.allergens?.length) {
    parts.push(`Allergens: ${item.allergens.join(', ')}`)
  }
  return parts.length ? parts.join(' · ') : item.name
}

export default function IngredientAuditCards({ data }: Props) {
  const groupRefs: Record<IngredientStatus, React.RefObject<HTMLDivElement | null>> = {
    safe: useRef<HTMLDivElement>(null),
    avoid: useRef<HTMLDivElement>(null),
    depends: useRef<HTMLDivElement>(null),
  }

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

  return (
    <div className="space-y-4">
      {/* Status summary pills: click to scroll to section */}
      <div className="flex flex-wrap items-center gap-2">
        {(['safe', 'avoid', 'depends'] as IngredientStatus[]).map((status) => {
          const count = counts[status]
          if (!count) return null
          return (
            <button
              key={status}
              type="button"
              title={STATUS_TOOLTIP[status]}
              aria-label={`${count} ${STATUS_LABEL[status]}. Click to scroll.`}
              onClick={() => groupRefs[status].current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  groupRefs[status].current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }
              }}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-bold transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-slate-400 ${statusColors[status].pill}`}
            >
              {STATUS_ICON[status]}
              <span className="font-sans">{STATUS_LABEL[status]} ({count})</span>
            </button>
          )
        })}
      </div>
      {data.summary && (
        <p className="text-sm font-medium text-slate-600 font-sans">{data.summary}</p>
      )}

      {/* Single card per status — ingredients as colored pills in one row per category */}
      <div className="space-y-4">
        {orderedGroups.map((group) => {
          const status = group.status
          const items = group.items
          const count = items.length
          if (count === 0) return null

          return (
            <div
              key={status}
              ref={groupRefs[status]}
              role="region"
              aria-label={`${STATUS_LABEL[status]} ingredients: ${count} items`}
              className="rounded-r-[12px] border-l-4 pl-4 pr-4 pt-3 pb-3 shadow-card"
              style={{ borderLeftColor: colors[status], backgroundColor: cardBg[status] }}
            >
              <div className="font-serif text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">
                {STATUS_LABEL[status]} ({count})
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {items.map((item) => (
                  <span
                    key={item.name}
                    title={buildItemTooltip(item, status)}
                    className="inline-flex items-center rounded-full px-3 py-1.5 text-sm font-sans font-medium text-white border transition-shadow hover:shadow-md cursor-default"
                    style={{ backgroundColor: `${colors[status]}E6`, borderColor: colors[status] }}
                  >
                    {item.name}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Explanation clearly below all categories */}
      {data.explanation && (
        <div className="mt-4 rounded-[12px] bg-surface p-4 shadow-card">
          <div className="text-sm font-sans text-primary leading-[1.5] md:text-[15px]">
            <FormattedMessage content={data.explanation} />
          </div>
        </div>
      )}
    </div>
  )
}
