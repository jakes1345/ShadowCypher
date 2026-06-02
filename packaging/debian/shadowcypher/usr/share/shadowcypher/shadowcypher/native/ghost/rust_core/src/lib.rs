//! ShadowCypher ghost-core — memory-safe ChaCha20-Poly1305 encryption
//! exported over the C ABI for Go / Python consumers.
//!
//! Wire format for `encrypt_signal`:
//!     hex(nonce[12] || ciphertext_with_tag)
//!
//! Key derivation:
//!     sha256(key_bytes) -> 32 raw bytes
//!
//! Callers MUST free returned strings with `free_signal`.

use chacha20poly1305::{
    aead::{Aead, KeyInit, OsRng},
    AeadCore, ChaCha20Poly1305, Nonce,
};
use sha2::{Digest, Sha256};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

/// Return a heap-allocated C string whose ownership is transferred to the caller.
/// The caller must free it with `free_signal`.
fn leak_cstring(s: &str) -> *mut c_char {
    match CString::new(s) {
        Ok(c) => c.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Safely copy a `*const c_char` into a Rust byte vector.
/// Returns None if `p` is null.
unsafe fn cstr_to_bytes(p: *const c_char) -> Option<Vec<u8>> {
    if p.is_null() {
        return None;
    }
    Some(CStr::from_ptr(p).to_bytes().to_vec())
}

fn derive_key(raw: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(raw);
    let digest = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&digest);
    out
}

/// Encrypt `data` with `key`. Returns hex(nonce || ciphertext_with_tag),
/// or a literal "ENCRYPTION_FAILURE" on any error path.
#[no_mangle]
pub extern "C" fn encrypt_signal(key: *const c_char, data: *const c_char) -> *mut c_char {
    let key_bytes = match unsafe { cstr_to_bytes(key) } {
        Some(b) => b,
        None => return leak_cstring("ENCRYPTION_FAILURE"),
    };
    let plaintext = match unsafe { cstr_to_bytes(data) } {
        Some(b) => b,
        None => return leak_cstring("ENCRYPTION_FAILURE"),
    };

    let derived = derive_key(&key_bytes);
    let cipher = ChaCha20Poly1305::new(&derived.into());
    let nonce = ChaCha20Poly1305::generate_nonce(&mut OsRng);

    let ciphertext = match cipher.encrypt(&nonce, plaintext.as_ref()) {
        Ok(ct) => ct,
        Err(_) => return leak_cstring("ENCRYPTION_FAILURE"),
    };

    let mut combined = Vec::with_capacity(nonce.len() + ciphertext.len());
    combined.extend_from_slice(&nonce);
    combined.extend_from_slice(&ciphertext);
    leak_cstring(&hex::encode(combined))
}

/// Decrypt hex(nonce || ciphertext_with_tag) with `key`.
/// Returns the plaintext or "DECRYPTION_FAILURE" on any error.
#[no_mangle]
pub extern "C" fn decrypt_signal(key: *const c_char, hex_data: *const c_char) -> *mut c_char {
    let key_bytes = match unsafe { cstr_to_bytes(key) } {
        Some(b) => b,
        None => return leak_cstring("DECRYPTION_FAILURE"),
    };
    let hex_bytes = match unsafe { cstr_to_bytes(hex_data) } {
        Some(b) => b,
        None => return leak_cstring("DECRYPTION_FAILURE"),
    };

    let combined = match hex::decode(&hex_bytes) {
        Ok(c) => c,
        Err(_) => return leak_cstring("DECRYPTION_FAILURE"),
    };
    if combined.len() < 12 + 16 {
        // 12-byte nonce + 16-byte Poly1305 tag is the minimum
        return leak_cstring("DECRYPTION_FAILURE");
    }
    let (nonce_bytes, ciphertext) = combined.split_at(12);
    let nonce = Nonce::from_slice(nonce_bytes);

    let derived = derive_key(&key_bytes);
    let cipher = ChaCha20Poly1305::new(&derived.into());

    match cipher.decrypt(nonce, ciphertext) {
        Ok(pt) => match CString::new(pt) {
            Ok(c) => c.into_raw(),
            Err(_) => leak_cstring("DECRYPTION_FAILURE"),
        },
        Err(_) => leak_cstring("DECRYPTION_FAILURE"),
    }
}

/// Free a C string previously returned by `encrypt_signal` or `decrypt_signal`.
#[no_mangle]
pub extern "C" fn free_signal(s: *mut c_char) {
    if s.is_null() {
        return;
    }
    unsafe {
        let _ = CString::from_raw(s);
    }
}
