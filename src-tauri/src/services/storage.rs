use std::fs;
use std::path::PathBuf;

#[derive(Debug, thiserror::Error)]
pub enum StorageError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Windows DPAPI error: {0}")]
    Dpapi(String),
}

/// Returns the Cineforge app data directory: `%APPDATA%\Cineforge` on Windows,
/// or an appropriate fallback path in user home or local temp for testing.
pub fn get_storage_dir() -> PathBuf {
    if let Ok(appdata) = std::env::var("APPDATA") {
        PathBuf::from(appdata).join("Cineforge")
    } else if let Ok(home) = std::env::var("USERPROFILE").or_else(|_| std::env::var("HOME")) {
        PathBuf::from(home).join(".cineforge")
    } else {
        std::env::temp_dir().join("cineforge")
    }
}

/// Returns the path to the encrypted Telegram session file.
pub fn get_session_file_path() -> PathBuf {
    get_storage_dir().join("telegram_session.enc")
}

#[cfg(target_os = "windows")]
mod dpapi {
    use super::StorageError;

    const CRYPTPROTECT_UI_FORBIDDEN: u32 = 0x1;

    #[repr(C)]
    struct DataBlob {
        cb_data: u32,
        pb_data: *mut u8,
    }

    #[link(name = "crypt32")]
    unsafe extern "system" {
        fn CryptProtectData(
            p_data_in: *mut DataBlob,
            sz_data_descr: *const u16,
            p_optional_entropy: *mut DataBlob,
            pv_reserved: *mut std::ffi::c_void,
            p_prompt_struct: *mut std::ffi::c_void,
            dw_flags: u32,
            p_data_out: *mut DataBlob,
        ) -> i32;

        fn CryptUnprotectData(
            p_data_in: *mut DataBlob,
            ppsz_data_descr: *mut *mut u16,
            p_optional_entropy: *mut DataBlob,
            pv_reserved: *mut std::ffi::c_void,
            p_prompt_struct: *mut std::ffi::c_void,
            dw_flags: u32,
            p_data_out: *mut DataBlob,
        ) -> i32;
    }

    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn LocalFree(h_mem: *mut std::ffi::c_void) -> *mut std::ffi::c_void;
    }

    /// Encrypts byte data at rest using the current Windows user's DPAPI master key.
    pub fn encrypt(data: &[u8]) -> Result<Vec<u8>, StorageError> {
        if data.is_empty() {
            return Ok(Vec::new());
        }

        let mut data_in = DataBlob {
            cb_data: data.len() as u32,
            pb_data: data.as_ptr() as *mut u8,
        };
        let mut data_out = DataBlob {
            cb_data: 0,
            pb_data: std::ptr::null_mut(),
        };

        let res = unsafe {
            CryptProtectData(
                &mut data_in,
                std::ptr::null(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                CRYPTPROTECT_UI_FORBIDDEN,
                &mut data_out,
            )
        };

        if res == 0 {
            let err = std::io::Error::last_os_error();
            return Err(StorageError::Dpapi(format!("CryptProtectData failed: {err}")));
        }

        let slice = unsafe { std::slice::from_raw_parts(data_out.pb_data, data_out.cb_data as usize) };
        let ciphertext = slice.to_vec();
        unsafe { LocalFree(data_out.pb_data as _) };
        Ok(ciphertext)
    }

    /// Decrypts data that was previously encrypted with Windows DPAPI.
    pub fn decrypt(ciphertext: &[u8]) -> Result<Vec<u8>, StorageError> {
        if ciphertext.is_empty() {
            return Ok(Vec::new());
        }

        let mut data_in = DataBlob {
            cb_data: ciphertext.len() as u32,
            pb_data: ciphertext.as_ptr() as *mut u8,
        };
        let mut data_out = DataBlob {
            cb_data: 0,
            pb_data: std::ptr::null_mut(),
        };

        let res = unsafe {
            CryptUnprotectData(
                &mut data_in,
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                CRYPTPROTECT_UI_FORBIDDEN,
                &mut data_out,
            )
        };

        if res == 0 {
            let err = std::io::Error::last_os_error();
            return Err(StorageError::Dpapi(format!("CryptUnprotectData failed: {err}")));
        }

        let slice = unsafe { std::slice::from_raw_parts(data_out.pb_data, data_out.cb_data as usize) };
        let plaintext = slice.to_vec();
        unsafe { LocalFree(data_out.pb_data as _) };
        Ok(plaintext)
    }
}

#[cfg(not(target_os = "windows"))]
mod dpapi {
    use super::StorageError;

    pub fn encrypt(data: &[u8]) -> Result<Vec<u8>, StorageError> {
        Ok(data.iter().map(|b| b ^ 0xAA).collect())
    }

    pub fn decrypt(ciphertext: &[u8]) -> Result<Vec<u8>, StorageError> {
        Ok(ciphertext.iter().map(|b| b ^ 0xAA).collect())
    }
}

/// Encrypts and writes the session data to `%APPDATA%\Cineforge\telegram_session.enc`.
pub fn save_encrypted_session(session_bytes: &[u8]) -> Result<(), StorageError> {
    let dir = get_storage_dir();
    fs::create_dir_all(&dir)?;

    let ciphertext = dpapi::encrypt(session_bytes)?;
    let session_file = get_session_file_path();
    fs::write(session_file, ciphertext)?;
    Ok(())
}

/// Reads and decrypts the session data from `%APPDATA%\Cineforge\telegram_session.enc`.
/// Returns `Ok(None)` if no session file exists.
pub fn load_encrypted_session() -> Result<Option<Vec<u8>>, StorageError> {
    let session_file = get_session_file_path();
    if !session_file.exists() {
        return Ok(None);
    }

    let ciphertext = fs::read(session_file)?;
    if ciphertext.is_empty() {
        return Ok(None);
    }

    let plaintext = dpapi::decrypt(&ciphertext)?;
    Ok(Some(plaintext))
}

/// Deletes the session file from `%APPDATA%\Cineforge\telegram_session.enc` upon logout/disconnect.
pub fn delete_session() -> Result<(), StorageError> {
    let session_file = get_session_file_path();
    if session_file.exists() {
        fs::remove_file(session_file)?;
    }
    Ok(())
}

/// Returns the path to the encrypted personal bot mapping file.
pub fn get_bot_mapping_file_path() -> PathBuf {
    get_storage_dir().join("telegram_bot.enc")
}

/// Checks whether an encrypted session file currently exists on disk.
pub fn has_session() -> bool {
    get_session_file_path().exists()
}

/// Encrypts and writes the durable bot mapping to `%APPDATA%\Cineforge\telegram_bot.enc`.
pub fn save_encrypted_bot_mapping(mapping_bytes: &[u8]) -> Result<(), StorageError> {
    let dir = get_storage_dir();
    fs::create_dir_all(&dir)?;

    let ciphertext = dpapi::encrypt(mapping_bytes)?;
    let bot_file = get_bot_mapping_file_path();
    fs::write(bot_file, ciphertext)?;
    Ok(())
}

/// Reads and decrypts the durable bot mapping from `%APPDATA%\Cineforge\telegram_bot.enc`.
pub fn load_encrypted_bot_mapping() -> Result<Option<Vec<u8>>, StorageError> {
    let bot_file = get_bot_mapping_file_path();
    if !bot_file.exists() {
        return Ok(None);
    }

    let ciphertext = fs::read(bot_file)?;
    if ciphertext.is_empty() {
        return Ok(None);
    }

    let plaintext = dpapi::decrypt(&ciphertext)?;
    Ok(Some(plaintext))
}

/// Deletes the local bot mapping cache from `%APPDATA%\Cineforge\telegram_bot.enc`.
pub fn delete_encrypted_bot_mapping() -> Result<(), StorageError> {
    let bot_file = get_bot_mapping_file_path();
    if bot_file.exists() {
        fs::remove_file(bot_file)?;
    }
    Ok(())
}

/// Checks whether an encrypted bot mapping currently exists on disk.
pub fn has_bot_mapping() -> bool {
    get_bot_mapping_file_path().exists()
}

pub static TEST_STORAGE_MUTEX: std::sync::Mutex<()> = std::sync::Mutex::new(());

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dpapi_encryption_roundtrip() {
        let original_data = b"cineforge_secure_telegram_session_payload_123456789";
        let encrypted = dpapi::encrypt(original_data).expect("encryption failed");
        
        // Assert ciphertext is non-empty and does not match plaintext
        assert!(!encrypted.is_empty());
        assert_ne!(encrypted.as_slice(), original_data);

        let decrypted = dpapi::decrypt(&encrypted).expect("decryption failed");
        assert_eq!(decrypted.as_slice(), original_data);
    }

    #[test]
    fn test_dpapi_bot_mapping_roundtrip() {
        let _guard = TEST_STORAGE_MUTEX.lock().unwrap();
        let _ = delete_encrypted_bot_mapping();

        let mapping = b"{\"user_id\":12345,\"bot_id\":67890,\"bot_username\":\"cf_12345_bot\"}";
        save_encrypted_bot_mapping(mapping).expect("save bot mapping failed");
        assert!(has_bot_mapping());

        let loaded = load_encrypted_bot_mapping().expect("load bot mapping failed").expect("missing mapping");
        assert_eq!(loaded.as_slice(), mapping);

        delete_encrypted_bot_mapping().expect("delete bot mapping failed");
        assert!(!has_bot_mapping());
    }
}
