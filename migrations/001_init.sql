-- Enable uuid generation
create extension if not exists "pgcrypto";

-- Conversations state (no message text stored)
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  ig_user_id text not null,
  peer_id text not null,
  conversation_ext_id text null,

  created_at timestamptz not null default now(),
  last_message_at timestamptz null,

  last_preprocessed_at timestamptz null,
  pending_count int not null default 0,
  pending_since timestamptz null,

  rolling_summary text null,
  status text not null default 'active',

  constraint conversations_status_chk check (status in ('active','archived')),
  constraint conversations_uniq unique (ig_user_id, peer_id)
);

create index if not exists conversations_pending_idx
  on public.conversations (pending_count, pending_since);

create index if not exists conversations_last_message_idx
  on public.conversations (last_message_at desc);

-- Message events (NO text)
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

-- Preprocess runs (payload plan only; no transcript stored)
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
  constraint preprocess_status_chk check (status in ('ready_for_ai','skipped','error'))
);

create index if not exists preprocess_runs_created_idx
  on public.preprocess_runs (created_at desc);

-- (Future) risk cases and snapshots - placeholders (not used yet)
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