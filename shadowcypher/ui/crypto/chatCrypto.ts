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
    const secret = TweetNaCl.box(
        new Uint8Array(0),
        decodeBase64(peerPublicKey),
        new Uint8Array(32),  // Dummy nonce
        decodeBase64(privateKey),
        decodeBase64(peerPublicKey)
    );
    return secret;
}

export function encryptMessage(plaintext: string, sessionKey: string): {ciphertext: string, nonce: string} {
    const nonce = TweetNaCl.randomBytes(24);
    const ciphertext = TweetNaCl.secretbox(
        encodeUTF8(plaintext),
        nonce,
        decodeBase64(sessionKey)
    );
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

export function fingerprint(publicKey: string): string {
    // SHA256(pubkey)[:8] - implement in browser
    const hash = sha256(publicKey);
    return hash.substring(0, 8);
}
