/** Contract-accurate grocery chat streams from PR #17. Not an invented backend. */

import { INGREDIENT_AUDIT_TAG, PROFILE_REQUIRED_TAG, PROFILE_UPDATE_TAG } from '../../src/constants/chatProtocol'

const emptyProfile = JSON.stringify({
  user_id: 'e2e-user',
  dietary_preference: 'No rules',
  allergens: [],
  lifestyle: [],
})

const dairyProfile = JSON.stringify({
  user_id: 'e2e-user',
  dietary_preference: 'Dairy-Free',
  allergens: [],
  lifestyle: [],
})

const veganProfile = JSON.stringify({
  user_id: 'e2e-user',
  dietary_preference: 'Vegan',
  allergens: [],
  lifestyle: [],
})

function profileBlock(json: string): string {
  return `${PROFILE_UPDATE_TAG}${json}${PROFILE_UPDATE_TAG}`
}

const avoidMilkAudit = JSON.stringify({
  summary: '0 Safe, 1 Avoid, 0 Depends',
  groups: [{ status: 'avoid', items: [{ name: 'Milk', reason: 'dairy product' }] }],
  explanation: 'Based on your dairy-free diet, this product is not suitable.',
  explanation_source: 'template',
  confidence_tier: 'standard',
})

const bilingualAudit = JSON.stringify({
  summary: '1 Safe, 1 Avoid, 0 Depends',
  groups: [
    { status: 'avoid', items: [{ name: 'Milk' }] },
    { status: 'safe', items: [{ name: 'Sugar' }] },
  ],
  explanation: 'Milk conflicts with a dairy-free profile.',
  explanation_source: 'template',
  confidence_tier: 'standard',
})

export const STREAMS = {
  profileRequired: `${PROFILE_REQUIRED_TAG}\n\nI need to know which restrictions apply before I can say SAFE or NOT SAFE. Tell me your diet or allergies.\nI read: water, salt.\n${profileBlock(emptyProfile)}`,

  lactoseConfirm: `I'll treat this as a dairy restriction for this check. Is lactose-free dairy acceptable, and should I save this on your profile?\n\nI understood: milk, sugar. Checking against: dairy-free.\n\nChecking ingredients…\n\n${INGREDIENT_AUDIT_TAG}${avoidMilkAudit}${INGREDIENT_AUDIT_TAG}${profileBlock(emptyProfile)}`,

  confirmYes: `Saved on your profile.\n${profileBlock(dairyProfile)}`,

  confirmNo: `Okay, I won't save that restriction.\n${profileBlock(emptyProfile)}`,

  confirmOnlyToday: `I'll keep this restriction for this session only; it is not saved.\n${profileBlock(emptyProfile)}`,

  emergencyGeneric: `If this is a medical emergency, stop using this app and call your local emergency number now: 911 (US/Canada), 999 (UK), 112 (EU/India), 000 (Australia), 111 (New Zealand), 998 (UAE). I am not emergency services and I will not evaluate ingredients while you may need urgent care.\n${profileBlock(emptyProfile)}`,

  productName: `I need the ingredient list from the pack, not just the product name. I will not mark this SAFE from the name alone.\n${profileBlock(veganProfile)}`,

  bilingual: `I understood: sugar, milk, sucre, lait, zucker, milch. Checking against: dairy-free.\n\nChecking ingredients…\n\n${INGREDIENT_AUDIT_TAG}${bilingualAudit}${INGREDIENT_AUDIT_TAG}${profileBlock(dairyProfile)}`,

  multiProduct: `That looks like more than one product. Paste one ingredient list at a time so I don't combine them into one verdict.\n${profileBlock(veganProfile)}`,

  unsupported: `I don't evaluate keto. I can still check ingredients you paste against a diet or allergy profile.\n${profileBlock(emptyProfile)}`,

  degraded: `I could not finish that check. Treat this as UNCERTAIN, not safe.\n`,
} as const
