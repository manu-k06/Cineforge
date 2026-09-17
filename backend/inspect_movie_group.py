import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.telegram import telegram_service


async def main():
    await telegram_service.connect()
    client = telegram_service.client

    chat_id = -1002498462288  # Movie-Series Group
    print(f"Inspecting messages in Movie-Series Group (id={chat_id})...")
    async for message in client.iter_messages(chat_id, limit=60):
        if message.media and hasattr(message.media, "document"):
            doc = message.media.document
            name = getattr(message.file, "name", "unknown") or "unknown"
            size_mb = round(doc.size / (1024 * 1024), 2)
            mime = doc.mime_type or ""
            print(f"msg_id={message.id}: file='{name}', size={size_mb} MB, mime='{mime}'")


if __name__ == "__main__":
    asyncio.run(main())
