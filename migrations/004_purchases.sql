-- Migration 004: one-time purchases (lifetime unlocks)
-- Run this in the Supabase SQL editor.
--
-- Context: as of Phase A pricing restructure, the Pro tier becomes a one-time
-- purchase ("Full Report") rather than a recurring subscription. This table
-- stores lifetime unlocks so get_subscription_tier() can grant access based
-- on a prior payment rather than an active subscription row.

create table if not exists public.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  stripe_customer_id text,
  stripe_payment_intent_id text unique,
  stripe_checkout_session_id text unique,
  stripe_price_id text,
  product_type text not null default 'full_report',
  amount_cents integer,
  currency text default 'usd',
  status text default 'completed',
  created_at timestamptz not null default now()
);

create index if not exists purchases_user_id_idx on public.purchases(user_id);
create index if not exists purchases_product_type_idx on public.purchases(product_type);

alter table public.purchases enable row level security;

-- Users can read their own purchases
drop policy if exists "Users can read own purchases" on public.purchases;
create policy "Users can read own purchases"
  on public.purchases for select
  using (auth.uid() = user_id);

-- Service role (used by the stripe-webhook Edge Function) can write any row
drop policy if exists "Service role can write purchases" on public.purchases;
create policy "Service role can write purchases"
  on public.purchases for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
