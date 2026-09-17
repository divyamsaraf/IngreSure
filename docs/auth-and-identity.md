# Auth and identity (no sign-in / sign-up)

Profile and chat work without sign-in or sign-up. This doc describes the current behaviour and the **recommended options** for identifying users and hardening the system.

## Current behaviour

- **Frontend:** Generates a UUID once (e.g. via `crypto.randomUUID()`), stores it in `localStorage`, and sends it as `user_id` in profile and chat requests.
- **Backend:** Accepts `user_id` from the client. If chat is called without `user_id`, the backend generates a one-off anonymous id (`anon-<12 hex chars>`). All `user_id` values are validated (length ≤ 256, characters: letters, numbers, hyphens, underscores).
- **Storage:** Profiles are keyed by `user_id` in backend storage (e.g. file or Supabase). No passwords or sign-up flow.

## Best option for “auth” without sign-in

**Recommended: server-issued anonymous identity**

- Backend issues a **signed token** (e.g. short-lived JWT or signed cookie) that encodes an anonymous `user_id` (or session id that maps to a `user_id`).
- Frontend sends this token on each request (e.g. `Authorization` header or cookie). Backend verifies the signature and uses the embedded identity.
- **Benefits:** Identity is under backend control; no client-supplied user_id spoofing; you can rotate or revoke tokens; same flow works for “unique id per device/session” by binding the issued id to the first request from that client.

**Alternatives (short term):**

- **Harden current model:** Keep client-generated UUID + strict **rate limiting** and **user_id validation** (already in place). Easiest; good for low-risk / MVP.
- **BFF assigns user_id:** Next.js API routes (BFF) generate and store a `user_id` (e.g. in an httpOnly cookie) and always send that to the backend. Backend never trusts a client-origin `user_id` unless it comes from the BFF with a shared secret or signed token.

## Unique ID per user (device / IP / etc.)

- **Device fingerprint (browser):** Possible but brittle (browser/OS updates, privacy concerns, not stable across devices). Not recommended as the primary id.
- **IP address:** Not unique per user (NAT, mobile networks), changes often, and has privacy implications. Can be used as a **hint** for abuse detection or rate limiting, not as the sole user identity.
- **Best approach:** Use a **server-issued anonymous id** (or session id) created on first request. That id is effectively “per session/device” from the server’s perspective: same browser sending the same cookie/token gets the same id until expiry or clear. No sign-up; identity is stable for the lifetime of the token/session.

**Practical recommendation:** Implement a small **anonymous session** flow: e.g. `GET /anon-session` or first chat request returns a signed token (or sets an httpOnly cookie) containing a new `user_id`. Frontend uses that for all subsequent profile/chat requests. That gives you a unique, server-controlled id per “session/device” without sign-in or IP/device fingerprinting.

## Summary

| Goal                         | Best option                                      |
|-----------------------------|---------------------------------------------------|
| Auth without sign-in/sign-up| Server-issued anonymous token (JWT or signed cookie) |
| Unique id per user/device   | Backend-issued id in that token (session-bound)   |
| Avoid exposing 500 details | `ENVIRONMENT=production` (see main README)       |
| Safe user_id input          | Backend validation (length + format) — already in place |
