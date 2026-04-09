-- ============================================================================
-- Phase 7: Subscriptions table for Stripe billing
-- Run in Supabase SQL Editor: Dashboard -> SQL Editor -> New Query -> paste -> Run
-- ============================================================================

create table public.subscriptions (
    id                      uuid primary key default uuid_generate_v4(),
    user_id                 uuid not null references auth.users(id) on delete cascade,
    tier                    text not null default 'free'
                            check (tier in ('free', 'pro', 'team')),
    status                  text not null default 'active'
                            check (status in ('active', 'canceled', 'past_due', 'trialing')),
    stripe_customer_id      text,
    stripe_subscription_id  text unique,
    stripe_price_id         text,
    current_period_start    timestamptz,
    current_period_end      timestamptz,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now()
);

alter table public.subscriptions enable row level security;

create policy "Users can view own subscriptions"
    on public.subscriptions for select
    using (auth.uid() = user_id);

-- Only the service role (webhook handler) should insert/update subscriptions,
-- but we also allow the user to read their own. For the webhook, use the
-- service_role key (not the publishable key).
create policy "Service role can manage subscriptions"
    on public.subscriptions for all
    using (true)
    with check (true);

-- -------------------------------------------------------------------------
-- Indexes
-- -------------------------------------------------------------------------
create index idx_subscriptions_user on public.subscriptions(user_id);
create index idx_subscriptions_stripe_customer on public.subscriptions(stripe_customer_id);
create index idx_subscriptions_stripe_sub on public.subscriptions(stripe_subscription_id);
