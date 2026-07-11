import * as TweetNaCl from 'tweetnacl';
import { encodeBase64, decodeBase64 } from 'tweetnacl-util';

// ──────────────────────────────────────────────────────────────────────────────
// Legacy Keypair Functions (X25519 + TweetNaCl) — for 1-to-1 conversations
// ──────────────────────────────────────────────────────────────────────────────

export async function generateKeypair(): Promise<{privateKey: string, publicKey: string}> {
    const keypair = TweetNaCl.box.keyPair();
    return {
        privateKey: encodeBase64(keypair.secretKey),
        publicKey: encodeBase64(keypair.publicKey)
    };
}

export function deriveSharedSecret(privateKey: string, peerPublicKey: string): Uint8Array {
    // X25519 key exchange using TweetNaCl's box precomputation
    // This derives a shared secret from our private key and peer's public key
    const decodedPrivateKey = decodeBase64(privateKey);
    const decodedPeerPublicKey = decodeBase64(peerPublicKey);

    // Use box.before to precompute shared secret
    const sharedSecret = TweetNaCl.box.before(decodedPeerPublicKey, decodedPrivateKey);
    return sharedSecret;
}

export function encryptMessage(plaintext: string, sessionKey: string): {ciphertext: string, nonce: string} {
    const nonce = TweetNaCl.randomBytes(24);
    const message = new TextEncoder().encode(plaintext);
    const key = decodeBase64(sessionKey);
    const ciphertext = TweetNaCl.secretbox(message, nonce, key);
    return {
        ciphertext: encodeBase64(ciphertext),
        nonce: encodeBase64(nonce)
    };
}

export function decryptMessage(ciphertext: string, nonce: string, sessionKey: string): string {
    const plaintext = TweetNaCl.secretbox.open(
        decodeBase64(ciphertext),
        decodeBase64(nonce),
        decodeBase64(sessionKey)
    );
    if (!plaintext) throw new Error('Decryption failed');
    return new TextDecoder().decode(plaintext);
}

// ──────────────────────────────────────────────────────────────────────────────
// Group Chat Functions — AES-256-GCM (matches backend)
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Encrypt a group message using AES-256-GCM (Web Crypto API)
 * @param plaintext Message to encrypt
 * @param groupKeyHex Hex-encoded 32-byte AES-256 key
 * @returns Object with ciphertext (hex) and nonce (hex)
 */
export async function encryptGroupMessage(
    plaintext: string,
    groupKeyHex: string
): Promise<{ ciphertext: string; nonce: string }> {
    // Decode hex key to bytes
    const keyBytes = new Uint8Array(
        groupKeyHex.match(/.{1,2}/g)!.map(byte => parseInt(byte, 16))
    );

    // Import key for Web Crypto
    const key = await crypto.subtle.importKey(
        'raw',
        keyBytes,
        { name: 'AES-GCM' },
        false,
        ['encrypt']
    );

    // Generate 96-bit (12-byte) nonce
    const nonce = crypto.getRandomValues(new Uint8Array(12));

    // Encrypt plaintext
    const encoder = new TextEncoder();
    const encodedPlaintext = encoder.encode(plaintext);

    const ciphertext = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: nonce },
        key,
        encodedPlaintext
    );

    // Convert to hex strings (ciphertext includes auth tag)
    const ciphertextHex = Array.from(new Uint8Array(ciphertext))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
    const nonceHex = Array.from(nonce)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');

    return {
        ciphertext: ciphertextHex,
        nonce: nonceHex
    };
}

/**
 * Decrypt a group message using AES-256-GCM
 * @param ciphertextHex Hex-encoded ciphertext (includes 16-byte auth tag)
 * @param nonceHex Hex-encoded 12-byte nonce
 * @param groupKeyHex Hex-encoded 32-byte AES-256 key
 * @returns Decrypted plaintext
 */
export async function decryptGroupMessage(
    ciphertextHex: string,
    nonceHex: string,
    groupKeyHex: string
): Promise<string> {
    // Decode hex inputs to bytes
    const ciphertextBytes = new Uint8Array(
        ciphertextHex.match(/.{1,2}/g)!.map(byte => parseInt(byte, 16))
    );
    const nonceBytes = new Uint8Array(
        nonceHex.match(/.{1,2}/g)!.map(byte => parseInt(byte, 16))
    );
    const keyBytes = new Uint8Array(
        groupKeyHex.match(/.{1,2}/g)!.map(byte => parseInt(byte, 16))
    );

    // Import key for Web Crypto
    const key = await crypto.subtle.importKey(
        'raw',
        keyBytes,
        { name: 'AES-GCM' },
        false,
        ['decrypt']
    );

    try {
        const plaintext = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: nonceBytes },
            key,
            ciphertextBytes
        );

        const decoder = new TextDecoder();
        return decoder.decode(plaintext);
    } catch (error) {
        throw new Error(`Decryption failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
}

export async function fingerprint(publicKey: string): Promise<string> {
    // SHA256(pubkey)[:8] using Web Crypto API
    const publicKeyBytes = new Uint8Array(decodeBase64(publicKey));
    const hashBuffer = await crypto.subtle.digest('SHA-256', publicKeyBytes);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex.substring(0, 8);
}
