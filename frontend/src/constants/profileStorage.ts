/** Profile and user_id are client-held; auth/authorization is the backend's responsibility. */
export const USER_ID_STORAGE_KEY = 'ingresure_user_id'
/** When using server-issued identity (GET /anon-session), the returned token is stored here. */
export const ANON_SESSION_TOKEN_KEY = 'ingresure_anon_token'
export const PROFILE_STORAGE_KEY = 'ingresure_profile'
export const RECENT_CHECKS_STORAGE_KEY = 'ingresure_recent_checks'
export const PROFILE_BANNER_DISMISSED_KEY = 'ingresure_profile_banner_dismissed'
export const PROFILE_UPDATED_EVENT_NAME = 'ingresure-profile-updated'
