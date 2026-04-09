-- ============================================================================
-- Phase 5: Recommendation Tracker
-- Run in Supabase SQL Editor: Dashboard -> SQL Editor -> New Query -> paste -> Run
-- ============================================================================

-- -------------------------------------------------------------------------
-- Recommendation Tracker
-- Stores individual recommendations from AI analysis with user-updatable status.
-- -------------------------------------------------------------------------
create table public.recommendation_tracker (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    company_id  uuid not null references public.companies(id) on delete cascade,
    audit_id    uuid not null references public.audits(id) on delete cascade,
    dimension   text not null,
    recommendation text not null,
    status      text not null default 'not_started'
                check (status in ('not_started', 'in_progress', 'done')),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

alter table public.recommendation_tracker enable row level security;

create policy "Users can view own recommendations"
    on public.recommendation_tracker for select
    using (auth.uid() = user_id);

create policy "Users can insert own recommendations"
    on public.recommendation_tracker for insert
    with check (auth.uid() = user_id);

create policy "Users can update own recommendations"
    on public.recommendation_tracker for update
    using (auth.uid() = user_id);

-- -------------------------------------------------------------------------
-- Indexes
-- -------------------------------------------------------------------------
create index idx_rec_tracker_user on public.recommendation_tracker(user_id);
create index idx_rec_tracker_company on public.recommendation_tracker(company_id);
create index idx_rec_tracker_audit on public.recommendation_tracker(audit_id);

-- -------------------------------------------------------------------------
-- Add dimension_scores jsonb column to audits (for per-dimension history)
-- -------------------------------------------------------------------------
alter table public.audits
    add column if not exists dimension_scores jsonb;
