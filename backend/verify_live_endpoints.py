import json
import time
import urllib.request
import urllib.parse


def make_request(url, method="GET", data=None, headers=None):
    headers = headers or {}
    req = urllib.request.Request(url, method=method, headers=headers)
    if data:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
        return resp.status, dict(resp.headers), content


def main():
    print("Verifying backend server is running...")
    status, headers, body = make_request("http://127.0.0.1:8000/api/telegram/status")
    print(f"Telegram status endpoint: {status} -> {body.decode('utf-8')}")

    print("\nCreating streaming session for real media (msg_id=9763, chat_id=5178541569)...")
    status, headers, body = make_request(
        "http://127.0.0.1:8000/api/media/session",
        method="POST",
        data={"message_id": 9763, "chat_id": 5178541569}
    )
    session_data = json.loads(body.decode("utf-8"))
    session_id = session_data["session_id"]
    print(f"Session created: ID={session_id}")
    print(f"File Name: {session_data.get('file_name')}, Size: {session_data.get('size')} bytes")

    print("\nProbing media metadata...")
    status, headers, body = make_request(f"http://127.0.0.1:8000/api/media/session/{session_id}/metadata")
    meta_json = json.loads(body.decode("utf-8"))
    print("Metadata:", json.dumps(meta_json.get("metadata", {}), indent=2))

    print("\nVerifying Stream Redirect...")
    status, headers, body = make_request(f"http://127.0.0.1:8000/api/media/stream/{session_id}")
    print(f"Stream Redirect Status: {status}, Location: {headers.get('Location')}")

    print("\nPlayer URL ready for browser testing:")
    print(f"http://127.0.0.1:8000/api/media/session/{session_id}/player")


if __name__ == "__main__":
    main()
