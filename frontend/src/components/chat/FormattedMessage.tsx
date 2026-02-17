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
    return <p className="leading-relaxed">{content}</p>
  }

  const blocks = content.split('\n')
  const elements: React.ReactNode[] = []
  let bulletBuffer: string[] = []
  let keyIdx = 0

  const flushBullets = () => {
    if (bulletBuffer.length === 0) return
    elements.push(
      <ul key={`ul-${keyIdx++}`} className="space-y-1.5 my-2">
        {bulletBuffer.map((item, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-red-400 flex-shrink-0" />
            <span className="leading-relaxed">{renderInline(item)}</span>
          </li>
        ))}
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
      <p key={`p-${keyIdx++}`} className="leading-relaxed">
        {renderInline(trimmed)}
      </p>
    )
  }

  flushBullets()

  return <div className="space-y-1">{elements}</div>
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
    // Push text before the match
    if (match.index > lastIndex) {
      nodes.push(<span key={`t-${key++}`}>{text.slice(lastIndex, match.index)}</span>)
    }

    if (match[1]) {
      // **bold**
      nodes.push(
        <strong key={`b-${key++}`} className="font-semibold text-slate-900">
          {match[2]}
        </strong>
      )
    } else if (match[3]) {
      // _italic_
      nodes.push(
        <em key={`i-${key++}`} className="text-slate-500 italic text-[0.85em]">
          {match[4]}
        </em>
      )
    }

    lastIndex = match.index + match[0].length
  }

  // Push remaining text
  if (lastIndex < text.length) {
    nodes.push(<span key={`t-${key++}`}>{text.slice(lastIndex)}</span>)
  }

  return nodes
}
