-- Append-only API request history for analytics/sync (backend service_role writes only).
-- RLS enabled with no policies => anon/authenticated cannot access; service role bypasses RLS.

create table if not exists public.request_history (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone not null default timezone('utc'::text, now()),
  started_at timestamp with time zone not null,
  completed_at timestamp with time zone,
  duration_ms integer,
  user_id text,
  route text not null,
  status integer not null,
  error_code text,
  user_input text,
  output_text text,
  metadata jsonb,
  profile_update jsonb
);

create index if not exists idx_request_history_started_at on public.request_history (started_at desc);
create index if not exists idx_request_history_completed_at on public.request_history (completed_at desc);
create index if not exists idx_request_history_user_started on public.request_history (user_id, started_at desc);
create index if not exists idx_request_history_route_started on public.request_history (route, started_at desc);

alter table public.request_history enable row level security;

comment on table public.request_history is 'Write-only analytics from FastAPI; no client RLS policies.';
