use crate::server::BackendInfo;
use tauri::State;

/// Tauri command invoked by the desktop frontend to discover the local Axum backend address.
#[tauri::command]
pub fn get_backend_info(state: State<'_, BackendInfo>) -> BackendInfo {
    state.inner().clone()
}
