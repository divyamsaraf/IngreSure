import { describe, it, expect } from 'vitest'
import { normalizeAuditData } from './streamChatResponse'
import { PROFILE_REQUIRED_TAG, PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG } from '@/constants/chatProtocol'

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
    })
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
