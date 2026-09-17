import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.telegram import telegram_service


async def main():
    await telegram_service.connect()
    client = telegram_service.client

    dialog_ids = [5178541569, 7718845373, 8590332446, 8575051515, 7627028736, 8264214434]
    for cid in dialog_ids:
        print(f"\n--- Checking dialog {cid} ---")
        async for message in client.iter_messages(cid, limit=20):
            if message.media and hasattr(message.media, "document"):
                doc = message.media.document
                name = getattr(message.file, "name", "unknown") or "unknown"
                safe_name = name.encode("ascii", "replace").decode()
                size_mb = round(doc.size / (1024 * 1024), 2)
                mime = doc.mime_type or ""
                print(f"msg_id={message.id}, chat_id={cid}: file='{safe_name}', size={size_mb} MB, mime='{mime}'")


if __name__ == "__main__":
    asyncio.run(main())
