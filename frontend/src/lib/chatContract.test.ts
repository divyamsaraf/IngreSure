import { describe, it, expect } from 'vitest'
import {
  classifyConfirmReply,
  emergencyNumberForRegion,
  httpErrorMessage,
  isConfirmPrompt,
  isDegradedText,
  isEmergencyGuidance,
  isEmergencyQuery,
  parseUnderstandingEcho,
  regionFromLocale,
  resolveRegionHint,
} from './chatContract'

describe('region hint', () => {
  it('maps browser locales to verified numbers', () => {
    expect(regionFromLocale('en-US')).toBe('US')
    expect(regionFromLocale('en-GB')).toBe('GB')
    expect(regionFromLocale('en-IN')).toBe('IN')
    expect(regionFromLocale('en-AU')).toBe('AU')
    expect(regionFromLocale('en-NZ')).toBe('NZ')
    expect(regionFromLocale('en-CA')).toBe('CA')
    expect(regionFromLocale('ar-AE')).toBe('AE')
    expect(regionFromLocale('fr-FR')).toBe('EU')
    expect(regionFromLocale('en')).toBeNull()
    expect(regionFromLocale('xx-ZZ')).toBeNull()
  })

  it('prefers profile region over locale; unknown falls back', () => {
    expect(resolveRegionHint('UK', 'en-US')).toBe('UK')
    expect(resolveRegionHint('', 'en-GB')).toBe('GB')
    expect(resolveRegionHint(undefined, 'en')).toBeNull()
    expect(emergencyNumberForRegion('IN')).toBe('112')
    expect(emergencyNumberForRegion(null)).toBeNull()
  })
})

describe('emergency detection', () => {
  it('matches backend trigger phrases', () => {
    expect(isEmergencyQuery('Call 911 for me. Ingredients: water.')).toBe(true)
    expect(isEmergencyQuery("I ate peanuts and I can't breathe.")).toBe(true)
    expect(isEmergencyQuery('Call emergency. Ingredients: water.')).toBe(true)
    expect(isEmergencyQuery('Ingredients: water, sugar.')).toBe(false)
  })

  it('detects backend guidance text', () => {
    expect(
      isEmergencyGuidance(
        'If this is a medical emergency, stop using this app and call your local emergency number now: 911 (US/Canada). I am not emergency services and I will not evaluate ingredients while you may need urgent care.',
      ),
    ).toBe(true)
    expect(isEmergencyGuidance('I understood: water. Checking against: vegan.')).toBe(false)
  })
})

describe('confirm + degraded + echo', () => {
  it('classifies yes / no / only-today like the backend', () => {
    expect(classifyConfirmReply('yes')).toBe('yes')
    expect(classifyConfirmReply("that's right")).toBe('yes')
    expect(classifyConfirmReply('nope')).toBe('no')
    expect(classifyConfirmReply('only today')).toBe('only-today')
    expect(classifyConfirmReply('maybe later')).toBeNull()
  })

  it('detects lactose confirm prose', () => {
    expect(
      isConfirmPrompt(
        "I'll treat this as a dairy restriction for this check. Is lactose-free dairy acceptable, and should I save this on your profile?",
      ),
    ).toBe(true)
  })

  it('detects fail-closed degraded text', () => {
    expect(isDegradedText('I could not finish that check. Treat this as UNCERTAIN, not safe.')).toBe(
      true,
    )
  })

  it('extracts understanding echo and leaves the rest', () => {
    const parsed = parseUnderstandingEcho(
      'I understood: milk, sugar. I could not use: leftover. Checking against: dairy-free.\n\nChecking ingredients…',
    )
    expect(parsed.echo).toEqual({
      understood: 'milk, sugar',
      unused: 'leftover',
      checkingAgainst: 'dairy-free',
    })
    expect(parsed.remainder).toContain('Checking ingredients')
  })
})

describe('httpErrorMessage', () => {
  it('maps 413 / 422 / 429', () => {
    expect(httpErrorMessage(413)).toMatch(/too large/i)
    expect(httpErrorMessage(422)).toMatch(/could not be processed/i)
    expect(httpErrorMessage(429)).toMatch(/too many requests/i)
    expect(httpErrorMessage(500, 'Backend Error')).toBe('Backend Error')
  })
})
