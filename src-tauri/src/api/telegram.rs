use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use std::sync::Arc;

use crate::models::telegram::{
    CodeLoginRequest, PasswordLoginRequest, PhoneLoginRequest, TelegramAuthActionResponse,
    TelegramAuthStatusResponse, TelegramQrResponse,
};
use crate::services::bot_provisioning::BotProvisioningService;
use crate::services::streamer_sidecar::StreamerSidecarService;
use crate::services::telegram_auth::TelegramAuthService;

#[derive(Clone)]
pub struct TelegramAuthState {
    pub auth: Arc<TelegramAuthService>,
    pub sidecar: Arc<StreamerSidecarService>,
    pub provisioning: Arc<BotProvisioningService>,
}

/// Convenience router builder using default/mock sidecar and provisioning services for tests.
pub fn create_telegram_auth_router(auth_service: Arc<TelegramAuthService>) -> Router {
    let sidecar = Arc::new(StreamerSidecarService::new_mock(59199));
    let provisioning = Arc::new(BotProvisioningService::new_mock(
        88888888,
        "cf_mock_streamer_bot",
        "mock_token",
    ));
    create_telegram_auth_router_with_services(auth_service, sidecar, provisioning)
}

/// Full router builder with live auth, sidecar, and provisioning services.
pub fn create_telegram_auth_router_with_services(
    auth_service: Arc<TelegramAuthService>,
    sidecar_service: Arc<StreamerSidecarService>,
    provisioning_service: Arc<BotProvisioningService>,
) -> Router {
    let state = TelegramAuthState {
        auth: auth_service,
        sidecar: sidecar_service,
        provisioning: provisioning_service,
    };

    Router::new()
        .route("/status", get(get_auth_status))
        .route("/qr/start", post(start_qr))
        .route("/qr/check", get(check_qr))
        .route("/phone", post(request_phone_code))
        .route("/code", post(submit_code))
        .route("/password", post(submit_password))
        .route("/disconnect", post(disconnect))
        .with_state(state)
}

async fn get_auth_status(
    State(state): State<TelegramAuthState>,
) -> Result<Json<TelegramAuthStatusResponse>, (StatusCode, Json<serde_json::Value>)> {
    match state.auth.get_status().await {
        Ok(mut status) => {
            if status.connected {
                status.personal_bot = state.provisioning.get_personal_bot_info().await;
            }
            Ok(Json(status))
        }
        Err(err) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({
                "status": "error",
                "message": err
            })),
        )),
    }
}

async fn start_qr(
    State(state): State<TelegramAuthState>,
) -> Result<Json<TelegramQrResponse>, (StatusCode, Json<serde_json::Value>)> {
    match state.auth.start_qr().await {
        Ok(qr) => Ok(Json(qr)),
        Err(err) => Err((
            StatusCode::BAD_GATEWAY,
            Json(serde_json::json!({
                "status": "error",
                "message": err
            })),
        )),
    }
}

async fn check_qr(
    State(state): State<TelegramAuthState>,
) -> Result<Json<TelegramAuthActionResponse>, (StatusCode, Json<serde_json::Value>)> {
    match state.auth.check_qr().await {
        Ok(res) => Ok(Json(res)),
        Err(err) => Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "status": "error",
                "message": err
            })),
        )),
    }
}

async fn request_phone_code(
    State(state): State<TelegramAuthState>,
    Json(payload): Json<PhoneLoginRequest>,
) -> Result<Json<TelegramAuthActionResponse>, (StatusCode, Json<serde_json::Value>)> {
    if payload.phone.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "status": "error",
                "message": "Phone number cannot be empty."
            })),
        ));
    }

    match state.auth.request_phone_code(&payload.phone).await {
        Ok(res) => Ok(Json(res)),
        Err(err) => Err((
            StatusCode::BAD_GATEWAY,
            Json(serde_json::json!({
                "status": "error",
                "message": err
            })),
        )),
    }
}

async fn submit_code(
    State(state): State<TelegramAuthState>,
    Json(payload): Json<CodeLoginRequest>,
) -> Result<Json<TelegramAuthActionResponse>, (StatusCode, Json<serde_json::Value>)> {
    if payload.code.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "status": "error",
                "message": "Verification code cannot be empty."
            })),
        ));
    }

    match state.auth.submit_code(&payload.code).await {
        Ok(res) => Ok(Json(res)),
        Err(err) => Err((
            StatusCode::BAD_GATEWAY,
            Json(serde_json::json!({
                "status": "error",
                "message": err
            })),
        )),
    }
}

async fn submit_password(
    State(state): State<TelegramAuthState>,
    Json(payload): Json<PasswordLoginRequest>,
) -> Result<Json<TelegramAuthActionResponse>, (StatusCode, Json<serde_json::Value>)> {
    if payload.password.trim().is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "status": "error",
                "message": "Password cannot be empty."
            })),
        ));
    }

    match state.auth.submit_password(&payload.password).await {
        Ok(res) => Ok(Json(res)),
        Err(err) => Err((
            StatusCode::BAD_GATEWAY,
            Json(serde_json::json!({
                "status": "error",
                "message": err
            })),
        )),
    }
}

async fn disconnect(
    State(state): State<TelegramAuthState>,
) -> Result<Json<TelegramAuthActionResponse>, (StatusCode, Json<serde_json::Value>)> {
    // 1. Terminate running Go streamer sidecar process
    let _ = state.sidecar.stop().await;
    // 2. Clear runtime personal bot tokens from memory
    state.provisioning.clear_runtime_tokens().await;
    // 3. Disconnect user session and wipe session file (retaining durable bot mapping)
    match state.auth.disconnect().await {
        Ok(res) => Ok(Json(res)),
        Err(err) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({
                "status": "error",
                "message": err
            })),
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::to_bytes;
    use axum::http::Request;
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_telegram_auth_router_status() {
        let auth_service = Arc::new(TelegramAuthService::new_mock());
        let router = create_telegram_auth_router(auth_service);

        let response = router
            .oneshot(
                Request::builder()
                    .uri("/status")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        let body = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
        let json: TelegramAuthStatusResponse = serde_json::from_slice(&body).unwrap();
        assert_eq!(json.connected, false);
        assert_eq!(json.status, "disconnected");
    }

    #[tokio::test]
    async fn test_telegram_auth_router_qr_flow() {
        let auth_service = Arc::new(TelegramAuthService::new_mock());
        let router = create_telegram_auth_router(auth_service);

        // 1. Start QR
        let res_start = router
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/qr/start")
                    .header("content-type", "application/json")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_start.status(), StatusCode::OK);
        let body = to_bytes(res_start.into_body(), 1024 * 16).await.unwrap();
        let qr: TelegramQrResponse = serde_json::from_slice(&body).unwrap();
        assert!(qr.qr_uri.starts_with("tg://login?token="));

        // 2. Check QR
        let res_check = router
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/qr/check")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_check.status(), StatusCode::OK);
        let body_check = to_bytes(res_check.into_body(), 1024 * 16).await.unwrap();
        let action: TelegramAuthActionResponse = serde_json::from_slice(&body_check).unwrap();
        assert_eq!(action.status, "connected");
        assert_eq!(action.user.unwrap().first_name, "MockUser");

        // 3. Disconnect
        let res_disc = router
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/disconnect")
                    .header("content-type", "application/json")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_disc.status(), StatusCode::OK);
    }
}
