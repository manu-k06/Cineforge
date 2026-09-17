import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.telegram import telegram_service


async def main():
    await telegram_service.connect()
    client = telegram_service.client

    channels = [-1002828590309, -1002379265316, -1001899713036, -5524428004]
    for cid in channels:
        print(f"\n--- Checking channel {cid} ---")
        count = 0
        async for message in client.iter_messages(cid, limit=50):
            if message.media and hasattr(message.media, "document"):
                doc = message.media.document
                name = getattr(message.file, "name", "unknown") or "unknown"
                safe_name = name.encode("ascii", "replace").decode()
                size_mb = round(doc.size / (1024 * 1024), 2)
                mime = doc.mime_type or ""
                print(f"msg_id={message.id}, chat_id={cid}: file='{safe_name}', size={size_mb} MB, mime='{mime}'")
                count += 1
                if count >= 10:
                    break


if __name__ == "__main__":
    asyncio.run(main())
