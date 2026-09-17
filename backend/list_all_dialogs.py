import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.telegram import telegram_service


async def main():
    await telegram_service.connect()
    client = telegram_service.client

    print("Listing all dialogs:")
    async for dialog in client.iter_dialogs():
        safe_name = dialog.name.encode("ascii", "replace").decode()
        print(f"Dialog id={dialog.id}, title='{safe_name}', is_user={dialog.is_user}, is_group={dialog.is_group}, is_channel={dialog.is_channel}")


if __name__ == "__main__":
    asyncio.run(main())
