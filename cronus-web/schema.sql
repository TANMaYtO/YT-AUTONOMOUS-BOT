-- Enable pgcrypto for uuid generation
create extension if not exists "pgcrypto";

-- youtube_connections
create table youtube_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  channel_id text not null,
  channel_name text not null,
  subscriber_count integer default 0,
  access_token text not null,
  refresh_token text not null,
  token_expiry timestamptz not null,
  connected_at timestamptz default now()
);

-- user_configs
create table user_configs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  niche text,
  topics jsonb default '[]'::jsonb,
  characters jsonb default '[]'::jsonb,
  videos_per_day integer default 1 check (videos_per_day in (1, 2, 3)),
  upload_times jsonb default '[]'::jsonb,
  is_active boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  constraint user_configs_user_id_key unique (user_id)
);

-- videos
create table videos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  run_id text unique not null,
  title text not null,
  topic text not null,
  character_a text not null,
  character_b text,
  youtube_video_id text,
  youtube_url text,
  status text not null check (status in ('pending', 'uploaded', 'failed')),
  scheduled_upload_time timestamptz not null,
  error_message text,
  created_at timestamptz default now(),
  uploaded_at timestamptz
);

-- plans
create table plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  plan_type text not null check (plan_type in ('free', 'pro')),
  videos_per_day_limit integer default 1,
  started_at timestamptz default now(),
  expires_at timestamptz
);

-- Enable RLS
alter table youtube_connections enable row level security;
alter table user_configs enable row level security;
alter table videos enable row level security;
alter table plans enable row level security;

-- Create policies
create policy "Users can view own youtube connection" on youtube_connections for select using (auth.uid() = user_id);
create policy "Users can insert own youtube connection" on youtube_connections for insert with check (auth.uid() = user_id);
create policy "Users can update own youtube connection" on youtube_connections for update using (auth.uid() = user_id);
create policy "Users can delete own youtube connection" on youtube_connections for delete using (auth.uid() = user_id);

create policy "Users can view own config" on user_configs for select using (auth.uid() = user_id);
create policy "Users can insert own config" on user_configs for insert with check (auth.uid() = user_id);
create policy "Users can update own config" on user_configs for update using (auth.uid() = user_id);

create policy "Users can view own videos" on videos for select using (auth.uid() = user_id);
create policy "Users can insert own videos" on videos for insert with check (auth.uid() = user_id);
create policy "Users can update own videos" on videos for update using (auth.uid() = user_id);
create policy "Users can delete own videos" on videos for delete using (auth.uid() = user_id);

create policy "Users can view own plan" on plans for select using (auth.uid() = user_id);
