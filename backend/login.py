import asyncio
from app.services.telegram import interactive_login

if __name__ == "__main__":
    asyncio.run(interactive_login())
