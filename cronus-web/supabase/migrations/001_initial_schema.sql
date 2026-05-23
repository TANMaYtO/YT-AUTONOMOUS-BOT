-- 1. Create Tables
CREATE TABLE youtube_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  channel_id text NOT NULL,
  channel_name text NOT NULL,
  subscriber_count integer DEFAULT 0,
  access_token text,
  refresh_token text,
  token_expiry timestamptz,
  connected_at timestamptz DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE user_configs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  niche text,
  topics jsonb DEFAULT '[]',
  characters jsonb DEFAULT '[]',
  videos_per_day integer DEFAULT 3,
  upload_times jsonb DEFAULT '["09:00","15:00","20:00"]',
  is_active boolean DEFAULT false,
  last_run_at timestamptz,
  telegram_bot_token text,
  telegram_chat_id text,
  daily_summary boolean DEFAULT true,
  failure_alerts boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE videos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  run_id text UNIQUE,
  title text,
  topic text,
  character_a text,
  character_b text,
  youtube_video_id text,
  youtube_url text,
  status text DEFAULT 'pending' CHECK (status IN ('pending', 'uploaded', 'failed')),
  scheduled_upload_time timestamptz,
  error_message text,
  updated_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

CREATE TABLE plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  plan_type text DEFAULT 'free' CHECK (plan_type IN ('free', 'pro')),
  videos_per_day_limit integer DEFAULT 1,
  started_at timestamptz DEFAULT now(),
  expires_at timestamptz,
  UNIQUE(user_id)
);

-- 2. Indexes
CREATE INDEX idx_videos_user_created ON videos(user_id, created_at DESC);

-- 3. Row Level Security (RLS)
ALTER TABLE youtube_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own youtube_connections" 
  ON youtube_connections FOR ALL 
  USING (auth.uid() = user_id) 
  WITH CHECK (auth.uid() = user_id);

ALTER TABLE user_configs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own user_configs" 
  ON user_configs FOR ALL 
  USING (auth.uid() = user_id) 
  WITH CHECK (auth.uid() = user_id);

ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own videos" 
  ON videos FOR ALL 
  USING (auth.uid() = user_id) 
  WITH CHECK (auth.uid() = user_id);

ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own plans" 
  ON plans FOR ALL 
  USING (auth.uid() = user_id) 
  WITH CHECK (auth.uid() = user_id);
