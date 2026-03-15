/**
 * Server-side only: fetch backend config and cache. Used by BFF routes to align
 * with backend (e.g. max_chat_message_length). Single source: backend GET /config.
 */
import { FALLBACK_MAX_CHAT_MESSAGE_LENGTH } from '@/constants/configDefaults'

let cached: { max_chat_message_length: number } | null = null

export async function getMaxChatMessageLength(): Promise<number> {
  if (cached !== null) return cached.max_chat_message_length
  const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
  try {
    const res = await fetch(`${backendUrl}/config`, { cache: 'no-store' })
    if (res.ok) {
      const data = await res.json()
      const value = typeof data?.max_chat_message_length === 'number' ? data.max_chat_message_length : FALLBACK_MAX_CHAT_MESSAGE_LENGTH
      cached = { max_chat_message_length: value }
      return value
    }
  } catch {
    // use fallback
  }
  cached = { max_chat_message_length: FALLBACK_MAX_CHAT_MESSAGE_LENGTH }
  return FALLBACK_MAX_CHAT_MESSAGE_LENGTH
}
