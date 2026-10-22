import { describe, it, expect } from 'vitest'
import type React from 'react'
import {
  normalizeAuditData,
  deriveTopLevelVerdict,
  buildRecentChecksFromMessages,
  applyAssistantContract,
  streamChatResponse,
  type Message,
} from './streamChatResponse'
import { PROFILE_REQUIRED_TAG, PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG } from '@/constants/chatProtocol'
import { DEFAULT_PROFILE, type UserProfile } from '@/types/userProfile'
import { OLD_UNMARKED_STREAMS, STREAMS } from '@/lib/chatContractStreams'

function makeReader(text: string, chunkSize = 17): ReadableStreamDefaultReader<Uint8Array> {
  const encoded = new TextEncoder().encode(text)
  let offset = 0
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (offset >= encoded.length) {
        controller.close()
        return
      }
      controller.enqueue(encoded.slice(offset, offset + chunkSize))
      offset += chunkSize
    },
  }).getReader()
}

async function replayChatStream(body: string) {
  let messages: Message[] = [{ role: 'assistant', content: '' }]
  let onboarding = false
  let profile: UserProfile = { ...DEFAULT_PROFILE }
  const setMessages: React.Dispatch<React.SetStateAction<Message[]>> = (update) => {
    messages = typeof update === 'function' ? update(messages) : update
  }
  const setProfile: React.Dispatch<React.SetStateAction<UserProfile>> = (update) => {
    profile = typeof update === 'function' ? update(profile) : update
  }
  await streamChatResponse(
    makeReader(body),
    setMessages,
    setProfile,
    (open) => {
      if (open) onboarding = true
    },
    () => undefined,
  )
  return { last: messages[messages.length - 1], onboarding, profile }
}

describe('normalizeAuditData', () => {
  it('normalizes array-style groups', () => {
    const raw = {
      summary: '2 Safe, 1 Avoid',
      groups: [
        { status: 'safe' as const, items: [{ name: 'Sugar' }, { name: 'Water' }] },
        { status: 'avoid' as const, items: [{ name: 'Gelatin' }] },
      ],
    }
    const result = normalizeAuditData(raw)
    expect(result.summary).toBe('2 Safe, 1 Avoid')
    expect(result.groups).toHaveLength(2)
    expect(result.groups[0].status).toBe('safe')
    expect(result.groups[0].items).toHaveLength(2)
    expect(result.groups[0].items[0].name).toBe('Sugar')
    expect(result.groups[1].status).toBe('avoid')
    expect(result.groups[1].items[0].name).toBe('Gelatin')
  })

  it('normalizes keyed-object groups (safe, avoid, depends)', () => {
    const raw = {
      groups: {
        safe: [{ name: 'A' }, { name: 'B' }],
        avoid: [{ name: 'C' }],
        depends: [],
      },
    }
    const result = normalizeAuditData(raw)
    expect(result.groups).toHaveLength(2)
    const safeGroup = result.groups.find((g) => g.status === 'safe')
    const avoidGroup = result.groups.find((g) => g.status === 'avoid')
    expect(safeGroup?.items).toHaveLength(2)
    expect(avoidGroup?.items).toHaveLength(1)
    expect(result.summary).toBe('2 Safe, 1 Avoid, 0 Depends')
  })

  it('uses raw.summary when provided', () => {
    const raw = { summary: 'Custom summary', groups: [] }
    const result = normalizeAuditData(raw)
    expect(result.summary).toBe('Custom summary')
  })

  it('passes through explanation', () => {
    const raw = {
      groups: [],
      explanation: '**Gelatin** is _often_ animal-derived.',
    }
    const result = normalizeAuditData(raw)
    expect(result.explanation).toBe('**Gelatin** is _often_ animal-derived.')
  })

  it('passes through a valid confidence_tier', () => {
    const raw = { groups: [], confidence_tier: 'verified' }
    const result = normalizeAuditData(raw)
    expect(result.confidenceTier).toBe('verified')
  })

  it('drops an unrecognized confidence_tier', () => {
    const raw = { groups: [], confidence_tier: 'bogus' }
    const result = normalizeAuditData(raw)
    expect(result.confidenceTier).toBeUndefined()
  })

  it('leaves confidenceTier undefined when confidence_tier is absent', () => {
    const raw = { groups: [] }
    const result = normalizeAuditData(raw)
    expect(result.confidenceTier).toBeUndefined()
  })

  it('passes through degraded when the audit JSON includes it', () => {
    const result = normalizeAuditData({ groups: [], degraded: true })
    expect(result.degraded).toBe(true)
  })

  it('maps item fields (diets, allergens, alternatives)', () => {
    const raw = {
      groups: [
        {
          status: 'avoid' as const,
          items: [
            {
              name: 'X',
              diets: ['Vegan'],
              allergens: ['Milk'],
              alternatives: ['Y'],
              reason: 'dairy product',
            },
          ],
        },
      ],
    }
    const result = normalizeAuditData(raw)
    expect(result.groups[0].items[0]).toEqual({
      name: 'X',
      status: 'avoid',
      diets: ['Vegan'],
      allergens: ['Milk'],
      alternatives: ['Y'],
      reason: 'dairy product',
    })
  })
})

describe('deriveTopLevelVerdict', () => {
  it('returns avoid when any avoid items exist', () => {
    const audit = normalizeAuditData({
      groups: [
        { status: 'safe', items: [{ name: 'Sugar' }] },
        { status: 'avoid', items: [{ name: 'Gelatin' }] },
      ],
    })
    expect(deriveTopLevelVerdict(audit)).toBe('avoid')
  })

  it('returns depends when no avoid but depends items exist', () => {
    const audit = normalizeAuditData({
      groups: [{ status: 'depends', items: [{ name: 'Natural flavor' }] }],
    })
    expect(deriveTopLevelVerdict(audit)).toBe('depends')
  })

  it('returns safe when only safe items exist', () => {
    const audit = normalizeAuditData({
      groups: [{ status: 'safe', items: [{ name: 'Water' }] }],
    })
    expect(deriveTopLevelVerdict(audit)).toBe('safe')
  })
})

describe('buildRecentChecksFromMessages', () => {
  it('pairs user queries with the next assistant audit verdict', () => {
    const audit = normalizeAuditData({
      groups: [{ status: 'avoid', items: [{ name: 'Gelatin' }] }],
    })
    const entries = buildRecentChecksFromMessages([
      { role: 'user', content: 'Is this vegan?' },
      { role: 'assistant', content: '', audit },
    ])
    expect(entries).toEqual([{ query: 'Is this vegan?', verdict: 'avoid' }])
  })
})

describe('chat protocol tags', () => {
  it('protocol tag constants are non-empty and unique', () => {
    expect(PROFILE_REQUIRED_TAG).toBe('<<<PROFILE_REQUIRED>>>')
    expect(PROFILE_UPDATE_TAG).toBe('<<<PROFILE_UPDATE>>>')
    expect(INGREDIENT_AUDIT_TAG).toBe('<<<INGREDIENT_AUDIT>>>')
    expect(PROFILE_REQUIRED_TAG).not.toBe(PROFILE_UPDATE_TAG)
    expect(PROFILE_UPDATE_TAG).not.toBe(INGREDIENT_AUDIT_TAG)
    expect(INGREDIENT_AUDIT_TAG).not.toBe(PROFILE_REQUIRED_TAG)
  })

  it('stream content stripping removes PROFILE_UPDATE block', () => {
    const tag = PROFILE_UPDATE_TAG
    const text = `Hello${tag}{"user_id":"x"}${tag}World`
    const regex = new RegExp(`${tag}[\\s\\S]*?${tag}`, 'g')
    expect(text.replace(regex, '')).toBe('HelloWorld')
  })

  it('stream content stripping removes INGREDIENT_AUDIT block', () => {
    const tag = INGREDIENT_AUDIT_TAG
    const text = `Before${tag}{"groups":[]}${tag}After`
    const regex = new RegExp(`${tag}[\\s\\S]*?${tag}`, 'g')
    expect(text.replace(regex, '')).toBe('BeforeAfter')
  })
})

describe('applyAssistantContract', () => {
  it('flags PROFILE_REQUIRED from the tag extras and drops audit', () => {
    const applied = applyAssistantContract(
      `${PROFILE_REQUIRED_TAG}\nI need to know which restrictions apply.`,
      {
        profileRequired: true,
        audit: normalizeAuditData({
          groups: [{ status: 'safe', items: [{ name: 'Water' }] }],
        }),
      },
    )
    expect(applied.profileRequired).toBe(true)
    expect(applied.audit).toBeUndefined()
    expect(applied.content).toContain('restrictions')
  })

  it('flags unmarked PROFILE_REQUIRED prose without extras', () => {
    const applied = applyAssistantContract(
      'I need to know which restrictions apply before I can say SAFE or NOT SAFE. Tell me your diet or allergies.\nI read: water, salt.',
      {
        audit: normalizeAuditData({
          groups: [{ status: 'safe', items: [{ name: 'Water' }] }],
        }),
      },
    )
    expect(applied.profileRequired).toBe(true)
    expect(applied.audit).toBeUndefined()
  })

  it('extracts understanding echo and confirm, keeps audit', () => {
    const audit = normalizeAuditData({
      groups: [{ status: 'avoid', items: [{ name: 'Milk' }] }],
    })
    const applied = applyAssistantContract(
      "I'll treat this as a dairy restriction for this check. Is lactose-free dairy acceptable, and should I save this on your profile?\n\nI understood: milk, sugar. Checking against: dairy-free.",
      { audit },
    )
    expect(applied.understandingEcho?.understood).toBe('milk, sugar')
    expect(applied.understandingEcho?.checkingAgainst).toBe('dairy-free')
    expect(applied.confirmPending).toBe(true)
    expect(applied.audit).toBe(audit)
  })

  it('flags emergency and drops audit', () => {
    const applied = applyAssistantContract(
      'If this is a medical emergency, stop using this app and call 999 now (or your local emergency number). I am not emergency services and I will not evaluate ingredients while you may need urgent care.',
      {
        audit: normalizeAuditData({
          groups: [{ status: 'safe', items: [{ name: 'Water' }] }],
        }),
      },
    )
    expect(applied.emergency).toBe(true)
    expect(applied.audit).toBeUndefined()
    expect(applied.profileRequired).toBe(false)
  })

  it('flags degraded fail-closed text', () => {
    const applied = applyAssistantContract(
      'I could not finish that check. Treat this as UNCERTAIN, not safe.',
      {
        audit: normalizeAuditData({
          groups: [{ status: 'safe', items: [{ name: 'Water' }] }],
          degraded: true,
        }),
      },
    )
    expect(applied.degraded).toBe(true)
    expect(applied.audit?.degraded).toBe(true)
  })
})

describe('replay old unmarked vs tagged grocery streams', () => {
  it('PROFILE_REQUIRED: unmarked prose, 200+marker only, and tagged body', async () => {
    const unmarked = await replayChatStream(OLD_UNMARKED_STREAMS.profileRequired)
    expect(unmarked.last.profileRequired).toBe(true)
    expect(unmarked.onboarding).toBe(true)
    expect(unmarked.last.audit).toBeUndefined()
    expect(unmarked.last.content).not.toContain(PROFILE_REQUIRED_TAG)

    const markerOnly = await replayChatStream(OLD_UNMARKED_STREAMS.profileRequiredMarkerOnly)
    expect(markerOnly.last.profileRequired).toBe(true)
    expect(markerOnly.onboarding).toBe(true)
    expect(markerOnly.last.content).toMatch(/restrictions apply/i)
    expect(markerOnly.last.content).not.toContain(PROFILE_REQUIRED_TAG)

    const tagged = await replayChatStream(STREAMS.profileRequired)
    expect(tagged.last.profileRequired).toBe(true)
    expect(tagged.onboarding).toBe(true)
    expect(tagged.last.audit).toBeUndefined()
    expect(tagged.last.content).not.toContain(PROFILE_REQUIRED_TAG)
    expect(tagged.last.content).toMatch(/I read: water, salt/)
  })

  it('confirm + echo: unmarked prose and tagged audit body', async () => {
    const unmarked = await replayChatStream(OLD_UNMARKED_STREAMS.lactoseConfirm)
    expect(unmarked.last.confirmPending).toBe(true)
    expect(unmarked.last.understandingEcho?.understood).toBe('milk, sugar')
    expect(unmarked.last.understandingEcho?.checkingAgainst).toBe('dairy-free')
    expect(unmarked.last.profileRequired).toBeFalsy()
    expect(unmarked.last.content).not.toMatch(/<<<[A-Z_]+>>>/)

    const tagged = await replayChatStream(STREAMS.lactoseConfirm)
    expect(tagged.last.confirmPending).toBe(true)
    expect(tagged.last.understandingEcho?.understood).toBe('milk, sugar')
    expect(tagged.last.audit?.groups[0]?.items[0]?.name).toBe('Milk')
    expect(tagged.last.content).not.toContain(INGREDIENT_AUDIT_TAG)
    expect(tagged.last.content).not.toContain(PROFILE_UPDATE_TAG)
  })

  it('yes / no / only-today remain unmarked follow-ups', async () => {
    const yes = await replayChatStream(OLD_UNMARKED_STREAMS.confirmYes)
    expect(yes.last.content).toMatch(/Saved on your profile/)
    const no = await replayChatStream(OLD_UNMARKED_STREAMS.confirmNo)
    expect(no.last.content).toMatch(/won't save that restriction/)
    const today = await replayChatStream(OLD_UNMARKED_STREAMS.confirmOnlyToday)
    expect(today.last.content).toMatch(/this session only/)
  })

  it('echo-only unmarked sentences parse without tags', async () => {
    const unmarked = await replayChatStream(OLD_UNMARKED_STREAMS.echoOnly)
    expect(unmarked.last.understandingEcho).toEqual({
      understood: 'milk, sugar',
      unused: 'leftover',
      checkingAgainst: 'dairy-free',
    })
    expect(unmarked.last.content).not.toMatch(/I understood:/)
  })

  it('emergency is unmarked prose with no <<<EMERGENCY>>> tag', async () => {
    expect(OLD_UNMARKED_STREAMS.emergencyGeneric).not.toContain('<<<EMERGENCY>>>')
    expect(STREAMS.emergencyGeneric).not.toContain('<<<EMERGENCY>>>')
    const unmarked = await replayChatStream(OLD_UNMARKED_STREAMS.emergencyGeneric)
    expect(unmarked.last.emergency).toBe(true)
    expect(unmarked.last.audit).toBeUndefined()
    const tagged = await replayChatStream(STREAMS.emergencyGeneric)
    expect(tagged.last.emergency).toBe(true)
  })

  it('degraded is the fail-closed sentence on both shapes', async () => {
    const unmarked = await replayChatStream(OLD_UNMARKED_STREAMS.degraded)
    expect(unmarked.last.degraded).toBe(true)
    const tagged = await replayChatStream(STREAMS.degraded)
    expect(tagged.last.degraded).toBe(true)
  })
})
