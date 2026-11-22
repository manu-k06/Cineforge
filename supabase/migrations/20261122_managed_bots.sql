-- Cineforge Managed Streamer Bots Migration
-- ==========================================
-- Stores the durable mapping between verified Telegram user IDs and their personal streamer bots.
-- CRITICAL SECURITY RULE: Personal streamer bot tokens are NEVER stored in this table or Supabase.

CREATE TABLE IF NOT EXISTS public.managed_bots (
    telegram_user_id BIGINT PRIMARY KEY,
    bot_id BIGINT NOT NULL,
    bot_access_hash BIGINT NOT NULL,
    bot_username TEXT NOT NULL,
    created_at BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint,
    updated_at BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint,
    CONSTRAINT uq_managed_bots_bot_id UNIQUE (bot_id)
);

COMMENT ON TABLE public.managed_bots IS 'Durable account-to-bot mappings for Cineforge. Bot tokens are never stored in the database. Existing rows are immutable.';

-- Enable Row Level Security (RLS) to protect user bot mappings
ALTER TABLE public.managed_bots ENABLE ROW LEVEL SECURITY;

-- 1. Explicitly revoke ALL table privileges from all roles, including service_role
REVOKE ALL ON TABLE public.managed_bots FROM PUBLIC, anon, authenticated, service_role;

-- 2. Grant strictly SELECT and INSERT to service_role
-- Enables the hosted helper on Render to look up (SELECT) and save (INSERT) bot links,
-- while completely barring it from changing (UPDATE) or deleting (DELETE) existing links.
GRANT SELECT, INSERT ON TABLE public.managed_bots TO service_role;

-- 3. Row Level Security policies for service_role strictly for SELECT and INSERT
DROP POLICY IF EXISTS "Allow service_role full access to managed_bots" ON public.managed_bots;
DROP POLICY IF EXISTS "Allow service_role select on managed_bots" ON public.managed_bots;
DROP POLICY IF EXISTS "Allow service_role insert on managed_bots" ON public.managed_bots;

CREATE POLICY "Allow service_role select on managed_bots"
    ON public.managed_bots
    FOR SELECT
    TO service_role
    USING (true);

CREATE POLICY "Allow service_role insert on managed_bots"
    ON public.managed_bots
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- 4. Enforce immutability at the database level:
-- Any attempt to update or overwrite an existing user's mapping is strictly rejected with an exception
CREATE OR REPLACE FUNCTION public.prevent_managed_bot_replacement()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Account mapping conflict: updating or replacing an existing managed bot mapping for Telegram user % is strictly prohibited.', OLD.telegram_user_id
        USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_managed_bot_update ON public.managed_bots;
CREATE TRIGGER trg_prevent_managed_bot_update
    BEFORE UPDATE ON public.managed_bots
    FOR EACH ROW
    EXECUTE FUNCTION public.prevent_managed_bot_replacement();
