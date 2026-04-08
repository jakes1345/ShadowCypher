"""Admin Suite - Ticket Decryption Engine.
DO NOT DISTRIBUTE.
Decrypts Base64 RSA-OAEP tickets received from users.
"""
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
import base64
import sys

def decrypt_ticket(b64_ticket):
    try:
        print("[*] Loading Master Private Key...")
        with open("admin_private.pem", "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
            )
            
        print("[*] Decrypting Secure Block...")
        ciphertext = base64.b64decode(b64_ticket)
        
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print("\n\033[92m[+] DECRYPTED MESSAGE:\033[0m")
        print("-" * 50)
        print(plaintext.decode())
        print("-" * 50)
        
    except Exception as e:
        print(f"\033[91m[!] FAILED TO DECRYPT: Incorrect Key or corrupted transmission ({e})\033[0m")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 decrypt_tickets.py <BASE64_CIPHERTEXT>")
        sys.exit(1)
    decrypt_ticket(sys.argv[1])
