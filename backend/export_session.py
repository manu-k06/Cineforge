"""
Utility to export existing cineforge_session.session into a TELEGRAM_STRING_SESSION
for cloud deployments like Render, Railway, or Fly.io.
"""

import os
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from app.config import settings

def main():
    session_file = f"{settings.TELEGRAM_SESSION_NAME}.session"
    if not os.path.exists(session_file):
        print(f"Error: '{session_file}' not found in current directory.")
        print("Please run 'python login.py' first to authenticate.")
        return

    print("=" * 70)
    print(" Cineforge — Session String Exporter for Cloud (Render / Railway)")
    print("=" * 70)

    try:
        client = TelegramClient(
            settings.TELEGRAM_SESSION_NAME,
            settings.TELEGRAM_API_ID or 12345,
            settings.TELEGRAM_API_HASH or "dummy",
        )
        session_str = StringSession.save(client.session)

        print("\nYour Telethon StringSession has been generated successfully!")
        print("\n" + "-" * 70)
        print("Copy the value below and add it to your Render Environment Variables:")
        print("-" * 70)
        print(f"\nTELEGRAM_STRING_SESSION={session_str}\n")
        print("-" * 70)
        print("On Render Dashboard:")
        print("  Key:   TELEGRAM_STRING_SESSION")
        print(f"  Value: {session_str}")
        print("-" * 70 + "\n")
    except Exception as e:
        print(f"Error exporting session string: {e}")

if __name__ == "__main__":
    main()
