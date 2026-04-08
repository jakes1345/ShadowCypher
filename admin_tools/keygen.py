"""Admin Key Generator - DO NOT DISTRIBUTE.
This script generates the Master Public/Private RSA keys for the Support Nexus.
"""

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os


def generate_admin_keys():
    import getpass

    print("[*] Generating 4096-bit RSA Admin Keys...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    public_key = private_key.public_key()

    passphrase = getpass.getpass("Enter passphrase for private key (empty for none): ")
    if passphrase:
        encryption = serialization.BestAvailableEncryption(passphrase.encode())
    else:
        encryption = serialization.NoEncryption()

    priv_path = "admin_private.pem"
    with open(priv_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=encryption,
            )
        )
    os.chmod(priv_path, 0o600)

    pub_path = "shadowcypher/core/admin_public.pem"
    with open(pub_path, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    print(f"[+] Private Key saved to {priv_path} (KEEP SECRET. DO NOT UPLOAD.)")
    print(f"[+] Public Key saved to {pub_path} (Shipped with the code.)")


if __name__ == "__main__":
    generate_admin_keys()
