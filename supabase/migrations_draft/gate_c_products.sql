-- DRAFT ONLY. Not applied.
-- This file lives in supabase/migrations_draft/, not supabase/migrations/.
-- CI `supabase start` applies only supabase/migrations/; do not move this
-- file there until a later gate reviews and applies it.
--
-- Gate C products identity: (market, gtin).
-- Japan (JP) remains UNVERIFIED. A JP row must not enable the region
-- or ingest MEXT / OFF Japan. See deploy/japan_parser_plan.md.

create table if not exists public.gate_c_products (
  id uuid primary key default gen_random_uuid(),

  -- Identity key: market (region code) + GTIN.
  market text not null,
  gtin text not null,

  -- Full pack label text keyed by language code, e.g. {"ja": "...", "en": "..."}.
  label_text jsonb not null default '{}'::jsonb,

  -- Content fingerprint of the stored label set (sha256 hex of canonical JSON).
  label_version_hash text not null,

  -- Declared allergens as printed (not inferred). JSON array of name objects
  -- or strings, e.g. [{"lang":"ja","name":"小麦"}, "wheat"].
  declared_allergens jsonb not null default '[]'::jsonb,

  -- On-pack claims (e.g. allergen-free, organic). JSON array; empty if none.
  claims jsonb not null default '[]'::jsonb,

  -- SPDX id or source license class. Must be in license_allowlist.json
  -- before any ingest gate. Nullable until a source is attached.
  license text,

  -- Date the label/source was retrieved (ISO date). Required.
  retrieved_at date not null,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint gate_c_products_market_gtin_uidx unique (market, gtin),
  constraint gate_c_products_market_nonempty check (length(trim(market)) > 0),
  constraint gate_c_products_gtin_digits check (gtin ~ '^[0-9]{8,14}$'),
  constraint gate_c_products_label_text_object check (jsonb_typeof(label_text) = 'object'),
  constraint gate_c_products_allergens_array check (jsonb_typeof(declared_allergens) = 'array'),
  constraint gate_c_products_claims_array check (jsonb_typeof(claims) = 'array'),
  constraint gate_c_products_hash_nonempty check (length(trim(label_version_hash)) > 0)
);

create index if not exists gate_c_products_retrieved_idx
  on public.gate_c_products (retrieved_at);
create index if not exists gate_c_products_market_idx
  on public.gate_c_products (market);

comment on table public.gate_c_products is
  'DRAFT Gate C packaged-product rows keyed on market+GTIN. Not applied.';
comment on column public.gate_c_products.market is
  'Region/market code (e.g. AU, NZ, JP). JP is UNVERIFIED.';
comment on column public.gate_c_products.gtin is
  'GTIN-8/12/13/14 digits; text so leading zeros are preserved.';
comment on column public.gate_c_products.label_text is
  'Map of language code to full label text.';
comment on column public.gate_c_products.label_version_hash is
  'Hash of the stored label version; same (market, gtin) overwrites.';
comment on column public.gate_c_products.declared_allergens is
  'Allergens as declared on pack, not inferred.';
comment on column public.gate_c_products.claims is
  'On-pack claims as printed.';
comment on column public.gate_c_products.license is
  'Source license (SPDX / allowlist class). Required before ingest.';
comment on column public.gate_c_products.retrieved_at is
  'Retrieval date of the label/source.';

-- Backend-only: RLS on, no policies => only service_role can access.
alter table public.gate_c_products enable row level security;
