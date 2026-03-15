export const PROFILE_REQUIRED_TAG = '<<<PROFILE_REQUIRED>>>'
export const PROFILE_UPDATE_TAG = '<<<PROFILE_UPDATE>>>'
export const INGREDIENT_AUDIT_TAG = '<<<INGREDIENT_AUDIT>>>'

/** Fallback max length when config not available. Single source: constants/configDefaults.ts; prefer backend GET /config. */
export { FALLBACK_MAX_CHAT_MESSAGE_LENGTH as MAX_CHAT_MESSAGE_LENGTH } from './configDefaults'
