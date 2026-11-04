// ShadowCypher identity keys — everything here runs on the user's device.
//
// The account password never leaves the app. Argon2id stretches it into a
// master secret, which HKDF splits into:
//   loginSecret — sent to the auth server in place of the password
//   kek         — unlocks the user's OpenPGP private key; never sent anywhere
// The private key is also stored under a recovery phrase that is shown to the
// user once and never sent to the server.
//
// Requires the vendored `openpgp` and `hashwasm` globals.
(function (root) {
    'use strict';

    const KDF_V1 = Object.freeze({ v: 1, alg: 'argon2id', m: 65536, t: 3, p: 1 });
    const LIMITS = { mMin: 19456, mMax: 262144, tMin: 1, tMax: 10, pMin: 1, pMax: 4 };
    const PHRASE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    const PHRASE_BYTES = 20; // 160 bits → 32 characters
    const DOMAIN = 'shadowcypher.site';

    const enc = new TextEncoder();

    function lib(name) {
        const l = root[name];
        if (!l) throw new Error(`${name} library is not loaded`);
        return l;
    }

    function b64encode(bytes) {
        let s = '';
        for (const b of bytes) s += String.fromCharCode(b);
        return btoa(s);
    }

    function b64decode(str) {
        const s = atob(str);
        const out = new Uint8Array(s.length);
        for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
        return out;
    }

    function b64url(bytes) {
        return b64encode(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }

    function newKdfParams() {
        return { ...KDF_V1, salt: b64encode(crypto.getRandomValues(new Uint8Array(16))) };
    }

    // Params come from the server; refuse anything that could be a downgrade or a DoS.
    function validateKdf(kdf) {
        if (!kdf || kdf.v !== 1 || kdf.alg !== 'argon2id') throw new Error('Unsupported key-derivation parameters');
        const ints = ['m', 't', 'p'].every(k => Number.isInteger(kdf[k]));
        if (!ints
            || kdf.m < LIMITS.mMin || kdf.m > LIMITS.mMax
            || kdf.t < LIMITS.tMin || kdf.t > LIMITS.tMax
            || kdf.p < LIMITS.pMin || kdf.p > LIMITS.pMax) {
            throw new Error('Key-derivation parameters out of range');
        }
        const salt = b64decode(kdf.salt || '');
        if (salt.length < 16 || salt.length > 64) throw new Error('Invalid key-derivation salt');
        return salt;
    }

    async function hkdf(master, info) {
        const key = await crypto.subtle.importKey('raw', master, 'HKDF', false, ['deriveBits']);
        const bits = await crypto.subtle.deriveBits(
            { name: 'HKDF', hash: 'SHA-256', salt: new Uint8Array(0), info: enc.encode(info) },
            key, 256
        );
        return new Uint8Array(bits);
    }

    async function deriveSecrets(password, kdf) {
        const salt = validateKdf(kdf);
        const master = await lib('hashwasm').argon2id({
            password: enc.encode(password),
            salt,
            parallelism: kdf.p,
            iterations: kdf.t,
            memorySize: kdf.m,
            hashLength: 32,
            outputType: 'binary',
        });
        const [login, kek] = await Promise.all([
            hkdf(master, 'shadowcypher/auth/v1'),
            hkdf(master, 'shadowcypher/key-encryption/v1'),
        ]);
        master.fill(0);
        // 43 chars: within bcrypt's 72-byte limit on the auth server.
        return { loginSecret: b64url(login), kek: b64url(kek) };
    }

    function newRecoveryPhrase() {
        const bytes = crypto.getRandomValues(new Uint8Array(PHRASE_BYTES));
        let bits = 0, value = 0, out = '';
        for (const b of bytes) {
            value = (value << 8) | b;
            bits += 8;
            while (bits >= 5) {
                out += PHRASE_ALPHABET[(value >>> (bits - 5)) & 31];
                bits -= 5;
            }
        }
        return out.match(/.{4}/g).join('-');
    }

    function normalizePhrase(phrase) {
        const s = String(phrase || '').toUpperCase().replace(/[\s-]/g, '');
        if (s.length !== 32 || [...s].some(c => !PHRASE_ALPHABET.includes(c))) {
            throw new Error('That recovery phrase is not valid');
        }
        return s;
    }

    function emailFor(handle) {
        return `${handle}@${DOMAIN}`;
    }

    async function createIdentity(handle) {
        const openpgp = lib('openpgp');
        const { privateKey } = await openpgp.generateKey({
            type: 'ecc',
            userIDs: [{ name: handle, email: emailFor(handle) }],
            format: 'object',
        });
        return {
            privateKey,
            publicKey: privateKey.toPublic().armor(),
            fingerprint: privateKey.getFingerprint(),
        };
    }

    async function lockPrivateKey(privateKey, secret) {
        const locked = await lib('openpgp').encryptKey({ privateKey, passphrase: secret });
        return locked.armor();
    }

    async function unlockPrivateKey(armoredPrivateKey, secret) {
        const openpgp = lib('openpgp');
        const key = await openpgp.readPrivateKey({ armoredKey: armoredPrivateKey });
        return openpgp.decryptKey({ privateKey: key, passphrase: secret });
    }

    // Builds the bundle uploaded to the server. Both private-key copies are locked.
    async function buildBundle(privateKey, kek, recoveryPhrase) {
        return {
            public_key: privateKey.toPublic().armor(),
            fingerprint: privateKey.getFingerprint(),
            encrypted_private_key: await lockPrivateKey(privateKey, kek),
            recovery_private_key: recoveryPhrase
                ? await lockPrivateKey(privateKey, normalizePhrase(recoveryPhrase))
                : undefined,
        };
    }

    root.ScIdentity = Object.freeze({
        KDF_V1,
        newKdfParams,
        validateKdf,
        deriveSecrets,
        newRecoveryPhrase,
        normalizePhrase,
        createIdentity,
        lockPrivateKey,
        unlockPrivateKey,
        buildBundle,
    });
})(typeof window !== 'undefined' ? window : globalThis);
