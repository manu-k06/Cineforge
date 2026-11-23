fn main() {
    println!("cargo::rustc-check-cfg=cfg(mobile)");
    println!("cargo:rerun-if-env-changed=CINEFORGE_PROVISIONER_ONLY");
    println!("cargo:rerun-if-env-changed=RENDER");

    // When building the standalone provisioner helper (e.g. on Render),
    // skip the Tauri desktop build setup which checks for desktop streamer sidecars.
    if std::env::var("CINEFORGE_PROVISIONER_ONLY").is_ok() || std::env::var("RENDER").is_ok() {
        return;
    }

    tauri_build::build();
}
