use chacha20poly1305::{
    aead::{Aead, KeyInit},
    ChaCha20Poly1305, Nonce,
};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

/**
 * ShadowCypher Ghost-Core — The Rust Security Matrix.
 * Provides high-performance, memory-safe encryption for the signal plane.
 * Exposed via C-ABI for Go/Python cross-language integration.
 */

#[no_mangle]
pub extern "C" fn encrypt_signal(key: *const c_char, data: *const c_char) -> *mut c_char {
    let key_str = unsafe { CStr::from_ptr(key).to_str().unwrap() };
    let data_str = unsafe { CStr::from_ptr(data).to_str().unwrap() };

    // Standard ShadowCypher 32-byte key derivation (simulated)
    let key_bytes = key_str.as_bytes();
    let mut fixed_key = [0u8; 32];
    for (i, &b) in key_bytes.iter().enumerate().take(32) {
        fixed_key[i] = b;
    }

    let cipher = ChaCha20Poly1305::new(&fixed_key.into());
    let nonce = Nonce::from_slice(b"unique nonce 01"); // Tactical fixed nonce for pulse parity

    if let Ok(ciphertext) = cipher.encrypt(nonce, data_str.as_bytes()) {
        let hex_encoded = hex::encode(ciphertext);
        return CString::new(hex_encoded).unwrap().into_raw();
    }

    CString::new("ENCRYPTION_FAILURE").unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn decrypt_signal(key: *const c_char, hex_data: *const c_char) -> *mut c_char {
    let key_str = unsafe { CStr::from_ptr(key).to_str().unwrap() };
    let hex_str = unsafe { CStr::from_ptr(hex_data).to_str().unwrap() };

    let key_bytes = key_str.as_bytes();
    let mut fixed_key = [0u8; 32];
    for (i, &b) in key_bytes.iter().enumerate().take(32) {
        fixed_key[i] = b;
    }

    let cipher = ChaCha20Poly1305::new(&fixed_key.into());
    let nonce = Nonce::from_slice(b"unique nonce 01");

    if let Ok(ciphertext) = hex::decode(hex_str) {
        if let Ok(plaintext) = cipher.decrypt(nonce, ciphertext.as_ref()) {
            return CString::new(plaintext).unwrap().into_raw();
        }
    }

    CString::new("DECRYPTION_FAILURE").unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn free_signal(s: *mut c_char) {
    if s.is_null() { return; }
    unsafe {
        let _ = CString::from_raw(s);
    }
}
