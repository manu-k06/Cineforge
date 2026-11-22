pub mod api;
pub mod commands;
pub mod config;
pub mod models;
pub mod server;
pub mod services;

use std::sync::Mutex;
use tauri::Manager;
use tokio::sync::oneshot;

pub struct ShutdownState(pub Mutex<Option<oneshot::Sender<()>>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    config::load_env_files();
    let config = config::ServerConfig::default();
    let running_server = tauri::async_runtime::block_on(async {
        server::start_server(config).await
    }).expect("failed to start local Axum API service");

    let backend_info = running_server.info.clone();
    let shutdown_tx = running_server.shutdown_tx;

    let app = tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .manage(backend_info)
        .manage(ShutdownState(Mutex::new(shutdown_tx)))
        .invoke_handler(tauri::generate_handler![commands::get_backend_info])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            log::info!("Application exiting, triggering local Axum server shutdown...");
            if let Some(state) = app_handle.try_state::<ShutdownState>() {
                if let Ok(mut lock) = state.0.lock() {
                    if let Some(tx) = lock.take() {
                        let _ = tx.send(());
                    }
                }
            }
        }
    });
}
