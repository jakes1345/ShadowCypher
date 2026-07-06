import * as TweetNaCl from 'tweetnacl';
import { decodeUTF8, encodeUTF8, encodeBase64, decodeBase64 } from 'tweetnacl-util';

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
    // @ts-ignore - tweetnacl-util types are loose
    const message = encodeUTF8(plaintext);
    const key = new Uint8Array(decodeBase64(sessionKey) as any);
    // @ts-ignore - tweetnacl types accept Uint8Array
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
    if (!plaintext) throw new Error("Decryption failed");
    return encodeUTF8(plaintext);
}

export async function fingerprint(publicKey: string): Promise<string> {
    // SHA256(pubkey)[:8] using Web Crypto API
    const publicKeyBytes = new Uint8Array(decodeBase64(publicKey) as any);
    const hashBuffer = await crypto.subtle.digest('SHA-256', publicKeyBytes);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex.substring(0, 8);
}
