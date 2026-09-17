
import asyncio
import os
import subprocess
import sys
import time
import httpx
from telethon import TelegramClient
from telethon.sessions import StringSession

from dotenv import load_dotenv

# Load credentials from backend/.env
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
load_dotenv(os.path.join(backend_dir, ".env"))
sys.path.insert(0, backend_dir)

from app.config import settings

async def main():
    print("=" * 70)
    print("STAGE B2R.3: TESTING GOTD NATIVE STREAMER PROTOTYPE")
    print("=" * 70)

    # 1. Export Telethon Session to String
    print("\n[Step 1] Exporting Telethon session to StringSession...")
    session_file = os.path.join(backend_dir, settings.TELEGRAM_SESSION_NAME)
    client = TelegramClient(session_file, settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("ERROR: User account is not authorized in session file.")
        await client.disconnect()
        return

    string_session = StringSession.save(client.session)
    me = await client.get_me()
    print(f"Logged in as: @{me.username} (ID: {me.id})")
    print(f"Telethon StringSession generated ({len(string_session)} chars)")
    await client.disconnect()

    # 2. Launch streamer.exe subprocess
    print("\n[Step 2] Launching streamer.exe on 127.0.0.1:8088...")
    streamer_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), "streamer.exe"))
    
    env = os.environ.copy()
    env["TELEGRAM_API_ID"] = str(settings.TELEGRAM_API_ID)
    env["TELEGRAM_API_HASH"] = settings.TELEGRAM_API_HASH
    env["TELEGRAM_SESSION_STRING"] = string_session
    env["PORT"] = "8088"

    proc = subprocess.Popen(
        [streamer_exe],
        cwd=os.path.dirname(streamer_exe),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Helper to stream proc logs in background
    def print_logs():
        try:
            for line in proc.stdout:
                print(f"[Streamer LOG] {line.strip()}")
        except Exception:
            pass

    import threading
    log_thread = threading.Thread(target=print_logs, daemon=True)
    log_thread.start()

    # Wait for healthcheck
    print("[Step 3] Waiting for streamer.exe to report healthy...")
    healthy = False
    async with httpx.AsyncClient(timeout=5.0) as http_client:
        for _ in range(30):
            try:
                res = await http_client.get("http://127.0.0.1:8088/health")
                if res.status_code == 200 and res.json().get("status") == "healthy":
                    healthy = True
                    break
            except Exception:
                await asyncio.sleep(0.5)

    if not healthy:
        print("ERROR: streamer.exe failed to become healthy.")
        proc.terminate()
        return

    print("Streamer is healthy and connected to Telegram MTProto!")

    # 3. Test HTTP Range Download of 4 MB and 16 MB
    msg_id = 9763  # Detective Ujjwalan in Saved Messages
    url = f"http://127.0.0.1:8088/stream/me/{msg_id}"
    
    print(f"\n[Step 4] Benchmarking HTTP Range Stream from {url}...")
    
    test_ranges = [
        ("4 MB Range (bytes=0-4194303)", 0, 4194303, 4 * 1024 * 1024),
        ("16 MB Range (bytes=0-16777215)", 0, 16777215, 16 * 1024 * 1024),
    ]

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        for label, start, end, expected_bytes in test_ranges:
            print(f"\n--- Testing {label} ---")
            t0 = time.perf_counter()
            headers = {"Range": f"bytes={start}-{end}"}
            
            bytes_received = 0
            async with http_client.stream("GET", url, headers=headers) as response:
                print(f"HTTP Status: {response.status_code}")
                print(f"Content-Range: {response.headers.get('Content-Range')}")
                print(f"Content-Length: {response.headers.get('Content-Length')}")
                print(f"Content-Type: {response.headers.get('Content-Type')}")
                
                assert response.status_code == 206, f"Expected 206, got {response.status_code}"
                
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    bytes_received += len(chunk)
            
            elapsed = time.perf_counter() - t0
            mb = bytes_received / (1024 * 1024)
            mbps = (bytes_received * 8) / (elapsed * 1_000_000)
            mb_per_sec = mb / max(elapsed, 0.001)
            
            print(f"Received: {bytes_received} bytes ({mb:.2f} MB)")
            print(f"Time Taken: {elapsed:.2f}s")
            print(f"Throughput: {mb_per_sec:.2f} MB/s ({mbps:.2f} Mbps)")
            print(f"Comparison: Old Telethon was ~0.35 MB/s (~2.8 Mbps)")

    print("\n[Step 5] Shutting down streamer process...")
    proc.terminate()
    proc.wait(timeout=5)
    print("Streamer shutdown clean. Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
