"""Admin Suite - License Generation Engine.
DO NOT DISTRIBUTE.
Generates the AES-256 License Keys that users need to unlock the app.
"""
from cryptography.fernet import Fernet

def generate_key():
    print("====================================")
    print("   SHADOWCYPHER LICENSE GENERATOR   ")
    print("====================================")
    
    key = Fernet.generate_key()
    
    print("\n\033[92m[+] NEW LICENSE KEY GENERATED:\033[0m")
    print(key.decode())
    print("\nInstructions:")
    print("1. Send this exact string to the authorized user.")
    print("2. Tell them to paste it into the System Control > DRM Unlock tab.")
    print("3. Once submitted, their Arsenal will decrypt permanently.")

if __name__ == "__main__":
    generate_key()
