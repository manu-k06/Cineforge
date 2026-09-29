-- Cineforge Dynamic Server Status & Tunnel URL Table
-- Enables zero-config frontend auto-discovery of live Cloudflare Tunnel URL

CREATE TABLE IF NOT EXISTS public.server_status (
    id TEXT PRIMARY KEY DEFAULT 'live',
    backend_url TEXT NOT NULL,
    is_online BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.server_status ENABLE ROW LEVEL SECURITY;

-- Allow public read access (anon & authenticated frontend can read live URL)
DROP POLICY IF EXISTS "Allow public read access to server_status" ON public.server_status;
CREATE POLICY "Allow public read access to server_status"
    ON public.server_status
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Allow service_role full write access (backend writes live URL on boot)
DROP POLICY IF EXISTS "Allow service_role full access to server_status" ON public.server_status;
CREATE POLICY "Allow service_role full access to server_status"
    ON public.server_status
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Insert initial record if not exists
INSERT INTO public.server_status (id, backend_url, is_online, updated_at)
VALUES ('live', 'http://127.0.0.1:8000', false, now())
ON CONFLICT (id) DO NOTHING;
