import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.telegram import telegram_service
from app.services.media_reader import media_reader_service


async def main():
    print("Connecting Telegram client...")
    connected = await telegram_service.connect()

    client = telegram_service.client
    me = await client.get_me()
    print(f"Logged in as: {me.first_name} [id={me.id}]")

    print("\nScanning dialogs for video media...")
    found_media = []
    async for dialog in client.iter_dialogs(limit=30):
        safe_dialog_name = dialog.name.encode("ascii", "replace").decode()
        async for message in client.iter_messages(dialog.id, limit=50):
            if message.media and hasattr(message.media, "document"):
                doc = message.media.document
                mime = doc.mime_type or ""
                raw_name = getattr(message.file, "name", "unknown") or "unknown"
                safe_name = raw_name.encode("ascii", "replace").decode()
                size_mb = round(doc.size / (1024 * 1024), 2)
                if "video" in mime or safe_name.endswith((".mkv", ".mp4", ".avi", ".mov")):
                    print(f"  -> Found media: msg_id={message.id}, chat_id={dialog.id}, file='{safe_name}', size={size_mb} MB, mime='{mime}', dialog='{safe_dialog_name}'")
                    found_media.append({
                        "msg_id": message.id,
                        "chat_id": dialog.id,
                        "name": safe_name,
                        "size_mb": size_mb,
                        "mime": mime
                    })
                    if len(found_media) >= 8:
                        break
        if len(found_media) >= 8:
            break

    print(f"\nTotal media files found: {len(found_media)}")
    return found_media


if __name__ == "__main__":
    asyncio.run(main())
