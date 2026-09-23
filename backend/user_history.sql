-- Cineforge Phase 5: User Watch History & Watchlist Schema
-- Run this script in your Supabase Project Dashboard -> SQL Editor

-- 1. Enable UUID Extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. User Watch History Table
CREATE TABLE IF NOT EXISTS public.user_watch_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    clean_title TEXT,
    year TEXT,
    poster_url TEXT,
    backdrop_url TEXT,
    stream_url TEXT NOT NULL,
    candidate_title TEXT,
    quality TEXT,
    progress_seconds FLOAT NOT NULL DEFAULT 0,
    duration_seconds FLOAT NOT NULL DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, title)
);

-- Index for speedy user-specific queries
CREATE INDEX IF NOT EXISTS idx_watch_history_user_updated 
ON public.user_watch_history(user_id, updated_at DESC);

-- 3. User Watchlist / Favorites Table
CREATE TABLE IF NOT EXISTS public.user_watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    clean_title TEXT,
    year TEXT,
    rating TEXT,
    poster_url TEXT,
    backdrop_url TEXT,
    overview TEXT,
    genres TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, title)
);

-- Index for speedy watchlist lookups
CREATE INDEX IF NOT EXISTS idx_watchlist_user_created 
ON public.user_watchlist(user_id, created_at DESC);

-- 4. Enable Row Level Security (RLS)
ALTER TABLE public.user_watch_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_watchlist ENABLE ROW LEVEL SECURITY;

-- 5. Policies for user_watch_history: Users can only see and modify their own history
CREATE POLICY "Users can view their own watch history" 
ON public.user_watch_history FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own watch history" 
ON public.user_watch_history FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own watch history" 
ON public.user_watch_history FOR UPDATE 
USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own watch history" 
ON public.user_watch_history FOR DELETE 
USING (auth.uid() = user_id);

-- 6. Policies for user_watchlist: Users can only see and modify their own watchlist
CREATE POLICY "Users can view their own watchlist" 
ON public.user_watchlist FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own watchlist" 
ON public.user_watchlist FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own watchlist" 
ON public.user_watchlist FOR DELETE 
USING (auth.uid() = user_id);
