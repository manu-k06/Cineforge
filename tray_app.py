"""
Cineforge Windows System Tray Application
Runs Cineforge Backend, TG-FileStreamBot, and Cloudflare Tunnel silently in the background.
Eliminates visible console windows and prevents accidental server shutdowns.
"""

import atexit
import ctypes
import logging
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw
import pystray

# Directory and executable paths
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FSB_DIR = PROJECT_ROOT / "TG-FileStreamBot"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

PYTHON_EXE = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
FSB_EXE = FSB_DIR / "fsb.exe"
CLOUDFLARED_EXE = Path("C:/Program Files (x86)/cloudflared/cloudflared.exe")

WEB_PLAYER_URL = "https://cineforge-v1.vercel.app"
LOCAL_API_URL = "http://127.0.0.1:8000/docs"

# Setup logging for the tray app itself
logging.basicConfig(
    filename=LOGS_DIR / "tray.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cineforge.tray")


def create_tray_icon(status: str = "starting") -> Image.Image:
    """Generate a dynamic high-DPI tray icon."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded background
    draw.rounded_rectangle(
        [4, 4, size - 4, size - 4],
        radius=14,
        fill=(24, 24, 27, 255),  # Zinc-900
        outline=(245, 158, 11, 255),  # Amber-500
        width=3,
    )

    # Centered Film / Play Triangle
    draw.polygon(
        [(25, 18), (25, 46), (47, 32)],
        fill=(245, 158, 11, 255),
    )

    # Status badge in bottom right
    badge_colors = {
        "online": (16, 185, 129, 255),   # Emerald green
        "starting": (245, 158, 11, 255), # Amber orange
        "offline": (239, 68, 68, 255),   # Red
    }
    badge_fill = badge_colors.get(status, (156, 163, 175, 255))
    draw.ellipse(
        [size - 18, size - 18, size - 4, size - 4],
        fill=badge_fill,
        outline=(24, 24, 27, 255),
        width=2,
    )
    return img


class CineforgeTrayApp:
    def __init__(self):
        self.fsb_proc: Optional[subprocess.Popen] = None
        self.backend_proc: Optional[subprocess.Popen] = None
        self.tunnel_proc: Optional[subprocess.Popen] = None

        self.tunnel_url: Optional[str] = None
        self.is_running = False
        self.status = "starting"  # starting, online, offline
        self.icon: Optional[pystray.Icon] = None
        self.watchdog_thread: Optional[threading.Thread] = None

        atexit.register(self.stop_all_services)

    def _kill_stale_processes(self):
        """Clean up existing port listeners and leftover processes."""
        logger.info("Cleaning up stale processes before startup...")
        cmds = [
            'taskkill /f /im fsb.exe >nul 2>&1',
            'taskkill /f /im cloudflared.exe >nul 2>&1',
            'taskkill /f /im ngrok.exe >nul 2>&1',
            'for /f "tokens=5" %a in (\'netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"\') do taskkill /f /pid %a >nul 2>&1',
            'for /f "tokens=5" %a in (\'netstat -aon ^| findstr ":8088" ^| findstr "LISTENING"\') do taskkill /f /pid %a >nul 2>&1',
        ]
        for cmd in cmds:
            try:
                subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                logger.debug("Cleanup command failed: %s", e)
        time.sleep(1.0)

    def _mark_supabase_status(self, is_online: bool, url: Optional[str] = None):
        """Publish status to Supabase using publish_tunnel utility."""
        try:
            cmd = [str(PYTHON_EXE), "-m", "app.services.publish_tunnel"]
            if is_online and url:
                cmd.extend(["--url", url])
            elif not is_online:
                cmd.append("--offline")
            else:
                return

            subprocess.run(
                cmd,
                cwd=str(BACKEND_DIR),
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10,
            )
            logger.info("Published Supabase status: online=%s, url=%s", is_online, url)
        except Exception as e:
            logger.warning("Failed to publish Supabase status: %s", e)

    def start_all_services(self):
        """Launch fsb.exe, backend uvicorn, and cloudflared tunnel with NO console windows."""
        self._kill_stale_processes()
        self.is_running = True
        self.status = "starting"
        self._update_icon()

        flags = subprocess.CREATE_NO_WINDOW

        # 1. Start Go TG-FileStreamBot
        fsb_log = open(LOGS_DIR / "streamer.log", "a", buffering=1, encoding="utf-8")
        logger.info("Starting TG-FileStreamBot on port 8088...")
        self.fsb_proc = subprocess.Popen(
            [str(FSB_EXE), "run"],
            cwd=str(FSB_DIR),
            stdout=fsb_log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )

        time.sleep(1.5)

        # 2. Start FastAPI Backend
        backend_log = open(LOGS_DIR / "backend.log", "a", buffering=1, encoding="utf-8")
        logger.info("Starting FastAPI backend on port 8000...")
        self.backend_proc = subprocess.Popen(
            [
                str(PYTHON_EXE),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=str(BACKEND_DIR),
            stdout=backend_log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )

        time.sleep(2.0)

        # 3. Start Cloudflare Tunnel
        tunnel_log_path = LOGS_DIR / "tunnel.log"
        if tunnel_log_path.exists():
            try:
                tunnel_log_path.unlink()
            except Exception:
                pass

        logger.info("Starting Cloudflare tunnel to port 8000...")
        self.tunnel_proc = subprocess.Popen(
            [
                str(CLOUDFLARED_EXE),
                "tunnel",
                "--url",
                "http://localhost:8000",
                "--logfile",
                str(tunnel_log_path),
            ],
            creationflags=flags,
        )

        # Start background thread to discover tunnel URL and monitor processes
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

    def _watchdog_loop(self):
        """Continuously check tunnel URL and ensure processes remain healthy."""
        tunnel_log_path = LOGS_DIR / "tunnel.log"
        url_regex = re.compile(r"https://[a-zA-Z0-9\.-]+\.trycloudflare\.com")

        # 1. Wait for tunnel URL
        for _ in range(30):
            if not self.is_running:
                return
            if tunnel_log_path.exists():
                try:
                    content = tunnel_log_path.read_text(encoding="utf-8", errors="ignore")
                    match = url_regex.search(content)
                    if match:
                        self.tunnel_url = match.group(0)
                        logger.info("Cloudflare tunnel active: %s", self.tunnel_url)
                        self._on_tunnel_established(self.tunnel_url)
                        break
                except Exception as e:
                    logger.debug("Error reading tunnel log: %s", e)
            time.sleep(1.0)

        if not self.tunnel_url:
            logger.warning("Tunnel URL could not be detected within 30 seconds.")

        # 2. Main watchdog loop
        while self.is_running:
            time.sleep(5.0)
            if not self.is_running:
                break

            # Check child processes
            if self.fsb_proc and self.fsb_proc.poll() is not None:
                logger.warning("TG-FileStreamBot unexpectedly exited (code: %s). Restarting...", self.fsb_proc.returncode)
                fsb_log = open(LOGS_DIR / "streamer.log", "a", buffering=1, encoding="utf-8")
                self.fsb_proc = subprocess.Popen(
                    [str(FSB_EXE), "run"],
                    cwd=str(FSB_DIR),
                    stdout=fsb_log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

            if self.backend_proc and self.backend_proc.poll() is not None:
                logger.warning("Backend unexpectedly exited (code: %s). Restarting...", self.backend_proc.returncode)
                backend_log = open(LOGS_DIR / "backend.log", "a", buffering=1, encoding="utf-8")
                self.backend_proc = subprocess.Popen(
                    [
                        str(PYTHON_EXE),
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8000",
                    ],
                    cwd=str(BACKEND_DIR),
                    stdout=backend_log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

    def _on_tunnel_established(self, url: str):
        """Invoked when Cloudflare tunnel URL is established."""
        self.status = "online"
        self._update_icon()

        # Update Go streamer HOST in fsb.env
        try:
            fsb_env_file = FSB_DIR / "fsb.env"
            if fsb_env_file.exists():
                text = fsb_env_file.read_text(encoding="utf-8")
                text = re.sub(r"^HOST=.*", f"HOST={url}", text, flags=re.MULTILINE)
                fsb_env_file.write_text(text, encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to update fsb.env HOST: %s", e)

        # Publish to Supabase
        self._mark_supabase_status(is_online=True, url=url)

        # Show desktop notification
        if self.icon:
            try:
                self.icon.notify(
                    f"Cineforge is running silently in the background!\nTunnel: {url}",
                    "Cineforge Server Online",
                )
            except Exception as e:
                logger.debug("Notification error: %s", e)

    def _update_icon(self):
        """Update the system tray icon image, title, and menu."""
        if not self.icon:
            return
        self.icon.icon = create_tray_icon(self.status)
        if self.status == "online" and self.tunnel_url:
            self.icon.title = f"Cineforge: Online\n{self.tunnel_url}"
        elif self.status == "starting":
            self.icon.title = "Cineforge: Starting services..."
        else:
            self.icon.title = "Cineforge: Offline"
        self.icon.menu = self._build_menu()

    def stop_all_services(self):
        """Gracefully stop all services and notify Supabase."""
        if not self.is_running and self.status == "offline":
            return

        logger.info("Stopping all Cineforge services...")
        self.is_running = False
        self.status = "offline"

        # Mark offline in Supabase first
        self._mark_supabase_status(is_online=False)

        for proc in [self.tunnel_proc, self.backend_proc, self.fsb_proc]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

        time.sleep(1.0)
        self._kill_stale_processes()
        logger.info("All services stopped successfully.")

    # ------------------ Menu Actions ------------------ #
    def copy_tunnel_url(self):
        """Copy active tunnel URL to clipboard."""
        if not self.tunnel_url:
            if self.icon:
                self.icon.notify("Tunnel URL is still warming up...", "Cineforge")
            return

        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{self.tunnel_url}'"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if self.icon:
                self.icon.notify(f"Copied to clipboard:\n{self.tunnel_url}", "Cineforge Tunnel URL")
        except Exception as e:
            logger.warning("Failed to copy URL to clipboard: %s", e)

    def open_web_player(self):
        webbrowser.open(WEB_PLAYER_URL)

    def open_local_api(self):
        webbrowser.open(LOCAL_API_URL)

    def open_logs_folder(self):
        try:
            os.startfile(str(LOGS_DIR))
        except Exception as e:
            logger.warning("Failed to open logs folder: %s", e)

    def open_log_file(self, filename: str):
        filepath = LOGS_DIR / filename
        if not filepath.exists():
            filepath.write_text(f"--- Log started for {filename} ---\n", encoding="utf-8")
        try:
            os.startfile(str(filepath))
        except Exception as e:
            logger.warning("Failed to open log file %s: %s", filename, e)

    def restart_services(self):
        """Restart all services."""
        if self.icon:
            self.icon.notify("Restarting Cineforge services...", "Cineforge")
        self.stop_all_services()
        time.sleep(1.5)
        self.start_all_services()

    def exit_app(self):
        """Exit the tray app completely."""
        self.stop_all_services()
        if self.icon:
            self.icon.stop()

    def _build_menu(self) -> pystray.Menu:
        """Construct the context menu for the system tray icon."""
        status_text = (
            f"● Online ({self.tunnel_url[:28]}...)"
            if (self.status == "online" and self.tunnel_url)
            else ("● Starting Services..." if self.status == "starting" else "● Stopped")
        )

        return pystray.Menu(
            pystray.MenuItem(status_text, lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🔗 Copy Tunnel URL",
                lambda: self.copy_tunnel_url(),
                enabled=bool(self.tunnel_url),
            ),
            pystray.MenuItem("🎬 Open Web Player", lambda: self.open_web_player()),
            pystray.MenuItem("⚡ Open API Docs", lambda: self.open_local_api()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "📄 View Logs",
                pystray.Menu(
                    pystray.MenuItem("Backend Log", lambda: self.open_log_file("backend.log")),
                    pystray.MenuItem("Streamer Bot Log", lambda: self.open_log_file("streamer.log")),
                    pystray.MenuItem("Tunnel Log", lambda: self.open_log_file("tunnel.log")),
                    pystray.MenuItem("Tray App Log", lambda: self.open_log_file("tray.log")),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("📁 Open Logs Directory", lambda: self.open_logs_folder()),
                ),
            ),
            pystray.MenuItem("🔄 Restart Services", lambda: self.restart_services()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🛑 Stop and Exit", lambda: self.exit_app()),
        )

    def run(self):
        """Start services and enter the system tray event loop."""
        initial_image = create_tray_icon(self.status)
        self.icon = pystray.Icon(
            name="Cineforge",
            icon=initial_image,
            title="Cineforge: Starting...",
            menu=self._build_menu(),
        )

        # Launch services in background
        self.start_all_services()

        # Run system tray event loop (blocks until exit_app is called)
        self.icon.run()


def acquire_single_instance_lock(mutex_name: str = "Global\\CineforgeTrayAppMutex"):
    """Ensure only one instance of Cineforge tray app runs at a time using Windows kernel mutex."""
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        last_error = ctypes.windll.kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if last_error == ERROR_ALREADY_EXISTS:
            return None
        return mutex
    except Exception as e:
        logger.warning("Could not create single-instance mutex: %s", e)
        return True  # Fallback gracefully if ctypes fails


if __name__ == "__main__":
    _mutex = acquire_single_instance_lock()
    if not _mutex:
        logger.warning("Another instance of Cineforge Tray App is already running. Exiting silently.")
        sys.exit(0)

    app = CineforgeTrayApp()
    app.run()
