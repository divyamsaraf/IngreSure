'use client'

import React, { useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  X,
  XCircle,
} from 'lucide-react'
import FormattedMessage, { stripEmojiFromText } from './FormattedMessage'
import { useProfileContext } from '@/context/ProfileContext'
import { statusColors, colors } from '@/theme/tokens'

export type IngredientStatus = 'safe' | 'avoid' | 'depends'

export interface IngredientAuditItem {
  name: string
  status: IngredientStatus
  diets?: string[]
  allergens?: string[]
  alternatives?: string[]
  reason?: string
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
  explanation_source?: string
  llm_used?: boolean
  source?: string
  groups?:
    | Array<{ status?: IngredientStatus; items?: Array<Record<string, unknown>> }>
    | Record<IngredientStatus, Array<Record<string, unknown>>>
}

interface Props {
  data: IngredientAuditData
  showPersonaliseNudge?: boolean
  onPersonalise?: () => void
}

const PILL_LABEL: Record<IngredientStatus, string> = {
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

const AVOID_CAP = 8
const BULLET_LINE = /^\s*(?:[-•*]|\d+\.)\s/

function withOpacity(hex: string, opacity: number): string {
  const alpha = Math.round(opacity * 255)
    .toString(16)
    .padStart(2, '0')
  return `${hex}${alpha}`
}

function buildItemReason(item: IngredientAuditItem, status: IngredientStatus): string | null {
  if (status === 'safe') return null
  if (item.reason?.trim()) return item.reason.trim()
  const parts: string[] = []
  if (item.allergens?.length) {
    parts.push(...item.allergens.map((a) => a.toLowerCase()))
  }
  if (item.diets?.length) {
    if (status === 'avoid') {
      parts.push(`${item.diets[0].toLowerCase()} restriction`)
    } else if (status === 'depends') {
      parts.push(`may vary for ${item.diets[0].toLowerCase()}`)
    }
  }
  if (status === 'depends' && parts.length === 0) {
    return 'may need manual checking'
  }
  return parts.length ? parts.join(' · ') : null
}

function buildItemTooltip(item: IngredientAuditItem, status: IngredientStatus): string {
  const reason = buildItemReason(item, status)
  if (reason) return `${item.name} — ${reason}`
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

function getInitialSafeState(avoidCount: number): 1 | 2 {
  return avoidCount > 0 ? 1 : 2
}

function hasBulletList(text: string): boolean {
  return text.split('\n').some((line) => {
    const trimmed = line.trim()
    return BULLET_LINE.test(trimmed) || trimmed.startsWith('- ')
  })
}

function isRestAreSafeLine(line: string): boolean {
  return /the rest are.*safe/i.test(stripEmojiFromText(line))
}

function isUncertainLine(line: string): boolean {
  const trimmed = line.trim()
  return trimmed.startsWith('🟧') || /^couldn't find reliable/i.test(trimmed)
}

function normalizeOpeningSentence(line: string): string {
  return line
    .replace(/\*\*/g, '')
    .replace(/the following (?:are|is) not suitable:?/gi, 'this product is not suitable.')
    .trim()
}

function buildTemplateExplanation(
  counts: { avoid: number; depends: number; safe: number },
  diet: string | undefined,
): string | null {
  const dietLabel = diet && diet !== 'No rules' ? diet : 'your dietary profile'
  if (counts.avoid > 0) {
    const ing = counts.avoid === 1 ? 'ingredient' : 'ingredients'
    const alt =
      diet && diet !== 'No rules'
        ? `Look for a ${diet}-certified alternative.`
        : 'Look for a suitable alternative.'
    return `Based on your ${dietLabel} diet, this product is not suitable — it contains ${counts.avoid} ${ing} that conflict with your profile. ${alt}`
  }
  if (counts.depends > 0) {
    const ing = counts.depends === 1 ? 'ingredient' : 'ingredients'
    return `Based on your ${dietLabel} diet, this product has ${counts.depends} ${ing} that need verification. Check with the manufacturer before consuming.`
  }
  if (counts.safe > 0) {
    const ing = counts.safe === 1 ? 'ingredient' : 'ingredients'
    return `Based on your ${dietLabel} diet, all ${counts.safe} ${ing} in this product are suitable for you.`
  }
  return null
}

function processAuditExplanation(
  explanation: string | undefined,
  counts: { avoid: number; depends: number; safe: number },
  diet: string | undefined,
): string | null {
  if (!explanation?.trim()) {
    return buildTemplateExplanation(counts, diet)
  }

  const stripped = stripEmojiFromText(explanation)
  const hasBullets = hasBulletList(stripped)
  const hasDuplicateStructure =
    /the following (?:are|is)/i.test(stripped) || stripped.split('\n').some(isRestAreSafeLine)

  if (!hasBullets && !hasDuplicateStructure) {
    return stripped
  }

  const lines = stripped.split('\n')
  let opening: string | null = null
  const actions: string[] = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (BULLET_LINE.test(trimmed) || trimmed.startsWith('- ')) continue
    if (isRestAreSafeLine(trimmed)) continue
    if (isUncertainLine(trimmed)) continue
    if (/^note:/i.test(trimmed.replace(/_/g, ''))) continue

    if (
      !opening &&
      (/based on your/i.test(trimmed) ||
        /this doesn't appear/i.test(trimmed) ||
        /doesn't appear to be compatible/i.test(trimmed))
    ) {
      opening = normalizeOpeningSentence(trimmed)
      continue
    }

    if (/^look for/i.test(trimmed) || /check with the manufacturer/i.test(trimmed)) {
      actions.push(trimmed.replace(/\*\*/g, ''))
    }
  }

  if (opening) {
    const parts = [opening]
    if (actions.length > 0 && !opening.includes(actions[0])) {
      parts.push(actions[0])
    }
    return parts.join(' ')
  }

  return buildTemplateExplanation(counts, diet)
}

interface SectionHeaderBarProps {
  backgroundColor: string
  icon: React.ReactNode
  label: string
  onClick?: () => void
  chevron?: 'right' | 'down' | null
}

function SectionHeaderBar({ backgroundColor, icon, label, onClick, chevron }: SectionHeaderBarProps) {
  const className = `mb-1.5 flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-white ${
    onClick ? 'cursor-pointer' : ''
  }`

  const inner = (
    <>
      <span className="shrink-0">{icon}</span>
      <span className="min-w-0 flex-1 text-left text-xs font-semibold tracking-[0.03em]">{label}</span>
      {chevron === 'right' ? <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden /> : null}
      {chevron === 'down' ? <ChevronDown className="h-3.5 w-3.5 shrink-0" aria-hidden /> : null}
    </>
  )

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className} style={{ backgroundColor }}>
        {inner}
      </button>
    )
  }

  return (
    <div className={className} style={{ backgroundColor }}>
      {inner}
    </div>
  )
}

interface IngredientRowProps {
  item: IngredientAuditItem
  status: 'avoid' | 'depends'
  accentColor: string
  textClass: string
}

function IngredientRow({ item, status, accentColor, textClass }: IngredientRowProps) {
  const reason = buildItemReason(item, status)
  return (
    <div
      className="flex w-full items-center gap-3 rounded-r-[6px] py-[7px] pr-2.5 pl-2.5"
      style={{
        backgroundColor: withOpacity(accentColor, 0.08),
        borderLeft: `3px solid ${accentColor}`,
      }}
      title={buildItemTooltip(item, status)}
    >
      <span className={`min-w-[90px] shrink-0 text-[13px] font-semibold ${textClass}`}>{item.name}</span>
      {reason ? (
        <span className="min-w-0 flex-1 text-[12px] font-normal" style={{ color: colors.muted }}>
          {reason}
        </span>
      ) : (
        <span className="min-w-0 flex-1" />
      )}
    </div>
  )
}

interface AvoidSectionProps {
  items: IngredientAuditItem[]
  fullyExpanded: boolean
  searchQuery: string
  onExpandAll: () => void
  onCollapse: () => void
  onSearchChange: (value: string) => void
  sectionRef: React.RefObject<HTMLDivElement | null>
}

function AvoidSection({
  items,
  fullyExpanded,
  searchQuery,
  onExpandAll,
  onCollapse,
  onSearchChange,
  sectionRef,
}: AvoidSectionProps) {
  if (items.length === 0) return null

  const needsCap = items.length > AVOID_CAP
  const collapsedVisible = needsCap && !fullyExpanded ? items.slice(0, AVOID_CAP) : items

  const filteredItems =
    fullyExpanded && needsCap && searchQuery.trim()
      ? items.filter((item) => item.name.toLowerCase().includes(searchQuery.trim().toLowerCase()))
      : fullyExpanded && needsCap
        ? items
        : collapsedVisible

  return (
    <div ref={sectionRef} role="region" aria-label={`Avoid ingredients: ${items.length} items`}>
      <SectionHeaderBar
        backgroundColor={colors.danger}
        icon={<X className="h-[13px] w-[13px]" aria-hidden />}
        label={`AVOID · ${items.length} items`}
      />
      <div className="flex flex-col gap-1">
        {filteredItems.map((item) => (
          <IngredientRow
            key={item.name}
            item={item}
            status="avoid"
            accentColor={colors.danger}
            textClass={statusColors.avoid.text}
          />
        ))}
      </div>
      {needsCap && !fullyExpanded ? (
        <button
          type="button"
          onClick={onExpandAll}
          className={`mt-1 w-full cursor-pointer rounded-md border border-dashed px-2 py-2 text-center text-[12px] font-medium ${statusColors.avoid.text}`}
          style={{
            backgroundColor: withOpacity(colors.danger, 0.04),
            borderColor: colors.danger,
          }}
        >
          Show all {items.length} avoided ingredients ↓
        </button>
      ) : null}
      {needsCap && fullyExpanded ? (
        <>
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search avoided ingredients..."
            className={`audit-avoid-search mb-1.5 mt-1 w-full rounded-md px-2.5 py-1.5 outline-none ${statusColors.avoid.text}`}
            style={{ border: `0.5px solid ${colors.danger}` }}
          />
          <button
            type="button"
            onClick={onCollapse}
            className={`cursor-pointer py-1 text-[12px] ${statusColors.avoid.text}`}
          >
            Show less ↑
          </button>
        </>
      ) : null}
    </div>
  )
}

interface CheckSectionProps {
  items: IngredientAuditItem[]
  expanded: boolean
  onToggle: () => void
  sectionRef: React.RefObject<HTMLDivElement | null>
}

function CheckSection({ items, expanded, onToggle, sectionRef }: CheckSectionProps) {
  if (items.length === 0) return null

  return (
    <div ref={sectionRef} role="region" aria-label={`Check before buying: ${items.length} items`}>
      <SectionHeaderBar
        backgroundColor={colors.warning}
        icon={<AlertTriangle className="h-[13px] w-[13px]" aria-hidden />}
        label={`CHECK BEFORE BUYING · ${items.length} items`}
        onClick={onToggle}
        chevron={expanded ? 'down' : 'right'}
      />
      {expanded ? (
        <div className="flex flex-col gap-1">
          {items.map((item) => (
            <IngredientRow
              key={item.name}
              item={item}
              status="depends"
              accentColor={colors.warning}
              textClass={statusColors.depends.text}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

interface SafeSectionProps {
  items: IngredientAuditItem[]
  safeState: 1 | 2 | 3
  onToggle: () => void
  onShowMore: () => void
  onShowLess: () => void
  sectionRef: React.RefObject<HTMLDivElement | null>
}

function SafeSection({ items, safeState, onToggle, onShowMore, onShowLess, sectionRef }: SafeSectionProps) {
  if (items.length === 0) return null

  const expanded = safeState >= 2
  const visiblePills = safeState === 2 ? items.slice(0, 5) : items
  const hiddenPillCount = items.length - 5

  return (
    <div ref={sectionRef} role="region" aria-label={`Safe ingredients: ${items.length} items`}>
      <SectionHeaderBar
        backgroundColor={colors.safe}
        icon={<Check className="h-[13px] w-[13px]" aria-hidden />}
        label={
          safeState === 1
            ? `SAFE · ${items.length} ingredients — tap to see`
            : `SAFE · ${items.length} ingredients`
        }
        onClick={onToggle}
        chevron={safeState === 1 ? 'right' : 'down'}
      />
      {expanded ? (
        <>
          <div className="flex flex-wrap gap-[5px]">
            {visiblePills.map((item) => (
              <span
                key={item.name}
                title={buildItemTooltip(item, 'safe')}
                className={`rounded-xl px-2.5 py-1 text-[12px] font-medium ${statusColors.safe.text}`}
                style={{ backgroundColor: withOpacity(colors.safe, 0.15) }}
              >
                ✓ {item.name}
              </span>
            ))}
          </div>
          {safeState === 2 && hiddenPillCount > 0 ? (
            <button
              type="button"
              onClick={onShowMore}
              className={`cursor-pointer py-1 text-[12px] font-medium ${statusColors.safe.text}`}
            >
              + {hiddenPillCount} more safe ingredients
            </button>
          ) : null}
          {safeState === 3 ? (
            <button
              type="button"
              onClick={onShowLess}
              className={`cursor-pointer py-1 text-[12px] ${statusColors.safe.text}`}
            >
              ↑ Show less
            </button>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

function AllSafeBanner() {
  return (
    <div
      className={`mb-2 flex w-full items-center gap-2 rounded-lg border px-3.5 py-2.5 text-[13px] font-medium ${statusColors.safe.text}`}
      style={{
        backgroundColor: withOpacity(colors.safe, 0.1),
        borderColor: colors.safe,
      }}
    >
      <CircleCheck className="h-4 w-4 shrink-0" style={{ color: colors.safe }} aria-hidden />
      <span>All ingredients are suitable for your profile</span>
    </div>
  )
}

export default function IngredientAuditCards(props: Props) {
  const resultFingerprint = useMemo(
    () =>
      JSON.stringify({
        summary: props.data.summary,
        explanation: props.data.explanation,
        groups: props.data.groups.map((g) => ({
          status: g.status,
          items: g.items.map((i) => ({ name: i.name, reason: i.reason })),
        })),
      }),
    [props.data.summary, props.data.explanation, props.data.groups],
  )
  return <IngredientAuditCardsContent key={resultFingerprint} {...props} />
}

function IngredientAuditCardsContent({ data, showPersonaliseNudge, onPersonalise }: Props) {
  const { profile } = useProfileContext()
  const safeSectionRef = useRef<HTMLDivElement>(null)
  const avoidSectionRef = useRef<HTMLDivElement>(null)
  const dependsSectionRef = useRef<HTMLDivElement>(null)

  const scrollToGroup = (status: IngredientStatus) => {
    const target =
      status === 'safe'
        ? safeSectionRef
        : status === 'avoid'
          ? avoidSectionRef
          : dependsSectionRef
    target.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const avoidItems = data.groups.find((g) => g.status === 'avoid')?.items ?? []
  const checkItems = data.groups.find((g) => g.status === 'depends')?.items ?? []
  const safeItems = data.groups.find((g) => g.status === 'safe')?.items ?? []

  const counts = useMemo(
    () => ({
      safe: safeItems.length,
      avoid: avoidItems.length,
      depends: checkItems.length,
    }),
    [safeItems.length, avoidItems.length, checkItems.length],
  )

  const [avoidFullyExpanded, setAvoidFullyExpanded] = useState(false)
  const [avoidSearchQuery, setAvoidSearchQuery] = useState('')
  const [checkExpanded, setCheckExpanded] = useState(false)
  const [safeState, setSafeState] = useState<1 | 2 | 3>(() => getInitialSafeState(avoidItems.length))

  const showAllSafeBanner = counts.avoid === 0 && counts.depends === 0 && counts.safe > 0

  const processedExplanation = useMemo(
    () => processAuditExplanation(data.explanation, counts, profile.dietary_preference),
    [data.explanation, counts, profile.dietary_preference],
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
              aria-label={`${count} ${PILL_LABEL[status]}. Click to scroll.`}
              onClick={() => scrollToGroup(status)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  scrollToGroup(status)
                }
              }}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-bold transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-slate-400 ${statusColors[status].pill}`}
            >
              {STATUS_ICON[status]}
              <span className="font-sans">
                {PILL_LABEL[status]} ({count})
              </span>
            </button>
          )
        })}
      </div>

      <div className="space-y-2">
        <AvoidSection
          items={avoidItems}
          fullyExpanded={avoidFullyExpanded}
          searchQuery={avoidSearchQuery}
          onExpandAll={() => setAvoidFullyExpanded(true)}
          onCollapse={() => {
            setAvoidFullyExpanded(false)
            setAvoidSearchQuery('')
          }}
          onSearchChange={setAvoidSearchQuery}
          sectionRef={avoidSectionRef}
        />
        <CheckSection
          items={checkItems}
          expanded={checkExpanded}
          onToggle={() => setCheckExpanded((prev) => !prev)}
          sectionRef={dependsSectionRef}
        />
        {showAllSafeBanner ? <AllSafeBanner /> : null}
        <SafeSection
          items={safeItems}
          safeState={safeState}
          onToggle={() => setSafeState((prev) => (prev === 1 ? 2 : 1))}
          onShowMore={() => setSafeState(3)}
          onShowLess={() => setSafeState(2)}
          sectionRef={safeSectionRef}
        />
      </div>

      {processedExplanation ? (
        <div className="audit-explanation font-sans text-primary">
          <FormattedMessage
            content={processedExplanation}
            textClassName="text-chat-explanation"
            stripEmoji
          />
        </div>
      ) : null}

      {showPersonaliseNudge && onPersonalise ? (
        <div className="mt-3 rounded-[12px] bg-amber-50 border border-amber-100 px-3 py-2 text-chat-reason text-amber-800">
          <span>⚠ This result is generic. Set your diet to see if this is safe for you.</span>{' '}
          <button
            type="button"
            onClick={onPersonalise}
            className="font-medium underline underline-offset-2 hover:text-amber-900 transition-colors"
          >
            Personalise →
          </button>
        </div>
      ) : null}
    </div>
  )
}
