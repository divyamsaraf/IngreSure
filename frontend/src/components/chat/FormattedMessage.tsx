'use client'

import React from 'react'

export type IngredientAnnotationStatus = 'safe' | 'avoid' | 'depends'

export interface IngredientAnnotation {
  name: string
  status: IngredientAnnotationStatus
}

interface FormattedMessageProps {
  content: string
  isUser?: boolean
  /** Typography token class for assistant message text (default: text-chat-body). */
  textClassName?: string
  /** Strip emoji characters before rendering (used for audit explanations). */
  stripEmoji?: boolean
  /** Optional ingredient → verdict map for linter-style inline underlines. */
  annotations?: IngredientAnnotation[]
}

const ANNOTATION_CLASS: Record<IngredientAnnotationStatus, string> = {
  safe: 'underline decoration-2 underline-offset-[3px] decoration-safe text-emerald-800',
  avoid: 'underline decoration-2 underline-offset-[3px] decoration-avoid text-rose-800',
  depends: 'underline decoration-2 underline-offset-[3px] decoration-depends text-amber-800',
}

/**
 * Renders a chat message with inline markdown-like formatting:
 *   **bold**  →  <strong>
 *   _italic_  →  <em>
 *   Lines starting with "- " → styled bullet list items
 *   Blank lines → paragraph breaks
 *   annotations → verdict-colored underlines on matching ingredient names
 */
export function stripEmojiFromText(text: string): string {
  return text.replace(/\p{Emoji}/gu, '').replace(/\s{2,}/g, ' ').trim()
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function buildAnnotationRegex(annotations: IngredientAnnotation[]): RegExp | null {
  const names = Array.from(
    new Set(
      annotations
        .map((a) => a.name.trim())
        .filter((n) => n.length > 0)
        .sort((a, b) => b.length - a.length),
    ),
  )
  if (names.length === 0) return null
  return new RegExp(`\\b(${names.map(escapeRegExp).join('|')})\\b`, 'gi')
}

function annotatePlainText(
  text: string,
  annotationMap: Map<string, IngredientAnnotationStatus>,
  regex: RegExp | null,
  keyPrefix: string,
  usedNames?: Set<string>,
): React.ReactNode {
  if (!text) return null
  if (!regex || annotationMap.size === 0) {
    return text
  }

  const seen = usedNames ?? new Set<string>()
  const nodes: React.ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0
  regex.lastIndex = 0

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index))
    }
    const matched = match[1]
    const keyName = matched.toLowerCase()
    const status = annotationMap.get(keyName)
    // Only highlight the first mention of each ingredient — avoids coloring
    // alternatives like "Try Flax egg instead" after "Egg is not suitable…".
    const alreadyUsed = seen.has(keyName)
    if (status && !alreadyUsed) {
      seen.add(keyName)
      nodes.push(
        <span
          key={`${keyPrefix}-a-${key++}`}
          className={`font-semibold ${ANNOTATION_CLASS[status]}`}
          title={`${matched} — ${status}`}
        >
          {matched}
        </span>,
      )
    } else {
      nodes.push(matched)
    }
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex))
  }

  return nodes.length === 1 ? nodes[0] : nodes
}

export default function FormattedMessage({
  content,
  isUser = false,
  textClassName = 'text-chat-body',
  stripEmoji = false,
  annotations = [],
}: FormattedMessageProps) {
  if (!content) return null

  const displayContent = stripEmoji ? stripEmojiFromText(content) : content
  if (!displayContent) return null

  if (isUser) {
    return <p className="text-chat-body text-white">{displayContent}</p>
  }

  const annotationMap = new Map(
    annotations.map((a) => [a.name.trim().toLowerCase(), a.status] as const),
  )
  const annotationRegex = buildAnnotationRegex(annotations)
  /** Shared across the whole message so "Egg" highlights once, not again in "Flax egg". */
  const usedAnnotationNames = new Set<string>()

  const blocks = displayContent.split('\n')
  const elements: React.ReactNode[] = []
  let bulletBuffer: string[] = []
  let keyIdx = 0

  const bulletDot = (item: string): { color: string; text: string } => {
    if (item.startsWith('❌ ')) return { color: 'bg-avoid', text: item.slice(2).trim() }
    if (item.startsWith('✅ ')) return { color: 'bg-safe', text: item.slice(2).trim() }
    if (item.startsWith('🟧 ') || item.startsWith('⚠ '))
      return {
        color: 'bg-depends',
        text: (item.startsWith('🟧 ') ? item.slice(2) : item.slice(1)).trim(),
      }
    return { color: 'bg-safe', text: item }
  }

  const flushBullets = () => {
    if (bulletBuffer.length === 0) return
    elements.push(
      <ul key={`ul-${keyIdx++}`} className="space-y-1.5 my-2 list-none">
        {bulletBuffer.map((item, i) => {
          const { color, text } = bulletDot(item)
          return (
            <li key={i} className="flex items-start gap-2">
              <span className={`mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0 ${color}`} aria-hidden />
              <span className={`${textClassName} text-primary`}>
                {renderInline(text, annotationMap, annotationRegex, `b-${keyIdx}-${i}`, usedAnnotationNames)}
              </span>
            </li>
          )
        })}
      </ul>,
    )
    bulletBuffer = []
  }

  for (const line of blocks) {
    const trimmed = line.trim()

    if (trimmed.startsWith('- ')) {
      bulletBuffer.push(trimmed.slice(2))
      continue
    }

    flushBullets()

    if (trimmed === '') {
      elements.push(<div key={`br-${keyIdx++}`} className="h-2" />)
      continue
    }

    elements.push(
      <p key={`p-${keyIdx++}`} className={`${textClassName} text-primary`}>
        {renderInline(trimmed, annotationMap, annotationRegex, `p-${keyIdx}`, usedAnnotationNames)}
      </p>,
    )
  }

  flushBullets()

  return <div className={`space-y-2 ${textClassName}`}>{elements}</div>
}

/**
 * Parse inline markdown tokens and return React nodes.
 * Handles: **bold**, _italic_, and ingredient annotations.
 */
function renderInline(
  text: string,
  annotationMap: Map<string, IngredientAnnotationStatus>,
  annotationRegex: RegExp | null,
  keyPrefix: string,
  usedNames: Set<string>,
): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  const regex = /(\*\*(.+?)\*\*)|(_(.+?)_)/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  const pushAnnotated = (chunk: string, prefix: string) => {
    const annotated = annotatePlainText(chunk, annotationMap, annotationRegex, prefix, usedNames)
    if (annotated == null || annotated === '') return
    if (Array.isArray(annotated)) nodes.push(...annotated)
    else nodes.push(annotated)
  }

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      pushAnnotated(text.slice(lastIndex, match.index), `${keyPrefix}-pre-${key}`)
    }

    if (match[1]) {
      nodes.push(
        <strong key={`${keyPrefix}-b-${key++}`} className="font-semibold text-primary">
          {annotatePlainText(match[2], annotationMap, annotationRegex, `${keyPrefix}-bold-${key}`, usedNames)}
        </strong>,
      )
    } else if (match[3]) {
      nodes.push(
        <em key={`${keyPrefix}-i-${key++}`} className="text-slate-600 italic text-[0.95em]">
          {annotatePlainText(match[4], annotationMap, annotationRegex, `${keyPrefix}-em-${key}`, usedNames)}
        </em>,
      )
    }

    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    pushAnnotated(text.slice(lastIndex), `${keyPrefix}-post`)
  }

  return nodes
}
