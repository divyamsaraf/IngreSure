import React from 'react'
import type {
  IngredientAuditData,
  IngredientAuditGroup,
  IngredientStatus,
  BackendAuditPayload,
  ConfidenceTier,
} from './IngredientAuditCards'
import { PROFILE_REQUIRED_TAG, PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG } from '@/constants/chatProtocol'
import { UserProfile, DEFAULT_PROFILE, backendToProfile, type BackendProfile, type ProfileUpdateStreamPayload } from '@/types/userProfile'
import type { RecentCheckEntry } from '@/lib/profileStorage'
import {
  isConfirmPrompt,
  isDegradedText,
  isEmergencyGuidance,
  isProfileRequiredText,
  parseUnderstandingEcho,
  type UnderstandingEcho,
} from '@/lib/chatContract'

export interface Message {
  role: 'user' | 'assistant'
  content: string
  audit?: IngredientAuditData
  profileRequired?: boolean
  degraded?: boolean
  emergency?: boolean
  understandingEcho?: UnderstandingEcho | null
  confirmPending?: boolean
}

const PROFILE_REQUIRED_FALLBACK =
  'I need to know which restrictions apply before I can say SAFE or NOT SAFE. Tell me your diet or allergies.'

export function applyAssistantContract(
  content: string,
  extras: {
    profileRequired?: boolean
    audit?: IngredientAuditData
    forceEmergency?: boolean
  } = {},
): Pick<
  Message,
  | 'content'
  | 'profileRequired'
  | 'degraded'
  | 'emergency'
  | 'understandingEcho'
  | 'confirmPending'
  | 'audit'
> {
  const { echo, remainder } = parseUnderstandingEcho(content)
  const emergency = Boolean(extras.forceEmergency) || isEmergencyGuidance(content)
  const profileRequired =
    (Boolean(extras.profileRequired) || isProfileRequiredText(content)) && !emergency
  const degraded = extras.audit?.degraded === true || isDegradedText(content)
  const confirmPending = !emergency && !profileRequired && isConfirmPrompt(content)
  let visible = remainder
  if (degraded) {
    visible = visible.replace(/I could not finish that check\.[^\n]*/gi, '').trim()
  }
  return {
    content: visible,
    understandingEcho: echo,
    profileRequired,
    degraded,
    emergency,
    confirmPending,
    audit: emergency || profileRequired ? undefined : extras.audit,
  }
}

/** Top-level verdict from audit groups: avoid beats depends beats safe. */
export function deriveTopLevelVerdict(audit: IngredientAuditData): IngredientStatus {
  const counts = audit.groups.reduce(
    (acc, g) => {
      acc[g.status] += g.items.length
      return acc
    },
    { safe: 0, avoid: 0, depends: 0 } as Record<IngredientStatus, number>,
  )
  if (counts.avoid > 0) return 'avoid'
  if (counts.depends > 0) return 'depends'
  return 'safe'
}

/** Build deduped recent checks (most recent first) with verdicts from paired assistant audits. */
export function buildRecentChecksFromMessages(messages: Message[]): RecentCheckEntry[] {
  const entries: RecentCheckEntry[] = []
  const seen = new Set<string>()
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i]
    if (msg.role !== 'user') continue
    if (seen.has(msg.content)) continue
    seen.add(msg.content)
    let verdict: IngredientStatus | undefined
    for (let j = i + 1; j < messages.length; j++) {
      if (messages[j].role === 'user') break
      const audit = messages[j].audit
      if (messages[j].role === 'assistant' && audit) {
        verdict = deriveTopLevelVerdict(audit)
        break
      }
    }
    entries.push({ query: msg.content, verdict })
    if (entries.length >= 5) break
  }
  return entries
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
    reason: typeof item.reason === 'string' ? item.reason : undefined,
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

  const validTiers: ConfidenceTier[] = ['verified', 'standard', 'limited']
  const confidenceTier = validTiers.includes(raw.confidence_tier as ConfidenceTier)
    ? (raw.confidence_tier as ConfidenceTier)
    : undefined

  return {
    summary,
    groups: groupsArray,
    explanation: raw.explanation,
    confidenceTier,
    degraded: raw.degraded === true,
  }
}

const STREAM_UI_THROTTLE_MS = 50

const STATUS_PLACEHOLDER_LINES = [
  /^Checking ingredients[….]{0,3}\s*$/i,
  /^Analyzing[….]{0,3}\s*$/i,
]

/** Remove stream progress placeholders so they are not persisted in message content. */
export function stripStatusPlaceholders(text: string): string {
  return text
    .split('\n')
    .filter((line) => !STATUS_PLACEHOLDER_LINES.some((re) => re.test(line.trim())))
    .join('\n')
    .trim()
}

function flushStreamContent(
  buffer: string,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  flags: { profileRequired: boolean; forceEmergency: boolean },
) {
  const content = stripStatusPlaceholders(
    buffer
      .replace(new RegExp(`${PROFILE_UPDATE_TAG}[\\s\\S]*?${PROFILE_UPDATE_TAG}`, 'g'), '')
      .replaceAll(PROFILE_REQUIRED_TAG, '')
      .replace(new RegExp(`${INGREDIENT_AUDIT_TAG}[\\s\\S]*?${INGREDIENT_AUDIT_TAG}`, 'g'), '')
      .trim(),
  )
  setMessages((prev) => {
    const newMsgs = [...prev]
    const last = newMsgs[newMsgs.length - 1]
    if (last && last.role === 'assistant') {
      Object.assign(
        last,
        applyAssistantContract(content, {
          profileRequired: flags.profileRequired,
          audit: last.audit,
          forceEmergency: flags.forceEmergency || Boolean(last.emergency),
        }),
      )
    }
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
  const flags = { profileRequired: false, forceEmergency: false }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      if (flags.profileRequired && !stripStatusPlaceholders(buffer.replaceAll(PROFILE_REQUIRED_TAG, '')).trim()) {
        buffer = `${buffer}\n${PROFILE_REQUIRED_FALLBACK}`
      }
      flushStreamContent(buffer, setMessages, flags)
      break
    }

    const chunk = decoder.decode(value, { stream: true })
    buffer += chunk

    if (buffer.includes(PROFILE_REQUIRED_TAG) || isProfileRequiredText(buffer)) {
      flags.profileRequired = true
      setShowOnboarding(true)
    }
    if (isEmergencyGuidance(buffer)) {
      flags.forceEmergency = true
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
            if (last && last.role === 'assistant' && !flags.profileRequired && !flags.forceEmergency) {
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
      flushStreamContent(buffer, setMessages, flags)
      lastFlushAt = now
    }
  }
}
