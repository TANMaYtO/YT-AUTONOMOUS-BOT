-- Migration 002: Add missing columns and fix constraints
-- Run this in the Supabase SQL Editor

-- Add R2 storage columns to videos table
ALTER TABLE videos ADD COLUMN IF NOT EXISTS storage_key text;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS video_path text;

-- Fix plans upsert: ensure unique constraint exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint 
    WHERE conname = 'plans_user_id_key'
  ) THEN
    ALTER TABLE plans ADD CONSTRAINT plans_user_id_key UNIQUE (user_id);
  END IF;
END$$;

-- Add Stripe subscription tracking columns to plans table
ALTER TABLE plans ADD COLUMN IF NOT EXISTS stripe_customer_id text;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS stripe_subscription_id text;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS subscription_status text DEFAULT 'inactive';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS current_period_end timestamptz;

-- Remove Telegram columns (replaced by in-app notifications)
ALTER TABLE user_configs DROP COLUMN IF EXISTS telegram_bot_token;
ALTER TABLE user_configs DROP COLUMN IF EXISTS telegram_chat_id;
ALTER TABLE user_configs DROP COLUMN IF EXISTS daily_summary;
ALTER TABLE user_configs DROP COLUMN IF EXISTS failure_alerts;

-- Create in-app notifications table
CREATE TABLE IF NOT EXISTS app_notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  type text NOT NULL CHECK (type IN ('success', 'error', 'warning', 'info')),
  title text NOT NULL,
  message text NOT NULL,
  read boolean DEFAULT false,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS app_notifications_user_unread 
  ON app_notifications (user_id, read, created_at DESC);

ALTER TABLE app_notifications ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can read own notifications' AND tablename = 'app_notifications') THEN
    CREATE POLICY "Users can read own notifications"
      ON app_notifications FOR SELECT
      TO authenticated
      USING (auth.uid() = user_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can update own notifications' AND tablename = 'app_notifications') THEN
    CREATE POLICY "Users can update own notifications"
      ON app_notifications FOR UPDATE
      TO authenticated
      USING (auth.uid() = user_id);
  END IF;
END $$;
