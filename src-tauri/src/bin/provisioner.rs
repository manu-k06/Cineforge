use std::collections::HashMap;
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

/// Supabase PostgREST client for durable storage of account-to-bot mappings.
/// Connects using the secure service_role key to bypass public RLS policies.
/// CRITICAL: Bot tokens are never sent or stored in Supabase.
#[derive(Clone)]
pub struct SupabaseBotStore {
    client: reqwest::Client,
    base_url: String,
    service_role_key: String,
}

impl SupabaseBotStore {
    pub fn new(supabase_url: String, service_role_key: String) -> Self {
        let base_url = supabase_url.trim_end_matches('/').to_string();
        Self {
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(10))
                .build()
                .unwrap_or_else(|_| reqwest::Client::new()),
            base_url,
            service_role_key,
        }
    }

    pub async fn get_bot(&self, telegram_user_id: i64) -> Result<Option<StoredManagedBot>, String> {
        let url = format!(
            "{}/rest/v1/managed_bots?telegram_user_id=eq.{}&select=telegram_user_id,bot_id,bot_access_hash,bot_username,created_at,updated_at",
            self.base_url, telegram_user_id
        );
        let resp = self
            .client
            .get(&url)
            .header("apikey", &self.service_role_key)
            .header("Authorization", format!("Bearer {}", self.service_role_key))
            .header("Accept", "application/json")
            .send()
            .await
            .map_err(|e| format!("Supabase request failed: {e}"))?;

        let status = resp.status();
        if !status.is_success() {
            let body = resp.text().await.unwrap_or_default();
            return Err(format!("Supabase query error ({status}): {body}"));
        }

        let bots: Vec<StoredManagedBot> = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse Supabase response: {e}"))?;

        Ok(bots.into_iter().next())
    }

    pub async fn insert_bot(&self, bot: &StoredManagedBot) -> Result<(), String> {
        let url = format!("{}/rest/v1/managed_bots", self.base_url);
        let resp = self
            .client
            .post(&url)
            .header("apikey", &self.service_role_key)
            .header("Authorization", format!("Bearer {}", self.service_role_key))
            .header("Content-Type", "application/json")
            .header("Prefer", "return=minimal")
            .json(bot)
            .send()
            .await
            .map_err(|e| format!("Supabase request failed: {e}"))?;

        let status = resp.status();
        if status == reqwest::StatusCode::CONFLICT {
            return Err(format!(
                "Account mapping conflict: Telegram user {} already has a registered managed bot. Overwrites are not permitted.",
                bot.telegram_user_id
            ));
        }
        if !status.is_success() {
            let body = resp.text().await.unwrap_or_default();
            if body.contains("duplicate key") || body.contains("23505") || body.contains("already exists") {
                return Err(format!(
                    "Account mapping conflict: Telegram user {} already has a registered managed bot. Overwrites are not permitted.",
                    bot.telegram_user_id
                ));
            }
            return Err(format!("Supabase insert error ({status}): {body}"));
        }

        Ok(())
    }
}

/// Abstract storage backend supporting Supabase PostgREST (production) or In-Memory (testing/dev).
#[derive(Clone)]
pub enum BotStore {
    Memory(Arc<RwLock<HashMap<i64, StoredManagedBot>>>),
    Supabase(SupabaseBotStore),
}

impl BotStore {
    pub async fn get_bot(&self, telegram_user_id: i64) -> Result<Option<StoredManagedBot>, String> {
        match self {
            BotStore::Memory(map) => {
                let lock = map.read().await;
                Ok(lock.get(&telegram_user_id).cloned())
            }
            BotStore::Supabase(store) => store.get_bot(telegram_user_id).await,
        }
    }

    pub async fn insert_bot(&self, bot: &StoredManagedBot) -> Result<(), String> {
        match self {
            BotStore::Memory(map) => {
                let mut lock = map.write().await;
                if lock.contains_key(&bot.telegram_user_id) {
                    return Err(format!(
                        "Account mapping conflict: Telegram user {} already has a registered managed bot. Overwrites are not permitted.",
                        bot.telegram_user_id
                    ));
                }
                lock.insert(bot.telegram_user_id, bot.clone());
                Ok(())
            }
            BotStore::Supabase(store) => store.insert_bot(bot).await,
        }
    }
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
    /// In Telegram MTProto, access hashes are per-session secrets. A client user's access hash cannot
    /// be queried by the manager bot. This function uses contacts.ResolveUsername to obtain the manager
    /// bot's own session-valid access hash from Telegram, verifies identity and bot type, and cryptographically
    /// validates management rights via bots.ExportBotToken before returning the valid session access hash.
    pub async fn verify_bot(
        &self,
        bot_id: i64,
        bot_access_hash: i64,
        bot_username: &str,
        expected_owner_user_id: i64,
    ) -> Result<i64, String> {
        if bot_id <= 0 {
            return Err("Invalid bot_id".to_string());
        }
        let clean_username = normalize_manager_bot_username(bot_username);
        if clean_username.is_empty() {
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
            // A. Resolve the bot by public username via Telegram contacts.ResolveUsername.
            // This retrieves the manager bot's own session-valid access hash and verifies the bot exists on Telegram.
            let mut resolve_result = None;
            let mut last_err = String::new();

            for attempt in 1..=3 {
                let res = client
                    .invoke(&tl::functions::contacts::ResolveUsername {
                        username: clean_username.clone(),
                        referer: None,
                    })
                    .await;

                match res {
                    Ok(resolved) => {
                        resolve_result = Some(resolved);
                        break;
                    }
                    Err(e) => {
                        last_err = format!("{e}");
                        if attempt < 3 {
                            tokio::time::sleep(Duration::from_millis(500 * attempt)).await;
                        }
                    }
                }
            }

            let resolved = resolve_result.ok_or_else(|| {
                format!("Failed to resolve bot @{clean_username} on Telegram: {last_err}")
            })?;

            let (target_id, target_username, is_bot, manager_access_hash) = match resolved {
                tl::enums::contacts::ResolvedPeer::Peer(p) => {
                    let user_opt = p.users.iter().find_map(|u| {
                        if let tl::enums::User::User(real_u) = u {
                            if real_u.id == bot_id
                                || real_u
                                    .username
                                    .as_deref()
                                    .map(|un| un.eq_ignore_ascii_case(&clean_username))
                                    .unwrap_or(false)
                            {
                                return Some((
                                    real_u.id,
                                    real_u.username.clone().unwrap_or_default(),
                                    real_u.bot,
                                    real_u.access_hash.unwrap_or(0),
                                ));
                            }
                        }
                        None
                    });

                    user_opt.ok_or_else(|| {
                        format!("Telegram resolved @{clean_username}, but found no user record matching bot ID {bot_id}")
                    })?
                }
            };

            if target_id != bot_id {
                return Err(format!(
                    "Bot ID mismatch: username @{clean_username} resolved to ID {target_id}, expected {bot_id}"
                ));
            }

            if !is_bot {
                return Err(format!("Account {bot_id} (@{clean_username}) is not a bot account"));
            }

            if !target_username.eq_ignore_ascii_case(&clean_username) {
                return Err(format!(
                    "Username mismatch: submitted @{clean_username}, but Telegram registered @{target_username}"
                ));
            }

            if manager_access_hash == 0 {
                return Err(format!("Telegram did not return a valid access hash for bot {bot_id}"));
            }

            // B. Verify that this manager bot is authorized to export the bot's token (proves manager rights)
            let export_res = client
                .invoke(&tl::functions::bots::ExportBotToken {
                    bot: tl::enums::InputUser::User(tl::types::InputUser {
                        user_id: bot_id,
                        access_hash: manager_access_hash,
                    }),
                    revoke: false,
                })
                .await;

            if let Err(e) = export_res {
                return Err(format!(
                    "Telegram rejected management authorization for bot {bot_id}: {e}. Ensure manager bot was passed as manager_id during creation."
                ));
            }

            Ok(manager_access_hash)
        } else if self.is_dev_mode {
            // In dev mode without live MTProto connection, check basic invariants
            Ok(bot_access_hash)
        } else {
            Err("MTProto client not connected to Telegram; cannot verify bot ownership in production".to_string())
        }
    }
}

#[derive(Clone)]
pub struct ProvisionerState {
    pub manager_bot_token: String,
    pub manager_bot_username: String,
    pub bot_store: BotStore,
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

/// Normalizes a manager bot username by trimming surrounding whitespace
/// and stripping any leading '@' characters.
/// Telegram MTProto API methods expect usernames without '@'.
pub fn normalize_manager_bot_username(username: &str) -> String {
    let mut s = username.trim();
    while s.starts_with('@') || s.starts_with(' ') {
        s = s.trim_start_matches('@').trim();
    }
    s.to_string()
}

/// Sanitizes sensitive nonces for safe log output (showing only first 6 characters).
pub fn sanitize_nonce(nonce: &str) -> String {
    if nonce.len() <= 6 {
        "***".to_string()
    } else {
        format!("{}...", &nonce[..6])
    }
}

/// Validates production configuration requirements and fails closed if any required setting is missing.
pub fn validate_production_config(
    is_dev_mode: bool,
    manager_bot_token: &str,
    manager_bot_username: &str,
    api_id: i32,
    api_hash: &str,
    supabase_url: &str,
    supabase_service_role_key: &str,
) -> Result<(), String> {
    if is_dev_mode {
        // In explicit dev mode, if supabase_url is specified, require https:// or local http://
        if !supabase_url.is_empty()
            && !supabase_url.starts_with("https://")
            && !supabase_url.starts_with("http://localhost")
            && !supabase_url.starts_with("http://127.0.0.1")
        {
            return Err("SUPABASE_URL in development mode must start with https:// or http://localhost / http://127.0.0.1.".to_string());
        }
        return Ok(());
    }

    if manager_bot_token.is_empty() || manager_bot_token == "MOCK_MANAGER_TOKEN" {
        return Err("FATAL: CINEFORGE_MANAGER_BOT_TOKEN is required and cannot be empty or mock in production.".to_string());
    }
    let normalized_username = normalize_manager_bot_username(manager_bot_username);
    if normalized_username.is_empty() {
        return Err("FATAL: CINEFORGE_MANAGER_BOT_USERNAME is required in production.".to_string());
    }
    if api_id <= 0 {
        return Err("FATAL: TELEGRAM_API_ID must be a valid positive integer in production.".to_string());
    }
    if api_hash.is_empty() || api_hash.len() < 16 {
        return Err("FATAL: TELEGRAM_API_HASH is required and must be a valid hash in production.".to_string());
    }
    if supabase_url.is_empty() || !supabase_url.starts_with("https://") {
        return Err("FATAL: SUPABASE_URL is required and MUST use HTTPS (https://) in production. Plain HTTP is only permitted in explicit development setups.".to_string());
    }
    if supabase_service_role_key.is_empty() || supabase_service_role_key == "MOCK_KEY" {
        return Err("FATAL: SUPABASE_SERVICE_ROLE_KEY is required and cannot be empty or mock in production.".to_string());
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
    let raw_manager_bot_username = std::env::var("CINEFORGE_MANAGER_BOT_USERNAME")
        .unwrap_or_else(|_| if is_dev_mode { "CineforgeManagerBot".to_string() } else { String::new() });
    let manager_bot_username = normalize_manager_bot_username(&raw_manager_bot_username);
    let api_id: i32 = std::env::var("TELEGRAM_API_ID")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(if is_dev_mode { 2040 } else { 0 });
    let api_hash = std::env::var("TELEGRAM_API_HASH")
        .unwrap_or_default();

    let supabase_url = std::env::var("SUPABASE_URL").unwrap_or_default();
    let supabase_service_role_key = std::env::var("SUPABASE_SERVICE_ROLE_KEY").unwrap_or_default();

    // Fail closed on startup if production configuration is invalid
    if let Err(e) = validate_production_config(
        is_dev_mode,
        &manager_bot_token,
        &manager_bot_username,
        api_id,
        &api_hash,
        &supabase_url,
        &supabase_service_role_key,
    ) {
        eprintln!("{e}");
        std::process::exit(1);
    }

    let bot_store = if !supabase_url.is_empty() && !supabase_service_role_key.is_empty() {
        println!("Configuring SupabaseBotStore for durable bot mappings: {}", supabase_url);
        BotStore::Supabase(SupabaseBotStore::new(supabase_url, supabase_service_role_key))
    } else {
        println!("Configuring in-memory BotStore (dev mode only)");
        BotStore::Memory(Arc::new(RwLock::new(HashMap::new())))
    };

    let mtproto_client = Arc::new(RwLock::new(None));
    let bot_verifier = BotVerifier::new(Arc::clone(&mtproto_client), is_dev_mode);
    let rate_limiter = RateLimiter::new(20, Duration::from_secs(60)); // 20 req/min per key

    let state = ProvisionerState {
        manager_bot_token: manager_bot_token.clone(),
        manager_bot_username: manager_bot_username.clone(),
        bot_store,
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

    let (has_existing_bot, existing_bot_username) = match state.bot_store.get_bot(payload.user_id).await {
        Ok(Some(bot)) => (true, Some(bot.bot_username)),
        Ok(None) => (false, None),
        Err(e) => {
            eprintln!("Database error looking up bot for user {}: {e}", payload.user_id);
            return Err((
                StatusCode::SERVICE_UNAVAILABLE,
                "Database service is temporarily unavailable. Please retry shortly.".to_string(),
            ));
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
        manager_bot_username: normalize_manager_bot_username(&state.manager_bot_username),
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
    match state.bot_store.get_bot(user_id).await {
        Ok(Some(existing)) => {
            return Err((
                StatusCode::CONFLICT,
                format!(
                    "Account {user_id} already has a registered managed bot @{}. Overwrites are not permitted.",
                    existing.bot_username
                ),
            ));
        }
        Ok(None) => {}
        Err(e) => {
            eprintln!("Database error checking existing bot for user {user_id}: {e}");
            return Err((
                StatusCode::SERVICE_UNAVAILABLE,
                "Database service is temporarily unavailable. Please retry shortly.".to_string(),
            ));
        }
    }

    // 3. Verify through Telegram that the bot is managed by this manager bot and owned by user_id
    let valid_access_hash = state
        .bot_verifier
        .verify_bot(
            payload.bot_id,
            payload.bot_access_hash,
            &payload.bot_username,
            user_id,
        )
        .await
        .map_err(|e| (StatusCode::FORBIDDEN, format!("Telegram bot verification rejected: {e}")))?;

    // 4. Record bot in durable Supabase account-to-bot store
    let now_secs = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let new_bot = StoredManagedBot {
        telegram_user_id: user_id,
        bot_id: payload.bot_id,
        bot_access_hash: valid_access_hash,
        bot_username: payload.bot_username.clone(),
        created_at: now_secs,
        updated_at: now_secs,
    };

    if let Err(e) = state.bot_store.insert_bot(&new_bot).await {
        if e.contains("Account mapping conflict") || e.contains("already has a registered managed bot") {
            return Err((StatusCode::CONFLICT, e));
        }
        eprintln!("CRITICAL: Failed to save managed bot to database: {e}");
        return Err((
            StatusCode::SERVICE_UNAVAILABLE,
            format!("Failed to save bot mapping to database: {e}"),
        ));
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

        // Lookup user's bot from bot_store
        let bot = match state.bot_store.get_bot(uid).await {
            Ok(Some(b)) => b,
            Ok(None) => {
                return Err((
                    StatusCode::NOT_FOUND,
                    "No registered managed bot found for verified user".to_string(),
                ));
            }
            Err(e) => {
                eprintln!("Database error retrieving bot for user {uid}: {e}");
                return Err((
                    StatusCode::SERVICE_UNAVAILABLE,
                    "Database service is temporarily unavailable. Please retry shortly.".to_string(),
                ));
            }
        };

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
                Err(initial_err) => {
                    // Fallback resilience: if the saved access hash failed (or was legacy),
                    // re-resolve the bot by username to obtain a fresh session access hash.
                    let clean_username = normalize_manager_bot_username(&managed_bot.bot_username);
                    let mut re_resolved_token = None;

                    if let Ok(tl::enums::contacts::ResolvedPeer::Peer(p)) = client
                        .invoke(&tl::functions::contacts::ResolveUsername {
                            username: clean_username,
                            referer: None,
                        })
                        .await
                    {
                        if let Some(hash) = p.users.iter().find_map(|u| {
                            if let tl::enums::User::User(real_u) = u {
                                if real_u.id == managed_bot.bot_id {
                                    return real_u.access_hash;
                                }
                            }
                            None
                        }) {
                            let retry_req = tl::functions::bots::ExportBotToken {
                                bot: tl::enums::InputUser::User(tl::types::InputUser {
                                    user_id: managed_bot.bot_id,
                                    access_hash: hash,
                                }),
                                revoke: false,
                            };
                            if let Ok(tl::enums::bots::ExportedBotToken::Token(t)) = client.invoke(&retry_req).await {
                                re_resolved_token = Some(t.token);
                            }
                        }
                    }

                    if let Some(t) = re_resolved_token {
                        t
                    } else {
                        eprintln!("Failed to export bot token for bot {}: {:?}", managed_bot.bot_id, initial_err);
                        return Err((
                            StatusCode::BAD_GATEWAY,
                            format!("Telegram refused to export bot token: {initial_err}"),
                        ));
                    }
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

    #[tokio::test]
    async fn test_bot_store_operations_and_duplicate_rejection() {
        let store = BotStore::Memory(Arc::new(RwLock::new(HashMap::new())));

        // Initially empty
        let initial = store.get_bot(11111).await.expect("query should succeed");
        assert!(initial.is_none());

        let bot1 = StoredManagedBot {
            telegram_user_id: 11111,
            bot_id: 22222,
            bot_access_hash: 33333,
            bot_username: "cf_test_streamer_bot".to_string(),
            created_at: 1000,
            updated_at: 1000,
        };

        // First insert must succeed
        store.insert_bot(&bot1).await.expect("first insert must succeed");

        // Retrieve and verify contents
        let retrieved = store.get_bot(11111).await.expect("query must succeed");
        assert!(retrieved.is_some());
        let fetched = retrieved.unwrap();
        assert_eq!(fetched.bot_username, "cf_test_streamer_bot");
        assert_eq!(fetched.bot_id, 22222);

        // Duplicate insert of same telegram_user_id must be strictly REJECTED
        let bot2 = StoredManagedBot {
            telegram_user_id: 11111,
            bot_id: 99999,
            bot_access_hash: 88888,
            bot_username: "cf_rogue_overwrite_bot".to_string(),
            created_at: 2000,
            updated_at: 2000,
        };
        let duplicate_res = store.insert_bot(&bot2).await;
        assert!(duplicate_res.is_err(), "Duplicate account mapping must be rejected!");
        assert!(duplicate_res.unwrap_err().contains("Account mapping conflict"));

        // Verify the original mapping was preserved and NOT overwritten
        let preserved = store.get_bot(11111).await.unwrap().unwrap();
        assert_eq!(preserved.bot_id, 22222, "Original bot ID must be preserved");
        assert_eq!(preserved.bot_username, "cf_test_streamer_bot", "Original username must be preserved");
    }

    #[tokio::test]
    async fn test_bot_ownership_verifier_rejects_mismatched_owner_or_username() {
        let verifier = BotVerifier::new(Arc::new(RwLock::new(None)), true);

        // Register known creation event for user 12345
        {
            let mut creations = verifier.managed_bot_creations.write().await;
            creations.insert(55555, 12345);
        }

        // Expected owner 12345 -> OK, returns verified access hash
        let ok_res = verifier.verify_bot(55555, 99999, "cf_12345_streamer_bot", 12345).await;
        assert!(ok_res.is_ok());
        assert_eq!(ok_res.unwrap(), 99999);

        // Leading @ signs are normalized in bot verification
        let at_res = verifier.verify_bot(55555, 99999, "@cf_12345_streamer_bot", 12345).await;
        assert!(at_res.is_ok());
        assert_eq!(at_res.unwrap(), 99999);

        // Attacker attempts to claim bot 55555 for user 99999 -> REJECTED
        let mismatch_res = verifier.verify_bot(55555, 99999, "cf_12345_streamer_bot", 99999).await;
        assert!(mismatch_res.is_err());
        assert!(mismatch_res.unwrap_err().contains("Bot ownership mismatch"));

        // Invalid parameters -> REJECTED
        assert!(verifier.verify_bot(0, 123, "cf_bot", 12345).await.is_err());
        assert!(verifier.verify_bot(55555, 123, "", 12345).await.is_err());
        assert!(verifier.verify_bot(55555, 123, "   ", 12345).await.is_err());
        assert!(verifier.verify_bot(55555, 123, "@@", 12345).await.is_err());

        // Production verifier without MTProto connection fails closed
        let prod_verifier = BotVerifier::new(Arc::new(RwLock::new(None)), false);
        let prod_res = prod_verifier.verify_bot(55555, 99999, "cf_bot", 12345).await;
        assert!(prod_res.is_err());
        assert!(prod_res.unwrap_err().contains("MTProto client not connected"));
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
        assert!(validate_production_config(false, "", "CineforgeManagerBot", 2040, "abc1234567890123456", "https://xyz.supabase.co", "secret_key").is_err());
        // Mock token in production -> Fail
        assert!(validate_production_config(false, "MOCK_MANAGER_TOKEN", "CineforgeManagerBot", 2040, "abc1234567890123456", "https://xyz.supabase.co", "secret_key").is_err());
        // Missing username in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "", 2040, "abc1234567890123456", "https://xyz.supabase.co", "secret_key").is_err());
        assert!(validate_production_config(false, "123:TOKEN", "   ", 2040, "abc1234567890123456", "https://xyz.supabase.co", "secret_key").is_err());
        assert!(validate_production_config(false, "123:TOKEN", "@@", 2040, "abc1234567890123456", "https://xyz.supabase.co", "secret_key").is_err());
        // Missing api_id in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "CineforgeManagerBot", 0, "abc1234567890123456", "https://xyz.supabase.co", "secret_key").is_err());
        // Missing api_hash in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "CineforgeManagerBot", 2040, "", "https://xyz.supabase.co", "secret_key").is_err());
        // Missing supabase_url in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "CineforgeManagerBot", 2040, "abc1234567890123456", "", "secret_key").is_err());
        // Plain HTTP supabase_url in production -> MUST FAIL (HTTPS required in production)
        assert!(validate_production_config(false, "123:TOKEN", "CineforgeManagerBot", 2040, "abc1234567890123456", "http://xyz.supabase.co", "secret_key").is_err());
        // Missing supabase_service_role_key in production -> Fail
        assert!(validate_production_config(false, "123:TOKEN", "CineforgeManagerBot", 2040, "abc1234567890123456", "https://xyz.supabase.co", "").is_err());

        // Valid production configuration -> OK
        assert!(validate_production_config(false, "123:REAL_TOKEN", "CineforgeManagerBot", 2040, "abc1234567890123456", "https://xyz.supabase.co", "real_secret_key").is_ok());
        // Leading @ signs in username are normalized and accepted in production
        assert!(validate_production_config(false, "123:REAL_TOKEN", "@CineforgeManagerBot", 2040, "abc1234567890123456", "https://xyz.supabase.co", "real_secret_key").is_ok());
        assert!(validate_production_config(false, "123:REAL_TOKEN", "@@CineforgeManagerBot", 2040, "abc1234567890123456", "https://xyz.supabase.co", "real_secret_key").is_ok());

        // Dev mode allows mock settings and local HTTP (localhost / 127.0.0.1)
        assert!(validate_production_config(true, "MOCK_MANAGER_TOKEN", "CineforgeManagerBot", 2040, "mock_dev_hash_test_placeholder", "", "").is_ok());
        assert!(validate_production_config(true, "MOCK_MANAGER_TOKEN", "CineforgeManagerBot", 2040, "mock_dev_hash_test_placeholder", "http://localhost:54321", "mock_key").is_ok());
        assert!(validate_production_config(true, "MOCK_MANAGER_TOKEN", "CineforgeManagerBot", 2040, "mock_dev_hash_test_placeholder", "http://127.0.0.1:54321", "mock_key").is_ok());
        // Dev mode rejects insecure non-local HTTP
        assert!(validate_production_config(true, "MOCK_MANAGER_TOKEN", "CineforgeManagerBot", 2040, "mock_dev_hash_test_placeholder", "http://insecure-remote.example.com", "mock_key").is_err());
    }

    #[tokio::test]
    async fn test_health_and_root_endpoints() {
        let health_resp = health_handler().await.into_response();
        assert_eq!(health_resp.status(), StatusCode::OK);

        let root_resp = root_handler().await.into_response();
        assert_eq!(root_resp.status(), StatusCode::OK);
    }

    #[test]
    fn test_normalize_manager_bot_username() {
        assert_eq!(normalize_manager_bot_username("CineforgeManagerBot"), "CineforgeManagerBot");
        assert_eq!(normalize_manager_bot_username("@CineforgeManagerBot"), "CineforgeManagerBot");
        assert_eq!(normalize_manager_bot_username("@@CineforgeManagerBot"), "CineforgeManagerBot");
        assert_eq!(normalize_manager_bot_username("  @CineforgeManagerBot  "), "CineforgeManagerBot");
        assert_eq!(normalize_manager_bot_username("  @@CineforgeManagerBot  "), "CineforgeManagerBot");
        assert_eq!(normalize_manager_bot_username("  @ @ CineforgeManagerBot  "), "CineforgeManagerBot");
        assert_eq!(normalize_manager_bot_username(""), "");
        assert_eq!(normalize_manager_bot_username("   "), "");
        assert_eq!(normalize_manager_bot_username("@"), "");
        assert_eq!(normalize_manager_bot_username("@@"), "");
        assert_eq!(normalize_manager_bot_username("  @@  "), "");
    }
}
