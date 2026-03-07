'use client'

import React from 'react'

interface FormattedMessageProps {
  content: string
  isUser?: boolean
}

/**
 * Renders a chat message with inline markdown-like formatting:
 *   **bold**  →  <strong>
 *   _italic_  →  <em>
 *   Lines starting with "- " → styled bullet list items
 *   Blank lines → paragraph breaks
 */
export default function FormattedMessage({ content, isUser = false }: FormattedMessageProps) {
  if (!content) return null

  if (isUser) {
    return <p className="text-base leading-[1.5] text-white">{content}</p>
  }

  const blocks = content.split('\n')
  const elements: React.ReactNode[] = []
  let bulletBuffer: string[] = []
  let keyIdx = 0

  const bulletDot = (item: string): { color: string; text: string } => {
    if (item.startsWith('❌ ')) return { color: 'bg-[#EF4444]', text: item.slice(2).trim() }
    if (item.startsWith('✅ ')) return { color: 'bg-[#10B981]', text: item.slice(2).trim() }
    if (item.startsWith('🟧 ') || item.startsWith('⚠ ')) return { color: 'bg-[#F59E0B]', text: (item.startsWith('🟧 ') ? item.slice(2) : item.slice(1)).trim() }
    return { color: 'bg-[#10B981]', text: item }
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
              <span className="leading-[1.5] text-[#0F172A]">{renderInline(text)}</span>
            </li>
          )
        })}
      </ul>
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
      <p key={`p-${keyIdx++}`} className="leading-[1.5] text-[#0F172A]">
        {renderInline(trimmed)}
      </p>
    )
  }

  flushBullets()

  return <div className="space-y-2 text-base">{elements}</div>
}

/**
 * Parse inline markdown tokens and return React nodes.
 * Handles: **bold**, _italic_, and `em dash —` splitting for visual hierarchy.
 */
function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  // Regex for **bold** and _italic_
  const regex = /(\*\*(.+?)\*\*)|(_(.+?)_)/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  while ((match = regex.exec(text)) !== null) {
    // Push text before the match (inherit color from parent)
    if (match.index > lastIndex) {
      nodes.push(<span key={`t-${key++}`} className="text-inherit">{text.slice(lastIndex, match.index)}</span>)
    }

    if (match[1]) {
      // **bold** – key ingredients / warnings
      nodes.push(
        <strong key={`b-${key++}`} className="font-semibold text-[#0F172A]">
          {match[2]}
        </strong>
      )
    } else if (match[3]) {
      // _italic_ – conditional notes
      nodes.push(
        <em key={`i-${key++}`} className="text-slate-600 italic text-[0.95em]">
          {match[4]}
        </em>
      )
    }

    lastIndex = match.index + match[0].length
  }

  // Push remaining text
  if (lastIndex < text.length) {
    nodes.push(<span key={`t-${key++}`} className="text-inherit">{text.slice(lastIndex)}</span>)
  }

  return nodes
}
