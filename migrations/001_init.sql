-- Enable uuid generation
create extension if not exists "pgcrypto";

-- =========================================================
-- 1) App users (padres/tutores) + children
-- =========================================================
create table if not exists public.app_users (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  full_name text null,
  created_at timestamptz not null default now(),

  constraint app_users_email_uniq unique (email)
);

create table if not exists public.children (
  id uuid primary key default gen_random_uuid(),
  parent_id uuid not null references public.app_users(id) on delete cascade,

  display_name text not null, -- alias sin PII (ej. "Hijo 1")
  created_at timestamptz not null default now(),

  constraint children_user_display_uniq unique (user_id, display_name)
);

-- =========================================================
-- 2) Instagram accounts (cuentas que se monitorean)
-- =========================================================
create table if not exists public.ig_accounts (
  id uuid primary key default gen_random_uuid(),
  child_id uuid not null references public.children(id) on delete cascade,

  -- Instagram-side identifiers
  ig_user_id text not null,          -- el IG account id que aparece en entry.id
  ig_username text null,

  -- Token storage (MVP). En producción pensar cifrado/rotación.
  access_token text null,
  token_expires_at timestamptz null,

  -- Webhook / routing
  webhook_enabled boolean not null default true,

  status text not null default 'active', -- active|paused|revoked
  created_at timestamptz not null default now(),

  constraint ig_accounts_status_chk check (status in ('active','paused','revoked')),
  constraint ig_accounts_ig_user_id_uniq unique (ig_user_id)
);

create index if not exists ig_accounts_child_idx
  on public.ig_accounts (child_id);

-- =========================================================
-- 3) Conversations (estado por chat, ligado a ig_account)
-- =========================================================
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),

  ig_account_id uuid not null references public.ig_accounts(id) on delete cascade,

  -- peer = la otra persona del chat
  peer_id text not null,

  -- Conversations API id (aWdf...) para reconstruir transcript
  conversation_ext_id text null,

  created_at timestamptz not null default now(),
  last_message_at timestamptz null,

  last_preprocessed_at timestamptz null,
  pending_count int not null default 0,
  pending_since timestamptz null,

  -- rolling_summary en jsonb
  rolling_summary jsonb null,

  status text not null default 'active',

  constraint conversations_status_chk check (status in ('active','archived')),
  constraint conversations_uniq unique (ig_account_id, peer_id)
);

create index if not exists conversations_pending_idx
  on public.conversations (pending_count, pending_since);

create index if not exists conversations_last_message_idx
  on public.conversations (last_message_at desc);

create index if not exists conversations_ig_account_idx
  on public.conversations (ig_account_id);

-- =========================================================
-- 4) Message events (NO text)
-- =========================================================
create table if not exists public.message_events (
  id uuid primary key default gen_random_uuid(),

  conversation_id uuid not null references public.conversations(id) on delete cascade,

  mid text not null,
  sent_at timestamptz not null,
  direction text not null,
  text_hash text null,
  features jsonb null,

  created_at timestamptz not null default now(),

  constraint message_events_direction_chk check (direction in ('inbound','outbound')),
  constraint message_events_mid_uniq unique (mid)
);

create index if not exists message_events_conv_sent_idx
  on public.message_events (conversation_id, sent_at desc);

-- =========================================================
-- 5) Preprocess runs
-- =========================================================
create table if not exists public.preprocess_runs (
  id uuid primary key default gen_random_uuid(),

  conversation_id uuid not null references public.conversations(id) on delete cascade,

  window_start timestamptz not null,
  window_end timestamptz not null,

  trigger text not null,
  status text not null default 'ready_for_ai',
  message_count int not null default 0,

  fetch_plan jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  error text null,

  constraint preprocess_trigger_chk check (trigger in ('hourly','threshold_10')),
  constraint preprocess_status_chk check (status in ('ready_for_ai','processing','ai_done','skipped','error'))
);

create index if not exists preprocess_runs_created_idx
  on public.preprocess_runs (created_at desc);

create index if not exists preprocess_runs_status_idx
  on public.preprocess_runs (status, created_at);

-- =========================================================
-- 6) Risk cases and snapshots
-- =========================================================
create table if not exists public.risk_cases (
  id uuid primary key default gen_random_uuid(),

  conversation_id uuid not null references public.conversations(id) on delete cascade,
  opened_at timestamptz not null default now(),

  status text not null default 'open',
  stage int null,
  confidence numeric null,
  reason_safe text null,
  evidence_window_start timestamptz null,
  evidence_window_end timestamptz null,

  constraint risk_cases_status_chk check (status in ('open','closed'))
);

create table if not exists public.case_snapshots (
  id uuid primary key default gen_random_uuid(),
  risk_case_id uuid not null references public.risk_cases(id) on delete cascade,
  snapshot_json jsonb not null,
  encrypted boolean not null default false,
  created_at timestamptz not null default now()
);

-- Notes:
-- For MVP, use service role key from backend; you can enable RLS later.