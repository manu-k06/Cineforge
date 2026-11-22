use serde::{Deserialize, Serialize};
use std::net::Ipv4Addr;
use std::path::PathBuf;

/// Loads supported `.env` configuration files without overwriting existing environment variables.
/// Checks:
/// 1. Current working directory `.env`
/// 2. Installed application directory (`<exe_dir>/.env`)
/// 3. `%APPDATA%\Cineforge\.env` (user configuration directory)
/// 4. `backend/.env` and `../backend/.env` (development/migration)
/// 5. `frontend/.env` and `../frontend/.env` (development)
pub fn load_env_files() {
    let _ = dotenvy::dotenv();

    let mut candidate_paths = vec![
        PathBuf::from(".env"),
        crate::services::storage::get_storage_dir().join(".env"),
        PathBuf::from("backend/.env"),
        PathBuf::from("../backend/.env"),
        PathBuf::from("frontend/.env"),
        PathBuf::from("../frontend/.env"),
    ];

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            candidate_paths.push(exe_dir.join(".env"));
        }
    }

    for path in &candidate_paths {
        if path.exists() {
            let _ = dotenvy::from_path(path);
        }
    }
}

/// Strongly-typed configuration for the local Rust desktop backend.
/// Uses safe defaults: strictly loopback (127.0.0.1) and an ephemeral port (0)
/// to eliminate port collision with Python (8000), Streamer (8088), or Vite (5173).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: Ipv4Addr,
    pub port: u16,
    pub app_name: String,
    pub environment: String,
}

impl Default for ServerConfig {
    fn default() -> Self {
        load_env_files();

        let port = std::env::var("CINEFORGE_API_PORT")
            .ok()
            .and_then(|p| p.parse::<u16>().ok())
            .unwrap_or(0); // 0 = OS assigns an available ephemeral port

        Self {
            host: Ipv4Addr::new(127, 0, 0, 1),
            port,
            app_name: "Cineforge Local Desktop API".to_string(),
            environment: "desktop".to_string(),
        }
    }
}
