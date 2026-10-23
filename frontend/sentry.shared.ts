/**
 * Shared Sentry options. Safe to import without @sentry/nextjs.
 * sendDefaultPii is always false. Ingredient text and profile/health
 * fields are stripped in beforeSend. release = git SHA.
 */

export const REDACTED = "[REDACTED]";

const SENSITIVE_KEYS = new Set([
  "query",
  "message",
  "user_input",
  "output_text",
  "ingredients",
  "ingredients_text",
  "raw_label",
  "raw_input",
  "raw_inputs",
  "ingredient",
  "atom",
  "canonical_name",
  "userprofile",
  "user_profile",
  "profile",
  "profile_update",
  "profile_context",
  "dietary_preference",
  "diet_type",
  "allergens",
  "allergies",
  "lifestyle",
  "preferences",
  "restriction_ids",
  "email",
  "name",
  "body",
  "data",
  "request_body",
  "payload",
  "text",
  "prompt",
  "content",
]);

export function gitSha(): string {
  return (
    process.env.NEXT_PUBLIC_GIT_SHA ||
    process.env.VERCEL_GIT_COMMIT_SHA ||
    process.env.GITHUB_SHA ||
    "unknown"
  );
}

export function sentryDsn(): string {
  return (process.env.NEXT_PUBLIC_SENTRY_DSN || process.env.SENTRY_DSN || "").trim();
}

export function isSensitiveKey(key: unknown): boolean {
  if (key == null) return false;
  return SENSITIVE_KEYS.has(String(key).trim().toLowerCase());
}

export function scrubValue(value: unknown, key?: unknown): unknown {
  if (isSensitiveKey(key)) return REDACTED;
  if (Array.isArray(value)) return value.map((item) => scrubValue(item));
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = scrubValue(v, k);
    }
    return out;
  }
  return value;
}

type SentryEvent = {
  request?: {
    data?: unknown;
    headers?: Record<string, string>;
    [key: string]: unknown;
  };
  extra?: unknown;
  contexts?: unknown;
  user?: { id?: unknown; [key: string]: unknown };
  [key: string]: unknown;
};

export function beforeSend<T extends SentryEvent>(event: T): T {
  if (event.request) {
    const nextRequest = { ...event.request };
    delete nextRequest.data;
    if (nextRequest.headers) {
      const headers = { ...nextRequest.headers };
      for (const headerKey of Object.keys(headers)) {
        const lower = headerKey.toLowerCase();
        if (lower === "authorization" || lower === "cookie" || lower === "x-api-key") {
          headers[headerKey] = REDACTED;
        }
      }
      nextRequest.headers = headers;
    }
    event.request = nextRequest;
  }
  if (event.extra) event.extra = scrubValue(event.extra);
  if (event.contexts) event.contexts = scrubValue(event.contexts);
  if (event.user) {
    event.user = event.user.id != null ? { id: event.user.id } : {};
  }
  return event;
}

export function sentryInitOptions(dsn: string): Record<string, unknown> {
  return {
    dsn,
    release: gitSha(),
    sendDefaultPii: false,
    beforeSend,
    beforeSendTransaction: beforeSend,
  };
}
