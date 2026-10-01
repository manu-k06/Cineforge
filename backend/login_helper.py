import asyncio
import os
import sys
import time
import webbrowser

# Force UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from app.config import settings

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Cineforge Telegram Login</title>
    <meta http-equiv="refresh" content="15">
    <style>
        body {
            background: #09090b;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .card {
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 20px;
            padding: 36px 32px;
            text-align: center;
            box-shadow: 0 12px 40px rgba(0,0,0,0.6);
            max-width: 420px;
            width: 90%;
        }
        h2 { margin-top: 0; margin-bottom: 8px; color: #f59e0b; font-size: 22px; }
        .subtitle { color: #a1a1aa; font-size: 14px; margin-bottom: 20px; }
        .qr-wrapper {
            background: white;
            border-radius: 16px;
            padding: 16px;
            display: inline-block;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        img { display: block; border-radius: 8px; }
        ol { text-align: left; line-height: 1.8; color: #d4d4d8; font-size: 14px; margin: 0 0 20px 0; padding-left: 24px; }
        strong { color: #ffffff; }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #10b981;
            padding: 6px 16px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 500;
        }
        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(0.85); } }
    </style>
</head>
<body>
    <div class="card">
        <h2>Telegram Quick Link</h2>
        <div class="subtitle">Connect Cineforge to your Telegram account</div>
        <div class="qr-wrapper">
            <img src="telegram_login_qr.png?t={timestamp}" width="260" height="260" alt="Telegram Login QR Code">
        </div>
        <ol>
            <li>Open <strong>Telegram</strong> on your phone</li>
            <li>Go to <strong>Settings &gt; Devices &gt; Link Desktop Device</strong></li>
            <li>Point your camera at this QR code</li>
        </ol>
        <div class="status-badge">
            <div class="dot"></div>
            <span>Listening for mobile scan...</span>
        </div>
    </div>
</body>
</html>
"""

HTML_SUCCESS = """<!DOCTYPE html>
<html>
<head>
    <title>Cineforge Telegram Login - Success</title>
    <style>
        body {
            background: #09090b;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: #18181b;
            border: 1px solid #10b981;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 12px 40px rgba(0,0,0,0.6);
            max-width: 420px;
        }
        h2 { color: #10b981; margin-top: 0; }
        p { color: #a1a1aa; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="card">
        <h2>&#9989; Authentication Successful!</h2>
        <p>Logged in as: <strong>{name}</strong></p>
        <p>Your Telegram session has been activated and saved. You can close this browser tab and return to Cineforge.</p>
    </div>
</body>
</html>
"""


def update_qr_files(url):
    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(url)
    img = qr.make_image(fill_color="black", back_color="white")
    
    qr_img_path = os.path.abspath("telegram_login_qr.png")
    img.save(qr_img_path)
    
    html_content = HTML_TEMPLATE.replace("{timestamp}", str(int(time.time())))
    html_path = os.path.abspath("qr_login.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return html_path


async def main():
    session_file = settings.TELEGRAM_SESSION_NAME
    client = TelegramClient(session_file, settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    await client.connect()

    print("Generating Telegram login QR code...", flush=True)
    qr_login = await client.qr_login()

    html_path = update_qr_files(qr_login.url)
    print(f"Opening browser login page: {html_path}", flush=True)
    webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")

    print("\n" + "=" * 65, flush=True)
    print("Scan the QR code displayed in your browser with Telegram App:")
    print("   1. Open Telegram on your phone", flush=True)
    print("   2. Go to Settings > Devices > Link Desktop Device", flush=True)
    print("   3. Point camera at the QR code on your screen", flush=True)
    print("=" * 65 + "\n", flush=True)
    print("Waiting for you to scan...", flush=True)

    user = None
    for attempt in range(20):  # Keep alive for ~10 minutes
        try:
            update_qr_files(qr_login.url)
            user = await qr_login.wait()
            if user:
                break
        except asyncio.TimeoutError:
            print(f"Token refreshed ({attempt + 1}/20). Still waiting...", flush=True)
            await qr_login.recreate()
        except SessionPasswordNeededError:
            print("\n2FA Cloud Password is enabled on this Telegram account.", flush=True)
            pwd = input("Please enter your 2FA Cloud Password: ").strip()
            user = await client.sign_in(password=pwd)
            break

    if user:
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        print("\n" + "=" * 65, flush=True)
        print("AUTHENTICATION SUCCESSFUL!", flush=True)
        print(f"Logged in as: {name} (User ID: {user.id})", flush=True)
        print(f"Session saved to: {session_file}.session", flush=True)
        print("=" * 65, flush=True)
        
        # Write success HTML
        with open("qr_login.html", "w", encoding="utf-8") as f:
            f.write(HTML_SUCCESS.replace("{name}", name))
    else:
        print("\nLogin timed out. Run the script again whenever you are ready.", flush=True)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
