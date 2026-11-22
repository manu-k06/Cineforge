use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{Mutex, RwLock};

use crate::models::delivery::StreamerStatus;

pub struct StreamerSidecarService {
    status: Arc<RwLock<StreamerStatus>>,
    child_process: Arc<Mutex<Option<tokio::process::Child>>>,
    port: Arc<RwLock<Option<u16>>>,
    is_mock: bool,
    client: reqwest::Client,
}

impl StreamerSidecarService {
    /// Creates a production instance targeting the real Go streamer executable.
    pub fn new() -> Self {
        Self {
            status: Arc::new(RwLock::new(StreamerStatus::Stopped)),
            child_process: Arc::new(Mutex::new(None)),
            port: Arc::new(RwLock::new(None)),
            is_mock: false,
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(5))
                .build()
                .unwrap_or_default(),
        }
    }

    /// Creates a mock instance for testing without spawning external processes.
    pub fn new_mock(port: u16) -> Self {
        Self {
            status: Arc::new(RwLock::new(StreamerStatus::Running {
                port,
                host: format!("http://127.0.0.1:{port}"),
                pid: 9999,
            })),
            child_process: Arc::new(Mutex::new(None)),
            port: Arc::new(RwLock::new(Some(port))),
            is_mock: true,
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(2))
                .build()
                .unwrap_or_default(),
        }
    }

    /// Discovers the sidecar executable location across dev, sidecar folder, and installed directory.
    pub fn find_executable() -> Result<PathBuf, String> {
        let mut candidates = Vec::new();

        // 1. Next to current executable (installed Windows package)
        if let Ok(current_exe) = std::env::current_exe() {
            if let Some(parent) = current_exe.parent() {
                candidates.push(parent.join("fsb.exe"));
                candidates.push(parent.join("binaries").join("fsb.exe"));
                candidates.push(parent.join("binaries").join("fsb-x86_64-pc-windows-msvc.exe"));
            }
        }

        // 2. Local workspace src-tauri/binaries/
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        candidates.push(manifest_dir.join("binaries").join("fsb-x86_64-pc-windows-msvc.exe"));
        candidates.push(manifest_dir.join("binaries").join("fsb.exe"));

        // 3. TG-FileStreamBot directory in repo root
        if let Some(workspace_root) = manifest_dir.parent() {
            candidates.push(workspace_root.join("TG-FileStreamBot").join("fsb.exe"));
        }

        // 4. Current working directory
        candidates.push(PathBuf::from("TG-FileStreamBot/fsb.exe"));
        candidates.push(PathBuf::from("fsb.exe"));

        for p in candidates {
            if p.is_file() {
                log::info!("Discovered Go streamer sidecar executable at: {:?}", p);
                return Ok(p);
            }
        }

        Err("Go streamer sidecar executable (fsb.exe) not found in candidate paths.".to_string())
    }

    /// Discovers the working directory for the streamer (where fsb.session and fsb.env reside).
    pub fn find_workdir() -> Result<PathBuf, String> {
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

        // 1. Workspace TG-FileStreamBot
        if let Some(root) = manifest_dir.parent() {
            let p = root.join("TG-FileStreamBot");
            if p.is_dir() {
                return Ok(p);
            }
        }

        // 2. Relative to current dir
        let local_p = PathBuf::from("TG-FileStreamBot");
        if local_p.is_dir() {
            return Ok(local_p);
        }

        // 3. %APPDATA%\Cineforge
        if let Ok(appdata) = std::env::var("APPDATA") {
            let p = Path::new(&appdata).join("Cineforge");
            if p.is_dir() {
                return Ok(p);
            }
        }

        // 4. Fallback to current working directory
        std::env::current_dir().map_err(|e| e.to_string())
    }

    /// Starts the Go streamer sidecar process on an ephemeral loopback port using default configuration.
    pub async fn start(&self) -> Result<u16, String> {
        self.start_with_token(None).await
    }

    /// Starts the Go streamer sidecar process on an ephemeral loopback port,
    /// injecting the personal streamer bot token only at runtime.
    pub async fn start_with_token(&self, bot_token: Option<&str>) -> Result<u16, String> {
        if self.is_mock {
            let p = self.port.read().await.unwrap_or(8080);
            return Ok(p);
        }

        // Check if already running and healthy
        {
            let current_status = self.status.read().await.clone();
            if let StreamerStatus::Running { port, .. } = current_status {
                if self.check_health(port).await {
                    return Ok(port);
                }
            }
        }

        *self.status.write().await = StreamerStatus::Starting;

        let exe_path = Self::find_executable()?;
        let workdir = Self::find_workdir().unwrap_or_else(|_| PathBuf::from("."));

        // Allocate a free ephemeral port on 127.0.0.1
        let port = {
            let listener = std::net::TcpListener::bind("127.0.0.1:0")
                .map_err(|e| format!("Failed to bind ephemeral port for streamer: {e}"))?;
            let addr = listener.local_addr().map_err(|e| e.to_string())?;
            addr.port()
        };

        let host = format!("http://127.0.0.1:{port}");
        log::info!("Starting Go streamer sidecar on {} (workdir: {:?})", host, workdir);

        let mut cmd = tokio::process::Command::new(&exe_path);
        cmd.arg("run")
            .arg("--port")
            .arg(port.to_string())
            .arg("--host")
            .arg(&host)
            .env("LOG_CHANNEL", "0")
            .current_dir(&workdir)
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .kill_on_drop(true);

        if let Some(token) = bot_token {
            if !token.is_empty() {
                cmd.env("BOT_TOKEN", token);
            }
        }

        let mut child = cmd.spawn().map_err(|e| {
            let err_msg = format!("Failed to spawn Go streamer sidecar (fsb.exe): {e}");
            log::error!("{err_msg}");
            err_msg
        })?;

        let pid = child.id().unwrap_or(0);
        log::info!("Go streamer sidecar process spawned with PID {}", pid);

        // Wait for health check confirmation
        let poll_start = std::time::Instant::now();
        let timeout_limit = Duration::from_secs(12);
        let mut ready = false;

        while poll_start.elapsed() < timeout_limit {
            tokio::time::sleep(Duration::from_millis(150)).await;

            // Check if process exited prematurely
            if let Ok(Some(status)) = child.try_wait() {
                let err_msg = format!("Go streamer sidecar exited unexpectedly with status: {status:?}");
                log::error!("{err_msg}");
                *self.status.write().await = StreamerStatus::Exited { code: status.code() };
                return Err(err_msg);
            }

            if self.check_health(port).await {
                ready = true;
                break;
            }
        }

        if !ready {
            let _ = child.kill().await;
            let err_msg = format!("Go streamer sidecar failed to become ready on port {port} within 12 seconds.");
            log::error!("{err_msg}");
            *self.status.write().await = StreamerStatus::Failed { error: err_msg.clone() };
            return Err(err_msg);
        }

        *self.port.write().await = Some(port);
        *self.status.write().await = StreamerStatus::Running {
            port,
            host: host.clone(),
            pid,
        };

        // Monitor process in background for unexpected exit
        let status_arc = Arc::clone(&self.status);
        let port_arc = Arc::clone(&self.port);

        // Store child handle
        *self.child_process.lock().await = Some(child);

        // Spawn watchdog monitor
        let child_arc = Arc::clone(&self.child_process);
        tokio::spawn(async move {
            let mut child_guard = child_arc.lock().await;
            if let Some(ref mut c) = *child_guard {
                if let Ok(exit_status) = c.wait().await {
                    log::warn!("Go streamer sidecar process exited: {:?}", exit_status);
                    *status_arc.write().await = StreamerStatus::Exited {
                        code: exit_status.code(),
                    };
                    *port_arc.write().await = None;
                }
            }
        });

        log::info!("Go streamer sidecar successfully initialized and listening on {}", host);
        Ok(port)
    }

    /// Checks whether the streamer HTTP service is responsive on the given port.
    pub async fn check_health(&self, port: u16) -> bool {
        let url = format!("http://127.0.0.1:{port}/");
        match self.client.get(&url).send().await {
            Ok(resp) => resp.status().is_success(),
            Err(_) => false,
        }
    }

    /// Stops the running Go streamer sidecar process cleanly and purges temporary session files.
    pub async fn stop(&self) -> Result<(), String> {
        let mut child_guard = self.child_process.lock().await;
        if let Some(mut child) = child_guard.take() {
            log::info!("Terminating Go streamer sidecar process...");
            let _ = child.kill().await;
            let _ = child.wait().await;
            log::info!("Go streamer sidecar process stopped.");
        }

        *self.status.write().await = StreamerStatus::Stopped;
        *self.port.write().await = None;

        // Clean up temporary runtime session files (fsb.session) so stale tokens are not persisted
        if let Ok(workdir) = Self::find_workdir() {
            let session_path = workdir.join("fsb.session");
            if session_path.exists() {
                let _ = std::fs::remove_file(session_path);
            }
        }
        Ok(())
    }

    /// Returns the current sidecar status.
    pub async fn get_status(&self) -> StreamerStatus {
        self.status.read().await.clone()
    }

    /// Returns the active port if the sidecar is running.
    pub async fn get_port(&self) -> Option<u16> {
        *self.port.read().await
    }

    /// Constructs the direct streamer URL for a given message ID and auth hash.
    pub async fn get_stream_url(&self, message_id: i64, hash: &str) -> Option<String> {
        let port = self.get_port().await?;
        Some(format!("http://127.0.0.1:{port}/stream/{message_id}?hash={hash}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_find_executable_discovers_binary() {
        let res = StreamerSidecarService::find_executable();
        assert!(res.is_ok(), "Expected to find fsb.exe in project: {:?}", res);
        let path = res.unwrap();
        assert!(path.is_file(), "Executable must be an existing file");
    }

    #[test]
    fn test_find_workdir_discovers_valid_directory() {
        let res = StreamerSidecarService::find_workdir();
        assert!(res.is_ok(), "Expected to find streamer working dir: {:?}", res);
        let dir = res.unwrap();
        assert!(dir.is_dir(), "Workdir must be a directory");
    }

    #[tokio::test]
    async fn test_mock_streamer_lifecycle() {
        let service = StreamerSidecarService::new_mock(59199);
        let port = service.start().await.expect("Mock start should succeed");
        assert_eq!(port, 59199);

        let status = service.get_status().await;
        match status {
            StreamerStatus::Running { port, host, .. } => {
                assert_eq!(port, 59199);
                assert_eq!(host, "http://127.0.0.1:59199");
            }
            _ => panic!("Expected running status, got {:?}", status),
        }

        let stream_url = service.get_stream_url(100, "abc123").await;
        assert_eq!(
            stream_url,
            Some("http://127.0.0.1:59199/stream/100?hash=abc123".to_string())
        );

        service.stop().await.expect("Stop should succeed");
        let stopped_status = service.get_status().await;
        assert_eq!(stopped_status, StreamerStatus::Stopped);
    }

    #[tokio::test]
    async fn test_mock_streamer_start_with_token() {
        let service = StreamerSidecarService::new_mock(59199);
        let port = service.start_with_token(Some("custom_bot_token")).await.expect("Mock start with token should succeed");
        assert_eq!(port, 59199);
        service.stop().await.expect("Stop should succeed");
    }
}
