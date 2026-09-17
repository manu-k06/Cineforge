import os
import subprocess
import sys
import time
import httpx

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

def run_integration_test():
    print("=" * 80)
    print("PHASE 11 LIVE INTEGRATION TEST: FASTAPI <-> GO STREAMER")
    print("=" * 80)

    streamer_dir = os.path.abspath(os.path.dirname(__file__))
    streamer_exe = os.path.join(streamer_dir, "streamer.exe")

    env = os.environ.copy()
    env["PORT"] = "8088"
    # Ensure STREAM_SECRET_KEY is empty for direct URL test or configured
    env["STREAM_SECRET_KEY"] = ""

    print(f"[1/6] Launching streamer.exe on port 8088 from {streamer_exe}...")
    proc = subprocess.Popen(
        [streamer_exe],
        cwd=streamer_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        # Wait for streamer /health
        health_url = "http://127.0.0.1:8088/health"
        streamer_ready = False
        print(f"[2/6] Polling {health_url}...")
        for attempt in range(25):
            try:
                r = httpx.get(health_url, timeout=1.0)
                if r.status_code == 200:
                    print(f"       -> Go Streamer responded 200 OK: {r.json()}")
                    streamer_ready = True
                    break
            except Exception:
                time.sleep(0.5)

        if not streamer_ready:
            print("ERROR: Streamer did not become ready in time!")
            out, _ = proc.communicate(timeout=2)
            print("Streamer Output:\n", out)
            return False

        # 3. Test FastAPI health proxy
        print("\n[3/6] Testing FastAPI streamer health endpoint: GET /api/stream/streamer/health...")
        client = TestClient(app)
        health_resp = client.get("/api/stream/streamer/health")
        print(f"       -> Status: {health_resp.status_code}, Body: {health_resp.json()}")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "healthy"
        assert health_data["reachable"] is True

        # 4. Create playback session in FastAPI
        print("\n[4/6] Creating playback session in FastAPI: POST /api/stream/session...")
        session_resp = client.post("/api/stream/session", json={"chat_id": "me", "message_id": 9763})
        print(f"       -> Status: {session_resp.status_code}, Body: {session_resp.json()}")
        assert session_resp.status_code == 200
        session_data = session_resp.json()
        session_id = session_data["session_id"]
        stream_url = session_data["stream_url"]

        assert session_data["chat_id"] == "me"
        assert session_data["message_id"] == 9763
        assert stream_url == "http://127.0.0.1:8088/stream/me/9763"

        # Check 307 redirect
        redirect_resp = client.get(f"/api/media/stream/{session_id}", follow_redirects=False)
        print(f"       -> GET /api/media/stream/{session_id} redirect status: {redirect_resp.status_code}, Location: {redirect_resp.headers.get('Location')}")
        assert redirect_resp.status_code == 307
        assert redirect_resp.headers.get("Location") == stream_url

        # 5. Make HEAD request against Go Streamer URL
        print(f"\n[5/6] Making HEAD request directly to Go Streamer: {stream_url}...")
        head_resp = httpx.head(stream_url, timeout=10.0)
        print(f"       -> Status: {head_resp.status_code}")
        print(f"       -> Content-Length: {head_resp.headers.get('Content-Length')}")
        print(f"       -> Accept-Ranges: {head_resp.headers.get('Accept-Ranges')}")
        print(f"       -> Content-Type: {head_resp.headers.get('Content-Type')}")
        assert head_resp.status_code == 200
        assert head_resp.headers.get("Content-Length") == "744246327"
        assert head_resp.headers.get("Accept-Ranges") == "bytes"

        # 6. Make Range: bytes=0-65535 request directly to Go Streamer URL
        print(f"\n[6/6] Making Range GET request directly to Go Streamer: Range: bytes=0-65535...")
        t0 = time.time()
        range_resp = httpx.get(stream_url, headers={"Range": "bytes=0-65535"}, timeout=30.0)
        elapsed = time.time() - t0

        print(f"       -> Status: {range_resp.status_code} (Expected: 206)")
        print(f"       -> Content-Range: {range_resp.headers.get('Content-Range')}")
        print(f"       -> Content-Length: {range_resp.headers.get('Content-Length')}")
        print(f"       -> Bytes received: {len(range_resp.content)}")
        print(f"       -> Latency: {elapsed:.2f}s")

        assert range_resp.status_code == 206
        assert range_resp.headers.get("Content-Range") == "bytes 0-65535/744246327"
        assert range_resp.headers.get("Content-Length") == "65536"
        assert len(range_resp.content) == 65536

        magic_hex = range_resp.content[:4].hex()
        first_16_hex = range_resp.content[:16].hex()
        print(f"       -> Magic Hex: {magic_hex} (Expected: 1a45dfa3)")
        print(f"       -> Header Hex (16 bytes): {first_16_hex}")
        assert magic_hex == "1a45dfa3", f"Expected 1a45dfa3, got {magic_hex}"

        print("\n" + "=" * 80)
        print("PHASE 11 LIVE INTEGRATION TEST PASSED 100%!")
        print("FastAPI successfully acts as control plane while 100% of media bytes come from Go streamer!")
        print("=" * 80)
        return True

    finally:
        print("\nShutting down streamer.exe process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("Streamer shutdown complete.")

if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)
