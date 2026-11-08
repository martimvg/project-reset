-- Applicant Desk database (Supabase / PostgreSQL)
-- Run this once in Supabase: SQL Editor -> New query -> paste -> Run.
--
-- Plain-English summary:
--   openings, firms, meta  = public job data. Anyone can read it; only the robot (secret key) and admins write it.
--   profiles, applications, todos, prep_answers, ai_usage = each student's own data.
--     "Row level security" makes sure a student can only ever read or change their own rows.

-- ---------- public job data ----------
create table if not exists public.openings (
  id            text primary key,
  firm          text not null,
  title         text not null,
  url           text default '',
  location      text default 'London',
  category      text default 'Investment Banking',   -- 'Investment Banking' | 'Private Equity'
  area          text default '',
  level         text default 'Summer Internship',    -- one of the seven programme types
  posted        text default '',
  first_seen    text default '',
  last_checked  text default '',
  deadline      text default '',                     -- 'YYYY-MM-DD' or ''
  rolling       boolean default false,
  status        text default 'open',                 -- 'open' | 'closed'
  source        text default 'robot',                -- 'robot' | 'hand' | 'found' | 'manual'
  found_on      text default '',
  note          text default '',
  unconfirmed   boolean default false,
  apply         jsonb default '{"method":"web"}'::jsonb,
  updated_at    timestamptz default now()
);

create table if not exists public.firms (
  id         text primary key,
  name       text not null,
  sector     text default '',
  category   text default 'Investment Banking',
  url        text default '',
  readable   boolean default false,
  last_read  text default '',
  updated_at timestamptz default now()
);

create table if not exists public.meta (
  key        text primary key,
  value      jsonb not null,
  updated_at timestamptz default now()
);

-- ---------- each student's own data ----------
create table if not exists public.profiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  name       text default '',
  cv         text default '',
  letter     text default '',
  is_admin   boolean default false,
  plan       text default 'free',                    -- 'free' | 'premium' (used when payments arrive)
  created_at timestamptz default now()
);

create table if not exists public.applications (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  opening_id  text,
  company     text not null,
  role        text not null,
  category    text default 'Investment Banking',
  level       text default 'Summer Internship',
  location    text default 'London',
  stage       text default 'Not started',
  max_stage   text default '',
  deadline    text default '',
  applied_on  text default '',
  next_step   text default '',
  next_date   text default '',
  link        text default '',
  notes       text default '',
  jd          text default '',
  cv_t        text default '',
  letter_t    text default '',
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

create table if not exists public.todos (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title      text not null,
  type       text default 'Other',
  firm       text default '',
  due        text default '',
  done       boolean default false,
  app_id     uuid references public.applications(id) on delete cascade,
  created_at timestamptz default now()
);

create table if not exists public.prep_answers (
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  question_id text not null,
  answer      text default '',
  feedback    text default '',
  done        boolean default false,
  updated_at  timestamptz default now(),
  primary key (user_id, question_id)
);

create table if not exists public.ai_usage (
  id         bigserial primary key,
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  kind       text not null,                            -- 'cv' | 'letter' | 'feedback'
  created_at timestamptz default now()
);

create index if not exists applications_user on public.applications(user_id);
create index if not exists todos_user on public.todos(user_id);
create index if not exists ai_usage_user_time on public.ai_usage(user_id, created_at);

-- ---------- a profile is created automatically when someone signs up ----------
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id) values (new.id) on conflict do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select is_admin from public.profiles where id = auth.uid()), false)
$$;

-- ---------- access rules (row level security) ----------
alter table public.openings     enable row level security;
alter table public.firms        enable row level security;
alter table public.meta         enable row level security;
alter table public.profiles     enable row level security;
alter table public.applications enable row level security;
alter table public.todos        enable row level security;
alter table public.prep_answers enable row level security;
alter table public.ai_usage     enable row level security;

drop policy if exists "anyone reads openings" on public.openings;
create policy "anyone reads openings" on public.openings for select using (true);
drop policy if exists "admins add roles" on public.openings;
create policy "admins add roles" on public.openings for insert with check (public.is_admin());
drop policy if exists "admins edit roles" on public.openings;
create policy "admins edit roles" on public.openings for update using (public.is_admin());

drop policy if exists "anyone reads firms" on public.firms;
create policy "anyone reads firms" on public.firms for select using (true);
drop policy if exists "anyone reads meta" on public.meta;
create policy "anyone reads meta" on public.meta for select using (true);

drop policy if exists "own profile" on public.profiles;
create policy "own profile" on public.profiles for select using (id = auth.uid());
drop policy if exists "edit own profile" on public.profiles;
create policy "edit own profile" on public.profiles for update using (id = auth.uid())
  with check (id = auth.uid() and is_admin = (select p.is_admin from public.profiles p where p.id = auth.uid())
              and plan = (select p.plan from public.profiles p where p.id = auth.uid()));

drop policy if exists "own applications" on public.applications;
create policy "own applications" on public.applications for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own todos" on public.todos;
create policy "own todos" on public.todos for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own prep" on public.prep_answers;
create policy "own prep" on public.prep_answers for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own ai usage" on public.ai_usage;
create policy "own ai usage" on public.ai_usage for select using (user_id = auth.uid());
drop policy if exists "log own ai usage" on public.ai_usage;
create policy "log own ai usage" on public.ai_usage for insert with check (user_id = auth.uid());
