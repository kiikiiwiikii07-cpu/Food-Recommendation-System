-- Initial schema for Supabase deployments. Backend service role owns protected writes.
create extension if not exists pgcrypto;

create table if not exists public.foods (
  id text primary key, name text not null, description text not null, category text not null,
  cuisine text not null, ingredients jsonb not null default '[]', allergens jsonb,
  allergen_status text not null default 'unknown' check (allergen_status in ('known','unknown','incomplete')),
  diet text not null, serving_size text, prep_minutes integer check (prep_minutes > 0),
  nutrition jsonb, provenance text not null, confidence text not null,
  image_url text, image_attribution text, published boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists public.user_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  diet text not null default 'any', allergies text[] not null default '{}',
  avoid_ingredients text[] not null default '{}', cuisines text[] not null default '{}',
  meal_slots text[] not null default '{breakfast,lunch,dinner}', max_minutes integer not null default 60,
  budget numeric, updated_at timestamptz not null default now()
);
create table if not exists public.recommendation_events (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
  food_id text not null references public.foods(id), meal_type text not null,
  algorithm_version text not null, ranking_signals jsonb not null default '{}', created_at timestamptz not null default now()
);
create table if not exists public.meal_feedback (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
  food_id text not null references public.foods(id), action text not null check (action in ('like','dislike','not_interested','save','alternative')),
  reason text, created_at timestamptz not null default now()
);
create table if not exists public.consumed_meals (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
  food_id text not null references public.foods(id), servings numeric not null check (servings > 0),
  consumed_at timestamptz not null default now()
);
create index if not exists recommendation_history_user_time on public.recommendation_events(user_id, created_at desc);
create index if not exists feedback_user_food_time on public.meal_feedback(user_id, food_id, created_at desc);
create index if not exists consumed_user_time on public.consumed_meals(user_id, consumed_at desc);
alter table public.foods enable row level security;
alter table public.user_preferences enable row level security;
alter table public.recommendation_events enable row level security;
alter table public.meal_feedback enable row level security;
alter table public.consumed_meals enable row level security;
create policy "published foods are readable" on public.foods for select using (published);
create policy "own preferences" on public.user_preferences for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own recommendations" on public.recommendation_events for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own feedback" on public.meal_feedback for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own consumption" on public.consumed_meals for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
