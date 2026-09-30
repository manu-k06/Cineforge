-- Cineforge: User Profiles Schema & Automatic Trigger
-- Run this script in your Supabase Project Dashboard -> SQL Editor

-- 1. Enable UUID Extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. User Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    avatar_id TEXT NOT NULL DEFAULT 'director',
    preferences JSONB DEFAULT '{"quality": "auto", "subtitles": false}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for speedy profile queries
CREATE INDEX IF NOT EXISTS idx_profiles_updated 
ON public.profiles(updated_at DESC);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- 4. Policies for profiles: Users can view, insert, and update their own profile
CREATE POLICY "Users can view their own profile" 
ON public.profiles FOR SELECT 
USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile" 
ON public.profiles FOR INSERT 
WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update their own profile" 
ON public.profiles FOR UPDATE 
USING (auth.uid() = id);

-- 5. Trigger Function to automatically create a profile row on signup
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, avatar_id)
  VALUES (
    new.id, 
    COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)), 
    COALESCE(new.raw_user_meta_data->>'avatar_id', 'director')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Trigger registration on auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 7. Backfill existing users (if any registered before running this migration)
INSERT INTO public.profiles (id, full_name, avatar_id)
SELECT 
    id, 
    COALESCE(raw_user_meta_data->>'full_name', split_part(email, '@', 1)), 
    COALESCE(raw_user_meta_data->>'avatar_id', 'director')
FROM auth.users
ON CONFLICT (id) DO NOTHING;
