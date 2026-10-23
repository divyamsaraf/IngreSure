/**
 * Node-runtime Sentry init. Safe to import: no-ops without a DSN or SDK.
 * Hook from a new instrumentation.ts — do not edit chat pages.
 */

import { sentryDsn, sentryInitOptions } from "./sentry.shared";

type SentrySdk = { init: (options: Record<string, unknown>) => void };

export function initSentry(sdk?: SentrySdk): boolean {
  const dsn = sentryDsn();
  if (!dsn || !sdk) return false;
  sdk.init(sentryInitOptions(dsn));
  return true;
}
