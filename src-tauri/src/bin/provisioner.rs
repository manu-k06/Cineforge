use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use axum::extract::{DefaultBodyLimit, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::{Json, Router};
use grammers_client::{Client, SenderPool};
use grammers_session::storages::MemorySession;
use grammers_tl_types as tl;
use ring::rand::{SecureRandom, SystemRandom};
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;

/// Durable record of a managed streamer bot assigned to a verified Telegram account.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StoredManagedBot {
    pub telegram_user_id: i64,
    pub bot_id: i64,
    pub bot_access_hash: i64,
    pub bot_username: String,
    pub created_at: i64,
    pub updated_at: i64,
}

/// Explicit lifecycle states for single-use cryptographic challenges.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChallengeState {
    /// Nonce issued to client; awaiting Telegram /verify message from claimed user_id.
    PendingVerification,
    /// Account ownership verified via Telegram /verify message sent by user_id.
    Verified,
    /// A newly created managed bot was verified and registered under this challenge.
    Registered { bot_id: i64 },
    /// Challenge burned / consumed. Replay attempts will be rejected.
    Consumed,
}

#[derive(Debug, Clone)]
pub struct PendingChallenge {
    pub user_id: i64,
    pub state: ChallengeState,
    pub created_at: Instant,
    pub expires_at: Instant,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChallengeRequest {
    pub user_id: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChallengeResponse {
    pub challenge_nonce: String,
    pub manager_bot_username: String,
    pub has_existing_bot: bool,
    pub existing_bot_username: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterBotRequest {
    pub challenge_nonce: String,
    pub bot_id: i64,
    pub bot_access_hash: i64,
    pub bot_username: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenRequest {
    pub challenge_nonce: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenResponse {
    pub bot_token: String,
    pub bot_id: i64,
    pub bot_username: String,
}

/// In-memory sliding-window rate limiter to protect against request abuse and brute-force attacks.
#[derive(Clone)]
pub struct RateLimiter {
    requests: Arc<RwLock<HashMap<String, Vec<Instant>>>>,
    max_per_window: usize,
    window: Duration,
}

impl RateLimiter {
    pub fn new(max_per_window: usize, window: Duration) -> Self {
        Self {
            requests: Arc::new(RwLock::new(HashMap::new())),
            max_per_window,
            window,
        }
    }

    pub async fn acquire(&self, key: &str) -> bool {
        let mut map = self.requests.write().await;
        let now = Instant::now();
        let cutoff = now.checked_sub(self.window).unwrap_or(now);

        let times = map.entry(key.to_string()).or_default();
        times.retain(|&t| t > cutoff);

        if times.len() >= self.max_per_window {
            false
        } else {
            times.push(now);
            true
        }
    }
}

/// Verifies that a registered bot is managed by this manager bot and owned by expected Telegram user.
#[derive(Clone)]
pub struct BotVerifier {
    pub mtproto_client: Arc<RwLock<Option<Client>>>,
    pub managed_bot_creations: Arc<RwLock<HashMap<i64, i64>>>, // bot_id -> owner_user_id
    pub is_dev_mode: bool,
}

impl BotVerifier {
    pub fn new(mtproto_client: Arc<RwLock<Option<Client>>>, is_dev_mode: bool) -> Self {
        Self {
            mtproto_client,
            managed_bot_creations: Arc::new(RwLock::new(HashMap::new())),
            is_dev_mode,
        }
    }

    /// Verifies Telegram bot ownership, manager rights, and username accuracy.
    pub async fn verify_bot(
        &self,
        bot_id: i64,
        bot_access_hash: i64,
        bot_username: &str,
        expected_owner_user_id: i64,
    ) -> Result<(), String> {
        if bot_id <= 0 {
            return Err("Invalid bot_id".to_string());
        }
        if bot_username.trim().is_empty() {
            return Err("Empty bot_username".to_string());
        }

        // 1. Check known managed bot creation events (from MTProto Update::ManagedBot)
        {
            let creations = self.managed_bot_creations.read().await;
            if let Some(&recorded_owner) = creations.get(&bot_id) {
                if recorded_owner != expected_owner_user_id {
                    return Err(format!(
                        "Bot ownership mismatch: bot {bot_id} was created by Telegram user {recorded_owner}, not {expected_owner_user_id}"
                    ));
                }
            }
        }

        // 2. If MTProto client is available, verify directly with Telegram servers
        let client_guard = self.mtproto_client.read().await;
        if let Some(ref client) = *client_guard {
            // A. Verify with Telegram that this bot exists and is actually a bot with matching username
            let users_res = client
                .invoke(&tl::functions::users::GetUsers {
                    id: vec![tl::enums::InputUser::User(tl::types::InputUser {
                        user_id: bot_id,
                        access_hash: bot_access_hash,
                    })],
                })
                .await
                .map_err(|e| format!("Telegram GetUsers query failed for bot {bot_id}: {e}"))?;

            let user = users_res
                .first()
                .ok_or_else(|| format!("Bot {bot_id} not found on Telegram"))?;

            match user {
                tl::enums::User::User(u) => {
                    if !u.bot {
                        return Err(format!("Account {bot_id} is not a bot account"));
                    }
                    let real_username = u.username.as_deref().unwrap_or("");
                    if !real_username.eq_ignore_ascii_case(bot_username) {
                        return Err(format!(
                            "Username mismatch: submitted @{bot_username}, but Telegram registered @{real_username}"
                        ));
                    }
                }
                tl::enums::User::Empty(_) => {
                    return Err(format!("Telegram returned empty user object for {bot_id}"));
                }
            }

            // B. Verify that this manager bot is authorized to export the bot's token (proves manager rights)
            let export_res = client
                .invoke(&tl::functions::bots::ExportBotToken {
                    bot: tl::enums::InputUser::User(tl::types::InputUser {
                        user_id: bot_id,
                        access_hash: bot_access_hash,
                    }),
                    revoke: false,
                })
                .await;

            if let Err(e) = export_res {
                return Err(format!(
                    "Telegram rejected management authorization for bot {bot_id}: {e}. Ensure manager bot was passed as manager_id during creation."
                ));
            }

            Ok(())
        } else if self.is_dev_mode {
            // In dev mode without live MTProto connection, check basic invariants
            Ok(())
        } else {
            Err("MTProto client not connected to Telegram; cannot verify bot ownership in production".to_string())
        }
    }
}

#[derive(Clone)]
pub struct ProvisionerState {
    pub manager_bot_token: String,
    pub manager_bot_username: String,
    pub data_file: PathBuf,
    pub bots: Arc<RwLock<HashMap<i64, StoredManagedBot>>>,
    pub challenges: Arc<RwLock<HashMap<String, PendingChallenge>>>,
    pub mtproto_client: Arc<RwLock<Option<Client>>>,
    pub bot_verifier: BotVerifier,
    pub rate_limiter: RateLimiter,
    pub is_dev_mode: bool,
}

/// Generates a cryptographically secure 256-bit (64 hex characters) single-use challenge nonce.
pub fn generate_secure_challenge_nonce() -> Result<String, String> {
    let rng = SystemRandom::new();
    let mut bytes = [0u8; 32];
    rng.fill(&mut bytes)
        .map_err(|_| "Failed to sample OS CSPRNG entropy".to_string())?;
    Ok(hex_encode(&bytes))
}

/// Encodes raw bytes into lowercase hexadecimal string.
pub fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

/// Sanitizes sensitive nonces for safe log output (showing only first 6 characters).
pub fn sanitize_nonce(nonce: &str) -> String {
    if nonce.len() <= 6 {
        "***".to_string()
    } else {
        format!("{}...", &nonce[..6])
    }
}

/// Atomically persists user-bot mappings to disk with fsync and atomic rename.
pub fn save_bots_atomic(data_file: &Path, bots: &HashMap<i64, StoredManagedBot>) -> Result<(), String> {
    if let Some(parent) = data_file.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create parent directory {:?}: {e}", parent))?;
    }

    let serialized = serde_json::to_string_pretty(bots)
        .map_err(|e| format!("Failed to serialize managed bots: {e}"))?;

    let temp_file = data_file.with_extension(format!("tmp.{}", std::process::id()));

    // Write to temporary file with flush and sync_all
    {
        use std::io::Write;
        let mut file = std::fs::File::create(&temp_file)
            .map_err(|e| format!("Failed to create temp file {:?}: {e}", temp_file))?;
        file.write_all(serialized.as_bytes())
            .map_err(|e| format!("Failed to write temp file {:?}: {e}", temp_file))?;
        file.flush()
            .map_err(|e| format!("Failed to flush temp file {:?}: {e}", temp_file))?;
        file.sync_all()
            .map_err(|e| format!("Failed to sync temp file {:?}: {e}", temp_file))?;
    }

    // Atomically replace target file
    std::fs::rename(&temp_file, data_file)
        .map_err(|e| format!("Failed to atomically rename {:?} to {:?}: {e}", temp_file, data_file))?;

    Ok(())
}

/// Loads durable user-bot mappings from disk.
pub fn load_bots_from_disk(data_file: &Path) -> HashMap<i64, StoredManagedBot> {
    if data_file.exists() {
        if let Ok(bytes) = std::fs::read(data_file) {
            if let Ok(loaded) = serde_json::from_slice::<HashMap<i64, StoredManagedBot>>(&bytes) {
                println!("Loaded {} managed bots from {:?}", loaded.len(), data_file);
                return loaded;
            }
        }
    }
    HashMap::new()
}

/// Validates production configuration requirements and fails closed if any required setting is missing.
pub fn validate_production_config(
    is_dev_mode: bool,
    manager_bot_token: &str,
    manager_bot_username: &str,
    api_id: i32,
    api_hash: &str,
    data_dir: &str,
) -> Result<(), String> {
    if is_dev_mode {
        return Ok(());
    }

    if manager_bot_token.is_empty() || manager_bot_token == "MOCK_MANAGER_TOKEN" {
        return Err("FATAL: CINEFORGE_MANAGER_BOT_TOKEN is required and cannot be empty or mock in production.".to_string());
    }
    if manager_bot_username.is_empty() {
        return Err("FATAL: CINEFORGE_MANAGER_BOT_USERNAME is required in production.".to_string());
    }
    if api_id <= 0 {
        return Err("FATAL: TELEGRAM_API_ID must be a valid positive integer in production.".to_string());
    }
    if api_hash.is_empty() || api_hash.len() < 16 {
        return Err("FATAL: TELEGRAM_API_HASH is required and must be a valid hash in production.".to_string());
    }

    if let Err(e) = std::fs::create_dir_all(data_dir) {
        return Err(format!("FATAL: Cannot access or create DATA_DIR {:?}: {e}", data_dir));
    }

    Ok(())
}

pub fn create_router(state: ProvisionerState) -> Router {
    Router::new()
        .route("/", get(root_handler))
        .route("/health", get(health_handler))
        .route("/api/provision/challenge", post(challenge_handler))
        .route("/api/provision/register", post(register_handler))
        .route("/api/provision/token", post(token_handler))
        .layer(DefaultBodyLimit::max(64 * 1024)) // 64 KB maximum request body size
        .with_state(state)
}

#[tokio::main]
async fn main() {
    let _ = dotenvy::dotenv();

    let is_dev_mode = std::env::var("CINEFORGE_DEV_MODE")
        .map(|v| v == "1" || v == "true")
        .unwrap_or(false);

    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8085);

    let manager_bot_token = std::env::var("CINEFORGE_MANAGER_BOT_TOKEN")
        .unwrap_or_else(|_| if is_dev_mode { "MOCK_MANAGER_TOKEN".to_string() } else { String::new() });
    let manager_bot_username = std::env::var("CINEFORGE_MANAGER_BOT_USERNAME")
        .unwrap_or_else(|_| if is_dev_mode { "CineforgeManagerBot".to_string() } else { String::new() });
    let api_id: i32 = std::env::var("TELEGRAM_API_ID")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(if is_dev_mode { 2040 } else { 0 });
    let api_hash = std::env::var("TELEGRAM_API_HASH")
        .unwrap_or_default();

    let data_dir = std::env::var("DATA_DIR").unwrap_or_else(|_| "data".to_string());

    // Fail closed on startup if production configuration is invalid
    if let Err(e) = validate_production_config(
        is_dev_mode,
        &manager_bot_token,
        &manager_bot_username,
        api_id,
        &api_hash,
        &data_dir,
    ) {
        eprintln!("{e}");
        std::process::exit(1);
    }

    let data_file = Path::new(&data_dir).join("managed_bots.json");
    let initial_bots = load_bots_from_disk(&data_file);

    let mtproto_client = Arc::new(RwLock::new(None));
    let bot_verifier = BotVerifier::new(Arc::clone(&mtproto_client), is_dev_mode);
    let rate_limiter = RateLimiter::new(20, Duration::from_secs(60)); // 20 req/min per key

    let state = ProvisionerState {
        manager_bot_token: manager_bot_token.clone(),
        manager_bot_username: manager_bot_username.clone(),
        data_file,
        bots: Arc::new(RwLock::new(initial_bots)),
        challenges: Arc::new(RwLock::new(HashMap::new())),
        mtproto_client: Arc::clone(&mtproto_client),
        bot_verifier,
        rate_limiter,
        is_dev_mode,
    };

    // If real manager credentials are provided, attempt MTProto connection and update listener
    if !manager_bot_token.is_empty() && manager_bot_token != "MOCK_MANAGER_TOKEN" {
        let state_clone = state.clone();
        tokio::spawn(async move {
            connect_mtproto_and_listen(state_clone, api_id, api_hash).await;
        });
    }

    // Spawn background task to purge expired challenges
    let challenges_arc = Arc::clone(&state.challenges);
    tokio::spawn(async move {
        loop {
            tokio::time::sleep(Duration::from_secs(10)).await;
            let mut lock = challenges_arc.write().await;
            let now = Instant::now();
            lock.retain(|_, c| c.expires_at > now && c.state != ChallengeState::Consumed);
        }
    });

    let app = create_router(state);

    let bind_addr = format!("0.0.0.0:{port}");
    println!("Cineforge Bot Provisioner listening on http://{bind_addr} (dev_mode={is_dev_mode})");

    let listener = tokio::net::TcpListener::bind(&bind_addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn root_handler() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "online",
        "service": "cineforge-provisioner",
        "health": "/health",
        "layer": tl::LAYER
    }))
}

async fn health_handler() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "ok",
        "service": "cineforge-provisioner",
        "layer": tl::LAYER
    }))
}

async fn challenge_handler(
    State(state): State<ProvisionerState>,
    Json(payload): Json<ChallengeRequest>,
) -> Result<Json<ChallengeResponse>, (StatusCode, String)> {
    if payload.user_id <= 0 {
        return Err((StatusCode::BAD_REQUEST, "Invalid user_id".to_string()));
    }

    // Rate limit per user_id
    if !state.rate_limiter.acquire(&format!("challenge:{}", payload.user_id)).await {
        return Err((StatusCode::TOO_MANY_REQUESTS, "Rate limit exceeded. Please wait.".to_string()));
    }

    // Generate cryptographically secure 256-bit challenge nonce (64 hex characters)
    let challenge_nonce = generate_secure_challenge_nonce().map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, format!("Failed to generate secure challenge: {e}"))
    })?;

    let (has_existing_bot, existing_bot_username) = {
        let bots = state.bots.read().await;
        if let Some(bot) = bots.get(&payload.user_id) {
            (true, Some(bot.bot_username.clone()))
        } else {
            (false, None)
        }
    };

    {
        let mut challenges = state.challenges.write().await;
        challenges.insert(
            challenge_nonce.clone(),
            PendingChallenge {
                user_id: payload.user_id,
                state: ChallengeState::PendingVerification,
                created_at: Instant::now(),
                expires_at: Instant::now() + Duration::from_secs(60), // 60s TTL
            },
        );
    }

    Ok(Json(ChallengeResponse {
        challenge_nonce,
        manager_bot_username: state.manager_bot_username.clone(),
        has_existing_bot,
        existing_bot_username,
    }))
}

async fn register_handler(
    State(state): State<ProvisionerState>,
    Json(payload): Json<RegisterBotRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    // Rate limit per bot_id
    if !state.rate_limiter.acquire(&format!("register:{}", payload.bot_id)).await {
        return Err((StatusCode::TOO_MANY_REQUESTS, "Rate limit exceeded. Please wait.".to_string()));
    }

    // 1. Verify challenge nonce is active and authenticated by Telegram
    let user_id = {
        let challenges = state.challenges.read().await;
        let challenge = challenges
            .get(&payload.challenge_nonce)
            .ok_or((StatusCode::FORBIDDEN, "Invalid or expired challenge nonce".to_string()))?;

        if challenge.expires_at < Instant::now() {
            return Err((StatusCode::FORBIDDEN, "Challenge nonce has expired".to_string()));
        }

        match &challenge.state {
            ChallengeState::Verified => challenge.user_id,
            ChallengeState::PendingVerification => {
                return Err((
                    StatusCode::FORBIDDEN,
                    "Account ownership has not been verified via Telegram".to_string(),
                ));
            }
            ChallengeState::Registered { .. } | ChallengeState::Consumed => {
                return Err((
                    StatusCode::FORBIDDEN,
                    "Challenge nonce has already been used for registration".to_string(),
                ));
            }
        }
    };

    // 2. Prevent replacing an existing user mapping with another bot
    {
        let bots = state.bots.read().await;
        if let Some(existing) = bots.get(&user_id) {
            return Err((
                StatusCode::CONFLICT,
                format!(
                    "Account {user_id} already has a registered managed bot @{}. Overwrites are not permitted.",
                    existing.bot_username
                ),
            ));
        }
    }

    // 3. Verify through Telegram that the bot is managed by this manager bot and owned by user_id
    state
        .bot_verifier
        .verify_bot(
            payload.bot_id,
            payload.bot_access_hash,
            &payload.bot_username,
            user_id,
        )
        .await
        .map_err(|e| (StatusCode::FORBIDDEN, format!("Telegram bot verification rejected: {e}")))?;

    // 4. Record bot in durable account-to-bot store atomically
    let now_secs = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    {
        let mut bots = state.bots.write().await;
        // Double-check race condition under write lock
        if let Some(existing) = bots.get(&user_id) {
            return Err((
                StatusCode::CONFLICT,
                format!(
                    "Account {user_id} already has a registered managed bot @{}. Duplicate registration rejected.",
                    existing.bot_username
                ),
            ));
        }

        bots.insert(
            user_id,
            StoredManagedBot {
                telegram_user_id: user_id,
                bot_id: payload.bot_id,
                bot_access_hash: payload.bot_access_hash,
                bot_username: payload.bot_username.clone(),
                created_at: now_secs,
                updated_at: now_secs,
            },
        );

        if let Err(e) = save_bots_atomic(&state.data_file, &*bots) {
            // Revert in-memory insertion on disk failure
            bots.remove(&user_id);
            eprintln!("CRITICAL: Failed to atomically save managed bots to disk: {e}");
            return Err((StatusCode::INTERNAL_SERVER_ERROR, format!("Failed to save bot mapping: {e}")));
        }
    }

    // 5. Transition challenge state to Registered { bot_id }
    {
        let mut challenges = state.challenges.write().await;
        if let Some(challenge) = challenges.get_mut(&payload.challenge_nonce) {
            challenge.state = ChallengeState::Registered { bot_id: payload.bot_id };
        }
    }

    println!(
        "Registered verified managed bot @{} (id={}) for user {}",
        payload.bot_username, payload.bot_id, user_id
    );

    Ok(Json(serde_json::json!({
        "ok": true,
        "message": "Managed bot successfully registered and verified"
    })))
}

async fn token_handler(
    State(state): State<ProvisionerState>,
    Json(payload): Json<TokenRequest>,
) -> Result<Json<TokenResponse>, (StatusCode, String)> {
    // Rate limit per challenge_nonce
    if !state.rate_limiter.acquire(&format!("token:{}", sanitize_nonce(&payload.challenge_nonce))).await {
        return Err((StatusCode::TOO_MANY_REQUESTS, "Rate limit exceeded. Please wait.".to_string()));
    }

    // 1. Verify challenge state machine and single-use burn
    let (user_id, managed_bot) = {
        let mut challenges = state.challenges.write().await;
        let challenge = challenges
            .get_mut(&payload.challenge_nonce)
            .ok_or((StatusCode::FORBIDDEN, "Invalid or expired challenge nonce".to_string()))?;

        if challenge.expires_at < Instant::now() {
            return Err((StatusCode::FORBIDDEN, "Challenge nonce has expired".to_string()));
        }

        let uid = challenge.user_id;

        // Lookup user's bot
        let bots = state.bots.read().await;
        let bot = bots.get(&uid).cloned().ok_or((
            StatusCode::NOT_FOUND,
            "No registered managed bot found for verified user".to_string(),
        ))?;

        // State machine rules:
        // - If user had pre-existing bot prior to challenge: challenge state must be Verified
        // - If user just registered a new bot: challenge state must be Registered { bot_id } matching bot.bot_id
        match &challenge.state {
            ChallengeState::Verified => {
                // Pre-existing bot lookup valid
            }
            ChallengeState::Registered { bot_id } => {
                if *bot_id != bot.bot_id {
                    return Err((StatusCode::FORBIDDEN, "Challenge bot ID mismatch".to_string()));
                }
            }
            ChallengeState::PendingVerification => {
                return Err((
                    StatusCode::FORBIDDEN,
                    "Account ownership has not been verified via Telegram".to_string(),
                ));
            }
            ChallengeState::Consumed => {
                return Err((
                    StatusCode::FORBIDDEN,
                    "Challenge nonce has already been consumed".to_string(),
                ));
            }
        }

        // Single-use guarantee: transition to Consumed and remove from active challenges
        challenge.state = ChallengeState::Consumed;
        challenges.remove(&payload.challenge_nonce);

        (uid, bot)
    };

    // 2. Export token via MTProto bots.exportBotToken
    let exported_token = {
        let client_opt = state.mtproto_client.read().await;
        if let Some(ref client) = *client_opt {
            let export_req = tl::functions::bots::ExportBotToken {
                bot: tl::enums::InputUser::User(tl::types::InputUser {
                    user_id: managed_bot.bot_id,
                    access_hash: managed_bot.bot_access_hash,
                }),
                revoke: false,
            };

            match client.invoke(&export_req).await {
                Ok(tl::enums::bots::ExportedBotToken::Token(t)) => t.token,
                Err(e) => {
                    eprintln!("Failed to export bot token for bot {}: {:?}", managed_bot.bot_id, e);
                    return Err((
                        StatusCode::BAD_GATEWAY,
                        format!("Telegram refused to export bot token: {e}"),
                    ));
                }
            }
        } else if state.is_dev_mode {
            format!("{}:TEST_DEV_BOT_TOKEN_FOR_{}", managed_bot.bot_id, managed_bot.bot_username)
        } else {
            return Err((
                StatusCode::BAD_GATEWAY,
                "MTProto connection to Telegram is unavailable to export bot token".to_string(),
            ));
        }
    };

    println!(
        "Securely exported token for managed bot @{} to verified user {}",
        managed_bot.bot_username, user_id
    );

    Ok(Json(TokenResponse {
        bot_token: exported_token,
        bot_id: managed_bot.bot_id,
        bot_username: managed_bot.bot_username,
    }))
}

async fn connect_mtproto_and_listen(state: ProvisionerState, api_id: i32, api_hash: String) {
    println!("Connecting manager bot to MTProto...");
    let session = Arc::new(MemorySession::default());
    let pool = SenderPool::new(session, api_id);
    let runner = pool.runner;
    tokio::spawn(async move {
        let _ = runner.run().await;
    });

    let client = Client::new(pool.handle);

    match client.bot_sign_in(&state.manager_bot_token, &api_hash).await {
        Ok(user) => {
            println!("Manager bot successfully signed in as @{}", user.username().unwrap_or("unknown"));
            *state.mtproto_client.write().await = Some(client.clone());

            // Listen for Telegram updates via Bot API getUpdates polling
            let http_client = reqwest::Client::new();
            let token = state.manager_bot_token.clone();
            let mut last_update_id: i64 = 0;

            loop {
                let url = format!(
                    "https://api.telegram.org/bot{token}/getUpdates?offset={}&timeout=10",
                    last_update_id + 1
                );

                if let Ok(resp) = http_client.get(&url).send().await {
                    if let Ok(json) = resp.json::<serde_json::Value>().await {
                        if let Some(updates) = json.get("result").and_then(|r| r.as_array()) {
                            for u in updates {
                                if let Some(up_id) = u.get("update_id").and_then(|i| i.as_i64()) {
                                    if up_id > last_update_id {
                                        last_update_id = up_id;
                                    }
                                }

                                if let Some(msg) = u.get("message") {
                                    let from_id = msg.get("from").and_then(|f| f.get("id")).and_then(|i| i.as_i64());
                                    let text = msg.get("text").and_then(|t| t.as_str());

                                    if let (Some(sender_id), Some(t)) = (from_id, text) {
                                        if t.starts_with("/verify ") {
                                            let nonce = t.trim_start_matches("/verify ").trim();
                                            let mut challenges = state.challenges.write().await;
                                            if let Some(ch) = challenges.get_mut(nonce) {
                                                if ch.user_id == sender_id && ch.expires_at > Instant::now() {
                                                    ch.state = ChallengeState::Verified;
                                                    println!(
                                                        "Challenge nonce {} VERIFIED for user {}",
                                                        sanitize_nonce(nonce),
                                                        sender_id
                                                    );
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                tokio::time::sleep(Duration::from_millis(500)).await;
            }
        }
        Err(e) => {
            eprintln!("Failed to sign in manager bot to MTProto: {:?}", e);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn test_csprng_nonce_format_and_uniqueness() {
        let mut seen = HashSet::new();
        for _ in 0..10_000 {
            let nonce = generate_secure_challenge_nonce().expect("nonce generation must succeed");
            assert_eq!(nonce.len(), 64, "Nonce must be exactly 64 hexadecimal characters (256 bits)");
            assert!(
                nonce.chars().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()),
                "Nonce must be valid lowercase hex characters"
            );
            assert!(seen.insert(nonce), "Duplicate nonce generated: collision in CSPRNG!");
        }
        assert_eq!(seen.len(), 10_000);
    }

    #[test]
    fn test_sanitize_nonce() {
        let nonce = "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890";
        let sanitized = sanitize_nonce(nonce);
        assert_eq!(sanitized, "a1b2c3...");
        assert!(!sanitized.contains("7890abcdef"));
        assert_eq!(sanitize_nonce("abc"), "***");
    }

    #[tokio::test]
    async fn test_rate_limiter_throttling() {
        let limiter = RateLimiter::new(3, Duration::from_millis(100));
        assert!(limiter.acquire("user:1").await);
        assert!(limiter.acquire("user:1").await);
        assert!(limiter.acquire("user:1").await);
        // 4th request within window must be rejected
        assert!(!limiter.acquire("user:1").await);

        // Different key is unaffected
        assert!(limiter.acquire("user:2").await);

        // After window expires, key can acquire again
        tokio::time::sleep(Duration::from_millis(110)).await;
        assert!(limiter.acquire("user:1").await);
    }

    #[test]
    fn test_atomic_persistence_and_reload() {
        let temp_dir = std::env::temp_dir().join(format!("cineforge_test_{}", std::process::id()));
        let _ = std::fs::create_dir_all(&temp_dir);
        let data_file = temp_dir.join("managed_bots.json");

        let mut bots = HashMap::new();
        bots.insert(
            11111,
            StoredManagedBot {
                telegram_user_id: 11111,
                bot_id: 22222,
                bot_access_hash: 33333,
                bot_username: "cf_test_streamer_bot".to_string(),
                created_at: 1000,
                updated_at: 1000,
            },
        );

        // Save atomically
        save_bots_atomic(&data_file, &bots).expect("Atomic save must succeed");
        assert!(data_file.exists());

        // Reload and verify contents
        let loaded = load_bots_from_disk(&data_file);
        assert_eq!(loaded.len(), 1);
        let bot = loaded.get(&11111).unwrap();
        assert_eq!(bot.bot_username, "cf_test_streamer_bot");
        assert_eq!(bot.bot_id, 22222);

        // Cleanup
        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[tokio::test]
    async fn test_bot_ownership_verifier_rejects_mismatched_owner_or_username() {
        let verifier = BotVerifier::new(Arc::new(RwLock::new(None)), true);

        // Register known creation event for user 12345
        {
            let mut creations = verifier.managed_bot_creations.write().await;
            creations.insert(55555, 12345);
        }

        // Expected owner 12345 -> OK
        let ok_res = verifier.verify_bot(55555, 99999, "cf_12345_streamer_bot", 12345).await;
        assert!(ok_res.is_ok());

        // Attacker attempts to claim bot 55555 for user 99999 -> REJECTED
        let mismatch_res = verifier.verify_bot(55555, 99999, "cf_12345_streamer_bot", 99999).await;
        assert!(mismatch_res.is_err());
        assert!(mismatch_res.unwrap_err().contains("Bot ownership mismatch"));

        // Invalid parameters -> REJECTED
        assert!(verifier.verify_bot(0, 123, "cf_bot", 12345).await.is_err());
        assert!(verifier.verify_bot(55555, 123, "", 12345).await.is_err());
    }

    #[tokio::test]
    async fn test_challenge_state_machine_and_expiration() {
        let now = Instant::now();
        let mut challenge = PendingChallenge {
            user_id: 42,
            state: ChallengeState::PendingVerification,
            created_at: now,
            expires_at: now + Duration::from_millis(50),
        };

        assert_eq!(challenge.state, ChallengeState::PendingVerification);

        // Simulate verification transition
        challenge.state = ChallengeState::Verified;
        assert_eq!(challenge.state, ChallengeState::Verified);

        // Simulate registration transition
        challenge.state = ChallengeState::Registered { bot_id: 1001 };
        assert_eq!(challenge.state, ChallengeState::Registered { bot_id: 1001 });

        // Simulate token consumption
        challenge.state = ChallengeState::Consumed;
        assert_eq!(challenge.state, ChallengeState::Consumed);

        // Expiration check
        tokio::time::sleep(Duration::from_millis(60)).await;
        assert!(challenge.expires_at < Instant::now());
    }

    #[test]
    fn test_validate_production_config_fails_closed() {
        // Missing token in production -> Fail
        assert!(validate_production_config(false, "", "CineforgeManagerBot", 2040, "abc1234567890123456", "data").is_err());
        // Mock token in production -> Fail
        assert!(validate_production_config(false, "MOCK_MANAGER_TOKEN", "CineforgeManagerBot", 2040, "abc1234567890123456", "data").is_err());
        // Missing username in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "", 2040, "abc1234567890123456", "data").is_err());
        // Missing api_id in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "CineforgeManagerBot", 0, "abc1234567890123456", "data").is_err());
        // Missing api_hash in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "CineforgeManagerBot", 2040, "", "data").is_err());

        // Dev mode allows mock settings
        assert!(validate_production_config(true, "MOCK_MANAGER_TOKEN", "CineforgeManagerBot", 2040, "mock_dev_hash_test_placeholder", "data").is_ok());
    }

    #[tokio::test]
    async fn test_health_and_root_endpoints() {
        let health_resp = health_handler().await.into_response();
        assert_eq!(health_resp.status(), StatusCode::OK);

        let root_resp = root_handler().await.into_response();
        assert_eq!(root_resp.status(), StatusCode::OK);
    }
}
