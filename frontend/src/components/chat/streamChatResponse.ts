import React from 'react'
import type { IngredientAuditData, IngredientAuditGroup, IngredientStatus, BackendAuditPayload } from './IngredientAuditCards'
import { PROFILE_REQUIRED_TAG, PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG } from '@/constants/chatProtocol'
import { UserProfile, DEFAULT_PROFILE, backendToProfile, type BackendProfile, type ProfileUpdateStreamPayload } from '@/types/userProfile'

export interface Message {
  role: 'user' | 'assistant'
  content: string
  audit?: IngredientAuditData
}

export function normalizeAuditData(raw: BackendAuditPayload): IngredientAuditData {
  const groupsArray: IngredientAuditGroup[] = []
  const keys: IngredientStatus[] = ['safe', 'avoid', 'depends']

  const mapItem = (item: Record<string, unknown>, status: IngredientStatus) => ({
    name: String(item.name ?? ''),
    status,
    diets: (item.diets ?? item.diet ?? []) as string[],
    allergens: (item.allergens ?? []) as string[],
    alternatives: (item.alternatives ?? []) as string[],
  })

  if (Array.isArray(raw.groups)) {
    for (const g of raw.groups) {
      if (!g || !keys.includes(g.status as IngredientStatus)) continue
      const status = g.status as IngredientStatus
      groupsArray.push({
        status,
        items: (g.items ?? []).map((item) => mapItem(item as Record<string, unknown>, status)),
      })
    }
  } else if (raw.groups && typeof raw.groups === 'object') {
    for (const status of keys) {
      const arr = raw.groups[status]
      if (!Array.isArray(arr) || arr.length === 0) continue
      groupsArray.push({
        status,
        items: arr.map((item) => mapItem(item, status)),
      })
    }
  }

  const counts = groupsArray.reduce(
    (acc, g) => {
      acc[g.status] += g.items.length
      return acc
    },
    { safe: 0, avoid: 0, depends: 0 } as Record<IngredientStatus, number>,
  )

  const summary =
    raw.summary && typeof raw.summary === 'string'
      ? raw.summary
      : `${counts.safe} Safe, ${counts.avoid} Avoid, ${counts.depends} Depends`

  return {
    summary,
    groups: groupsArray,
    explanation: raw.explanation,
  }
}

const STREAM_UI_THROTTLE_MS = 50

function flushStreamContent(
  buffer: string,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
) {
  const content = buffer
    .replace(new RegExp(`${PROFILE_UPDATE_TAG}[\\s\\S]*?${PROFILE_UPDATE_TAG}`, 'g'), '')
    .replace(new RegExp(`${PROFILE_REQUIRED_TAG}[\\s\\S]*?(?=${PROFILE_UPDATE_TAG}|$)`, 'g'), '')
    .replace(new RegExp(`${INGREDIENT_AUDIT_TAG}[\\s\\S]*?${INGREDIENT_AUDIT_TAG}`, 'g'), '')
    .trim()
  setMessages((prev) => {
    const newMsgs = [...prev]
    const last = newMsgs[newMsgs.length - 1]
    if (last && last.role === 'assistant') last.content = content || last.content
    return newMsgs
  })
}

export async function streamChatResponse(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  setProfile: React.Dispatch<React.SetStateAction<UserProfile>>,
  setShowOnboarding: (open: boolean) => void,
  persistProfile: (profile: UserProfile) => void,
) {
  const decoder = new TextDecoder()
  let buffer = ''
  let lastFlushAt = 0

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      flushStreamContent(buffer, setMessages)
      break
    }

    const chunk = decoder.decode(value, { stream: true })
    buffer += chunk

    if (buffer.includes(PROFILE_REQUIRED_TAG)) {
      setShowOnboarding(true)
      const profileRequiredPattern = new RegExp(`${PROFILE_REQUIRED_TAG}[^]*?(?=${PROFILE_UPDATE_TAG}|$)`, 'g')
      buffer = buffer.replace(profileRequiredPattern, '').trim()
      if (!buffer.trim())
        buffer =
          'Please set your dietary preference, allergens, and lifestyle in the form above so we can give you personalized advice.'
    }

    if (buffer.includes(PROFILE_UPDATE_TAG)) {
      const parts: string[] = buffer.split(PROFILE_UPDATE_TAG)
      if (parts.length >= 3) {
        const jsonStr = parts[1]
        try {
          const raw = JSON.parse(jsonStr) as ProfileUpdateStreamPayload
          const updatedProfile =
            raw.user_id != null
              ? backendToProfile(raw as BackendProfile)
              : {
                  ...DEFAULT_PROFILE,
                  ...raw,
                  allergies: raw.allergies ?? raw.allergens ?? [],
                  allergens: raw.allergens ?? raw.allergies ?? [],
                }
          updatedProfile.is_onboarding_completed = true
          const isEmpty =
            (!updatedProfile.dietary_preference || updatedProfile.dietary_preference === 'No rules') &&
            (updatedProfile.allergens?.length ?? 0) === 0 &&
            (updatedProfile.lifestyle?.length ?? 0) === 0
          setProfile((prev) => {
            if (isEmpty && prev.dietary_preference && prev.dietary_preference !== 'No rules') return prev
            if (
              isEmpty &&
              ((prev.allergens?.length ?? 0) > 0 || (prev.lifestyle?.length ?? 0) > 0)
            )
              return prev
            return updatedProfile
          })
          if (!isEmpty) persistProfile(updatedProfile)
          buffer = parts[0] + (parts[2] || '')
        } catch (e) {
          console.error('Failed to parse backend profile update', e)
        }
      }
    }

    if (buffer.includes(INGREDIENT_AUDIT_TAG)) {
      const parts = buffer.split(INGREDIENT_AUDIT_TAG)
      if (parts.length >= 3) {
        const jsonStr = parts[1]
        try {
          const raw = JSON.parse(jsonStr) as BackendAuditPayload
          const normalized = normalizeAuditData(raw)
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last && last.role === 'assistant') {
              last.audit = normalized
            }
            return next
          })
          buffer = (parts[0] + (parts[2] || '')).trim()
        } catch (e) {
          console.error('Failed to parse ingredient audit payload', e)
        }
      }
    }

    const now = Date.now()
    if (now - lastFlushAt >= STREAM_UI_THROTTLE_MS) {
      flushStreamContent(buffer, setMessages)
      lastFlushAt = now
    }
  }
}
