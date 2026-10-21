/** Frontend consumption of the grocery chat stream. See frontend/CHAT_CONTRACT.md. */

export const FAIL_CLOSED_TEXT =
  'I could not finish that check. Treat this as UNCERTAIN, not safe.'

export const GENERIC_EMERGENCY_NUMBERS = [
  { number: '911', place: 'US/Canada' },
  { number: '999', place: 'UK' },
  { number: '112', place: 'EU/India' },
  { number: '000', place: 'Australia' },
  { number: '111', place: 'New Zealand' },
  { number: '998', place: 'UAE' },
] as const

export const EMERGENCY_BY_REGION: Record<string, { number: string; label: string }> = {
  US: { number: '911', label: 'US' },
  CA: { number: '911', label: 'Canada' },
  GB: { number: '999', label: 'UK' },
  UK: { number: '999', label: 'UK' },
  EU: { number: '112', label: 'EU' },
  AU: { number: '000', label: 'Australia' },
  NZ: { number: '111', label: 'New Zealand' },
  AE: { number: '998', label: 'UAE' },
  IN: { number: '112', label: 'India' },
}

const EU_COUNTRY_CODES = new Set(['FR', 'DE', 'IT', 'ES', 'NL', 'IE', 'PT', 'SE', 'PL', 'BE'])

const EMERGENCY_QUERY_PATTERNS = [
  /\b(?:call|dial)\s*(?:911|999|112|000|111|998)\b/i,
  /\b911\b/,
  /\bcan(?:'|’)t\s+breathe\b/i,
  /\bcannot\s+breathe\b/i,
  /\banaphylax/i,
  /\b(?:having|had)\s+a\s+reaction\b/i,
  /\ballergic\s+reaction\b/i,
  /\bthroat\s+(?:is\s+)?(?:closing|swelling|closing\s+up)\b/i,
  /\bepipen\b|\bepi-pen\b/i,
  /\bcall\s+emergency\b/i,
]

const CONFIRM_PROMPT_PATTERNS = [
  /should i save this on your profile/i,
  /i will not save it until you confirm/i,
  /confirm if i should change your saved profile/i,
  /confirm whose profile to use/i,
  /i will not remove a (?:medical |saved )?restriction/i,
  /is lactose-free dairy acceptable/i,
]

const CONFIRM_YES = /^\s*(yes|y|yeah|yep|confirm|that's right|thats right|ok|okay)\s*[.!]?\s*$/i
const CONFIRM_NO = /^\s*(no|n|nope|nah|cancel|never mind|nevermind)\s*[.!]?\s*$/i
const CONFIRM_TODAY =
  /^\s*(only today|just today|this once|just for today|today only)\s*[.!]?\s*$/i

export interface UnderstandingEcho {
  preface?: string
  understood?: string
  unused?: string
  checkingAgainst?: string
}

function normalizeRegion(code: string): string | null {
  const region = code.trim().toUpperCase()
  if (!region) return null
  if (region in EMERGENCY_BY_REGION) return region
  if (EU_COUNTRY_CODES.has(region)) return 'EU'
  return null
}

/** Profile region wins; otherwise browser locale. Unknown → null (generic list). */
export function resolveRegionHint(
  profileRegion?: string | null,
  locale?: string | null,
): string | null {
  const fromProfile = normalizeRegion(profileRegion ?? '')
  if (fromProfile) return fromProfile
  return regionFromLocale(locale)
}

export function regionFromLocale(locale?: string | null): string | null {
  if (!locale) return null
  const parts = locale.replace('_', '-').split('-').filter(Boolean)
  if (parts.length < 2) return null
  return normalizeRegion(parts[parts.length - 1] ?? '')
}

export function emergencyNumberForRegion(region: string | null): string | null {
  if (!region) return null
  return EMERGENCY_BY_REGION[region]?.number ?? null
}

export function isEmergencyQuery(text: string): boolean {
  return EMERGENCY_QUERY_PATTERNS.some((re) => re.test(text || ''))
}

export function isEmergencyGuidance(text: string): boolean {
  const t = text || ''
  if (/i am not emergency services/i.test(t) && /medical emergency/i.test(t)) return true
  return isEmergencyQuery(t) && /stop using this app/i.test(t)
}

export function isDegradedText(text: string): boolean {
  return /treat this as uncertain, not safe/i.test(text || '')
}

export function isConfirmPrompt(text: string): boolean {
  const t = text || ''
  return CONFIRM_PROMPT_PATTERNS.some((re) => re.test(t))
}

export function classifyConfirmReply(text: string): 'yes' | 'no' | 'only-today' | null {
  const q = text || ''
  if (CONFIRM_YES.test(q)) return 'yes'
  if (CONFIRM_NO.test(q)) return 'no'
  if (CONFIRM_TODAY.test(q)) return 'only-today'
  return null
}

const ECHO_PREFACES = [
  'Treating this as a recipe, not a packaged label.',
  'That looks like more than one product.',
  'That looks like a product name, not an ingredient list.',
]

const UNDERSTOOD_RE = /I understood:\s*([^.]+)\./i
const UNUSED_RE = /I could not use:\s*([^.]+)\./i
const CHECKING_RE = /Checking against:\s*([^.]+)\./i

export function parseUnderstandingEcho(text: string): {
  echo: UnderstandingEcho | null
  remainder: string
} {
  const raw = text || ''
  const echo: UnderstandingEcho = {}
  let remainder = raw

  for (const preface of ECHO_PREFACES) {
    if (remainder.includes(preface)) {
      echo.preface = preface
      remainder = remainder.replace(preface, '')
      break
    }
  }

  const understood = remainder.match(UNDERSTOOD_RE)
  if (understood) {
    echo.understood = understood[1].trim()
    remainder = remainder.replace(understood[0], '')
  }
  const unused = remainder.match(UNUSED_RE)
  if (unused) {
    echo.unused = unused[1].trim()
    remainder = remainder.replace(unused[0], '')
  }
  const checking = remainder.match(CHECKING_RE)
  if (checking) {
    echo.checkingAgainst = checking[1].trim()
    remainder = remainder.replace(checking[0], '')
  }

  const hasEcho = Boolean(echo.preface || echo.understood || echo.unused || echo.checkingAgainst)
  return {
    echo: hasEcho ? echo : null,
    remainder: remainder.replace(/^\s+/, '').replace(/\n{3,}/g, '\n\n').trim(),
  }
}

export function httpErrorMessage(status: number, detail?: string): string {
  if (status === 413) return 'This request is too large. Shorten the label and try again.'
  if (status === 422) return 'That request could not be processed. Check the label and try again.'
  if (status === 429) return 'Too many requests. Please wait a moment and try again.'
  if (typeof detail === 'string' && detail.trim()) return detail.trim()
  return 'Sorry, I encountered an error. Please try again.'
}
