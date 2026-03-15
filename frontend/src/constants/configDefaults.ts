/**
 * Single source for fallback config values when backend GET /config is unavailable.
 * Prefer backend config when loaded; use these only as fallbacks for BFF and client.
 */
export const FALLBACK_MAX_CHAT_MESSAGE_LENGTH = 8192
