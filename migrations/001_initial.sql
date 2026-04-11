-- ============================================================================
-- Structural Advantage Audit, Initial Schema
-- Run in Supabase SQL Editor: Dashboard → SQL Editor → New Query → paste → Run
-- ============================================================================

-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- -------------------------------------------------------------------------
-- Companies
-- -------------------------------------------------------------------------
create table public.companies (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    name        text not null,
    industry    text,
    revenue_band text,
    ebitda_margin integer,
    headcount   integer,
    years       integer,
    owner_hours integer,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

alter table public.companies enable row level security;

create policy "Users can view own companies"
    on public.companies for select
    using (auth.uid() = user_id);

create policy "Users can insert own companies"
    on public.companies for insert
    with check (auth.uid() = user_id);

create policy "Users can update own companies"
    on public.companies for update
    using (auth.uid() = user_id);

-- -------------------------------------------------------------------------
-- Audits
-- -------------------------------------------------------------------------
create table public.audits (
    id              uuid primary key default uuid_generate_v4(),
    company_id      uuid not null references public.companies(id) on delete cascade,
    user_id         uuid not null references auth.users(id) on delete cascade,
    mode            text not null default 'lead_magnet',
    answers         jsonb not null default '{}',
    firmographics   jsonb not null default '{}',
    result          jsonb not null default '{}',
    ai_recommendations jsonb,
    overall_score   real,
    overall_band    text,
    created_at      timestamptz not null default now()
);

alter table public.audits enable row level security;

create policy "Users can view own audits"
    on public.audits for select
    using (auth.uid() = user_id);

create policy "Users can insert own audits"
    on public.audits for insert
    with check (auth.uid() = user_id);

-- -------------------------------------------------------------------------
-- Indexes
-- -------------------------------------------------------------------------
create index idx_companies_user on public.companies(user_id);
create index idx_audits_user on public.audits(user_id);
create index idx_audits_company on public.audits(company_id);
create index idx_audits_created on public.audits(created_at desc);
