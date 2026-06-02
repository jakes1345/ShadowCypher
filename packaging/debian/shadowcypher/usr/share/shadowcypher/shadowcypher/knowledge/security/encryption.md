# Encryption Reference

## Symmetric Encryption

### AES (Advanced Encryption Standard)
- Block cipher; block size: 128 bits
- Key sizes: 128, 192, 256 bits
- Rounds: 10 (128-bit), 12 (192-bit), 14 (256-bit)
- **AES-256-GCM**: authenticated encryption (AEAD); most common secure choice
- **AES-256-CBC**: needs separate HMAC for integrity; vulnerable to padding oracle without it
- NIST-approved; used by US government for TOP SECRET (AES-256)

### ChaCha20-Poly1305
- Stream cipher + MAC; designed by DJB (Daniel J. Bernstein)
- Faster than AES on systems without hardware AES acceleration
- Used in TLS 1.3, WireGuard, Signal Protocol
- Resistant to timing side-channel attacks

### 3DES (Triple DES)
- Legacy; block size: 64 bits → Sweet32 birthday attack
- Deprecated by NIST 2023; do not use

### Blowfish / Twofish
- Blowfish: 64-bit block → Sweet32 vulnerable in some modes
- Twofish: 128-bit block; AES finalist; no known practical attacks

## Asymmetric Encryption

### RSA
- Security based on integer factorization
- Key sizes: 2048-bit minimum, 4096-bit recommended
- RSA-2048 considered safe through ~2030
- PKCS#1 v1.5 padding: vulnerable to Bleichenbacher attack → use OAEP
- Use RSA only for key exchange/signatures; not bulk encryption

### ECC (Elliptic Curve Cryptography)
- Based on discrete log problem on elliptic curves
- Smaller keys for equivalent security: ECC-256 ≈ RSA-3072
- **P-256 (secp256r1/prime256v1)**: NIST curve; widely supported; TLS
- **P-384**: higher security margin; used for SECRET/TOP SECRET
- **Curve25519**: DJB design; used in X25519 key exchange (Signal, WireGuard, SSH)
- **secp256k1**: Bitcoin signing curve

### DH / ECDH
- Diffie-Hellman key exchange; allows shared secret without transmitting it
- ECDH (Elliptic Curve DH): X25519 preferred
- Forward secrecy: ephemeral DH keys; past sessions can't be decrypted if long-term key compromised

## Hash Functions

| Algorithm | Output | Status | Notes |
|-----------|--------|--------|-------|
| MD5 | 128-bit | Broken | Collision attacks; still used for file integrity (non-security) |
| SHA-1 | 160-bit | Broken | Shattered attack (2017); Google produced collision |
| SHA-256 | 256-bit | Secure | SHA-2 family; widely used |
| SHA-384 | 384-bit | Secure | SHA-2 family |
| SHA-512 | 512-bit | Secure | SHA-2 family; better on 64-bit systems |
| SHA3-256 | 256-bit | Secure | SHA-3 (Keccak); different construction from SHA-2 |
| BLAKE2b | 512-bit | Secure | Faster than SHA-2 on modern hardware |
| BLAKE3 | 256-bit | Secure | Even faster; parallelizable |

## Password Hashing (PHFs)

Never store plaintext passwords. Use:
- **Argon2id**: winner of Password Hashing Competition 2015; OWASP recommended #1
  - Parameters: m=47104 (46MB), t=1, p=1 (minimum); increase m for higher security
- **bcrypt**: time-tested; max 72-byte input (hash prefix if longer)
  - Work factor: 12 minimum; 14+ for high-value accounts
- **scrypt**: memory-hard; N=32768, r=8, p=1 minimum
- **PBKDF2**: FIPS-approved; 600,000+ iterations with SHA-256 (OWASP 2023)

Never use: MD5, SHA-1, unsalted SHA-256/SHA-512 for passwords.

## Key Exchange and Protocols

### TLS 1.3 Cipher Suites
- TLS_AES_256_GCM_SHA384
- TLS_CHACHA20_POLY1305_SHA256
- TLS_AES_128_GCM_SHA256

### TLS 1.2 (acceptable, prefer 1.3)
- TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 (forward secret)
- TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
- Disable: RC4, 3DES, non-ECDHE cipher suites (no forward secrecy)

### SSH
- Key types: Ed25519 (preferred), ECDSA P-256, RSA 4096
- Key exchange: curve25519-sha256 preferred
- Ciphers: chacha20-poly1305@openssh.com, aes256-gcm@openssh.com
- MACs: hmac-sha2-256-etm@openssh.com

## Cryptographic Attacks

| Attack | Target | Description |
|--------|--------|-------------|
| Brute force | Any | Exhaustive key/password search |
| Birthday attack | Hash functions | Find collision; probability = 2^(n/2) for n-bit hash |
| Meet-in-the-middle | 2DES | Time-space tradeoff attack |
| Padding oracle | CBC mode | Decrypt ciphertext via padding error responses |
| Timing side-channel | RSA, AES | Measure execution time to infer key bits |
| Bleichenbacher | RSA PKCS#1 v1.5 | Adaptive chosen ciphertext attack |
| Sweet32 | 3DES/Blowfish | 64-bit block birthday collision with long sessions |
| BEAST | TLS 1.0 CBC | Block boundary manipulation |
| POODLE | SSL 3.0 | Padding oracle on downgraded connection |
| CRIME/BREACH | TLS compression | Compression oracle; disable TLS compression |

## Quantum Computing Threat

- Shor's algorithm breaks RSA and ECC
- Grover's algorithm halves symmetric key strength (AES-128 → ~64-bit effective)
- Timeline: "harvest now, decrypt later" attacks already occurring
- NIST PQC (Post-Quantum Cryptography) standards finalized 2024:
  - **ML-KEM (CRYSTALS-Kyber)**: key encapsulation
  - **ML-DSA (CRYSTALS-Dilithium)**: digital signatures
  - **SLH-DSA (SPHINCS+)**: stateless hash-based signatures
- Hybrid mode: combine classical + PQC for transition period
