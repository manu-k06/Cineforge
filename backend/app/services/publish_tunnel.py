"""
Utility to publish live tunnel URL and server status into Supabase.
Enables the Vercel frontend to automatically discover the active backend without manual env updates.
"""

import argparse
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings

logger = logging.getLogger("cineforge.publish_tunnel")


def publish_tunnel_url(url: Optional[str] = None, is_online: bool = True) -> bool:
    """Upsert the active backend URL and online status to Supabase server_status table."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning("Supabase credentials not configured; skipping status publish.")
        return False

    try:
        from supabase import create_client
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

        payload = {
            "id": "live",
            "is_online": is_online,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if url:
            payload["backend_url"] = url.rstrip("/")

        res = client.table("server_status").upsert(payload).execute()
        logger.info("Successfully published server status to Supabase: %s", payload)
        print(f"[Cineforge Status] Successfully published to Supabase: online={is_online}, url={url}")
        return True
    except Exception as e:
        logger.warning(
            "Failed to publish server status to Supabase (ensure server_status.sql has been executed): %s",
            e,
        )
        print(f"[Cineforge Status Warning] Could not publish to Supabase: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Publish Cineforge live tunnel URL to Supabase")
    parser.add_argument("--url", type=str, help="Live public tunnel URL (e.g. https://*.trycloudflare.com)")
    parser.add_argument("--offline", action="store_true", help="Mark server as offline")
    args = parser.parse_args()

    if args.offline:
        publish_tunnel_url(is_online=False)
    elif args.url:
        publish_tunnel_url(url=args.url, is_online=True)
    else:
        print("Usage: python -m app.services.publish_tunnel --url <URL> | --offline")


if __name__ == "__main__":
    main()
