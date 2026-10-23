/**
 * Browser Sentry init. Safe to import: no-ops without a DSN or an SDK argument.
 * Hook from a new instrumentation-client.ts — do not edit chat pages.
 * See docs/observability/app_hooks.md.
 */

import { sentryDsn, sentryInitOptions } from "./sentry.shared";

type SentrySdk = { init: (options: Record<string, unknown>) => void };

export function initSentry(sdk?: SentrySdk): boolean {
  const dsn = sentryDsn();
  if (!dsn || !sdk) return false;
  sdk.init(sentryInitOptions(dsn));
  return true;
}
